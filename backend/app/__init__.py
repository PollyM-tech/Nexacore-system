from flask import Flask

from app.config import Config
from app.extensions import cors, db, jwt, migrate

# Load model so SQLAlchemy/Alembic sees it
from app.models.admin_user import AdminUser
from app.models.customer import Customer

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

    from app.api.auth import auth_bp
    from app.api.health import health_bp
    from app.api.customers import customers_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(customers_bp)

    return app
