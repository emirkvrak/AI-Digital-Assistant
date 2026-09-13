from bson import ObjectId
from flask import current_app
from core.database.mongo import (
    get_chat_rooms_collection,
    get_messages_collection,
    get_users_collection
)
from bson.errors import InvalidId


def get_user_id(email):
    users = get_users_collection()
    user = users.find_one({"email": email})
    if user:
        return user["_id"]
    
    current_app.logger.warning(f"⚠️ Kullanıcı bulunamadı: {email}")
    return None


def get_user_messages(email, room_id):
    chat_rooms = get_chat_rooms_collection()
    messages_collection = get_messages_collection()

    user_id = get_user_id(email)
    if not user_id:
        return []

    try:
        chat_room = chat_rooms.find_one({
            "_id": ObjectId(room_id),
            "user_id": ObjectId(user_id)
        })
    except InvalidId:
        return []

    if not chat_room:
        return []

    message_ids = chat_room.get("messages", [])
    if not message_ids:
        return []

    message_ids = [ObjectId(m) if isinstance(m, str) else m for m in message_ids]
    
    messages_cursor = messages_collection.find({"_id": {"$in": message_ids}})
    messages = list(messages_cursor)

    messages.sort(key=lambda x: x["created_at"])

    for message in messages:
        message["_id"] = str(message["_id"])
        message["chat_room_id"] = str(message["chat_room_id"])
        message["created_at"] = message["created_at"].isoformat()

        if "related_document_id" in message and message["related_document_id"]:
            message["related_document_id"] = str(message["related_document_id"])

    return messages

