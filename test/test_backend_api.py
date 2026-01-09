"""
测试后端API (backend_api.py)

此测试文件使用:
- test/patterns/test.json 中的测试计划
- test/test_fuction/get_daily_stats.py 中的工具函数
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from httpx import AsyncClient, ASGITransport

from front.backend_api import app, executor_manager, setup_test_tools, setup_llm_factory
from test.test_fuction.get_daily_stats import get_daily_stats


# =============================================================================
# 测试配置
# =============================================================================

@pytest.fixture(scope="session")
def test_plan():
    """加载测试计划"""
    test_json_path = project_root / "test" / "patterns" / "test.json"
    with open(test_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["test1"]


@pytest.fixture(scope="session", autouse=True)
def setup_backend():
    """设置后端环境"""
    # 注册测试工具
    executor_manager.register_tool("get_daily_stats", get_daily_stats)
    
    # 设置 LLM 工厂（使用环境变量中的 API Key）
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key:
        setup_llm_factory(api_key=api_key)
    else:
        print("⚠️  警告: 未设置 API Key，LLM 功能可能无法使用")
    
    yield
    
    # 清理
    executor_manager.executors.clear()


@pytest.fixture
async def client():
    """创建测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =============================================================================
# 基础 API 测试
# =============================================================================

@pytest.mark.asyncio
async def test_root_endpoint(client):
    """测试根路径健康检查"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "service" in data
    assert "version" in data
    print("✅ 根路径测试通过")


@pytest.mark.asyncio
async def test_list_tools(client):
    """测试列出工具"""
    response = await client.get("/api/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    
    # 检查是否包含我们注册的工具
    tool_names = [tool["name"] for tool in data["tools"]]
    assert "get_daily_stats" in tool_names
    print(f"✅ 工具列表测试通过，共 {len(tool_names)} 个工具")


# =============================================================================
# 执行器生命周期测试
# =============================================================================

@pytest.mark.asyncio
async def test_executor_lifecycle(client, test_plan):
    """测试执行器完整生命周期"""
    
    # 1. 初始化执行器
    print("\n📝 步骤 1: 初始化执行器")
    init_request = {
        "plan": test_plan,
        "user_message": "请帮我总结今天的用户行为数据",
        "tools_config": [
            {"name": "get_daily_stats", "limit": 10}
        ]
    }
    
    response = await client.post("/api/executor/init", json=init_request)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "initialized"
    assert data["node_count"] == 2  # test.json 中有 2 个节点
    
    executor_id = data["executor_id"]
    print(f"✅ 执行器已初始化: {executor_id}")
    
    # 2. 获取执行器状态
    print("\n📝 步骤 2: 获取执行器状态")
    response = await client.get(f"/api/executor/{executor_id}/status")
    assert response.status_code == 200
    status_data = response.json()
    assert status_data["executor_id"] == executor_id
    assert status_data["overall_status"] == "initialized"
    assert len(status_data["node_states"]) == 2
    print(f"✅ 执行器状态: {status_data['overall_status']}")
    
    # 3. 列出所有执行器
    print("\n📝 步骤 3: 列出所有执行器")
    response = await client.get("/api/executors")
    assert response.status_code == 200
    executors_data = response.json()
    assert len(executors_data["executors"]) >= 1
    executor_ids = [e["executor_id"] for e in executors_data["executors"]]
    assert executor_id in executor_ids
    print(f"✅ 当前有 {len(executors_data['executors'])} 个执行器")
    
    # 4. 终止执行器
    print("\n📝 步骤 4: 终止执行器")
    response = await client.delete(f"/api/executor/{executor_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "terminated"
    print(f"✅ 执行器已终止")
    
    # 5. 验证执行器已被删除
    print("\n📝 步骤 5: 验证执行器已删除")
    response = await client.get(f"/api/executor/{executor_id}/status")
    assert response.status_code == 404
    print(f"✅ 执行器已成功删除")


# =============================================================================
# 单步执行测试
# =============================================================================

@pytest.mark.asyncio
async def test_step_execution(client, test_plan):
    """测试单步执行"""
    
    # 初始化执行器
    print("\n📝 初始化执行器用于单步测试")
    init_request = {
        "plan": test_plan,
        "user_message": "请帮我总结今天的用户行为数据",
        "tools_config": [
            {"name": "get_daily_stats", "limit": 10}
        ]
    }
    
    response = await client.post("/api/executor/init", json=init_request)
    assert response.status_code == 200
    executor_id = response.json()["executor_id"]
    print(f"✅ 执行器已初始化: {executor_id}")
    
    try:
        # 执行第一步
        print("\n📝 执行第一步 (节点 1: 获取统计数据)")
        response = await client.post(f"/api/executor/{executor_id}/step")
        assert response.status_code == 200
        step1_data = response.json()
        assert step1_data["status"] == "success"
        assert step1_data["node_context"] is not None
        
        node_context = step1_data["node_context"]
        print(f"✅ 节点 {node_context['node_id']} 执行完成")
        print(f"   节点名称: {node_context['node_name']}")
        print(f"   LLM 输出: {node_context['llm_output'][:100]}...")
        
        # 获取节点上下文
        print("\n📝 获取节点 1 的详细上下文")
        response = await client.get(f"/api/executor/{executor_id}/nodes/1/context")
        assert response.status_code == 200
        context_data = response.json()
        assert context_data["node_id"] == 1
        print(f"✅ 节点上下文获取成功")
        
        # 执行第二步
        print("\n📝 执行第二步 (节点 2: 总结统计数据)")
        response = await client.post(f"/api/executor/{executor_id}/step")
        assert response.status_code == 200
        step2_data = response.json()
        assert step2_data["status"] == "success"
        
        node_context = step2_data["node_context"]
        print(f"✅ 节点 {node_context['node_id']} 执行完成")
        print(f"   节点名称: {node_context['node_name']}")
        print(f"   LLM 输出: {node_context['llm_output'][:100]}...")
        
        # 尝试执行第三步（应该返回完成状态）
        print("\n📝 尝试执行第三步（应该已完成）")
        response = await client.post(f"/api/executor/{executor_id}/step")
        assert response.status_code == 200
        step3_data = response.json()
        assert step3_data["status"] == "completed"
        print(f"✅ 所有节点已执行完成")
        
    finally:
        # 清理
        await client.delete(f"/api/executor/{executor_id}")
        print(f"\n🧹 执行器已清理")


# =============================================================================
# 同步执行测试
# =============================================================================

@pytest.mark.asyncio
async def test_sync_execution(client, test_plan):
    """测试同步执行（完整执行）"""
    
    # 初始化执行器
    print("\n📝 初始化执行器用于同步执行测试")
    init_request = {
        "plan": test_plan,
        "user_message": "请帮我总结今天的用户行为数据",
        "tools_config": [
            {"name": "get_daily_stats", "limit": 10}
        ]
    }
    
    response = await client.post("/api/executor/init", json=init_request)
    assert response.status_code == 200
    executor_id = response.json()["executor_id"]
    print(f"✅ 执行器已初始化: {executor_id}")
    
    try:
        # 同步执行
        print("\n📝 开始同步执行...")
        response = await client.post(f"/api/executor/{executor_id}/run-sync")
        assert response.status_code == 200
        result_data = response.json()
        
        assert result_data["status"] == "completed"
        assert result_data["executor_id"] == executor_id
        assert result_data["content"] is not None
        
        print(f"✅ 执行完成")
        print(f"   结果: {result_data['content'][:200]}...")
        print(f"   Token 使用: {result_data['tokens_usage']}")
        
        # 验证最终状态
        print("\n📝 验证最终状态")
        response = await client.get(f"/api/executor/{executor_id}/status")
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["overall_status"] == "completed"
        print(f"✅ 最终状态: {status_data['overall_status']}")
        
    finally:
        # 清理
        await client.delete(f"/api/executor/{executor_id}")
        print(f"\n🧹 执行器已清理")


# =============================================================================
# 消息获取测试
# =============================================================================

@pytest.mark.asyncio
async def test_get_messages(client, test_plan):
    """测试获取执行器消息"""
    
    # 初始化并执行
    print("\n📝 初始化执行器")
    init_request = {
        "plan": test_plan,
        "user_message": "请帮我总结今天的用户行为数据",
    }
    
    response = await client.post("/api/executor/init", json=init_request)
    executor_id = response.json()["executor_id"]
    
    try:
        # 执行一步
        await client.post(f"/api/executor/{executor_id}/step")
        
        # 获取所有线程的消息
        print("\n📝 获取所有线程的消息")
        response = await client.get(f"/api/executor/{executor_id}/messages")
        assert response.status_code == 200
        messages_data = response.json()
        assert "threads" in messages_data
        print(f"✅ 获取到 {len(messages_data['threads'])} 个线程的消息")
        
        # 获取特定线程的消息
        if messages_data["threads"]:
            thread_id = list(messages_data["threads"].keys())[0]
            print(f"\n📝 获取线程 {thread_id} 的消息")
            response = await client.get(
                f"/api/executor/{executor_id}/messages",
                params={"thread_id": thread_id}
            )
            assert response.status_code == 200
            thread_messages = response.json()
            assert thread_messages["thread_id"] == thread_id
            print(f"✅ 线程消息获取成功，共 {len(thread_messages['messages'])} 条消息")
        
    finally:
        await client.delete(f"/api/executor/{executor_id}")
        print(f"\n🧹 执行器已清理")


# =============================================================================
# 错误处理测试
# =============================================================================

@pytest.mark.asyncio
async def test_error_handling(client):
    """测试错误处理"""
    
    # 测试不存在的执行器
    print("\n📝 测试访问不存在的执行器")
    fake_id = "non-existent-id"
    response = await client.get(f"/api/executor/{fake_id}/status")
    assert response.status_code == 404
    print(f"✅ 正确返回 404 错误")
    
    # 测试无效的计划
    print("\n📝 测试无效的执行计划")
    invalid_request = {
        "plan": {"invalid": "plan"},
        "user_message": "test"
    }
    response = await client.post("/api/executor/init", json=invalid_request)
    assert response.status_code == 400
    print(f"✅ 正确返回 400 错误")


# =============================================================================
# 主函数
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("🧪 开始测试后端 API")
    print("=" * 80)
    
    # 运行 pytest
    pytest.main([
        __file__,
        "-v",  # 详细输出
        "-s",  # 显示 print 输出
        "--tb=short",  # 简短的错误追踪
    ])
