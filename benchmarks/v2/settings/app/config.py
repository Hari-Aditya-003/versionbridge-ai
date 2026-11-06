def load_config():
    from pydantic import BaseSettings

    class Settings(BaseSettings):
        service_name: str = 'bridge'
        port: int = 8080
        model_config = {'env_prefix': 'VB_'}

    settings = Settings()
    return {'service_name': settings.service_name, 'port': settings.port}
