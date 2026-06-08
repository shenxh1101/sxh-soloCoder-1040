import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.task import Task
from app.models.execution_record import ExecutionRecord
from app.models.environment import Environment
from app.core.test_runner import TestRunner
from app.core.notification_sender import NotificationSender
from app.models.notification import NotificationConfig, NotificationRecord


class TaskScheduler:
    _instance = None
    _scheduler: Optional[AsyncIOScheduler] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler(timezone=settings.SCHEDULER_TIMEZONE)

    def start(self):
        if not self._scheduler.running:
            self._scheduler.start()
            self._load_scheduled_tasks()

    def shutdown(self):
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown()

    def _load_scheduled_tasks(self):
        db = SessionLocal()
        try:
            tasks = db.query(Task).filter(
                Task.task_type == "scheduled",
                Task.is_enabled == True,
                Task.cron_expression.isnot(None)
            ).all()
            
            for task in tasks:
                self._add_scheduled_task(task)
        finally:
            db.close()

    def _add_scheduled_task(self, task: Task):
        job_id = f"scheduled_task_{task.id}"
        
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
        
        try:
            trigger = CronTrigger.from_crontab(task.cron_expression, timezone=settings.SCHEDULER_TIMEZONE)
            
            self._scheduler.add_job(
                self._execute_scheduled_task,
                trigger=trigger,
                id=job_id,
                args=[task.id],
                replace_existing=True
            )
            
            next_run = self._scheduler.get_job(job_id).next_run_time
            
            db = SessionLocal()
            try:
                task.next_run_at = next_run
                db.commit()
            finally:
                db.close()
                
        except Exception as e:
            print(f"添加定时任务失败: {task.name}, 错误: {str(e)}")

    def update_scheduled_task(self, task: Task):
        if task.task_type == "scheduled" and task.is_enabled and task.cron_expression:
            self._add_scheduled_task(task)
        else:
            self._remove_scheduled_task(task.id)

    def _remove_scheduled_task(self, task_id: int):
        job_id = f"scheduled_task_{task_id}"
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

    async def _execute_scheduled_task(self, task_id: int):
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task or not task.is_enabled:
                return
            
            await self._execute_task(task, trigger_type="scheduled", db=db)
            
            next_run = self._scheduler.get_job(f"scheduled_task_{task_id}")
            if next_run:
                task.next_run_at = next_run.next_run_time
                db.commit()
                
        except Exception as e:
            print(f"执行定时任务失败: {str(e)}")
        finally:
            db.close()

    async def _execute_task(self, task: Task, trigger_type: str = "manual", 
                           db: Session = None, override_params: Dict[str, Any] = None) -> ExecutionRecord:
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False

        try:
            task.last_run_at = datetime.now()
            db.commit()

            environment_id = override_params.get("environment_id") if override_params else task.environment_id
            environment = db.query(Environment).filter(Environment.id == environment_id).first() if environment_id else None

            execution_record = ExecutionRecord(
                task_id=task.id,
                project_id=task.project_id,
                environment_id=environment_id,
                trigger_type=trigger_type,
                status="running",
                total_cases=0,
                passed_cases=0,
                failed_cases=0,
                skipped_cases=0,
                pass_rate=0.0,
                total_duration=0.0
            )
            db.add(execution_record)
            db.flush()

            runner = TestRunner(db)
            
            if override_params and (override_params.get("test_suite_ids") or 
                                    override_params.get("test_case_ids") or 
                                    override_params.get("tags")):
                temp_task = Task(
                    id=task.id,
                    project_id=task.project_id,
                    test_suite_ids=override_params.get("test_suite_ids") or task.test_suite_ids,
                    test_case_ids=override_params.get("test_case_ids") or task.test_case_ids,
                    tags=override_params.get("tags") or task.tags
                )
                test_cases = runner.get_test_cases_for_task(temp_task)
            else:
                test_cases = runner.get_test_cases_for_task(task)

            execution_record.total_cases = len(test_cases)

            passed, failed, skipped, duration = await runner.run_test_cases(
                execution_record_id=execution_record.id,
                test_cases=test_cases,
                environment=environment,
                retry_count=task.retry_count,
                retry_interval=task.retry_interval,
                run_parallel=task.run_parallel
            )

            execution_record.passed_cases = passed
            execution_record.failed_cases = failed
            execution_record.skipped_cases = skipped
            execution_record.total_duration = duration
            execution_record.pass_rate = (passed / len(test_cases) * 100) if test_cases else 0.0
            execution_record.status = "passed" if failed == 0 and skipped < len(test_cases) else "failed"
            execution_record.finished_at = datetime.now()

            db.commit()
            db.refresh(execution_record)

            await self._handle_notifications(execution_record, db)

            return execution_record

        except Exception as e:
            execution_record.status = "error"
            execution_record.error_message = str(e)
            execution_record.finished_at = datetime.now()
            db.commit()
            raise
        finally:
            if should_close:
                db.close()

    async def run_task_now(self, task_id: int, override_params: Dict[str, Any] = None) -> int:
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise ValueError("任务不存在")
            
            execution_record = await self._execute_task(task, trigger_type="manual", db=db, override_params=override_params)
            
            return execution_record.id
        finally:
            db.close()

    async def _handle_notifications(self, execution_record: ExecutionRecord, db: Session):
        try:
            configs = db.query(NotificationConfig).filter(
                NotificationConfig.project_id == execution_record.project_id,
                NotificationConfig.is_enabled == True
            ).all()

            failed_steps = []
            for case_result in execution_record.case_results:
                for step_result in case_result.step_results:
                    if step_result.status == "failed":
                        failed_steps.append({
                            "step_name": step_result.request_step_name,
                            "error_message": step_result.error_message,
                            "request_url": step_result.request_url,
                            "response_status": step_result.response_status,
                            "response_body_summary": step_result.response_body_summary
                        })

            for config in configs:
                should_notify = False
                
                if config.notify_when == "always":
                    should_notify = True
                elif config.notify_when == "on_failure" and execution_record.status in ["failed", "error"]:
                    should_notify = True

                if should_notify:
                    try:
                        result = await NotificationSender.send_notification(
                            config=config,
                            execution_record=execution_record,
                            failed_steps=failed_steps
                        )

                        notify_record = NotificationRecord(
                            notification_config_id=config.id,
                            execution_record_id=execution_record.id,
                            project_id=execution_record.project_id,
                            title="自动化测试执行结果通知",
                            content=result.get("error", "发送成功"),
                            notify_type=config.notify_type,
                            status="sent" if result.get("success") else "failed",
                            error_message=result.get("error"),
                            assignees=config.assignees or [],
                            sent_at=datetime.now()
                        )
                        db.add(notify_record)
                    except Exception as e:
                        notify_record = NotificationRecord(
                            notification_config_id=config.id,
                            execution_record_id=execution_record.id,
                            project_id=execution_record.project_id,
                            title="自动化测试执行结果通知",
                            content=f"通知发送异常: {str(e)}",
                            notify_type=config.notify_type,
                            status="failed",
                            error_message=str(e),
                            assignees=config.assignees or []
                        )
                        db.add(notify_record)

            db.commit()
        except Exception as e:
            print(f"处理通知失败: {str(e)}")
            db.rollback()


scheduler = TaskScheduler()
