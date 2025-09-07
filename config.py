import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TelegramConfig:
    """Telegram Bot 配置"""
    bot_token: str
    allowed_user_ids: List[int]
    admin_user_ids: List[int] = field(default_factory=list)
    connect_timeout: float = 30.0
    read_timeout: float = 30.0
    pool_timeout: float = 60.0
    connection_pool_size: int = 20
    
    def __post_init__(self):
        if not self.bot_token:
            raise ValueError("❌ TELEGRAM_BOT_TOKEN 不能为空")
        if not self.allowed_user_ids:
            raise ValueError("❌ ALLOWED_USER_IDS 不能为空")
        
        # 如果没有配置管理员，则所有允许的用户都是管理员
        if not self.admin_user_ids:
            self.admin_user_ids = self.allowed_user_ids.copy()
            logger.info("ℹ️ 未配置ADMIN_USER_IDS，所有ALLOWED_USER_IDS都将作为管理员")
        
        # 验证超时配置
        if self.connect_timeout <= 0:
            logger.warning("⚠️ connect_timeout 必须大于0，使用默认值30.0")
            self.connect_timeout = 30.0
        if self.read_timeout <= 0:
            logger.warning("⚠️ read_timeout 必须大于0，使用默认值30.0")
            self.read_timeout = 30.0
        if self.pool_timeout <= 0:
            logger.warning("⚠️ pool_timeout 必须大于0，使用默认值60.0")
            self.pool_timeout = 60.0
        if self.connection_pool_size <= 0:
            logger.warning("⚠️ connection_pool_size 必须大于0，使用默认值20")
            self.connection_pool_size = 20
        



@dataclass
class DanmakuAPIConfig:
    """弹幕API配置"""
    base_url: str
    api_key: str
    timeout: int = 60
    headers: Dict[str, str] = field(default_factory=lambda: {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    })
    
    def __post_init__(self):
        if not self.base_url:
            raise ValueError("❌ DANMAKU_API_BASE_URL 不能为空")
        if not self.api_key:
            raise ValueError("❌ DANMAKU_API_KEY 不能为空")
        
        # 验证超时配置
        if self.timeout <= 0:
            logger.warning("⚠️ API timeout 必须大于0，使用默认值60")
            self.timeout = 60
        
        # 确保URL格式正确
        if not self.base_url.startswith(('http://', 'https://')):
            raise ValueError("❌ DANMAKU_API_BASE_URL 必须以 http:// 或 https:// 开头")
        
        # 移除末尾的斜杠
        self.base_url = self.base_url.rstrip('/')


