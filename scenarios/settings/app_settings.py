from pydantic import BaseSettings


class AppSettings(BaseSettings):
    service_name: str = "versionbridge"
    retries: int = 3
