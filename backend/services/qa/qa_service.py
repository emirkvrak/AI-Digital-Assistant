from config.config import Config
from core.utils.http_client import http_client

def ask_question(question, contexts: list):
    try:
        response = http_client.post(
            f"{Config.MODEL_API_URL}/qa",
            json={"question": question, "contexts": contexts},
            headers={"Content-Type": "application/json"}
        )
        return response.json().get("answer", "")
    except Exception as e:
        print("❌ Soru-cevap servisi hatası:", e)
        return ""
