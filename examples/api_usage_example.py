import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


def api_request(method: str, endpoint: str, data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{API_PREFIX}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    try:
        if method == "GET":
            response = requests.get(url, params=params, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, params=params, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=data, params=params, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, params=params, headers=headers)
        else:
            return {"error": f"不支持的HTTP方法: {method}"}
        
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"请求失败: {str(e)}"}


def create_project_example():
    print("\n" + "=" * 60)
    print("示例1: 创建项目")
    print("=" * 60)
    
    project_data = {
        "name": "电商平台API测试",
        "description": "电商平台核心接口自动化测试",
        "owner": "测试组"
    }
    
    result = api_request("POST", "/projects", data=project_data)
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    if result.get("code") == 200 and result.get("data"):
        return result["data"]["id"]
    return None


def create_environment_example(project_id: int):
    print("\n" + "=" * 60)
    print("示例2: 创建环境配置")
    print("=" * 60)
    
    env_data = {
        "name": "测试环境",
        "project_id": project_id,
        "description": "功能测试环境",
        "base_url": "https://test-api.example.com",
        "is_default": True,
        "variables": [
            {"key": "app_id", "value": "test_app_001", "description": "应用ID"},
            {"key": "api_key", "value": "sk_test_123456", "is_secret": True, "description": "API密钥"},
            {"key": "timeout", "value": "30", "description": "超时时间"}
        ]
    }
    
    result = api_request("POST", "/environments", data=env_data)
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    if result.get("code") == 200 and result.get("data"):
        return result["data"]["id"]
    return None


def create_test_suite_example(project_id: int):
    print("\n" + "=" * 60)
    print("示例3: 创建测试套件")
    print("=" * 60)
    
    suite_data = {
        "name": "用户模块测试套件",
        "description": "用户注册、登录、信息查询相关接口测试",
        "project_id": project_id,
        "tags": ["用户模块", "核心功能"]
    }
    
    result = api_request("POST", "/test-suites", data=suite_data)
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    if result.get("code") == 200 and result.get("data"):
        return result["data"]["id"]
    return None


def create_test_case_example(suite_id: int):
    print("\n" + "=" * 60)
    print("示例4: 创建测试用例")
    print("=" * 60)
    
    case_data = {
        "name": "用户登录流程测试",
        "description": "验证用户登录接口的正确性",
        "test_suite_id": suite_id,
        "order": 1,
        "tags": ["登录", "高优先级"]
    }
    
    result = api_request("POST", "/test-cases", data=case_data)
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    if result.get("code") == 200 and result.get("data"):
        return result["data"]["id"]
    return None


def create_request_step_example(case_id: int):
    print("\n" + "=" * 60)
    print("示例5: 创建请求步骤")
    print("=" * 60)
    
    step_data = {
        "name": "用户登录请求",
        "test_case_id": case_id,
        "order": 1,
        "method": "POST",
        "url": "{{env.base_url}}/api/v1/auth/login",
        "headers": {"Content-Type": "application/json", "X-App-Id": "{{env.app_id}}"},
        "body": json.dumps({"username": "test_user", "password": "test123456"}),
        "body_type": "json",
        "extract_variables": {"access_token": "response_body.data.token"},
        "skip_on_failure": False,
        "timeout": 30
    }
    
    result = api_request("POST", "/request-steps", data=step_data)
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    if result.get("code") == 200 and result.get("data"):
        return result["data"]["id"]
    return None


