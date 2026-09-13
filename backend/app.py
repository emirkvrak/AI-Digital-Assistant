from flask import Flask, current_app
from flask_cors import CORS
from routes.register_routes import register_routes
from config.config import Config
from core.mail.mail import mail
from dotenv import load_dotenv
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import os
import traceback

from core.utils.response import error_response

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)

app.config.from_object(Config)

CORS(app, resources={r"/*": {"origins": [os.getenv("FRONTEND_URL")]}}, supports_credentials=True)

mail.init_app(app)

register_routes(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
log_directory = os.path.join(BASE_DIR, "applog")
os.makedirs(log_directory, exist_ok=True)

log_file = os.path.join(log_directory, "app.log")
file_handler = RotatingFileHandler(log_file, maxBytes=1 * 1024 * 1024, backupCount=7)
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

error_log_file = os.path.join(log_directory, "error.log")
error_handler = RotatingFileHandler(error_log_file, maxBytes=1 * 1024 * 1024, backupCount=7)
error_handler.setLevel(logging.ERROR)

error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
error_handler.setFormatter(error_formatter)

app.logger.addHandler(file_handler)
app.logger.addHandler(error_handler)
log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
app.logger.setLevel(log_level)
app.logger.propagate = False

@app.errorhandler(404)
def not_found_error(error):
    return error_response("Kaynak bulunamadı", 404)

@app.errorhandler(500)
def internal_server_error(error):
    return error_response("Sunucu hatası", 500)

@app.errorhandler(Exception)
def global_error_handler(error):
    current_app.logger.error(f"İşlenmeyen hata: {traceback.format_exc()}")
    return error_response("Beklenmeyen bir hata oluştu.", 500)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
