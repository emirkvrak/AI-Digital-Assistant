from datetime import datetime
from bson import ObjectId
from flask import current_app
from core.database.mongo import (
    get_messages_collection,
    get_chat_rooms_collection,
    get_context_logs_collection
)
from services.qa.context_builder import get_context_list_from_logs
from services.qa.qa_service import ask_question

chat_rooms = get_chat_rooms_collection()
messages = get_messages_collection()
context_logs = get_context_logs_collection()


def ensure_object_id(val):
    return val if isinstance(val, ObjectId) else ObjectId(val)


def process_ai_response(user_text, chatroom_obj_id, selected_files):
    try:
        contexts = get_context_list_from_logs(chatroom_obj_id, selected_files)
        if not contexts:
            current_app.logger.warning("Soru-cevap bağlamı boş, cevap üretilemedi.")
            save_ai_response_to_db("İlgili içerik bulunamadığı için cevap üretilemedi.", chatroom_obj_id)
            return

        answer = ask_question(question=user_text, contexts=contexts)
        if not answer:
            answer = "Üzgünüm, cevabı oluşturamadım."

        save_ai_response_to_db(answer, chatroom_obj_id)

    except Exception as e:
        current_app.logger.error(f"Yapay zekâ işlem hatası: {e}")


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
        current_app.logger.error(f"Yapay zekâ cevabı veritabanına kaydedilemedi: {e}")


def delete_context_log(chatroom_obj_id):
    try:
        context_logs.delete_one({"chat_room_id": ensure_object_id(chatroom_obj_id)})
        current_app.logger.info(f"Bağlam kaydı silindi: {chatroom_obj_id}")
    except Exception as e:
        current_app.logger.error(f"❌ context_logs silme hatası: {e}")
