import sys
import argparse
from database_server_factory import DatabaseServerFactory
from config_loader import ConfigLoader
import logging

def main():
    parser = argparse.ArgumentParser(description='Launch MCP Database Server')
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    parser.add_argument('--datasource', required=True, help='Datasource name to launch')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # 加载配置
        config_loader = ConfigLoader(args.config)
        config = config_loader.load_config()
        
        # 验证配置
        errors = config_loader.validate_config()
        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        
        # 找到指定的数据源
        datasource_config = config_loader.get_datasource_config(args.datasource)
        if not datasource_config:
            print(f"Datasource '{args.datasource}' not found in config")
            sys.exit(1)
        
        if not datasource_config.enabled:
            print(f"Datasource '{args.datasource}' is disabled")
            sys.exit(1)
        
        # 创建并启动服务器
        server = DatabaseServerFactory.create_server(datasource_config)
        print(f"Starting MCP server for {datasource_config.name} ({datasource_config.type})")
        server.run()
        
    except Exception as e:
        print(f"Error: {e}")
        logging.exception("Server launch failed")
        sys.exit(1)

if __name__ == "__main__":
    main()