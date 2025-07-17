"""
数据库服务器工厂 - 根据配置创建不同类型的MCP服务器
"""
import json
import asyncio
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

# 数据库驱动导入
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

try:
    import mysql.connector
except ImportError:
    mysql = None

import sqlite3

try:
    import pymongo
except ImportError:
    pymongo = None

try:
    import redis
except ImportError:
    redis = None

try:
    import elasticsearch
except ImportError:
    elasticsearch = None

import aiohttp
import logging
from mcp.server.fastmcp import FastMCP
from config_loader import ConfigLoader, DatabaseConfig

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseServerBase(ABC):
    """数据库服务器基类"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.mcp = FastMCP(f"{config.name}_server")
        self.connection = None
        self.setup_resources()
        self.setup_tools()
    
    @abstractmethod
    def setup_resources(self):
        """设置资源"""
        pass
    
    @abstractmethod
    def setup_tools(self):
        """设置工具"""
        pass
    
    @abstractmethod
    def connect(self):
        """连接数据库"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    def run(self):
        """运行服务器"""
        try:
            self.connect()
            logger.info(f"Starting MCP server for {self.config.name}")
            self.mcp.run()
        except Exception as e:
            logger.error(f"Error running server {self.config.name}: {e}")
        finally:
            self.disconnect()

