import os
from datetime import timedelta

from dotenv import load_dotenv


load_dotenv()


class Config:
    SECRET_KEY = os.environ["SECRET_KEY"]

    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)

    FRONTEND_ORIGIN = os.getenv(
        "FRONTEND_ORIGIN",
        "http://localhost:5173",
    )