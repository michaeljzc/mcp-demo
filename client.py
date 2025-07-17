import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json
import logging
from contextlib import AsyncExitStack

# 启用调试日志
logging.basicConfig(level=logging.DEBUG)

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
            
            print(f"Successfully connected to {name}")
            return True
        except Exception as e:
            print(f"Failed to connect to {name}: {e}")
            logging.exception(f"Detailed error for {name}")
            return False

    async def list_all_resources(self):
        """列出所有数据源的资源"""
        all_resources = {}
        for name, session in self.sessions.items():
            try:
                resources = await session.list_resources()
                all_resources[name] = resources
            except Exception as e:
                print(f"Error listing resources for {name}: {e}")
                logging.exception(f"Detailed error listing resources for {name}")
        return all_resources

    async def query_resource(self, source_name: str, resource_uri: str):
        """查询特定资源"""
        if source_name in self.sessions:
            try:
                session = self.sessions[source_name]
                content, mime_type = await session.read_resource(resource_uri)
                return content
            except Exception as e:
                print(f"Error reading resource {resource_uri} from {source_name}: {e}")
                logging.exception(f"Detailed error reading resource")
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
                print(f"Error calling tool {tool_name} on {source_name}: {e}")
                logging.exception(f"Detailed error calling tool")
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

async def test_server_startup():
    """测试服务器是否能正常启动"""
    servers_to_test = [
        ("database", StdioServerParameters(command="python", args=["database_server.py"])),
        ("api", StdioServerParameters(command="python", args=["api_server.py"]))
    ]
    
    for name, params in servers_to_test:
        print(f"Testing {name} server startup...")
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    print(f"{name} server test: SUCCESS")
        except Exception as e:
            print(f"{name} server test: FAILED - {e}")
            logging.exception(f"{name} server test failed")

async def main():
    # 首先测试服务器是否能启动
    await test_server_startup()
    
    # 使用上下文管理器确保资源正确清理
    async with MCPDataCenterManager() as manager:
        try:
            # 添加数据源
            db_params = StdioServerParameters(
                command="python",
                args=["database_server.py"]
            )
            
            api_params = StdioServerParameters(
                command="python",
                args=["api_server.py"]
            )
            
            # 连接到数据源
            print("Connecting to database...")
            db_success = await manager.add_data_source("database", db_params)
            
            print("Connecting to API...")
            api_success = await manager.add_data_source("api", api_params)
            
            if not db_success and not api_success:
                print("Failed to connect to any data source")
                return
            
            # 列出所有资源
            print("Listing resources...")
            resources = await manager.list_all_resources()
            print("All resources:", json.dumps(resources, indent=2, default=str))
            
            # 跨数据源查询
            if db_success and api_success:
                queries = {
                    "database": "database://table/users",
                    "api": "api://users"
                }
                print("Performing cross-source query...")
                results = await manager.cross_source_query(queries)
                print("Cross-source results:", results)
            
            # 调用工具
            if db_success:
                print("Calling database tool...")
                result = await manager.call_tool("database", "execute_query", {
                    "sql": "SELECT * FROM users LIMIT 5"
                })
                print("Tool result:", result)
        
        except Exception as e:
            print(f"Error in main: {e}")
            logging.exception("Error in main function")
    
    print("All resources have been automatically cleaned up")

if __name__ == "__main__":
    asyncio.run(main())