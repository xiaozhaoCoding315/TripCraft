"""
TripCraft Application Configuration

使用 pydantic-settings 管理配置，支持环境变量覆盖。
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    """应用配置"""

    app_name: str = Field(default="TripCraft API", description="应用名称")
    app_env: str = Field(default="development", description="运行环境")
    cors_origins: str = Field(
        default="http://localhost:5173",
        description="允许的 CORS 源（逗号分隔）",
    )

    # ========== 认证配置 ==========
    secret_key: str = Field(
        default="your-secret-key-change-in-production-1234567890abcdef",
        description="JWT 签名密钥（至少 32 字符，生产环境必须修改）",
    )
    token_expire_hours: int = Field(
        default=24,
        description="令牌过期时间（小时）",
    )

    # ========== LLM 配置 ==========
    dashscope_api_key: str | None = Field(
        default=None,
        description="DashScope API 密钥",
    )
    qwen_model: str = Field(default="qwen-plus", description="Qwen 模型名称")
    qwen_embedding_model: str = Field(
        default="text-embedding-v3", description="Qwen 嵌入模型"
    )
    qwen_embedding_dimension: int = Field(
        default=1024, description="嵌入向量维度"
    )

    # ========== Qdrant 配置 ==========
    qdrant_url: str = Field(
        default="http://192.168.150.128:6333",
        description="Qdrant 向量数据库地址",
    )
    qdrant_api_key: str | None = Field(
        default=None,
        description="Qdrant API 密钥",
    )
    qdrant_travel_notes_collection: str = Field(
        default="travel_notes", description="游记集合名"
    )
    qdrant_attractions_collection: str = Field(
        default="attractions", description="景点集合名"
    )

    # ========== 高德地图配置 ==========
    amap_api_key: str | None = Field(
        default=None,
        description="高德地图 API Key（Web端）",
    )
    amap_web_js_key: str | None = Field(
        default=None,
        description="高德地图 Web JS Key",
    )
    max_critic_rounds: int = Field(
        default=3,
        description="Critic Agent 最大审查轮数",
    )

    # ========== PostgreSQL 配置 ==========
    postgres_host: str = Field(
        default="192.168.150.128",
        description="PostgreSQL 主机地址",
    )
    postgres_port: int = Field(
        default=5432,
        description="PostgreSQL 端口",
    )
    postgres_user: str = Field(
        default="postgres",
        description="PostgreSQL 用户",
    )
    postgres_password: str = Field(
        default="postgres",
        description="PostgreSQL 密码",
    )
    postgres_db: str = Field(
        default="tripcraft",
        description="PostgreSQL 数据库名",
    )

    # ========== Redis 配置 ==========
    redis_enabled: bool = Field(
        default=True,
        description="是否启用 Redis 缓存",
    )
    redis_url: str = Field(
        default="redis://:159753852@192.168.150.128:6379/0",
        description="Redis 连接 URL",
    )

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def qwen_base_url(self) -> str:
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"

    @property
    def resolved_database_path(self) -> Path:
        """向后兼容：不再使用 SQLite，但保留此属性避免导入错误"""
        return BACKEND_ROOT / "data" / "tripcraft.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
