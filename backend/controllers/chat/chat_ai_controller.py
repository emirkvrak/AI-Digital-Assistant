# file: backend/controllers/chat/chat_ai_controller.py

from datetime import datetime
from bson import ObjectId
from flask import current_app
from core.database.mongo import (
    get_messages_collection,
    get_chat_rooms_collection,
    get_context_logs_collection,
    get_documents_collection
)
from services.qa.context_builder import get_context_list_from_logs
from services.qa.qa_service import ask_question

chat_rooms = get_chat_rooms_collection()
messages = get_messages_collection()
context_logs = get_context_logs_collection()
documents = get_documents_collection()


def ensure_object_id(val):
    from bson import ObjectId
    return val if isinstance(val, ObjectId) else ObjectId(val)


def process_ai_response(user_text, chatroom_obj_id, selected_files):
    try:
        contexts = get_context_list_from_logs(chatroom_obj_id, selected_files)
        if not contexts:
            current_app.logger.warning("⚠️ QA context boş, cevap üretilemedi.")
            save_ai_response_to_db("İlgili içerik bulunamadığı için cevap üretilemedi.", chatroom_obj_id)
            return

        answer = ask_question(question=user_text, contexts=contexts)
        if not answer:
            answer = "Üzgünüm, cevabı oluşturamadım."

        save_ai_response_to_db(answer, chatroom_obj_id)

    except Exception as e:
        current_app.logger.error(f"❌ AI işlem hatası: {e}")


def generate_ai_answer(question, user_id, chatroom_obj_id) -> str:
    try:
        contexts = get_context_list_from_logs(chatroom_obj_id)
        if not contexts:
            return "Üzgünüm, cevap verecek veri bulunamadı."

        answer = ask_question(question=question, contexts=contexts)
        return answer or "Üzgünüm, sorunuza uygun bir cevap bulunamadı."

    except Exception as e:
        current_app.logger.error(f"❌ QA cevabı üretilemedi: {e}")
        return "Üzgünüm, şu anda cevap veremiyorum."


def build_and_log_qa_context(question, chatroom_obj_id, selected_files):
    room = chat_rooms.find_one({"_id": chatroom_obj_id})
    if not room:
        current_app.logger.error("❌ Chat odası bulunamadı.")
        return None, None

    user_id = room.get("user_id")
    if not user_id:
        current_app.logger.error("❌ Kullanıcı ID eksik.")
        return None, None

    # ✅ SADECE seçilen dosyalardan context oluştur
    contexts = get_context_list_from_logs(chatroom_obj_id, selected_files)
    answer = ask_question(question=question, contexts=contexts)

    return answer, user_id


def save_ai_response_to_db(answer, chatroom_obj_id):
    try:
        ai_msg = {
            "chat_room_id": chatroom_obj_id,
            "sender": "assistant",
            "content": answer,
            "created_at": datetime.utcnow()
        }

        inserted_ai_msg = messages.insert_one(ai_msg)
        chat_rooms.update_one(
            {"_id": chatroom_obj_id},
            {"$push": {"messages": inserted_ai_msg.inserted_id}}
        )

    except Exception as e:
        current_app.logger.error(f"❌ AI cevabı DB'ye kaydedilemedi: {e}")


def delete_context_log(chatroom_obj_id):
    try:
        context_logs.delete_one({"chat_room_id": ensure_object_id(chatroom_obj_id)})
        current_app.logger.info(f"🗑️ context_logs silindi: {chatroom_obj_id}")
    except Exception as e:
        current_app.logger.error(f"❌ context_logs silme hatası: {e}")
