import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json
import logging
from contextlib import AsyncExitStack
from typing import Dict, List, Any

# 启用调试日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MCPDataCenterManager:
    def __init__(self):
        self.sessions = {}
        self.exit_stack = AsyncExitStack()

    async def __aenter__(self):
        await self.exit_stack.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.exit_stack.__aexit__(exc_type, exc_val, exc_tb)

    async def add_data_source(self, name: str, server_params: StdioServerParameters):
        """添加数据源"""
        try:
            # 使用 exit_stack 管理资源
            read, write = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            # 创建并进入会话上下文
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            
            # 初始化会话
            await session.initialize()
            
            # 存储会话
            self.sessions[name] = session
            
            logger.info(f"Successfully connected to {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {name}: {e}")
            return False

    async def list_all_resources(self):
        """列出所有数据源的资源"""
        all_resources = {}
        for name, session in self.sessions.items():
            try:
                resources = await session.list_resources()
                all_resources[name] = resources
            except Exception as e:
                logger.error(f"Error listing resources for {name}: {e}")
        return all_resources

    async def list_all_tools(self):
        """列出所有数据源的工具"""
        all_tools = {}
        for name, session in self.sessions.items():
            try:
                tools = await session.list_tools()
                all_tools[name] = tools
            except Exception:
                all_tools[name] = []
        return all_tools

    async def query_resource(self, source_name: str, resource_uri: str):
        """查询特定资源"""
        if source_name in self.sessions:
            try:
                session = self.sessions[source_name]
                result = await session.read_resource(resource_uri)
                return result
            except Exception as e:
                logger.error(f"Error reading resource {resource_uri} from {source_name}: {e}")
                return None
        return None

    async def call_tool(self, source_name: str, tool_name: str, arguments: dict):
        """调用工具"""
        if source_name in self.sessions:
            try:
                session = self.sessions[source_name]
                result = await session.call_tool(tool_name, arguments)
                return result
            except Exception as e:
                logger.error(f"Error calling tool {tool_name} on {source_name}: {e}")
                return None
        return None

    async def cross_source_query(self, queries: dict):
        """跨数据源查询"""
        results = {}
        for source_name, resource_uri in queries.items():
            content = await self.query_resource(source_name, resource_uri)
            if content:
                results[source_name] = content
        return results

    async def health_check(self):
        """健康检查：返回每个数据源的状态"""
        result = {}
        for name, session in self.sessions.items():
            try:
                # 简单调用 list_resources 作为健康检查
                await session.list_resources()
                result[name] = "healthy"
            except Exception:
                result[name] = "unhealthy"
        return result