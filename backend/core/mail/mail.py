from flask_mail import Mail, Message
from flask import current_app
import time

mail = Mail()

def send_email(subject, body, to, app, html_body=None, retries=3, delay=2):
    """E-posta gönderimini hata durumunda belirli sayıda tekrarlar."""
    with app.app_context():
        attempt = 0
        while attempt < retries:
            try:
                message = Message(subject=subject, recipients=[to], body=body)
                if html_body:
                    message.html = html_body
                mail.send(message)
                return True
            except Exception as e:
                attempt += 1
                current_app.logger.warning(f"📧 Mail gönderimi başarısız (deneme {attempt}/{retries}): {e}")
                if attempt == retries:
                    current_app.logger.error("❌ Tüm mail gönderim denemeleri başarısız oldu.")
                    raise e
                time.sleep(delay)
