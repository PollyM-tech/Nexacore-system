from flask import Flask

from app.config import Config
from app.extensions import cors, db, jwt, migrate


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    app.config["FRONTEND_ORIGIN"]
                ]
            }
        },
    )

    from app.api.health import health_bp

    app.register_blueprint(health_bp)

    return app