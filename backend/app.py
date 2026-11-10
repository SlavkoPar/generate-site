from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

# Must run before importing routes: the Anthropic client reads its key at import time.
load_dotenv()

from routes import api_bp  # noqa: E402


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)  # allow all origins on all routes; restrict via CORS(app, resources={...}) if needed
    app.register_blueprint(api_bp, url_prefix="/api")
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
