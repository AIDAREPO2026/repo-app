"""Read configuration from environment variables, failing early when one is missing."""

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Every environment variable the app reads. Fields without a default are required."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str
    database_url: str
    redis_url: str
    secret_key: str
    fernet_key: str
    ip_hash_salt: str
    # Outgoing email. The defaults suit the local Mailpit catcher; servers set real values.
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    # When set, the connection is upgraded with STARTTLS before signing in.
    smtp_username: str = ""
    smtp_password: str = ""
    mail_from: str = "aida-portal@localhost"


class MissingConfigError(RuntimeError):
    """Raised at startup when required environment variables are missing or invalid."""


def load_config(env_file: str | None = ".env") -> Config:
    """Load the config, turning pydantic's error into one clear startup message."""
    try:
        return Config(_env_file=env_file)  # type: ignore[call-arg]
    except ValidationError as error:
        names = sorted(str(issue["loc"][0]).upper() for issue in error.errors())
        raise MissingConfigError(
            f"Missing or invalid environment variables: {', '.join(names)}. See .env.example."
        ) from None
