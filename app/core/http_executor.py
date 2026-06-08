import httpx
import time
import json
from typing import Dict, Any, Optional, Tuple
from app.config import settings
from app.core.variable_replacer import VariableReplacer
from app.models.request_step import RequestStep


class HttpExecutor:
    @classmethod
    async def execute(cls, step: RequestStep, variables: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        
        url = VariableReplacer.replace_variables(step.url, variables)
        method = step.method.upper()
        headers = VariableReplacer.replace_variables(step.headers or {}, variables)
        params = VariableReplacer.replace_variables(step.params or {}, variables)
        body = VariableReplacer.replace_variables(step.body, variables)
        
        timeout = step.timeout or settings.REQUEST_TIMEOUT
        
        request_info = {
            "url": url,
            "method": method,
            "headers": headers,
            "params": params,
            "body": body
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                request_kwargs = cls._build_request_kwargs(method, headers, params, body, step.body_type)
                
                response = await client.request(method, url, **request_kwargs)
                
                duration = round((time.time() - start_time) * 1000, 2)
                
                response_body = cls._parse_response_body(response)
                response_body_summary = cls._summarize_response(response_body)
                
                result = {
                    "success": True,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_body,
                    "body_raw": response.text,
                    "body_summary": response_body_summary,
                    "duration": duration,
                    "request": request_info,
                    "error": None
                }
                
                return result
                
        except httpx.TimeoutException as e:
            duration = round((time.time() - start_time) * 1000, 2)
            return {
                "success": False,
                "status_code": None,
                "headers": {},
                "body": None,
                "body_raw": None,
                "body_summary": None,
                "duration": duration,
                "request": request_info,
                "error": f"请求超时: {str(e)}"
            }
            
        except httpx.RequestError as e:
            duration = round((time.time() - start_time) * 1000, 2)
            return {
                "success": False,
                "status_code": None,
                "headers": {},
                "body": None,
                "body_raw": None,
                "body_summary": None,
                "duration": duration,
                "request": request_info,
                "error": f"请求异常: {str(e)}"
            }
            
        except Exception as e:
            duration = round((time.time() - start_time) * 1000, 2)
            return {
                "success": False,
                "status_code": None,
                "headers": {},
                "body": None,
                "body_raw": None,
                "body_summary": None,
                "duration": duration,
                "request": request_info,
                "error": f"执行异常: {str(e)}"
            }

    @classmethod
    def _build_request_kwargs(cls, method: str, headers: Dict[str, Any], 
                               params: Dict[str, Any], body: Optional[str], 
                               body_type: str) -> Dict[str, Any]:
        kwargs = {
            "headers": headers,
            "params": params
        }
        
        if method in ["POST", "PUT", "PATCH"] and body:
            if body_type == "json":
                try:
                    kwargs["json"] = json.loads(body)
                except json.JSONDecodeError:
                    kwargs["content"] = body
                    if "Content-Type" not in headers:
                        kwargs["headers"]["Content-Type"] = "application/json"
            elif body_type == "form":
                kwargs["data"] = body
                if "Content-Type" not in headers:
                    kwargs["headers"]["Content-Type"] = "application/x-www-form-urlencoded"
            elif body_type == "xml":
                kwargs["content"] = body
                if "Content-Type" not in headers:
                    kwargs["headers"]["Content-Type"] = "application/xml"
            else:
                kwargs["content"] = body
        
        return kwargs

    @classmethod
    def _parse_response_body(cls, response: httpx.Response) -> Any:
        content_type = response.headers.get("content-type", "")
        
        if "application/json" in content_type:
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
        
        if "application/xml" in content_type or "text/xml" in content_type:
            return response.text
        
        if "text/" in content_type:
            return response.text
        
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text

    @classmethod
    def _summarize_response(cls, response_body: Any, max_length: int = 500) -> str:
        if response_body is None:
            return ""
        
        if isinstance(response_body, dict):
            summary = json.dumps(response_body, ensure_ascii=False)
        elif isinstance(response_body, list):
            summary = json.dumps(response_body, ensure_ascii=False)
        else:
            summary = str(response_body)
        
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary

    @classmethod
    def extract_variables(cls, extract_config: Dict[str, str], response_data: Dict[str, Any]) -> Dict[str, Any]:
        extracted = {}
        
        for var_name, expression in extract_config.items():
            try:
                if expression.startswith("response_body."):
                    expr = expression.replace("response_body.", "", 1)
                    value = VariableReplacer.extract_value("response_body", expr, response_data)
                elif expression.startswith("response_headers."):
                    expr = expression.replace("response_headers.", "", 1)
                    value = response_data.get("headers", {}).get(expr)
                elif expression == "response_status":
                    value = response_data.get("status_code")
                else:
                    value = VariableReplacer.extract_value("response_body", expression, response_data)
                
                if value is not None:
                    extracted[var_name] = value
            except Exception:
                continue
        
        return extracted
