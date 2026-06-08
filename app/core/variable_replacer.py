import re
import json
from typing import Dict, Any, Optional
from jinja2 import Template


class VariableReplacer:
    VARIABLE_PATTERN = r'\{\{\s*([\w\.]+)\s*\}\}'

    @classmethod
    def replace_variables(cls, value: Any, variables: Dict[str, Any]) -> Any:
        if value is None:
            return None
        
        if isinstance(value, str):
            return cls._replace_string(value, variables)
        
        if isinstance(value, dict):
            return {k: cls.replace_variables(v, variables) for k, v in value.items()}
        
        if isinstance(value, list):
            return [cls.replace_variables(item, variables) for item in value]
        
        return value

    @classmethod
    def _replace_string(cls, text: str, variables: Dict[str, Any]) -> str:
        def replacer(match):
            var_name = match.group(1)
            value = cls._get_nested_value(variables, var_name)
            return str(value) if value is not None else match.group(0)
        
        try:
            template = Template(text)
            return template.render(**variables)
        except Exception:
            return re.sub(cls.VARIABLE_PATTERN, replacer, text)

    @classmethod
    def _get_nested_value(cls, data: Dict[str, Any], key_path: str) -> Optional[Any]:
        keys = key_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value

    @classmethod
    def extract_value(cls, source: str, expression: Optional[str], data: Dict[str, Any]) -> Optional[Any]:
        try:
            if not expression:
                return None
            
            if source == "response_body":
                if '.' in expression:
                    return cls._get_nested_value(data, expression)
                return data.get(expression)
            
            if source == "response_headers":
                return data.get(expression)
            
            if source == "response_status":
                return data.get("status_code")
            
            if source == "response_time":
                return data.get("duration")
            
            return None
        except Exception as e:
            return None

    @classmethod
    def parse_json_body(cls, body: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(body) if body else None
        except (json.JSONDecodeError, TypeError):
            return None
