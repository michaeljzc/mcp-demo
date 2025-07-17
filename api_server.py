from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("API Server")

# 模拟API数据
USERS_DATA = [
    {"id": 1, "name": "Alice", "email": "alice@api.com"},
    {"id": 2, "name": "Bob", "email": "bob@api.com"}
]

@mcp.resource("api://users")
def get_api_users() -> str:
    return json.dumps(USERS_DATA)

@mcp.tool()
def search_users(query: str) -> str:
    results = [user for user in USERS_DATA if query.lower() in user["name"].lower()]
    return json.dumps(results)

if __name__ == "__main__":
    mcp.run()