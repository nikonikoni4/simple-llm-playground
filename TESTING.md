# 快速测试指南

这个文件提供最简洁的测试启动方法。

## 🚀 30秒快速开始

### 方法 1: 使用批处理脚本（最简单）

```bash
cd test
run_test.bat
```

然后选择 **选项 5**（同时启动后端和运行测试）

### 方法 2: 手动启动（更灵活）

**终端 1** - 启动后端：
```bash
python test/start_backend.py
```

**终端 2** - 运行演示：
```bash
python test/demo.py
```

## 📖 详细文档

完整的使用指南请查看：
- **快速指南**: `test/USAGE_GUIDE.md` 
- **详细文档**: `test/README.md`

## ⚙️ 环境要求

1. Python 3.10+
2. 安装依赖：
```bash
pip install fastapi uvicorn aiohttp langchain-core langchain-openai pydantic
```

3. （可选）设置 API Key 用于 LLM 测试：
```powershell
$env:OPENAI_API_KEY="your-api-key"
```

## 🎯 测试内容

测试将验证：
- ✅ 后端 API 服务
- ✅ 前端 API 客户端
- ✅ 执行器初始化和运行
- ✅ 单步调试功能
- ✅ 状态查询功能
- ✅ 工具调用功能

## 📁 测试文件

所有测试相关文件都在 `test/` 目录下：
- `test_integration.py` - 完整测试套件
- `demo.py` - 简单演示
- `start_backend.py` - 后端启动脚本
- `run_test.bat` - Windows 启动脚本

## ❓ 遇到问题？

查看 `test/USAGE_GUIDE.md` 中的"常见问题"章节。
