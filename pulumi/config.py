from pydantic_settings import BaseSettings
from pulumi_random import RandomPassword

class Settings(BaseSettings):
    NODE_COUNT: int = 3
    NODE_MACHINE_TYPE: str = "n1-standard-1"
    USERNAME: str = "admin"
    PASSWORD: str = RandomPassword("password", length=20, special=True).result
    MASTER_VERSION: str = "1.24.0"

    class Config:
        env_file = ".env"
        extra = "ignore"
    

    
