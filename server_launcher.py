#!/usr/bin/env python3
"""
改进的MCP数据中心启动脚本
"""
import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import Dict, List
import json

from mcp import StdioServerParameters
from client import MCPDataCenterManager
from config_loader import ConfigLoader
from database_server_factory import DatabaseServerFactory

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ImprovedDataCenter:
    """改进的数据中心管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_loader = ConfigLoader(config_path)
        self.config = None
        self.manager = None
        self.connected_sources = []
        self.running = False
    
    async def initialize(self):
        """初始化数据中心"""
        try:
            # 加载和验证配置
            self.config = self.config_loader.load()
            errors = self.config_loader.validate()
            
            if errors:
                logger.error("Configuration validation failed:")
                for error in errors:
                    logger.error(f"  - {error}")
                raise ValueError("Invalid configuration")
            
            logger.info(f"Loaded configuration for {len(self.config.datasources)} datasources")
            
            # 创建管理器
            self.manager = MCPDataCenterManager()
            await self.manager.__aenter__()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize data center: {e}")
            return False
    
    async def connect_datasources(self):
        """连接所有启用的数据源"""
        enabled_sources = self.config_loader.get_enabled_datasources()
        logger.info(f"Connecting to {len(enabled_sources)} enabled datasources")
        if not self.manager:
            logger.error("Manager is not initialized")
            return False
        for datasource in enabled_sources:
            try:
                logger.info(f"Connecting to {datasource.name} ({datasource.type})")
                server_params = StdioServerParameters(
                    command="python",
                    args=["server_launcher.py", "--datasource", datasource.name]
                )
                success = await self.manager.add_data_source(datasource.name, server_params)
                if success:
                    self.connected_sources.append(datasource.name)
                    logger.info(f"Successfully connected to {datasource.name}")
                else:
                    logger.warning(f"Failed to connect to {datasource.name}")
            except Exception as e:
                logger.error(f"Error connecting to {datasource.name}: {e}")
        logger.info(f"Connected to {len(self.connected_sources)} datasources: {self.connected_sources}")
        return len(self.connected_sources) > 0
    
    async def health_check(self) -> Dict:
        """执行健康检查"""
        logger.info("Performing health check...")
        if not self.manager:
            logger.error("Manager is not initialized")
            return {}
        health = await self.manager.health_check()
        
        healthy_count = sum(1 for status in health.values() if status == "healthy")
        logger.info(f"Health check: {healthy_count}/{len(health)} sources healthy")
        
        return health
    
    async def list_resources(self) -> Dict:
        """列出所有资源"""
        logger.info("Listing all resources...")
        if not self.manager:
            logger.error("Manager is not initialized")
            return {}
        resources = await self.manager.list_all_resources()
        
        total_resources = sum(len(source_resources) for source_resources in resources.values())
        logger.info(f"Found {total_resources} total resources across {len(resources)} sources")
        
        return resources
    
    async def list_tools(self) -> Dict:
        """列出所有工具"""
        logger.info("Listing all tools...")
        if not self.manager:
            logger.error("Manager is not initialized")
            return {}
        tools = await self.manager.list_all_tools()
        
        total_tools = sum(len(source_tools) for source_tools in tools.values())
        logger.info(f"Found {total_tools} total tools across {len(tools)} sources")
        
        return tools
    
    async def query_resource(self, source_name: str, resource_uri: str):
        """查询资源"""
        logger.info(f"Querying resource {resource_uri} from {source_name}")
        if not self.manager:
            logger.error("Manager is not initialized")
            return None
        result = await self.manager.query_resource(source_name, resource_uri)
        return result
    
    async def call_tool(self, source_name: str, tool_name: str, arguments: Dict):
        """调用工具"""
        logger.info(f"Calling tool {tool_name} on {source_name}")
        if not self.manager:
            logger.error("Manager is not initialized")
            return None
        result = await self.manager.call_tool(source_name, tool_name, arguments)
        return result
    
    async def run_interactive_mode(self):
        """运行交互模式"""
        logger.info("Starting interactive mode...")
        self.running = True
        
        while self.running:
            try:
                print("\n" + "="*50)
                print("MCP Data Center - Interactive Mode")
                print("="*50)
                print("1. Health Check")
                print("2. List Resources")
                print("3. List Tools")
                print("4. Query Resource")
                print("5. Call Tool")
                print("6. Cross-Source Query")
                print("0. Exit")
                
                choice = input("\nEnter your choice (0-6): ").strip()
                
                if choice == "0":
                    self.running = False
                    break
                elif choice == "1":
                    health = await self.health_check()
                    print(json.dumps(health, indent=2))
                elif choice == "2":
                    resources = await self.list_resources()
                    print(json.dumps(resources, indent=2, default=str))
                elif choice == "3":
                    tools = await self.list_tools()
                    print(json.dumps(tools, indent=2, default=str))
                elif choice == "4":
                    await self._interactive_query_resource()
                elif choice == "5":
                    await self._interactive_call_tool()
                elif choice == "6":
                    await self._interactive_cross_query()
                else:
                    print("Invalid choice!")
                    
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}")
    
    async def _interactive_query_resource(self):
        """交互式资源查询"""
        print(f"Available sources: {self.connected_sources}")
        source_name = input("Enter source name: ").strip()
        
        if source_name not in self.connected_sources:
            print(f"Source '{source_name}' not available")
            return
        
        if not self.manager:
            print("Manager is not initialized")
            return
        
        # 获取可用资源
        resources = await self.manager.list_all_resources()
        source_resources = resources.get(source_name, [])
        
        if not source_resources:
            print(f"No resources available for {source_name}")
            return
        
        print(f"Available resources for {source_name}:")
        for i, resource in enumerate(source_resources):
            print(f"  {i}: {resource.get('uri', 'N/A')}")
        
        try:
            index = int(input("Enter resource index: ").strip())
            if 0 <= index < len(source_resources):
                resource_uri = source_resources[index].get('uri')
                result = await self.query_resource(source_name, resource_uri)
                print(f"Result: {result}")
            else:
                print("Invalid index")
        except ValueError:
            print("Invalid input")
    
    async def _interactive_call_tool(self):
        """交互式工具调用"""
        print(f"Available sources: {self.connected_sources}")
        source_name = input("Enter source name: ").strip()
        
        if source_name not in self.connected_sources:
            print(f"Source '{source_name}' not available")
            return
        
        if not self.manager:
            print("Manager is not initialized")
            return
        
        # 获取可用工具
        tools = await self.manager.list_all_tools()
        source_tools = tools.get(source_name, [])
        
        if not source_tools:
            print(f"No tools available for {source_name}")
            return
        
        print(f"Available tools for {source_name}:")
        for i, tool in enumerate(source_tools):
            print(f"  {i}: {tool.get('name', 'N/A')}")
        
        try:
            index = int(input("Enter tool index: ").strip())
            if 0 <= index < len(source_tools):
                tool_name = source_tools[index].get('name')
                
                # 获取参数
                args_str = input("Enter arguments (JSON format, or empty for {}): ").strip()
                try:
                    arguments = json.loads(args_str) if args_str else {}
                except json.JSONDecodeError:
                    arguments = {}
                
                result = await self.call_tool(source_name, tool_name, arguments)
                print(f"Result: {result}")
            else:
                print("Invalid index")
        except ValueError:
            print("Invalid input")
    
    async def _interactive_cross_query(self):
        """交互式跨源查询"""
        print("Cross-source query example:")
        print("Enter multiple source:resource pairs")
        
        queries = {}
        while True:
            source_name = input("Enter source name (or 'done' to finish): ").strip()
            if source_name.lower() == 'done':
                break
            
            if source_name not in self.connected_sources:
                print(f"Source '{source_name}' not available")
                continue
            
            resource_uri = input(f"Enter resource URI for {source_name}: ").strip()
            queries[source_name] = resource_uri
        
        if queries:
            if not self.manager:
                print("Manager is not initialized")
                return
            result = await self.manager.cross_source_query(queries)
            print(f"Cross-query result: {json.dumps(result, indent=2, default=str)}")
    
    async def shutdown(self):
        """关闭数据中心"""
        logger.info("Shutting down data center...")
        self.running = False
        
        if self.manager:
            await self.manager.__aexit__(None, None, None)
        
        logger.info("Data center shutdown complete")

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MCP Data Center')
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    parser.add_argument('--mode', choices=['interactive', 'test'], default='interactive', help='Run mode')
    
    args = parser.parse_args()
    
    # 创建数据中心
    datacenter = ImprovedDataCenter(args.config)
    
    # 设置信号处理
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        datacenter.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 初始化
        if not await datacenter.initialize():
            sys.exit(1)
        
        # 连接数据源
        if not await datacenter.connect_datasources():
            logger.error("Failed to connect to any datasources")
            sys.exit(1)
        
        # 运行模式
        if args.mode == 'interactive':
            await datacenter.run_interactive_mode()
        elif args.mode == 'test':
            # 测试模式
            await datacenter.health_check()
            await datacenter.list_resources()
            await datacenter.list_tools()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await datacenter.shutdown()

if __name__ == "__main__":
    asyncio.run(main())