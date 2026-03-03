import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()


def create_app(config_name="development"):
    app = Flask(__name__)

    # Load config
    if config_name == "testing":
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret"
        app.config["JWT_SECRET_KEY"] = "test-jwt-secret"
    elif config_name == "development":
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///taskhive.db"
        app.config["SECRET_KEY"] = os.environ.get(
            "TASKHIVE_SECRET_KEY", "dev-secret"
        )
        app.config["JWT_SECRET_KEY"] = os.environ.get(
            "TASKHIVE_JWT_SECRET_KEY", "dev-jwt-secret"
        )
    else:
        raise ValueError(f"Unknown config_name: {config_name}")

    # Init extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from taskhive.routes.health import health_bp
    app.register_blueprint(health_bp)

    return app