def create_assertion_example(step_id: int):
    print("\n" + "=" * 60)
    print("示例6: 创建断言规则")
    print("=" * 60)
    
    assertions = [
        {
            "name": "验证响应状态码为200",
            "request_step_id": step_id,
            "assert_type": "response_status",
            "source": "response_status",
            "expected_value": "200",
            "comparator": "equals",
            "order": 1
        },
        {
            "name": "验证响应时间小于1秒",
            "request_step_id": step_id,
            "assert_type": "response_time",
            "source": "response_time",
            "expected_value": "1000",
            "comparator": "less_than",
            "order": 2
        },
        {
            "name": "验证响应包含access_token",
            "request_step_id": step_id,
            "assert_type": "response_body",
            "source": "response_body",
            "expression": "data.token",
            "comparator": "is_not_null",
            "order": 3
        },
        {
            "name": "验证响应码为0",
            "request_step_id": step_id,
            "assert_type": "response_body",
            "source": "response_body",
            "expression": "code",
            "expected_value": "0",
            "comparator": "equals",
            "order": 4
        }
    ]
    
    created_ids = []
    for assertion in assertions:
        result = api_request("POST", "/assertions", data=assertion)
        print(f"断言 '{assertion['name']}' 响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        if result.get("code") == 200 and result.get("data"):
            created_ids.append(result["data"]["id"])
    
    return created_ids


def create_task_example(project_id: int, suite_id: int, env_id: int):
    print("\n" + "=" * 60)
    print("示例7: 创建测试任务")
    print("=" * 60)
    
    task_data = {
        "name": "每日回归测试-用户模块",
        "project_id": project_id,
        "description": "每日凌晨执行用户模块回归测试",
        "task_type": "scheduled",
        "cron_expression": "0 0 2 * * ?",
        "test_suite_ids": [suite_id],
        "test_case_ids": [],
        "tags": ["日常回归"],
        "environment_id": env_id,
        "retry_count": 2,
        "retry_interval": 5,
        "run_parallel": False,
        "is_enabled": True
    }
    
    result = api_request("POST", "/tasks", data=task_data)
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    if result.get("code") == 200 and result.get("data"):
        return result["data"]["id"]
    return None


def create_notification_config_example(project_id: int):
    print("\n" + "=" * 60)
    print("示例8: 创建通知配置")
    print("=" * 60)
    
    notify_data = {
        "name": "测试失败钉钉通知",
        "project_id": project_id,
        "notify_type": "dingtalk",
        "notify_when": "on_failure",
        "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=your_token",
        "secret_key": "your_secret_key",
        "at_mobiles": ["13800138000"],
        "at_all": False,
        "assignees": ["张三", "李四"],
        "is_enabled": True
    }
    
    result = api_request("POST", "/notifications/configs", data=notify_data)
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    if result.get("code") == 200 and result.get("data"):
        return result["data"]["id"]
    return None


def run_task_example(task_id: int):
    print("\n" + "=" * 60)
    print("示例9: 立即执行任务")
    print("=" * 60)
    
    result = api_request("POST", f"/tasks/{task_id}/run")
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result


def query_report_example(record_id: int):
    print("\n" + "=" * 60)
    print("示例10: 查询执行报告")
    print("=" * 60)
    
    result = api_request("GET", f"/execution-records/{record_id}/report")
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result


def query_recent_issues_example(project_id: int):
    print("\n" + "=" * 60)
    print("示例11: 查询项目最近问题")
    print("=" * 60)
    
    result = api_request("GET", f"/execution-records/project/{project_id}/recent-issues", params={"days": 7})
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result


def query_project_statistics_example(project_id: int):
    print("\n" + "=" * 60)
    print("示例12: 查询项目统计数据")
    print("=" * 60)
    
    result = api_request("GET", f"/execution-records/project/{project_id}/statistics", params={"days": 30})
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result


def main():
    print("自动化测试后端服务 - API使用示例")
    print(f"服务地址: {BASE_URL}")
    print(f"API文档: {BASE_URL}/docs")
    
    print("\n请确保服务已启动，然后按回车键继续...")
    input()
    
    try:
        health_check = requests.get(f"{BASE_URL}/health")
        print(f"服务健康检查: {health_check.json()}")
    except requests.exceptions.RequestException:
        print("警告: 无法连接到服务，请先启动服务")
        print("启动命令: python run.py 或双击 start.bat")
        return
    
    print("\n" + "=" * 60)
    print("开始运行API示例")
    print("=" * 60)
    
    project_id = create_project_example()
    if not project_id:
        print("创建项目失败，终止示例")
        return
    
    env_id = create_environment_example(project_id)
    suite_id = create_test_suite_example(project_id)
    case_id = create_test_case_example(suite_id)
    step_id = create_request_step_example(case_id)
    assertion_ids = create_assertion_example(step_id)
    task_id = create_task_example(project_id, suite_id, env_id)
    notify_config_id = create_notification_config_example(project_id)
    
    print("\n" + "=" * 60)
    print("示例数据创建完成！")
    print(f"项目ID: {project_id}")
    print(f"环境ID: {env_id}")
    print(f"测试套件ID: {suite_id}")
    print(f"测试用例ID: {case_id}")
    print(f"请求步骤ID: {step_id}")
    print(f"断言数量: {len(assertion_ids)}")
    print(f"任务ID: {task_id}")
    print(f"通知配置ID: {notify_config_id}")
    print("=" * 60)
    
    print("\n其他常用API示例:")
    print("""
    # 查询项目列表
    GET /api/v1/projects?page=1&page_size=10
    
    # 查询测试套件列表
    GET /api/v1/test-suites?project_id={project_id}
    
    # 查询执行记录列表
    GET /api/v1/execution-records?project_id={project_id}&status=failed
    
    # 调试单个请求步骤
    POST /api/v1/request-steps/{step_id}/debug
    
    # 异步执行任务（不等待结果）
    POST /api/v1/tasks/{task_id}/run-async
    
    # 测试通知配置
    POST /api/v1/notifications/configs/{config_id}/test
    """)
    
    print("\n" + "=" * 60)
    print("示例运行完成！")
    print(f"请访问 {BASE_URL}/docs 查看完整的API文档")
    print("=" * 60)


if __name__ == "__main__":
    main()
