import logging
import sys
import warnings
from enum import Enum
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# backend/app/config.py → repo root is two levels up from app/
BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent

# Default secrets that must NEVER be used in production
_INSECURE_SECRETS = {
    "dev-secret-key",
    "dev-secret-key-local",
    "dev-jwt-secret",
    "dev-jwt-secret-local",
    "changeme",
    "secret",
    "your-api-key-here",
}


class Environment(str, Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    APP_NAME: str = "劳权智助"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    # Backward compatibility alias: APP_ENV is deprecated, use ENVIRONMENT instead
    APP_ENV: str = ""
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str = "dev-secret-key"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8010

    DATABASE_URL: str = "sqlite+aiosqlite:///./laboraid.db"
    DATABASE_URL_SYNC: str = "sqlite:///./laboraid.db"

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = "dev-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Primary LLM config — 填入 .env，详见 docs/api-config-locations.md
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-v4-pro"
    LLM_MAX_TOKENS: int = 8192

    # Word 导出：html=HTML中间格式（预览和导出一致，推荐）；court=法院仿宋/黑体；native=Word内置标题样式
    WORD_EXPORT_MODE: str = "html"

    # Vision / OCR LLM（默认阿里百炼 qwen-vl-ocr，与文本 LLM 分离）
    VISION_LLM_API_KEY: str = ""
    VISION_LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    VISION_LLM_MODEL: str = "qwen-vl-ocr-latest"
    VISION_LLM_MAX_TOKENS: int = 4096

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION: str = "laboraid_docs"

    CHINESE_LAW_MCP_ENABLED: bool = True

    QICHACHA_API_KEY: str = ""
    QICHACHA_SECRET_KEY: str = ""
    QICHACHA_API_URL: str = "https://api.qichacha.com"

    # 得理法律开放平台（法规/案例检索）
    DELILEGAL_ENABLED: bool = False
    DELILEGAL_BASE_URL: str = "https://openapi.delilegal.com"
    DELILEGAL_APPID: str = ""
    DELILEGAL_SECRET: str = ""

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_BASE_URL: str = ""

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    VAULT_QUOTA_MB: int = 500
    VAULT_MAX_FILES: int = 500

    CORS_ORIGINS: str = "http://localhost:5320,http://127.0.0.1:5320,http://localhost:3000"

    # 知识库官方法规定时同步（默认每周日 03:00 UTC+本地时区）
    KNOWLEDGE_CRAWL_SCHEDULE_ENABLED: bool = True
    KNOWLEDGE_CRAWL_WEEKDAY: int = 6  # 0=周一 … 6=周日
    KNOWLEDGE_CRAWL_HOUR: int = 3
    KNOWLEDGE_CRAWL_MINUTE: int = 0

    # 逗号分隔；注册/登录时自动提升为 admin（如 admin@example.com）
    ADMIN_EMAIL: str = ""

    # 首次启动时自动创建的初始管理员（仅当该邮箱不存在时创建）
    INITIAL_ADMIN_NAME: str = "Admin"
    INITIAL_ADMIN_EMAIL: str = "admin@laboraid.local"
    INITIAL_ADMIN_PASSWORD: str = "123456"

    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    LOG_FILE: str = ""  # Set to a file path to enable file logging in production

    # Email error notifications (production)
    ERROR_EMAIL_ENABLED: bool = False
    ERROR_EMAIL_SMTP_HOST: str = ""
    ERROR_EMAIL_SMTP_PORT: int = 587
    ERROR_EMAIL_SMTP_USER: str = ""
    ERROR_EMAIL_SMTP_PASSWORD: str = ""
    ERROR_EMAIL_FROM: str = ""
    ERROR_EMAIL_TO: str = ""  # Comma-separated list of recipients

    model_config = {
        "env_file": [str(Path(__file__).resolve().parent.parent.parent / ".env"), ".env"],
        "env_file_encoding": "utf-8",
    }

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_llm_env(cls, data):
        """Accept legacy CLAUDE_* env vars when LLM_* is unset."""
        if not isinstance(data, dict):
            return data
        for new_key, old_key in (
            ("LLM_API_KEY", "CLAUDE_API_KEY"),
            ("LLM_BASE_URL", "CLAUDE_BASE_URL"),
            ("LLM_MODEL", "CLAUDE_MODEL"),
            ("LLM_MAX_TOKENS", "CLAUDE_MAX_TOKENS"),
        ):
            if not data.get(new_key) and data.get(old_key):
                data[new_key] = data[old_key]
        return data

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def normalize_environment(cls, v):
        """Accept string values for ENVIRONMENT."""
        if isinstance(v, str):
            return Environment(v.lower())
        return v

    @field_validator("APP_ENV", mode="before")
    @classmethod
    def deprecate_app_env(cls, v):
        """Swallow APP_ENV value -- it's a backward-compat alias."""
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(
                f"LOG_LEVEL must be one of {sorted(allowed)}, got '{v}'"
            )
        return upper

    @field_validator("CHROMA_PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"CHROMA_PORT must be between 1 and 65535, got {v}")
        return v

    def model_post_init(self, __context) -> None:
        """Validate security settings based on environment.

        If APP_ENV is set (backward compat), use it to override ENVIRONMENT
        when ENVIRONMENT is still at its default.
        """
        if self.APP_ENV and self.APP_ENV.strip():
            try:
                self.ENVIRONMENT = Environment(self.APP_ENV.strip().lower())
            except ValueError:
                pass  # Ignore invalid APP_ENV values

        is_production = self.ENVIRONMENT == Environment.PRODUCTION

        # Debug mode must be off in production
        if is_production and self.APP_DEBUG:
            warnings.warn(
                "APP_DEBUG is True in production! This should be disabled.",
                stacklevel=2,
            )

        # Production: enforce secure secrets
        if is_production:
            if self.JWT_SECRET_KEY in _INSECURE_SECRETS:
                raise ValueError(
                    "SECURITY ERROR: JWT_SECRET_KEY is set to an insecure default in "
                    "production. Generate a strong secret with: "
                    "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
                )
            if self.APP_SECRET_KEY in _INSECURE_SECRETS:
                raise ValueError(
                    "SECURITY ERROR: APP_SECRET_KEY is set to an insecure default in "
                    "production. Generate a strong secret with: "
                    "python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )

        # Staging: warn about insecure secrets
        if self.ENVIRONMENT == Environment.STAGING:
            if self.JWT_SECRET_KEY in _INSECURE_SECRETS:
                logger.critical(
                    "SECURITY: JWT_SECRET_KEY is set to a default value in staging! "
                    "Please set a strong random secret."
                )
            if self.APP_SECRET_KEY in _INSECURE_SECRETS:
                logger.critical(
                    "SECURITY: APP_SECRET_KEY is set to a default value in staging! "
                    "Please set a strong random secret."
                )

        # Development: mild warning
        if self.ENVIRONMENT == Environment.DEVELOPMENT:
            if self.JWT_SECRET_KEY in _INSECURE_SECRETS:
                warnings.warn(
                    "JWT_SECRET_KEY is using the development default. "
                    "This is acceptable for local development only.",
                    stacklevel=2,
                )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    # Legacy aliases — existing services may still reference CLAUDE_*
    @property
    def CLAUDE_API_KEY(self) -> str:
        return self.LLM_API_KEY

    @property
    def CLAUDE_BASE_URL(self) -> str:
        return self.LLM_BASE_URL

    @property
    def CLAUDE_MODEL(self) -> str:
        return self.LLM_MODEL

    @property
    def CLAUDE_MAX_TOKENS(self) -> int:
        return self.LLM_MAX_TOKENS

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.ADMIN_EMAIL.split(",") if e.strip()}

    @property
    def upload_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def configure_logging(self) -> None:
        """Set up logging based on the current environment."""
        log_level = getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)

        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Remove existing handlers to avoid duplicates
        root_logger.handlers.clear()

        # Console handler (always)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)

        if self.is_production:
            # Production: structured format with timestamps
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        else:
            # Development: more readable format
            formatter = logging.Formatter(
                "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )

        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

        # File handler (production or when LOG_FILE is set)
        if self.LOG_FILE:
            try:
                from logging.handlers import RotatingFileHandler
                log_path = Path(self.LOG_FILE)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                file_handler = RotatingFileHandler(
                    str(log_path),
                    maxBytes=10 * 1024 * 1024,  # 10MB
                    backupCount=5,
                    encoding="utf-8",
                )
                file_handler.setLevel(log_level)
                file_handler.setFormatter(logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S",
                ))
                root_logger.addHandler(file_handler)
            except Exception as e:
                logger.warning("Failed to set up file logging: %s", e)

        # Email handler for critical errors in production
        if self.is_production and self.ERROR_EMAIL_ENABLED:
            try:
                from logging.handlers import SMTPHandler
                mail_handler = SMTPHandler(
                    mailhost=(self.ERROR_EMAIL_SMTP_HOST, self.ERROR_EMAIL_SMTP_PORT),
                    fromaddr=self.ERROR_EMAIL_FROM,
                    toaddrs=[a.strip() for a in self.ERROR_EMAIL_TO.split(",")],
                    subject=f"[{self.APP_NAME}] Production Error",
                    credentials=(self.ERROR_EMAIL_SMTP_USER, self.ERROR_EMAIL_SMTP_PASSWORD),
                    secure=(),
                )
                mail_handler.setLevel(logging.ERROR)
                mail_handler.setFormatter(logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(name)s | %(message)s\n"
                    "Path: %(pathname)s:%(lineno)d",
                ))
                root_logger.addHandler(mail_handler)
                logger.info("Error email notifications enabled")
            except Exception as e:
                logger.warning("Failed to set up email logging: %s", e)

        # Reduce noise from third-party libraries in production
        if self.is_production:
            for noisy in ("uvicorn.access", "httpx", "httpcore"):
                logging.getLogger(noisy).setLevel(logging.WARNING)

        logger.info(
            "Logging configured: level=%s env=%s",
            self.LOG_LEVEL,
            self.ENVIRONMENT.value,
        )

    def get_llm_client_config(self) -> dict:
        """Return a dict of the active default LLM client config.

        Useful for constructing clients or passing config to engines
        without coupling to the full Settings object.
        """
        return {
            "base_url": self.LLM_BASE_URL,
            "api_key": self.LLM_API_KEY,
            "model": self.LLM_MODEL,
            "max_tokens": self.LLM_MAX_TOKENS,
        }

    def get_vision_llm_config(self) -> dict:
        """Return vision/OCR LLM config from VISION_LLM_* env vars."""
        return {
            "base_url": self.VISION_LLM_BASE_URL,
            "api_key": self.VISION_LLM_API_KEY,
            "model": self.VISION_LLM_MODEL,
            "max_tokens": self.VISION_LLM_MAX_TOKENS,
        }


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.configure_logging()
    return settings
