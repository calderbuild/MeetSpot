import threading
import tomllib
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = get_project_root()
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"


class LLMSettings(BaseModel):
    model: str = Field(..., description="Model name")
    base_url: str = Field(..., description="API base URL")
    api_key: str = Field(..., description="API key")
    max_tokens: int = Field(4096, description="Maximum number of tokens per request")
    max_input_tokens: Optional[int] = Field(
        None,
        description="Maximum input tokens to use across all requests (None for unlimited)",
    )
    temperature: float = Field(1.0, description="Sampling temperature")
    api_type: str = Field(..., description="Azure, Openai, or Ollama")
    api_version: str = Field(..., description="Azure Openai version if AzureOpenai")


class ProxySettings(BaseModel):
    server: str = Field(None, description="Proxy server address")
    username: Optional[str] = Field(None, description="Proxy username")
    password: Optional[str] = Field(None, description="Proxy password")


class SearchSettings(BaseModel):
    engine: str = Field(default="Google", description="Search engine the llm to use")


class AMapSettings(BaseModel):
    """高德地图API配置"""

    api_key: str = Field(..., description="高德地图API密钥")
    js_api_key: Optional[str] = Field(None, description="高德地图JavaScript API密钥")
    security_js_code: Optional[str] = Field(
        None, description="高德地图JavaScript API安全密钥"
    )

    @property
    def web_api_key(self) -> Optional[str]:
        """兼容历史字段名。"""
        return self.js_api_key


class GoogleMapsSettings(BaseModel):
    """Google Maps API 配置 -- 用于国际场景 POI 搜索与地理编码"""

    api_key: str = Field("", description="Google Maps Platform API key")


class BrowserSettings(BaseModel):
    headless: bool = Field(False, description="Whether to run browser in headless mode")
    disable_security: bool = Field(
        True, description="Disable browser security features"
    )
    extra_chromium_args: List[str] = Field(
        default_factory=list, description="Extra arguments to pass to the browser"
    )
    chrome_instance_path: Optional[str] = Field(
        None, description="Path to a Chrome instance to use"
    )
    wss_url: Optional[str] = Field(
        None, description="Connect to a browser instance via WebSocket"
    )
    cdp_url: Optional[str] = Field(
        None, description="Connect to a browser instance via CDP"
    )
    proxy: Optional[ProxySettings] = Field(
        None, description="Proxy settings for the browser"
    )
    max_content_length: int = Field(
        2000, description="Maximum length for content retrieval operations"
    )


class SandboxSettings(BaseModel):
    """Configuration for the execution sandbox"""

    use_sandbox: bool = Field(False, description="Whether to use the sandbox")
    image: str = Field("python:3.12-slim", description="Base image")
    work_dir: str = Field("/workspace", description="Container working directory")
    memory_limit: str = Field("512m", description="Memory limit")
    cpu_limit: float = Field(1.0, description="CPU limit")
    timeout: int = Field(300, description="Default command timeout (seconds)")
    network_enabled: bool = Field(
        False, description="Whether network access is allowed"
    )


class AppConfig(BaseModel):
    llm: Dict[str, LLMSettings]
    sandbox: Optional[SandboxSettings] = Field(
        None, description="Sandbox configuration"
    )
    browser_config: Optional[BrowserSettings] = Field(
        None, description="Browser configuration"
    )
    search_config: Optional[SearchSettings] = Field(
        None, description="Search configuration"
    )
    amap: Optional[AMapSettings] = Field(None, description="高德地图API配置")
    google_maps: Optional[GoogleMapsSettings] = Field(
        None, description="Google Maps API 配置（国际场景）"
    )

    class Config:
        arbitrary_types_allowed = True