@dataclass
class TMDBConfig:
    """TMDB API 配置"""
    api_key: Optional[str] = None
    base_url: str = "https://api.themoviedb.org/3"
    
    def __post_init__(self):
        if not self.api_key or not self.api_key.strip():
            logger.info("ℹ️ 未配置 TMDB API Key，将跳过 TMDB 辅助搜索")
            return
            
        placeholder_values = ['your_tmdb_api_key_here', 'YOUR_TMDB_API_KEY', 'placeholder']
        if self.api_key.strip() in placeholder_values:
            logger.info("ℹ️ TMDB API Key为占位符值，请配置真实的API密钥")
            return
            
        # 验证API密钥
        if self._validate_api_key():
            logger.info("✅ TMDB API 配置已加载并验证通过，将启用辅助搜索功能")
        else:
            logger.info("❌ TMDB API Key验证失败，请检查密钥是否正确")
    
    @property
    def enabled(self) -> bool:
        """检查TMDB配置是否可用"""
        if not self.api_key or not self.api_key.strip():
            return False
        # 检查是否为占位符值
        placeholder_values = ['your_tmdb_api_key_here', 'YOUR_TMDB_API_KEY', 'placeholder']
        if self.api_key.strip() in placeholder_values:
            return False
        # 验证API密钥有效性
        return self._validate_api_key()
    
    def _validate_api_key(self) -> bool:
        """验证API密钥有效性"""
        try:
            import requests
            # 直接在这里验证，避免循环导入
            url = f"{self.base_url}/configuration"
            params = {'api_key': self.api_key}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return 'images' in data and 'base_url' in data.get('images', {})
            else:
                logger.debug(f"TMDB API密钥验证失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.debug(f"TMDB API密钥验证异常: {e}")
            return False


@dataclass
class TVDBConfig:
    """TVDB API 配置"""
    api_key: Optional[str] = None
    base_url: str = "https://api4.thetvdb.com/v4"
    
    def __post_init__(self):
        if not self.api_key or not self.api_key.strip():
            logger.info("ℹ️ 未配置 TVDB API Key，将跳过 TVDB 辅助搜索")
            return
            
        placeholder_values = ['your_tvdb_api_key_here', 'YOUR_TVDB_API_KEY', 'placeholder']
        if self.api_key.strip() in placeholder_values:
            logger.info("ℹ️ TVDB API Key为占位符值，请配置真实的API密钥")
            return
            
        logger.info("✅ TVDB API 配置已加载")
    
    @property
    def enabled(self) -> bool:
        """检查TVDB配置是否可用"""
        if not self.api_key or not self.api_key.strip():
            return False
        # 检查是否为占位符值
        placeholder_values = ['your_tvdb_api_key_here', 'YOUR_TVDB_API_KEY', 'placeholder']
        if self.api_key.strip() in placeholder_values:
            return False
        return True


@dataclass
class BGMConfig:
    """BGM (Bangumi) API 配置"""
    access_token: Optional[str] = None
    base_url: str = "https://api.bgm.tv"
    
    def __post_init__(self):
        if not self.access_token or not self.access_token.strip():
            logger.info("ℹ️ 未配置 BGM Access Token，将使用网页爬虫方式获取数据")
            return
            
        placeholder_values = ['your_bgm_access_token_here', 'YOUR_BGM_ACCESS_TOKEN', 'placeholder']
        if self.access_token.strip() in placeholder_values:
            logger.info("ℹ️ BGM Access Token为占位符值，将使用网页爬虫方式获取数据")
            return
            
        logger.info("✅ BGM API 配置已加载，将使用API方式获取数据")
    
    @property
    def enabled(self) -> bool:
        """检查BGM API配置是否可用"""
        if not self.access_token or not self.access_token.strip():
            return False
        # 检查是否为占位符值
        placeholder_values = ['your_bgm_access_token_here', 'YOUR_BGM_ACCESS_TOKEN', 'placeholder']
        if self.access_token.strip() in placeholder_values:
            return False
        return True


@dataclass
class ProxyConfig:
    """代理配置（使用Docker环境变量）"""
    
    def __post_init__(self):
        # 检查Docker代理环境变量
        http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
        https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
        
        if http_proxy or https_proxy:
            logger.info(f"🌐 检测到Docker代理配置: HTTP_PROXY={http_proxy}, HTTPS_PROXY={https_proxy}")
    
    @property
    def enabled(self) -> bool:
        """检查代理是否启用（基于Docker环境变量）"""
        return bool(os.getenv('HTTP_PROXY') or os.getenv('http_proxy') or 
                   os.getenv('HTTPS_PROXY') or os.getenv('https_proxy'))
    
    @property
    def url(self) -> Optional[str]:
        """获取代理URL（优先返回HTTPS代理）"""
        return (os.getenv('HTTPS_PROXY') or os.getenv('https_proxy') or 
                os.getenv('HTTP_PROXY') or os.getenv('http_proxy'))


@dataclass
class AppConfig:
    """应用程序配置"""
    log_level: str = "INFO"
    debug: bool = False
    environment: str = "production"
    api_timeout: int = 60
    
    def __post_init__(self):
        # 验证日志级别
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.log_level = self.log_level.upper()
        if self.log_level not in valid_levels:
            logger.warning(f"⚠️ 无效的日志级别 '{self.log_level}'，使用默认值 'INFO'")
            self.log_level = "INFO"
        
        # 设置调试模式
        if self.environment.lower() in ['dev', 'development', 'debug']:
            self.debug = True
            if self.log_level == "INFO":
                self.log_level = "DEBUG"


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self._telegram: Optional[TelegramConfig] = None
        self._danmaku_api: Optional[DanmakuAPIConfig] = None
        self._tmdb: Optional[TMDBConfig] = None
        self._tvdb: Optional[TVDBConfig] = None
        self._proxy: Optional[ProxyConfig] = None
        self._app: Optional[AppConfig] = None
        self._load_config()
    
    def _parse_user_ids(self, user_ids_str: str) -> List[int]:
        """解析用户ID字符串"""
        if not user_ids_str:
            return []
        
        user_ids = []
        for id_str in user_ids_str.split(","):
            id_str = id_str.strip()
            if id_str.isdigit():
                user_ids.append(int(id_str))
            else:
                logger.warning(f"⚠️ 忽略无效的用户ID: {id_str}")
        
        return user_ids
    
    def _load_config(self):
        """加载配置"""
        try:
            # 加载Telegram配置
            telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            user_ids_str = os.getenv("ALLOWED_USER_IDS", "")
            user_ids = self._parse_user_ids(user_ids_str)
            admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
            admin_ids = self._parse_user_ids(admin_ids_str)
            
            self._telegram = TelegramConfig(
                bot_token=telegram_token,
                allowed_user_ids=user_ids,
                admin_user_ids=admin_ids,
                connect_timeout=float(os.getenv("TELEGRAM_CONNECT_TIMEOUT", 30.0)),
                read_timeout=float(os.getenv("TELEGRAM_READ_TIMEOUT", 30.0)),
                pool_timeout=float(os.getenv("TELEGRAM_POOL_TIMEOUT", 60.0)),
                connection_pool_size=int(os.getenv("TELEGRAM_CONNECTION_POOL_SIZE", 20))
            )
            
            # 加载弹幕API配置
            self._danmaku_api = DanmakuAPIConfig(
                base_url=os.getenv("DANMAKU_API_BASE_URL", ""),
                api_key=os.getenv("DANMAKU_API_KEY", ""),
                timeout=int(os.getenv("API_TIMEOUT", 120))
            )
            
            # 加载TMDB配置
            self._tmdb = TMDBConfig(
                api_key=os.getenv("TMDB_API_KEY", "")
            )
            
            # 加载TVDB配置
            self._tvdb = TVDBConfig(
                api_key=os.getenv("TVDB_API_KEY", "")
            )
            
            # 加载BGM配置
            self._bgm = BGMConfig(
                access_token=os.getenv("BGM_ACCESS_TOKEN", "")
            )
            
            # 加载代理配置（基于Docker环境变量）
            self._proxy = ProxyConfig()
            
            # 加载应用配置
            self._app = AppConfig(
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                debug=os.getenv("DEBUG", "false").lower() in ['true', '1', 'yes'],
                environment=os.getenv("ENVIRONMENT", "production"),
                api_timeout=int(os.getenv("API_TIMEOUT", 120))
            )
            
            logger.info("✅ 配置加载成功")
            
        except Exception as e:
            logger.error(f"❌ 配置加载失败: {e}")
            raise
    
    @property
    def telegram(self) -> TelegramConfig:
        """获取Telegram配置"""
        if self._telegram is None:
            raise RuntimeError("Telegram配置未初始化")
        return self._telegram
    
    @property
    def danmaku_api(self) -> DanmakuAPIConfig:
        """获取弹幕API配置"""
        if self._danmaku_api is None:
            raise RuntimeError("弹幕API配置未初始化")
        return self._danmaku_api
    
    @property
    def tmdb(self) -> TMDBConfig:
        """获取TMDB配置"""
        if self._tmdb is None:
            raise RuntimeError("TMDB配置未初始化")
        return self._tmdb
    
    @property
    def tvdb(self) -> TVDBConfig:
        """获取TVDB配置"""
        if self._tvdb is None:
            raise RuntimeError("TVDB配置未初始化")
        return self._tvdb
    
    @property
    def bgm(self) -> BGMConfig:
        """获取BGM配置"""
        if self._bgm is None:
            raise RuntimeError("BGM配置未初始化")
        return self._bgm
    
    @property
    def proxy(self) -> ProxyConfig:
        """获取代理配置"""
        if self._proxy is None:
            raise RuntimeError("代理配置未初始化")
        return self._proxy
    
    @property
    def app(self) -> AppConfig:
        """获取应用配置"""
        if self._app is None:
            raise RuntimeError("应用配置未初始化")
        return self._app
    
    def reload(self):
        """重新加载配置"""
        load_dotenv(override=True)
        self._load_config()
        logger.info("🔄 配置已重新加载")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要（隐藏敏感信息）"""
        return {
            "telegram": {
                "bot_token": "***" + self.telegram.bot_token[-4:] if self.telegram.bot_token else "未配置",
                "allowed_users_count": len(self.telegram.allowed_user_ids),
                "timeouts": {
                    "connect": self.telegram.connect_timeout,
                    "read": self.telegram.read_timeout,
                    "pool": self.telegram.pool_timeout
                },
                "pool_size": self.telegram.connection_pool_size
            },
            "danmaku_api": {
                "base_url": self.danmaku_api.base_url,
                "api_key": "***" + self.danmaku_api.api_key[-4:] if self.danmaku_api.api_key else "未配置",
                "timeout": self.danmaku_api.timeout
            },
            "tmdb": {
                "enabled": self.tmdb.enabled,
                "api_key": "***" + self.tmdb.api_key[-4:] if self.tmdb.api_key else "未配置",
                "base_url": self.tmdb.base_url
            },
            "tvdb": {
                "enabled": self.tvdb.enabled,
                "api_key": "***" + self.tvdb.api_key[-4:] if self.tvdb.api_key else "未配置",
                "base_url": self.tvdb.base_url
            },
            "proxy": {
                "enabled": self.proxy.enabled,
                "url": self.proxy.url if self.proxy.enabled else "未配置"
            },
            "app": {
                "log_level": self.app.log_level,
                "debug": self.app.debug,
                "environment": self.app.environment
            }
        }


# 创建全局配置实例
config = ConfigManager()

# 向后兼容的变量（保持现有代码正常工作）
TELEGRAM_BOT_TOKEN = config.telegram.bot_token
ALLOWED_USER_IDS = config.telegram.allowed_user_ids
ADMIN_USER_IDS = config.telegram.admin_user_ids
DANMAKU_API_BASE_URL = config.danmaku_api.base_url
DANMAKU_API_KEY = config.danmaku_api.api_key
DANMAKU_API_HEADERS = config.danmaku_api.headers
API_TIMEOUT = config.danmaku_api.timeout
# 代理配置现在通过Docker环境变量处理
# SOCKS_PROXY_URL 和 HTTP_PROXY_URL 已废弃，请使用 HTTP_PROXY 和 HTTPS_PROXY
TELEGRAM_CONNECT_TIMEOUT = config.telegram.connect_timeout
TELEGRAM_READ_TIMEOUT = config.telegram.read_timeout
TELEGRAM_POOL_TIMEOUT = config.telegram.pool_timeout
TELEGRAM_CONNECTION_POOL_SIZE = config.telegram.connection_pool_size
LOG_LEVEL = config.app.log_level

# TMDB配置
TMDB_API_KEY = config.tmdb.api_key
TMDB_BASE_URL = config.tmdb.base_url
TMDB_ENABLED = config.tmdb.enabled

# TVDB配置
TVDB_API_KEY = config.tvdb.api_key
TVDB_BASE_URL = config.tvdb.base_url
TVDB_ENABLED = config.tvdb.enabled

# BGM配置
BGM_ACCESS_TOKEN = config.bgm.access_token
BGM_BASE_URL = config.bgm.base_url
BGM_ENABLED = config.bgm.enabled