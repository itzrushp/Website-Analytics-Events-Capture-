import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # PostgreSQL Configuration
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'analytics_user')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'analytics_password')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'analytics_db')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')

    # Redis Configuration
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))

    # API Configuration
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', '5000'))

    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

config = Config()
