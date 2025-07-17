#!/usr/bin/env python3
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 MCP 服务器
server = Server("mcp-server-demo")

@server.list_tools()
async def handle_list_tools() -> ListToolsResult:
    return ListToolsResult(
        tools=[
            Tool(
                name="hello",
                description="一个简单的问候工具",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "要问候的人名"
                        }
                    },
                    "required": ["name"]
                }
            ),
            Tool(
                name="echo",
                description="回显输入的消息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "要回显的消息"
                        }
                    },
                    "required": ["message"]
                }
            )
        ]
    )

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    logger.info(f"调用工具: {name}, 参数: {arguments}")
    
    if name == "hello":
        name_param = arguments.get("name", "世界")
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"你好，{name_param}！欢迎使用 MCP 服务器演示。"
                )
            ]
        )
    
    elif name == "echo":
        message = arguments.get("message", "")
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"回显: {message}"
                )
            ]
        )
    
    else:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"未知工具: {name}"
                )
            ]
        )

async def main():
    # 主函数
    # 运行服务器
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-server-demo",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
