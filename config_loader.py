"""
MCP数据中心配置文件加载器 - 简化版
"""
import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DataSource:
    """数据源配置"""
    name: str
    type: str
    enabled: bool = True
    description: str = ""
    connection: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    # 动态字段：tables/collections/indices/endpoints/headers/schemas
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    """统一配置"""
    datacenter: Dict[str, str] = field(default_factory=dict)
    datasources: List[DataSource] = field(default_factory=list)
    servers: List[Dict[str, Any]] = field(default_factory=list)
    management: Dict[str, Any] = field(default_factory=dict)
    security: Dict[str, Any] = field(default_factory=dict)
    logging: Dict[str, Any] = field(default_factory=dict)
    monitoring: Dict[str, Any] = field(default_factory=dict)


class ConfigLoader:
    """配置加载器"""
    
    # 连接字符串模板
    CONNECTION_TEMPLATES = {
        'postgresql': "postgresql://{username}:{password}@{host}:{port}/{database}",
        'mysql': "mysql://{username}:{password}@{host}:{port}/{database}",
        'sqlite': "sqlite:///{database_path}",
        'mongodb': "mongodb://{auth}{host}:{port}/{database}",
        'redis': "redis://{auth}{host}:{port}/{database}"
    }
    
    # 必需字段验证
    REQUIRED_FIELDS = {
        'postgresql': ['host', 'port', 'database', 'username', 'password'],
        'mysql': ['host', 'port', 'database', 'username', 'password'],
        'sqlite': ['database_path'],
        'mongodb': ['host', 'port', 'database'],
        'redis': ['host', 'port'],
        'elasticsearch': ['host', 'port'],
        'rest_api': ['base_url'],
        'graphql': ['endpoint']
    }
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config: Optional[Config] = None
    
    def load(self) -> Config:
        """加载配置"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 解析数据源
        datasources = []
        for ds in data.get('datasources', []):
            # 提取动态字段
            extras = {k: v for k, v in ds.items() 
                     if k not in ['name', 'type', 'enabled', 'description', 'connection', 'settings']}
            
            datasources.append(DataSource(
                name=ds['name'],
                type=ds['type'],
                enabled=ds.get('enabled', True),
                description=ds.get('description', ''),
                connection=ds.get('connection', {}),
                settings=ds.get('settings', {}),
                extras=extras
            ))
        
        self._config = Config(
            datacenter=data.get('datacenter', {}),
            datasources=datasources,
            servers=data.get('servers', []),
            management=data.get('management', {}),
            security=data.get('security', {}),
            logging=data.get('logging', {}),
            monitoring=data.get('monitoring', {})
        )
        
        return self._config
    
    @property
    def config(self) -> Config:
        """获取配置（懒加载）"""
        return self._config or self.load()
    
    def get_datasource(self, name: str) -> Optional[DataSource]:
        """获取指定数据源"""
        return next((ds for ds in self.config.datasources if ds.name == name), None)
    
    def get_enabled_datasources(self) -> List[DataSource]:
        """获取启用的数据源"""
        return [ds for ds in self.config.datasources if ds.enabled]
    
    def get_server(self, datasource_name: str) -> Optional[Dict[str, Any]]:
        """获取服务器配置"""
        return next((s for s in self.config.servers if s['datasource'] == datasource_name), None)
    
    def get_connection_string(self, datasource_name: str) -> Optional[str]:
        """生成连接字符串"""
        ds = self.get_datasource(datasource_name)
        if not ds or ds.type not in self.CONNECTION_TEMPLATES:
            return None
        
        conn = ds.connection
        template = self.CONNECTION_TEMPLATES[ds.type]
        
        try:
            if ds.type in ['mongodb', 'redis']:
                # 处理认证信息
                auth = f"{conn['username']}:{conn['password']}@" if conn.get('username') else ""
                return template.format(auth=auth, **conn)
            else:
                return template.format(**conn)
        except KeyError:
            return None
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        config = self.config
        
        # 验证数据源
        names = set()
        for ds in config.datasources:
            # 检查重复名称
            if ds.name in names:
                errors.append(f"数据源名称重复: {ds.name}")
            names.add(ds.name)
            
            # 检查必需字段
            if ds.type in self.REQUIRED_FIELDS:
                missing = [f for f in self.REQUIRED_FIELDS[ds.type] if f not in ds.connection]
                if missing:
                    errors.append(f"数据源 {ds.name} 缺少字段: {missing}")
        
        # 验证服务器
        ports = set()
        for server in config.servers:
            port = server.get('port')
            if port in ports:
                errors.append(f"端口冲突: {port}")
            ports.add(port)
            
            # 检查数据源引用
            if server.get('datasource') not in names:
                errors.append(f"服务器引用了不存在的数据源: {server.get('datasource')}")
        
        return errors
    
    def reload(self) -> Config:
        """重新加载配置"""
        self._config = None
        return self.load()
    
    def to_env_vars(self) -> Dict[str, str]:
        """转换为环境变量"""
        env_vars = {}
        
        for ds in self.get_enabled_datasources():
            prefix = f"{ds.name.upper()}_"
            
            # 连接配置
            for key, value in ds.connection.items():
                env_vars[f"{prefix}{key.upper()}"] = str(value)
            
            # 设置配置
            for key, value in ds.settings.items():
                env_vars[f"{prefix}SETTINGS_{key.upper()}"] = str(value)
        
        return env_vars


# 使用示例
if __name__ == "__main__":
    loader = ConfigLoader("config.yaml")
    
    try:
        config = loader.load()
        print(f"数据中心: {config.datacenter.get('name', 'N/A')}")
        print(f"数据源数量: {len(config.datasources)}")
        
        # 验证配置
        errors = loader.validate()
        if errors:
            print("配置错误:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("配置验证通过")
        
        # 显示启用的数据源
        enabled = loader.get_enabled_datasources()
        print(f"启用的数据源: {[ds.name for ds in enabled]}")
        
        # 生成连接字符串示例
        for ds in enabled[:3]:
            conn_str = loader.get_connection_string(ds.name)
            if conn_str:
                print(f"{ds.name}: {conn_str}")
    
    except Exception as e:
        print(f"配置加载失败: {e}")