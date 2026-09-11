# file: model_api.py
# HUGGINGFACE üzerindeki mistralai
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient
from langdetect import detect
from transformers import AutoTokenizer
from dotenv import load_dotenv
import logging
import os
from datetime import datetime

# --- Ortam değişkenleri
load_dotenv()
API_KEY = os.getenv("HUGGINGFACE_API_KEY")
MODEL_NAME = "mistralai/Mixtral-8x7B-Instruct-v0.1"

# --- Tokenizer (Mixtral için doğru tokenizer)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)

MAX_TOTAL_TOKENS = 32000
CHUNK_TOKEN_LIMIT = 25000

# --- Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model_api")

# --- Flask app
app = Flask(__name__)
CORS(app)

# --- Hugging Face istemcisi
client = InferenceClient(
    model=MODEL_NAME,
    token=API_KEY
)

def count_tokens(text: str) -> int:
    return len(tokenizer.encode(text, truncation=False))

def chunk_text(text, max_tokens=CHUNK_TOKEN_LIMIT):
    words = text.split()
    chunks, current, token_count = [], [], 0
    for word in words:
        current.append(word)
        token_count += 1
        if token_count >= max_tokens:
            chunks.append(" ".join(current))
            current, token_count = [], 0
    if current:
        chunks.append(" ".join(current))
    return chunks

def summarize_chunk(chunk_text):
    try:
        prompt = f"Aşağıdaki metni özetle:\n\n{chunk_text}\n\nÖzet:"
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.exception("❌ Chunk özetleme hatası:")
        return ""

def process_contexts(contexts):
    all_summaries = []
    for i, ctx in enumerate(contexts):
        raw = ctx.get("raw_text", "").strip()
        source = ctx.get("title") or f"Metin {i+1}"
        if not raw:
            continue
        logger.info(f"📄 {source} - {len(raw)} karakter")
        logger.info(f"📄 İçerik (ilk 300): {raw[:300]}")
        chunks = chunk_text(raw)
        chunk_summaries = []
        for j, chunk in enumerate(chunks):
            logger.info(f"🧩 {source} - Chunk {j+1}/{len(chunks)}")
            summary = summarize_chunk(chunk)
            if summary:
                chunk_summaries.append(summary)
        if chunk_summaries:
            full_summary = "\n".join(chunk_summaries)
            all_summaries.append(f"{source}:\n{full_summary}")
    return all_summaries

def build_final_prompt(all_summaries, question):
    context_text = "\n\n".join(all_summaries)
    prompt = (
        "Lütfen aşağıdaki talimatlara göre TÜRKÇE olarak yanıt veriniz.\n\n"
        f"Belge özetleri:\n{context_text}\n\n"
        f"Kullanıcının sorusu: {question}\n\n"
        "Yanıt:"
    )
    logger.info(f"📦 Final prompt token sayısı: {count_tokens(prompt)}")
    return prompt

@app.route("/qa", methods=["POST"])
def qa_answer():
    try:
        data = request.get_json()
        question = data.get("question", "").strip()
        contexts = data.get("contexts", [])

        if not question or not contexts:
            return jsonify({"error": "Eksik veri"}), 400

        try:
            lang = detect(question)
        except:
            lang = "tr"

        logger.info(f"📥 QA geldi: {question}")
        logger.info(f"📄 Context sayısı: {len(contexts)}")

        all_summaries = process_contexts(contexts)
        if not all_summaries:
            return jsonify({"answer": "Belgelerden içerik alınamadı."}), 200

        prompt = build_final_prompt(all_summaries, question)

        used_tokens = count_tokens(prompt)
        max_output_tokens = max(128, min(MAX_TOTAL_TOKENS - used_tokens, 2048))

        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_output_tokens,
            temperature=0.7
        )
        answer = response.choices[0].message.content.strip()

        # Log
        log_entry = (
            f"\n{'='*80}\n"
            f"🕒 Zaman: {datetime.utcnow().isoformat()} UTC\n"
            f"❓ Soru:\n{question}\n\n"
            f"📦 Prompt (ilk 500):\n{prompt[:500]}\n\n"
            f"💡 Cevap:\n{answer}\n"
            f"{'='*80}\n"
        )
        with open("qa_prompt_log.txt", "a", encoding="utf-8") as f:
            f.write(log_entry)

        return jsonify({"answer": answer})

    except Exception as e:
        logger.exception("❌ QA API genel hata:")
        return jsonify({"error": str(e)}), 500
