from pathlib import Path

from flask import Flask

from .config import Config
from .database import init_db
from .routes import main_bp


def create_app(config_class=Config):
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.from_object(config_class)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    init_db(app.config["DATABASE_PATH"])
    app.register_blueprint(main_bp)

    return app
