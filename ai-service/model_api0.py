# file: model_api.py

from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient
from langdetect import detect
from transformers import pipeline
import torch
import logging
from dotenv import load_dotenv
import os
from datetime import datetime

# --- Ortam değişkenlerini yükle
load_dotenv()
API_KEY = os.getenv("HUGGINGFACE_API_KEYDeneme0")
MODEL_NAME = "CohereLabs/aya-expanse-8b"

# --- Logger ayarı
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model_api")

# --- Flask app tanımı
app = Flask(__name__)
CORS(app)

# --- Hugging Face API istemcisi (Cohere üzerinden)
client = InferenceClient(provider="cohere", api_key=API_KEY)

# --- Türkçeden İngilizceye çeviri pipeline'ı
translator = pipeline(
    "translation",
    model="Helsinki-NLP/opus-mt-tr-en",
    device=0 if torch.cuda.is_available() else -1
)

# --- QA endpoint
@app.route("/qa", methods=["POST"])
def qa_answer():
    try:
        data = request.get_json()
        question = data.get("question", "").strip()
        contexts = data.get("contexts", [])

        if not question or not contexts:
            return jsonify({"error": "Eksik veri"}), 400

        context_text = "\n\n".join(ctx.get("raw_text", "").strip() for ctx in contexts if ctx.get("raw_text")).strip()
        if not context_text:
            return jsonify({"answer": ""})

        try:
            lang = detect(question)
        except:
            lang = "tr"

        # Prompt hazırlama
        if lang == "tr":
            prompt = (
                "Lütfen aşağıdaki talimatlara göre TÜRKÇE olarak yanıt veriniz.\n\n"
                f"Belge metni:\n{context_text}\n\n"
                f"Kullanıcının sorusu: {question}\n\n"
                "Yanıt:"
            )
        else:
            prompt = (
                f"Document:\n{context_text}\n\n"
                f"User question: {question}\n\n"
                "Answer:"
            )

        logger.info("📥 QA isteği alındı.")
        logger.info(f"❓ Soru: {question}")
        logger.info(f"📄 Context (ilk 300 karakter): {context_text[:300]}")

        # 🤖 Chat completion güvenli şekilde
        try:
            response = client.chat_completion(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.7
            )
            choices = response.choices
            if not choices:
                logger.warning("❗ Model boş cevap döndürdü.")
                return jsonify({"answer": ""})

            answer = choices[0].message.content.strip()

        except Exception as e:
            logger.exception("❌ Model yanıt üretim hatası:")
            return jsonify({"error": "Model cevabı alınamadı."}), 500

        # Log dosyasına yaz
        log_entry = (
            f"\n{'='*80}\n"
            f"🕒 Zaman: {datetime.utcnow().isoformat()} UTC\n"
            f"❓ Soru:\n{question}\n\n"
            f"📄 Context (ilk 500 karakter):\n{context_text[:500]}\n\n"
            f"📦 Prompt:\n{prompt}\n\n"
            f"💡 Cevap:\n{answer}\n"
            f"{'='*80}\n"
        )
        with open("qa_prompt_log.txt", "a", encoding="utf-8") as f:
            f.write(log_entry)

        return jsonify({"answer": answer})

    except Exception as e:
        logger.exception("❌ QA API hatası:")
        return jsonify({"error": str(e)}), 500
