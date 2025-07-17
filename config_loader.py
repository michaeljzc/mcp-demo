"""
MCP数据中心配置文件加载器
"""
import yaml
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class DatabaseConfig:
    """数据库配置"""
    name: str
    type: str
    enabled: bool
    description: str
    connection: Dict[str, Any]
    settings: Dict[str, Any]
    tables: Optional[List[str]] = None
    collections: Optional[List[str]] = None
    indices: Optional[List[str]] = None
    endpoints: Optional[List[Dict[str, str]]] = None
    headers: Optional[Dict[str, str]] = None
    schemas: Optional[List[str]] = None

@dataclass
class ServerConfig:
    """服务器配置"""
    datasource: str
    port: int
    log_level: str

@dataclass
class DataCenterConfig:
    """数据中心配置"""
    datacenter: Dict[str, str]
    datasources: List[DatabaseConfig]
    servers: List[ServerConfig]
    management: Dict[str, Any]
    security: Dict[str, Any]
    logging: Dict[str, Any]
    monitoring: Dict[str, Any]

class ConfigLoader:
    """配置文件加载器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config: Optional[DataCenterConfig] = None
    
    def load_config(self) -> DataCenterConfig:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # 解析数据源配置
        datasources = []
        for ds_config in config_data.get('datasources', []):
            datasource = DatabaseConfig(
                name=ds_config['name'],
                type=ds_config['type'],
                enabled=ds_config.get('enabled', True),
                description=ds_config.get('description', ''),
                connection=ds_config.get('connection', {}),
                settings=ds_config.get('settings', {}),
                tables=ds_config.get('tables'),
                collections=ds_config.get('collections'),
                indices=ds_config.get('indices'),
                endpoints=ds_config.get('endpoints'),
                headers=ds_config.get('headers'),
                schemas=ds_config.get('schemas')
            )
            datasources.append(datasource)
        
        # 解析服务器配置
        servers = []
        for server_config in config_data.get('servers', []):
            server = ServerConfig(
                datasource=server_config['datasource'],
                port=server_config['port'],
                log_level=server_config.get('log_level', 'INFO')
            )
            servers.append(server)
        
        # 创建完整配置
        self.config = DataCenterConfig(
            datacenter=config_data.get('datacenter', {}),
            datasources=datasources,
            servers=servers,
            management=config_data.get('management', {}),
            security=config_data.get('security', {}),
            logging=config_data.get('logging', {}),
            monitoring=config_data.get('monitoring', {})
        )
        
        return self.config
    
    def get_datasource_config(self, name: str) -> Optional[DatabaseConfig]:
        """获取指定数据源配置"""
        if not self.config:
            self.load_config()
        
        for datasource in self.config.datasources:
            if datasource.name == name:
                return datasource
        return None
    
    def get_enabled_datasources(self) -> List[DatabaseConfig]:
        """获取所有启用的数据源"""
        if not self.config:
            self.load_config()
        
        return [ds for ds in self.config.datasources if ds.enabled]
    
    def get_server_config(self, datasource_name: str) -> Optional[ServerConfig]:
        """获取指定数据源的服务器配置"""
        if not self.config:
            self.load_config()
        
        for server in self.config.servers:
            if server.datasource == datasource_name:
                return server
        return None
    
    def get_connection_string(self, datasource_name: str) -> Optional[str]:
        """生成数据库连接字符串"""
        datasource = self.get_datasource_config(datasource_name)
        if not datasource:
            return None
        
        conn = datasource.connection
        
        if datasource.type == 'postgresql':
            return f"postgresql://{conn['username']}:{conn['password']}@{conn['host']}:{conn['port']}/{conn['database']}"
        
        elif datasource.type == 'mysql':
            return f"mysql://{conn['username']}:{conn['password']}@{conn['host']}:{conn['port']}/{conn['database']}"
        
        elif datasource.type == 'sqlite':
            return f"sqlite:///{conn['database_path']}"
        
        elif datasource.type == 'mongodb':
            auth = f"{conn['username']}:{conn['password']}@" if conn.get('username') else ""
            return f"mongodb://{auth}{conn['host']}:{conn['port']}/{conn['database']}"
        
        elif datasource.type == 'redis':
            auth = f":{conn['password']}@" if conn.get('password') else ""
            return f"redis://{auth}{conn['host']}:{conn['port']}/{conn['database']}"
        
        return None
    
    def validate_config(self) -> List[str]:
        """验证配置文件"""
        errors = []
        
        if not self.config:
            try:
                self.load_config()
            except Exception as e:
                errors.append(f"配置文件加载失败: {e}")
                return errors
        
        # 验证数据源配置
        datasource_names = set()
        for datasource in self.config.datasources:
            if datasource.name in datasource_names:
                errors.append(f"数据源名称重复: {datasource.name}")
            datasource_names.add(datasource.name)
            
            # 验证连接配置
            if not datasource.connection:
                errors.append(f"数据源 {datasource.name} 缺少连接配置")
            
            # 验证必要字段
            required_fields = {
                'postgresql': ['host', 'port', 'database', 'username', 'password'],
                'mysql': ['host', 'port', 'database', 'username', 'password'],
                'sqlite': ['database_path'],
                'mongodb': ['host', 'port', 'database'],
                'redis': ['host', 'port'],
                'elasticsearch': ['host', 'port'],
                'rest_api': ['base_url'],
                'graphql': ['endpoint']
            }
            
            if datasource.type in required_fields:
                for field in required_fields[datasource.type]:
                    if field not in datasource.connection:
                        errors.append(f"数据源 {datasource.name} 缺少必要字段: {field}")
        
        # 验证服务器配置
        server_ports = set()
        for server in self.config.servers:
            if server.port in server_ports:
                errors.append(f"服务器端口冲突: {server.port}")
            server_ports.add(server.port)
            
            # 验证数据源是否存在
            if server.datasource not in datasource_names:
                errors.append(f"服务器配置引用了不存在的数据源: {server.datasource}")
        
        return errors
    
    def reload_config(self):
        """重新加载配置文件"""
        self.config = None
        return self.load_config()
    
    def get_environment_variables(self) -> Dict[str, str]:
        """生成环境变量配置"""
        env_vars = {}
        
        if not self.config:
            self.load_config()
        
        for datasource in self.config.datasources:
            if not datasource.enabled:
                continue
            
            prefix = f"{datasource.name.upper()}_"
            
            # 连接配置
            for key, value in datasource.connection.items():
                env_key = f"{prefix}{key.upper()}"
                env_vars[env_key] = str(value)
            
            # 设置配置
            for key, value in datasource.settings.items():
                env_key = f"{prefix}SETTINGS_{key.upper()}"
                env_vars[env_key] = str(value)
        
        return env_vars
    
    def export_config(self, format: str = 'yaml', output_path: str = None) -> str:
        """导出配置文件"""
        if not self.config:
            self.load_config()
        
        if format == 'yaml':
            config_dict = {
                'datacenter': self.config.datacenter,
                'datasources': [
                    {
                        'name': ds.name,
                        'type': ds.type,
                        'enabled': ds.enabled,
                        'description': ds.description,
                        'connection': ds.connection,
                        'settings': ds.settings,
                        **(({'tables': ds.tables} if ds.tables else {})),
                        **(({'collections': ds.collections} if ds.collections else {})),
                        **(({'indices': ds.indices} if ds.indices else {})),
                        **(({'endpoints': ds.endpoints} if ds.endpoints else {})),
                        **(({'headers': ds.headers} if ds.headers else {})),
                        **(({'schemas': ds.schemas} if ds.schemas else {}))
                    }
                    for ds in self.config.datasources
                ],
                'servers': [
                    {
                        'datasource': server.datasource,
                        'port': server.port,
                        'log_level': server.log_level
                    }
                    for server in self.config.servers
                ],
                'management': self.config.management,
                'security': self.config.security,
                'logging': self.config.logging,
                'monitoring': self.config.monitoring
            }
            
            content = yaml.dump(config_dict, default_flow_style=False, allow_unicode=True)
            
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return content
        
        raise ValueError(f"不支持的格式: {format}")

# 使用示例
if __name__ == "__main__":
    # 创建配置加载器
    config_loader = ConfigLoader("config.yaml")
    
    try:
        # 加载配置
        config = config_loader.load_config()
        print(f"数据中心: {config.datacenter['name']}")
        print(f"数据源数量: {len(config.datasources)}")
        print(f"服务器数量: {len(config.servers)}")
        
        # 验证配置
        errors = config_loader.validate_config()
        if errors:
            print("配置验证错误:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("配置验证通过")
        
        # 获取启用的数据源
        enabled_datasources = config_loader.get_enabled_datasources()
        print(f"启用的数据源: {[ds.name for ds in enabled_datasources]}")
        
        # 生成连接字符串
        for datasource in enabled_datasources[:3]:  # 只显示前3个
            conn_str = config_loader.get_connection_string(datasource.name)
            if conn_str:
                print(f"{datasource.name} 连接字符串: {conn_str}")
        
    except Exception as e:
        print(f"配置加载失败: {e}")