class Config:
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._config = None
                    self._load_initial_config()
                    self._initialized = True

    @staticmethod
    def _get_config_path() -> Path:
        root = PROJECT_ROOT
        config_path = root / "config" / "config.toml"
        if config_path.exists():
            return config_path
        example_path = root / "config" / "config.toml.example"
        if example_path.exists():
            return example_path
        # 如果都没有找到，返回默认路径，让后续创建默认配置
        return config_path

    def _load_config(self) -> dict:
        try:
            config_path = self._get_config_path()
            if not config_path.exists():
                # 创建默认配置
                default_config = {
                    "llm": {
                        "model": "gpt-3.5-turbo",
                        "api_key": "",
                        "base_url": "",
                        "max_tokens": 4096,
                        "temperature": 1.0,
                        "api_type": "",
                        "api_version": "",
                    },
                    "amap": {"api_key": "", "security_js_code": ""},
                    "log": {"level": "info", "file": "logs/meetspot.log"},
                    "server": {"host": "0.0.0.0", "port": 8000},
                }
                return default_config

            with config_path.open("rb") as f:
                return tomllib.load(f)
        except Exception as e:
            # 如果加载失败，返回默认配置
            print(f"Failed to load config file, using defaults: {e}")
            return {
                "llm": {
                    "model": "gpt-3.5-turbo",
                    "api_key": "",
                    "base_url": "",
                    "max_tokens": 4096,
                    "temperature": 1.0,
                    "api_type": "",
                    "api_version": "",
                }
            }

    def _load_initial_config(self):
        raw_config = self._load_config()
        base_llm = raw_config.get("llm", {})

        # 从环境变量读取敏感信息
        import os

        openai_api_key = os.getenv("OPENAI_API_KEY", "") or os.getenv("LLM_API_KEY", "")
        amap_api_key = os.getenv("AMAP_API_KEY", "")
        amap_js_api_key = os.getenv("AMAP_JS_API_KEY", "")
        amap_security_js_code = os.getenv("AMAP_SECURITY_JS_CODE", "")
        google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        # 支持 Render 部署的环境变量配置
        # 默认走 OpenRouter（统一 API 网关，支持多家模型）+ openai/gpt-4o-mini（便宜快速）
        llm_base_url = (
            os.getenv("LLM_API_BASE", "")
            or base_llm.get("base_url", "")
            or "https://openrouter.ai/api/v1"
        )
        llm_model = (
            os.getenv("LLM_MODEL", "")
            or base_llm.get("model", "")
            or "openai/gpt-4o-mini"
        )

        llm_overrides = {
            k: v for k, v in raw_config.get("llm", {}).items() if isinstance(v, dict)
        }

        default_settings = {
            "model": llm_model,  # 优先使用环境变量
            "base_url": llm_base_url,  # 优先使用环境变量
            "api_key": openai_api_key,  # 从环境变量获取
            "max_tokens": base_llm.get("max_tokens", 4096),
            "max_input_tokens": base_llm.get("max_input_tokens"),
            "temperature": base_llm.get("temperature", 1.0),
            "api_type": base_llm.get("api_type", ""),
            "api_version": base_llm.get("api_version", ""),
        }

        # handle browser config.
        browser_config = raw_config.get("browser", {})
        browser_settings = None

        if browser_config:
            # handle proxy settings.
            proxy_config = browser_config.get("proxy", {})
            proxy_settings = None

            if proxy_config and proxy_config.get("server"):
                proxy_settings = ProxySettings(
                    **{
                        k: v
                        for k, v in proxy_config.items()
                        if k in ["server", "username", "password"] and v
                    }
                )

            # filter valid browser config parameters.
            valid_browser_params = {
                k: v
                for k, v in browser_config.items()
                if k in BrowserSettings.__annotations__ and v is not None
            }

            # if there is proxy settings, add it to the parameters.
            if proxy_settings:
                valid_browser_params["proxy"] = proxy_settings

            # only create BrowserSettings when there are valid parameters.
            if valid_browser_params:
                browser_settings = BrowserSettings(**valid_browser_params)

        search_config = raw_config.get("search", {})
        search_settings = None
        if search_config:
            search_settings = SearchSettings(**search_config)
        sandbox_config = raw_config.get("sandbox", {})
        if sandbox_config:
            sandbox_settings = SandboxSettings(**sandbox_config)
        else:
            sandbox_settings = SandboxSettings()

        # 处理高德地图API配置
        amap_config = raw_config.get("amap", {})
        amap_settings = None
        # 优先使用环境变量中的 AMAP_API_KEY
        if amap_api_key:
            amap_settings = AMapSettings(
                api_key=amap_api_key,
                js_api_key=(
                    amap_js_api_key
                    or amap_config.get("js_api_key", "")
                    or amap_config.get("web_api_key", "")
                ),
                security_js_code=amap_security_js_code
                or amap_config.get("security_js_code", ""),
            )
        elif amap_config and amap_config.get("api_key"):
            amap_settings = AMapSettings(
                api_key=amap_config.get("api_key", ""),
                js_api_key=(
                    amap_js_api_key
                    or amap_config.get("js_api_key", "")
                    or amap_config.get("web_api_key", "")
                ),
                security_js_code=amap_security_js_code
                or amap_config.get("security_js_code", ""),
            )

        # 处理 Google Maps API 配置（国际场景）
        google_config = raw_config.get("google", {}) or raw_config.get(
            "google_maps", {}
        )
        google_settings = None
        resolved_google_key = google_maps_api_key or google_config.get("api_key", "")
        if resolved_google_key:
            google_settings = GoogleMapsSettings(api_key=resolved_google_key)

        config_dict = {
            "llm": {
                "default": default_settings,
                **{
                    name: {**default_settings, **override_config}
                    for name, override_config in llm_overrides.items()
                },
            },
            "sandbox": sandbox_settings,
            "browser_config": browser_settings,
            "search_config": search_settings,
            "amap": amap_settings,
            "google_maps": google_settings,
        }

        self._config = AppConfig(**config_dict)

    @property
    def llm(self) -> Dict[str, LLMSettings]:
        return self._config.llm

    @property
    def sandbox(self) -> SandboxSettings:
        return self._config.sandbox

    @property
    def browser_config(self) -> Optional[BrowserSettings]:
        return self._config.browser_config

    @property
    def search_config(self) -> Optional[SearchSettings]:
        return self._config.search_config

    @property
    def amap(self) -> Optional[AMapSettings]:
        """获取高德地图API配置"""
        return self._config.amap

    @property
    def google_maps(self) -> Optional[GoogleMapsSettings]:
        """获取 Google Maps API 配置（国际场景）"""
        return self._config.google_maps

    @property
    def workspace_root(self) -> Path:
        """Get the workspace root directory"""
        return WORKSPACE_ROOT

    @property
    def root_path(self) -> Path:
        """Get the root path of the application"""
        return PROJECT_ROOT


config = Config()
