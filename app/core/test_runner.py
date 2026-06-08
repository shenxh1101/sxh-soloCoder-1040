import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.test_suite import TestSuite
from app.models.test_case import TestCase
from app.models.request_step import RequestStep
from app.models.assertion import Assertion
from app.models.execution_record import ExecutionRecord, CaseResult, StepResult
from app.models.environment import Environment, EnvironmentVariable
from app.models.task import Task

from app.core.http_executor import HttpExecutor
from app.core.assertion_engine import AssertionEngine
from app.core.variable_replacer import VariableReplacer
from app.schemas.execution_record import AssertionResult as AssertionResultSchema


class TestRunner:
    def __init__(self, db: Session):
        self.db = db

    async def run_test_cases(self, execution_record_id: int, test_cases: List[TestCase],
                            environment: Optional[Environment] = None,
                            retry_count: int = 0, retry_interval: int = 5,
                            run_parallel: bool = False) -> Tuple[int, int, int, float]:
        variables = self._build_environment_variables(environment)
        
        total_cases = len(test_cases)
        passed_cases = 0
        failed_cases = 0
        skipped_cases = 0
        total_duration = 0.0

        if run_parallel:
            tasks = [self._run_single_case(execution_record_id, case, variables, retry_count, retry_interval) 
                    for case in test_cases]
            results = await asyncio.gather(*tasks)
            
            for passed, duration in results:
                if passed is None:
                    skipped_cases += 1
                elif passed:
                    passed_cases += 1
                else:
                    failed_cases += 1
                total_duration += duration
        else:
            for case in test_cases:
                passed, duration = await self._run_single_case(
                    execution_record_id, case, variables, retry_count, retry_interval
                )
                if passed is None:
                    skipped_cases += 1
                elif passed:
                    passed_cases += 1
                else:
                    failed_cases += 1
                total_duration += duration

        return passed_cases, failed_cases, skipped_cases, total_duration

    async def _run_single_case(self, execution_record_id: int, test_case: TestCase,
                              variables: Dict[str, Any], retry_count: int = 0,
                              retry_interval: int = 5) -> Tuple[Optional[bool], float]:
        case_start_time = time.time()
        
        case_variables = variables.copy()
        case_variables["test_case"] = {"id": test_case.id, "name": test_case.name}
        
        case_result = CaseResult(
            execution_record_id=execution_record_id,
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            status="running",
            duration=0.0
        )
        self.db.add(case_result)
        self.db.flush()

        request_steps = sorted(test_case.request_steps, key=lambda s: s.order)
        
        if not request_steps:
            case_result.status = "skipped"
            case_result.duration = round((time.time() - case_start_time) * 1000, 2)
            self.db.commit()
            return None, case_result.duration

        case_passed = True
        case_error = None

        for step in request_steps:
            step_passed, step_duration, error_msg = await self._run_step_with_retry(
                case_result.id, step, case_variables, retry_count, retry_interval
            )
            
            if not step_passed and not step.skip_on_failure:
                case_passed = False
                case_error = error_msg
                break

        case_result.status = "passed" if case_passed else "failed"
        case_result.duration = round((time.time() - case_start_time) * 1000, 2)
        case_result.error_message = case_error
        self.db.commit()

        return case_passed, case_result.duration

    async def _run_step_with_retry(self, case_result_id: int, step: RequestStep,
                                   variables: Dict[str, Any], max_retries: int = 0,
                                   retry_interval: int = 5) -> Tuple[bool, float, Optional[str]]:
        last_error = None
        total_duration = 0.0

        for attempt in range(max_retries + 1):
            step_passed, step_duration, error_msg = await self._run_single_step(
                case_result_id, step, variables, attempt
            )
            total_duration = step_duration

            if step_passed:
                return True, total_duration, None
            
            last_error = error_msg
            
            if attempt < max_retries:
                await asyncio.sleep(retry_interval)

        return False, total_duration, last_error

    async def _run_single_step(self, case_result_id: int, step: RequestStep,
                               variables: Dict[str, Any], attempt: int = 0) -> Tuple[bool, float, Optional[str]]:
        step_start_time = time.time()
        
        step_variables = variables.copy()
        step_variables["step"] = {"id": step.id, "name": step.name, "attempt": attempt}
        
        response_data = await HttpExecutor.execute(step, step_variables)
        step_duration = round((time.time() - step_start_time) * 1000, 2)

        assertion_results = []
        all_assertions_passed = True

        assertions = sorted(step.assertions, key=lambda a: a.order)
        
        for assertion in assertions:
            passed, actual_value, error_msg = AssertionEngine.assert_(
                assertion.assert_type,
                assertion.source,
                assertion.expression,
                assertion.expected_value,
                assertion.comparator,
                response_data
            )
            
            if not passed:
                all_assertions_passed = False
            
            assertion_results.append(
                AssertionResultSchema(
                    assertion_id=assertion.id,
                    assertion_name=assertion.name,
                    passed=passed,
                    actual_value=actual_value,
                    expected_value=assertion.expected_value,
                    error_message=error_msg
                ).model_dump()
            )

        step_passed = response_data.get("success", False) and all_assertions_passed
        
        extracted = {}
        if step_passed and step.extract_variables:
            extracted = HttpExecutor.extract_variables(step.extract_variables, response_data)
            variables.update(extracted)

        error_msg = None
        if not response_data.get("success", False):
            error_msg = response_data.get("error")
        elif not all_assertions_passed:
            failed_assertions = [r for r in assertion_results if not r["passed"]]
            if failed_assertions:
                error_msg = failed_assertions[0]["error_message"]

        step_result = StepResult(
            case_result_id=case_result_id,
            request_step_id=step.id,
            request_step_name=step.name,
            status="passed" if step_passed else "failed",
            duration=step_duration,
            request_url=response_data.get("request", {}).get("url"),
            request_method=response_data.get("request", {}).get("method"),
            request_headers=response_data.get("request", {}).get("headers"),
            request_body=response_data.get("request", {}).get("body"),
            response_status=response_data.get("status_code"),
            response_headers=response_data.get("headers"),
            response_body=response_data.get("body_raw"),
            response_body_summary=response_data.get("body_summary"),
            error_message=error_msg,
            assertion_results=assertion_results,
            extracted_variables=extracted
        )
        self.db.add(step_result)
        self.db.flush()

        return step_passed, step_duration, error_msg

    def _build_environment_variables(self, environment: Optional[Environment]) -> Dict[str, Any]:
        variables = {"env": {}}
        
        if environment:
            variables["env"]["base_url"] = environment.base_url
            variables["env"]["name"] = environment.name
            
            for var in environment.variables:
                variables["env"][var.key] = var.value

        variables["global"] = {
            "timestamp": int(time.time()),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return variables

    def get_test_cases_for_task(self, task: Task) -> List[TestCase]:
        from sqlalchemy import or_

        query = self.db.query(TestCase).join(TestCase.test_suite)
        
        conditions = []
        
        if task.test_suite_ids:
            conditions.append(TestCase.test_suite_id.in_(task.test_suite_ids))
        
        if task.test_case_ids:
            conditions.append(TestCase.id.in_(task.test_case_ids))
        
        if conditions:
            query = query.filter(or_(*conditions))
        else:
            query = query.filter(TestSuite.project_id == task.project_id)
        
        query = query.order_by(TestSuite.id, TestCase.order)
        
        test_cases = query.all()
        
        if task.tags:
            task_tags = set(tag.lower() for tag in task.tags)
            filtered_cases = []
            for case in test_cases:
                case_tags = set(tag.lower() for tag in (case.tags or []))
                suite_tags = set(tag.lower() for tag in (case.test_suite.tags or []))
                if task_tags & case_tags or task_tags & suite_tags:
                    filtered_cases.append(case)
            return filtered_cases
        
        return test_cases
