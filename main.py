from openai import api_key
from simple_llm_playground import executor_manager
import os

def _create_llm_instance(
    model: str,
    api_key: str,
    api_base: str,
    **kwargs
):
    """
    创建 LLM 实例的辅助函数

    Args:
        model: 模型名称
        api_key: API密钥
        api_base: API基础URL
        **kwargs: 其他参数

    Returns:
        ChatOpenAI 实例
    """
    try:
        from langchain_openai import ChatOpenAI

        # 使用 OpenAI 兼容模式，支持阿里云 DashScope 和 OpenAI
        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=kwargs.get('temperature', 0.7),
            top_p=kwargs.get('top_p', 0.9)
        )
    except ImportError:
        raise ValueError("langchain_openai not installed. Run: pip install langchain-openai")

def setup_llm_factory(
    api_key: str = None,
    model: str = "qwen-plus-2025-12-01",
    api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
    **kwargs
):
    """
    设置 LLM 工厂函数

    支持阿里云 DashScope API (通义千问) 和 OpenAI API

    Args:
        api_key: API密钥 (DashScope API Key 或 OpenAI API Key)。如果不传，尝试从环境读取。
        model: 模型名称，默认 "qwen-plus"
            - 通义千问: "qwen-plus", "qwen-max", "qwen-turbo" 等
            - OpenAI: "gpt-4", "gpt-3.5-turbo" 等
        api_base: API基础URL
            - 阿里云: "https://dashscope.aliyuncs.com/compatible-mode/v1"
            - OpenAI: "https://api.openai.com/v1" (默认)
        **kwargs: 其他参数如 temperature, top_p 等
    """
    # 尝试从环境变量读取 API Key
    if not api_key:
        api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("⚠️ Warning: No API key found. Please set DASHSCOPE_API_KEY or OPENAI_API_KEY environment variable.")

    # 使用 lambda 捕获所有参数，确保闭包正确捕获变量
    factory = lambda: _create_llm_instance(
        model=model,
        api_key=api_key,
        api_base=api_base,
        **kwargs
    )
    return factory
# 1. 设置模型 修改api_key, model, api_base

# api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY") # or api_key = "your_api_key"
# model = "your_model_name"
# api_base = "your_api_base"
# factory = setup_llm_factory(api_key=api_key, model=model, api_base=api_base)
factory = setup_llm_factory()
executor_manager.set_llm_factory(factory)


# 2. 设置工具
# from your_path import ( tools )

def setup_test_tools():
    """设置测试工具（用于开发测试）"""
    from langchain_core.tools import tool
    
    @tool
    def add(a: int, b: int) -> int:
        """Add two numbers"""
        return a + b
    
    @tool
    def multiply(a: int, b: int) -> int:
        """Multiply two numbers"""
        return a * b
    
    executor_manager.register_tool("add", add)
    executor_manager.register_tool("multiply", multiply)
setup_test_tools()

# 3. 运行脚本 终端输入：
# .\run.bat