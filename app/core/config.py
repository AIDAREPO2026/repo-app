"""Read configuration from environment variables, failing early when one is missing."""

from cryptography.fernet import Fernet
from pydantic import ValidationError, field_validator, model_validator
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
    # Where people reach the portal. Emailed links are built from this, never from the request's
    # Host header, which the sender controls. The default suits the local stack.
    portal_url: str = "http://localhost:8081"

    @field_validator("fernet_key")
    @classmethod
    def fernet_key_is_valid(cls, value: str) -> str:
        """Refuse a key Fernet cannot use, so a bad key stops startup, not someone's MFA enrolment."""
        Fernet(value.encode())
        return value

    @model_validator(mode="after")
    def servers_name_their_https_address(self) -> "Config":
        """Stop a server starting with links that point at a laptop or are not encrypted."""
        if self.app_env in ("staging", "production") and not self.portal_url.startswith("https://"):
            raise ValueError("PORTAL_URL must be the portal's https address on a server")
        return self


class MissingConfigError(RuntimeError):
    """Raised at startup when required environment variables are missing or invalid."""


def load_config(env_file: str | None = ".env") -> Config:
    """Load the config, turning pydantic's error into one clear startup message."""
    try:
        return Config(_env_file=env_file)  # type: ignore[call-arg]
    except ValidationError as error:
        # A check across several settings has no single name, so its message is used.
        names = sorted(
            str(issue["loc"][0]).upper() if issue["loc"] else issue["msg"] for issue in error.errors()
        )
        raise MissingConfigError(
            f"Missing or invalid environment variables: {', '.join(names)}. See .env.example."
        ) from None
