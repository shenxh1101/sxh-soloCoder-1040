import httpx
import json
import time
import hashlib
import base64
import hmac
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.notification import NotificationConfig, NotificationRecord
from app.models.execution_record import ExecutionRecord


class NotificationSender:
    @classmethod
    async def send_notification(cls, config: NotificationConfig, execution_record: ExecutionRecord,
                                failed_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        title = cls._build_title(execution_record)
        content = cls._build_content(execution_record, failed_steps)
        
        notify_result = {
            "success": False,
            "error": None
        }

        try:
            if config.notify_type == "dingtalk":
                notify_result = await cls._send_dingtalk(config, title, content)
            elif config.notify_type == "wechat":
                notify_result = await cls._send_wechat(config, title, content)
            elif config.notify_type == "webhook":
                notify_result = await cls._send_webhook(config, title, content, execution_record)
            elif config.notify_type == "email":
                notify_result = {"success": True, "info": "邮件通知需配置SMTP服务"}
            else:
                notify_result["error"] = f"不支持的通知类型: {config.notify_type}"
        except Exception as e:
            notify_result["error"] = f"发送通知异常: {str(e)}"

        return notify_result

    @classmethod
    def _build_title(cls, execution_record: ExecutionRecord) -> str:
        status_emoji = "✅" if execution_record.status == "passed" else "❌"
        return f"{status_emoji} 自动化测试执行结果 - {execution_record.status.upper()}"

    @classmethod
    def _build_content(cls, execution_record: ExecutionRecord, failed_steps: List[Dict[str, Any]]) -> str:
        project_name = execution_record.project.name if execution_record.project else "未知项目"
        env_name = execution_record.environment.name if execution_record.environment else "默认环境"
        
        content_lines = [
            f"**项目**: {project_name}",
            f"**环境**: {env_name}",
            f"**触发方式**: {execution_record.trigger_type}",
            f"**执行时间**: {execution_record.started_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**总用例数**: {execution_record.total_cases}",
            f"**通过**: {execution_record.passed_cases} | **失败**: {execution_record.failed_cases} | **跳过**: {execution_record.skipped_cases}",
            f"**通过率**: {execution_record.pass_rate:.2f}%",
            f"**总耗时**: {execution_record.total_duration:.2f}ms"
        ]

        if failed_steps:
            content_lines.append("\n**失败步骤**:")
            for i, step in enumerate(failed_steps[:5], 1):
                content_lines.append(f"\n{i}. {step.get('step_name', '未知步骤')}")
                content_lines.append(f"   错误: {step.get('error_message', '未知错误')}")
                if step.get('request_url'):
                    content_lines.append(f"   URL: {step.get('request_url')}")
                if step.get('response_status'):
                    content_lines.append(f"   状态码: {step.get('response_status')}")
            
            if len(failed_steps) > 5:
                content_lines.append(f"\n... 还有 {len(failed_steps) - 5} 个失败步骤")

        if execution_record.retry_attempt > 0:
            content_lines.append(f"\n**重试次数**: {execution_record.retry_attempt}")

        return "\n".join(content_lines)

    @classmethod
    async def _send_dingtalk(cls, config: NotificationConfig, title: str, content: str) -> Dict[str, Any]:
        if not config.webhook_url:
            return {"success": False, "error": "缺少Webhook地址"}

        webhook_url = config.webhook_url
        timestamp = str(round(time.time() * 1000))
        
        if config.secret_key:
            sign = cls._generate_dingtalk_sign(timestamp, config.secret_key)
            webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"### {title}\n\n{content}"
            },
            "at": {
                "atMobiles": config.at_mobiles or [],
                "isAtAll": config.at_all or False
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(webhook_url, json=payload)
                result = response.json()
                
                if result.get("errcode") == 0:
                    return {"success": True}
                else:
                    return {"success": False, "error": result.get("errmsg", "钉钉推送失败")}
        except Exception as e:
            return {"success": False, "error": f"钉钉推送异常: {str(e)}"}

    @classmethod
    def _generate_dingtalk_sign(cls, timestamp: str, secret: str) -> str:
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(secret.encode(), string_to_sign.encode(), digestmod=hashlib.sha256).digest()
        return base64.b64encode(hmac_code).decode()

    @classmethod
    async def _send_wechat(cls, config: NotificationConfig, title: str, content: str) -> Dict[str, Any]:
        if not config.webhook_url:
            return {"success": False, "error": "缺少Webhook地址"}

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"## {title}\n\n{content}",
                "mentioned_mobile_list": config.at_mobiles or []
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(config.webhook_url, json=payload)
                result = response.json()
                
                if result.get("errcode") == 0:
                    return {"success": True}
                else:
                    return {"success": False, "error": result.get("errmsg", "企业微信推送失败")}
        except Exception as e:
            return {"success": False, "error": f"企业微信推送异常: {str(e)}"}

    @classmethod
    async def _send_webhook(cls, config: NotificationConfig, title: str, content: str,
                            execution_record: ExecutionRecord) -> Dict[str, Any]:
        if not config.webhook_url:
            return {"success": False, "error": "缺少Webhook地址"}

        payload = {
            "title": title,
            "content": content,
            "execution_record_id": execution_record.id,
            "project_id": execution_record.project_id,
            "status": execution_record.status,
            "pass_rate": execution_record.pass_rate,
            "total_cases": execution_record.total_cases,
            "passed_cases": execution_record.passed_cases,
            "failed_cases": execution_record.failed_cases,
            "total_duration": execution_record.total_duration,
            "started_at": execution_record.started_at.isoformat() if execution_record.started_at else None,
            "assignees": config.assignees or []
        }

        headers = {"Content-Type": "application/json"}
        if config.secret_key:
            headers["X-Notification-Secret"] = config.secret_key

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(config.webhook_url, json=payload, headers=headers)
                
                if 200 <= response.status_code < 300:
                    return {"success": True}
                else:
                    return {"success": False, "error": f"Webhook推送失败，状态码: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"Webhook推送异常: {str(e)}"}
