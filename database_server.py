from mcp.server.fastmcp import FastMCP
import sqlite3
import json

mcp = FastMCP("Database Server")

# 初始化数据库
def init_db():
    conn = sqlite3.connect("test.db")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        )
    ''')
    conn.execute("INSERT OR IGNORE INTO users (id, name, email) VALUES (1, 'John Doe', 'john@example.com')")
    conn.execute("INSERT OR IGNORE INTO users (id, name, email) VALUES (2, 'Jane Smith', 'jane@example.com')")
    conn.commit()
    conn.close()

init_db()

@mcp.resource("database://table/users")
def get_users() -> str:
    conn = sqlite3.connect("test.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return json.dumps(users)

@mcp.tool()
def execute_query(sql: str) -> str:
    conn = sqlite3.connect("test.db")
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        if sql.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            return json.dumps(results)
        else:
            conn.commit()
            return f"Query executed. Rows affected: {cursor.rowcount}"
    except sqlite3.Error as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()

if __name__ == "__main__":
    mcp.run()