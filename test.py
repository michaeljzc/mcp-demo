import asyncio
from mcp import StdioServerParameters
from client import MCPDataCenterManager
import json

async def llm_query_example():
    """
    模拟大模型（如 LLM）通过 MCP 协议调用数据库：
    1. 查询数据库表结构
    2. 查询表数据
    3. 执行 SQL 工具
    """
    # 假设 config.yaml 里有名为 'oracle_demo' 的 Oracle 数据源
    datasource_name = 'oracle_demo'
    table_name = 'YOUR_TABLE_NAME'  # 替换为实际表名
    sql = f"SELECT * FROM {table_name} WHERE ROWNUM <= 5"

    # 启动 MCP 数据中心管理器
    async with MCPDataCenterManager() as manager:
        # 连接到 Oracle 数据源
        server_params = StdioServerParameters(
            command="python",
            args=["server_launcher.py", "--datasource", datasource_name]
        )
        print(f"Connecting to {datasource_name}...")
        success = await manager.add_data_source(datasource_name, server_params)
        if not success:
            print(f"Failed to connect to {datasource_name}")
            return
        print(f"Connected to {datasource_name}")

        # 1. 查询表结构（资源）
        resources = await manager.list_all_resources()
        print(f"All resources: {json.dumps(resources, indent=2, default=str)}")
        # 假设资源里有 oracle://oracle_demo/table/YOUR_TABLE_NAME
        resource_uri = f"oracle://{datasource_name}/table/{table_name}"
        content = await manager.query_resource(datasource_name, resource_uri)
        print(f"Table {table_name} data: {content}")

        # 2. 执行 SQL 工具
        result = await manager.call_tool(datasource_name, "execute_query", {"sql": sql})
        print(f"SQL tool result: {result}")

if __name__ == "__main__":
    asyncio.run(llm_query_example()) 