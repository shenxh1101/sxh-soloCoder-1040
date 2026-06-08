import re
import json
from typing import Any, Optional, Dict
from app.core.variable_replacer import VariableReplacer


class AssertionEngine:
    @classmethod
    def assert_(cls, assertion_type: str, source: str, expression: Optional[str], 
                expected_value: Optional[str], comparator: str, 
                response_data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[str]]:
        try:
            actual_value = None
            
            if assertion_type == "response_status":
                actual_value = response_data.get("status_code")
            elif assertion_type == "response_time":
                actual_value = response_data.get("duration")
            elif assertion_type == "response_body":
                actual_value = VariableReplacer.extract_value("response_body", expression, response_data.get("body", {}))
            elif assertion_type == "response_headers":
                actual_value = VariableReplacer.extract_value("response_headers", expression, response_data.get("headers", {}))
            else:
                actual_value = VariableReplacer.extract_value(source, expression, response_data)
            
            passed, error_msg = cls._compare(actual_value, expected_value, comparator)
            
            return passed, str(actual_value) if actual_value is not None else None, error_msg
            
        except Exception as e:
            return False, None, f"断言执行异常: {str(e)}"

    @classmethod
    def _compare(cls, actual: Any, expected: Optional[str], comparator: str) -> tuple[bool, Optional[str]]:
        try:
            if comparator == "equals":
                return cls._equals(actual, expected), None
            
            if comparator == "not_equals":
                return not cls._equals(actual, expected), None
            
            if comparator == "contains":
                return cls._contains(actual, expected), None
            
            if comparator == "not_contains":
                return not cls._contains(actual, expected), None
            
            if comparator == "greater_than":
                return cls._greater_than(actual, expected), None
            
            if comparator == "less_than":
                return cls._less_than(actual, expected), None
            
            if comparator == "greater_than_or_equal":
                return cls._greater_than_or_equal(actual, expected), None
            
            if comparator == "less_than_or_equal":
                return cls._less_than_or_equal(actual, expected), None
            
            if comparator == "matches":
                return cls._matches(actual, expected), None
            
            if comparator == "is_null":
                return actual is None, None
            
            if comparator == "is_not_null":
                return actual is not None, None
            
            if comparator == "is_empty":
                return cls._is_empty(actual), None
            
            if comparator == "is_not_empty":
                return not cls._is_empty(actual), None
            
            return False, f"不支持的比较器: {comparator}"
            
        except Exception as e:
            return False, f"比较异常: {str(e)}"

    @classmethod
    def _equals(cls, actual: Any, expected: Optional[str]) -> bool:
        if expected is None:
            return actual is None
        
        try:
            expected_parsed = json.loads(expected)
            if isinstance(expected_parsed, (int, float, bool)):
                return actual == expected_parsed
        except (json.JSONDecodeError, TypeError):
            pass
        
        return str(actual) == expected

    @classmethod
    def _contains(cls, actual: Any, expected: Optional[str]) -> bool:
        if expected is None:
            return False
        
        actual_str = str(actual) if actual is not None else ""
        return expected in actual_str

    @classmethod
    def _greater_than(cls, actual: Any, expected: Optional[str]) -> bool:
        try:
            actual_num = float(actual)
            expected_num = float(expected) if expected else 0
            return actual_num > expected_num
        except (TypeError, ValueError):
            return False

    @classmethod
    def _less_than(cls, actual: Any, expected: Optional[str]) -> bool:
        try:
            actual_num = float(actual)
            expected_num = float(expected) if expected else 0
            return actual_num < expected_num
        except (TypeError, ValueError):
            return False

    @classmethod
    def _greater_than_or_equal(cls, actual: Any, expected: Optional[str]) -> bool:
        try:
            actual_num = float(actual)
            expected_num = float(expected) if expected else 0
            return actual_num >= expected_num
        except (TypeError, ValueError):
            return False

    @classmethod
    def _less_than_or_equal(cls, actual: Any, expected: Optional[str]) -> bool:
        try:
            actual_num = float(actual)
            expected_num = float(expected) if expected else 0
            return actual_num <= expected_num
        except (TypeError, ValueError):
            return False

    @classmethod
    def _matches(cls, actual: Any, expected: Optional[str]) -> bool:
        if expected is None:
            return False
        
        actual_str = str(actual) if actual is not None else ""
        return bool(re.match(expected, actual_str))

    @classmethod
    def _is_empty(cls, actual: Any) -> bool:
        if actual is None:
            return True
        
        if isinstance(actual, (list, dict, str)):
            return len(actual) == 0
        
        return False
