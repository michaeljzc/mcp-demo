import asyncio
from mcp import StdioServerParameters
from client import MCPDataCenterManager
from config_loader import ConfigLoader
import json

async def test_datacenter():
    """测试数据中心功能"""
    config_loader = ConfigLoader("config.yaml")
    config = config_loader.load_config()
    
    # 获取启用的数据源
    enabled_sources = config_loader.get_enabled_datasources()
    print(f"Found {len(enabled_sources)} enabled datasources")
    
    async with MCPDataCenterManager() as manager:
        # 连接到所有启用的数据源
        connected_sources = []
        for datasource in enabled_sources:
            server_params = StdioServerParameters(
                command="python",
                args=["server_launcher.py", "--datasource", datasource.name]
            )
            
            print(f"Connecting to {datasource.name}...")
            success = await manager.add_data_source(datasource.name, server_params)
            if success:
                connected_sources.append(datasource.name)
        
        if not connected_sources:
            print("No datasources connected successfully")
            return
        
        print(f"Successfully connected to: {connected_sources}")
        
        # 健康检查
        health = await manager.health_check()
        print(f"Health check: {json.dumps(health, indent=2)}")
        
        # 列出所有资源
        resources = await manager.list_all_resources()
        print(f"Available resources: {json.dumps(resources, indent=2, default=str)}")
        
        # 列出所有工具
        tools = await manager.list_all_tools()
        print(f"Available tools: {json.dumps(tools, indent=2, default=str)}")
        
        # 测试查询资源
        for source_name in connected_sources[:2]:  # 测试前两个
            print(f"\nTesting {source_name}...")
            source_resources = resources.get(source_name, [])
            if source_resources:
                resource_uri = source_resources[0].get('uri')
                if resource_uri:
                    result = await manager.query_resource(source_name, resource_uri)
                    print(f"Resource {resource_uri}: {result}")
            
            # 测试调用工具
            source_tools = tools.get(source_name, [])
            if source_tools:
                tool_name = source_tools[0].get('name')
                if tool_name:
                    try:
                        result = await manager.call_tool(source_name, tool_name, {})
                        print(f"Tool {tool_name}: {result}")
                    except Exception as e:
                        print(f"Tool {tool_name} error: {e}")

if __name__ == "__main__":
    asyncio.run(test_datacenter())