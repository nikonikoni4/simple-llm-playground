# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Simple LLM Playground is a Qt-based visual workflow editor for creating, debugging, and testing LLM (Large Language Model) workflows. It uses a node-based architecture where workflows consist of LLM nodes and tool nodes connected via threads.

## Architecture

### Components

- **Backend (`simple_llm_playground/server/`)**: FastAPI server on port 8001
  - `backend_api.py`: REST API endpoints for workflow execution
  - `executor_manager.py`: Manages executor instances and tool registration
  - `async_executor.py`: Asynchronous workflow execution
  - `data_driving_schemas.py`: Pydantic models for workflow plans

- **Frontend (`simple_llm_playground/qt_front/`)**: PyQt5 desktop UI
  - `debugger_ui.py`: Main window with visual node editor
  - `execution_panel.py`: Execution controls (Initialize, Stop, Step, Run All)
  - `api_client.py`: HTTP client for backend communication

- **Core Engine (`llm_linear_executor/`)**: Git submodule containing the workflow execution engine. See its README.md for execution order details.

### Node Types

- `llm-first`: LLM processes input first, then calls tools if needed. Empty task_prompt = pass-through (no LLM call).
- `tool-first`: Executes specified tool first, then LLM analyzes results. Requires `initial_tool_name`.

### Thread-Based Data Flow

Workflows use threads for data routing:
- Each node has a `thread_id` (branch)
- `data_in_thread`: Source thread for input data
- `data_out_thread`: Target thread for output
- `data_in_slice`: Message range from source (e.g., `0,2` = first 2 messages, `-1,` = last message)

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start both backend and frontend (Windows)
.\run.bat

# Start backend only (port 8001, configured in config.py)
python main.py

# Start frontend only
python -m simple_llm_playground.qt_front.debugger_ui
```

## Configuration

### LLM Setup (`main.py`)

```python
# Configure LLM factory
llm_factory = create_llm_factory(
    model="qwen-plus-2025-12-01",  # or "gpt-4o"
    api_key="your_api_key",  # or None to read from DASHSCOPE_API_KEY/OPENAI_API_KEY env var
    chat_model=ChatOpenAI
)
executor_manager.set_llm_factory(llm_factory)
```

### Tool Registration

Tools are Langchain `@tool` decorated functions:

```python
from langchain_core.tools import tool
from simple_llm_playground.server.executor_manager import executor_manager

@tool
def my_tool(param: str) -> str:
    """Tool description"""
    return "result"

executor_manager.register_tool("my_tool", my_tool)
```

## Key Files

- `config.py`: Global config (BACKEND_PORT = 8001)
- `main.py`: Entry point, LLM factory setup, tool registration
- `run.bat`: Windows startup script (launches backend + frontend in separate windows)
- `test_plan/`: Example workflow JSON files

## Limitations

- No router nodes - branching requires multiple threads
- Only `llm-first` and `tool-first` node types supported
- Execution engine features depend on `llm-linear-executor` submodule
