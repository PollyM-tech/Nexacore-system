from flask import Flask

from app.config import Config
from app.extensions import cors, db, jwt, migrate

# Load models so SQLAlchemy/Alembic sees them
from app.models.admin_user import AdminUser
from app.models.customer import Customer
from app.models.organization import Organization


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

    # Register API blueprints
    from app.api.auth import auth_bp
    from app.api.customers import customers_bp
    from app.api.health import health_bp
    from app.api.organizations import organizations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(organizations_bp)

    return app