class PostgreSQLServer(DatabaseServerBase):
    """PostgreSQL服务器"""
    
    def connect(self):
        if not psycopg2:
            raise ImportError("psycopg2 is required for PostgreSQL support")
        
        conn_config = self.config.connection
        self.connection = psycopg2.connect(
            host=conn_config['host'],
            port=conn_config['port'],
            database=conn_config['database'],
            user=conn_config['username'],
            password=conn_config['password']
        )
        logger.info(f"Connected to PostgreSQL: {self.config.name}")
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            logger.info(f"Disconnected from PostgreSQL: {self.config.name}")
    
    def setup_resources(self):
        @self.mcp.resource(f"postgresql://{self.config.name}/schema")
        def get_schema() -> str:
            """获取数据库模式"""
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """)
            schema_info = cursor.fetchall()
            cursor.close()
            return json.dumps(schema_info, indent=2)
        
        if self.config.tables:
            for table in self.config.tables:
                @self.mcp.resource(f"postgresql://{self.config.name}/table/{table}")
                def get_table_data(table_name: str = table) -> str:
                    """获取表数据"""
                    cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 100")
                    data = cursor.fetchall()
                    cursor.close()
                    return json.dumps(data, default=str, indent=2)
    
    def setup_tools(self):
        @self.mcp.tool()
        def execute_query(sql: str) -> str:
            """执行SQL查询"""
            cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                cursor.execute(sql)
                if sql.strip().upper().startswith('SELECT'):
                    results = cursor.fetchall()
                    return json.dumps(results, default=str, indent=2)
                else:
                    self.connection.commit()
                    return f"Query executed successfully. Rows affected: {cursor.rowcount}"
            except Exception as e:
                self.connection.rollback()
                return f"Error: {str(e)}"
            finally:
                cursor.close()

class MySQLServer(DatabaseServerBase):
    """MySQL服务器"""
    
    def connect(self):
        if not mysql:
            raise ImportError("mysql-connector-python is required for MySQL support")
        
        conn_config = self.config.connection
        self.connection = mysql.connector.connect(
            host=conn_config['host'],
            port=conn_config['port'],
            database=conn_config['database'],
            user=conn_config['username'],
            password=conn_config['password']
        )
        logger.info(f"Connected to MySQL: {self.config.name}")
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            logger.info(f"Disconnected from MySQL: {self.config.name}")
    
    def setup_resources(self):
        @self.mcp.resource(f"mysql://{self.config.name}/schema")
        def get_schema() -> str:
            """获取数据库模式"""
            cursor = self.connection.cursor()
            cursor.execute(f"SHOW TABLES FROM {self.config.connection['database']}")
            tables = cursor.fetchall()
            cursor.close()
            return json.dumps(tables, indent=2)
        
        if self.config.tables:
            for table in self.config.tables:
                @self.mcp.resource(f"mysql://{self.config.name}/table/{table}")
                def get_table_data(table_name: str = table) -> str:
                    """获取表数据"""
                    cursor = self.connection.cursor(dictionary=True)
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 100")
                    data = cursor.fetchall()
                    cursor.close()
                    return json.dumps(data, default=str, indent=2)
    
    def setup_tools(self):
        @self.mcp.tool()
        def execute_query(sql: str) -> str:
            """执行SQL查询"""
            cursor = self.connection.cursor(dictionary=True)
            try:
                cursor.execute(sql)
                if sql.strip().upper().startswith('SELECT'):
                    results = cursor.fetchall()
                    return json.dumps(results, default=str, indent=2)
                else:
                    self.connection.commit()
                    return f"Query executed successfully. Rows affected: {cursor.rowcount}"
            except Exception as e:
                self.connection.rollback()
                return f"Error: {str(e)}"
            finally:
                cursor.close()

class SQLiteServer(DatabaseServerBase):
    """SQLite服务器"""
    
    def connect(self):
        self.connection = sqlite3.connect(self.config.connection['database_path'])
        self.connection.row_factory = sqlite3.Row
        logger.info(f"Connected to SQLite: {self.config.name}")
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            logger.info(f"Disconnected from SQLite: {self.config.name}")
    
    def setup_resources(self):
        @self.mcp.resource(f"sqlite://{self.config.name}/schema")
        def get_schema() -> str:
            """获取数据库模式"""
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            return json.dumps([dict(table) for table in tables], indent=2)
        
        if self.config.tables:
            for table in self.config.tables:
                @self.mcp.resource(f"sqlite://{self.config.name}/table/{table}")
                def get_table_data(table_name: str = table) -> str:
                    """获取表数据"""
                    cursor = self.connection.cursor()
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 100")
                    data = cursor.fetchall()
                    return json.dumps([dict(row) for row in data], default=str, indent=2)
    
    def setup_tools(self):
        @self.mcp.tool()
        def execute_query(sql: str) -> str:
            """执行SQL查询"""
            cursor = self.connection.cursor()
            try:
                cursor.execute(sql)
                if sql.strip().upper().startswith('SELECT'):
                    results = cursor.fetchall()
                    return json.dumps([dict(row) for row in results], default=str, indent=2)
                else:
                    self.connection.commit()
                    return f"Query executed successfully. Rows affected: {cursor.rowcount}"
            except Exception as e:
                self.connection.rollback()
                return f"Error: {str(e)}"
            finally:
                cursor.close()

class MongoDBServer(DatabaseServerBase):
    """MongoDB服务器"""
    
    def connect(self):
        if not pymongo:
            raise ImportError("pymongo is required for MongoDB support")
        
        conn_config = self.config.connection
        connection_string = f"mongodb://{conn_config['username']}:{conn_config['password']}@{conn_config['host']}:{conn_config['port']}/{conn_config['database']}"
        
        self.client = pymongo.MongoClient(connection_string)
        self.connection = self.client[conn_config['database']]
        logger.info(f"Connected to MongoDB: {self.config.name}")
    
    def disconnect(self):
        if self.client:
            self.client.close()
            logger.info(f"Disconnected from MongoDB: {self.config.name}")
    
    def setup_resources(self):
        @self.mcp.resource(f"mongodb://{self.config.name}/collections")
        def get_collections() -> str:
            """获取集合列表"""
            collections = self.connection.list_collection_names()
            return json.dumps(collections, indent=2)
        
        if self.config.collections:
            for collection in self.config.collections:
                @self.mcp.resource(f"mongodb://{self.config.name}/collection/{collection}")
                def get_collection_data(collection_name: str = collection) -> str:
                    """获取集合数据"""
                    coll = self.connection[collection_name]
                    data = list(coll.find().limit(100