from flask import request, current_app, g
from bson import ObjectId
from bson.errors import InvalidId
import os
from core.utils.response import success_response, error_response
from core.security.auth_decorator import require_auth
from core.database.mongo import (
    get_chat_rooms_collection,
    get_uploads_collection,
    get_documents_collection,
    get_context_logs_collection
)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")

chat_rooms = get_chat_rooms_collection()
uploads = get_uploads_collection()
documents = get_documents_collection()
context_logs = get_context_logs_collection()


def _safe_upload_path(filename):
    if not isinstance(filename, str) or not filename:
        return None

    upload_root = os.path.normcase(os.path.abspath(UPLOAD_FOLDER))
    file_path = os.path.normcase(os.path.abspath(os.path.join(UPLOAD_FOLDER, filename)))

    try:
        if os.path.commonpath([upload_root, file_path]) != upload_root:
            return None
    except ValueError:
        return None

    return file_path

@require_auth
def delete_file():
    try:
        filename = request.json.get('filename')
        chatroom_id = request.json.get('chatroom_id')

        if not filename or not chatroom_id:
            return error_response("file_delete_missing_fields", 400)

        try:
            chatroom_obj_id = ObjectId(chatroom_id)
        except InvalidId:
            return error_response("invalid_chatroom_id", 400)

        room = chat_rooms.find_one({
            "_id": chatroom_obj_id,
            "user_id": g.user_id,
        })
        if not room:
            return error_response("chat_room_not_found", 404)

        try:
            doc = documents.find_one({
                "chat_id": chatroom_obj_id,
                "source": filename
            })

            if doc:
                context_logs.update_many(
                    {"chat_room_id": chatroom_obj_id},
                    {"$pull": {"contexts": {"document_id": doc["_id"]}}}
                )
        except Exception as e:
            current_app.logger.error(f"❌ context_logs güncelleme hatası: {e}")

        try:
            documents.delete_many({"chat_id": chatroom_obj_id, "source": filename})
            uploads.delete_one({"chatroom_id": chatroom_id, "filename": filename})
            chat_rooms.update_one(
                {"_id": chatroom_obj_id},
                {"$pull": {"uploaded_files": {"filename": filename}}}
            )
        except Exception as e:
            current_app.logger.error(f"❌ Veritabanı silme hatası: {e}")
            return error_response("file_delete_failed", 500)

        try:
            file_path = _safe_upload_path(filename)
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            elif not file_path:
                current_app.logger.warning("Güvenli olmayan dosya yolu nedeniyle fiziksel silme atlandı.")
        except Exception as e:
            current_app.logger.warning(f"❗ Dosya fiziksel olarak silinemedi: {e}")

        return success_response("file_deleted_success")

    except Exception as e:
        current_app.logger.error(f"Dosya silme hatası: {e}")
        return error_response("file_delete_failed", 500)


@require_auth
def rename_file():
    try:
        old_filename = request.json.get('old_filename')
        new_filename = request.json.get('new_filename')
        new_original_name = request.json.get('new_original_name')
        chatroom_id = request.json.get('chatroom_id')

        if not old_filename or not new_filename or not new_original_name or not chatroom_id:
            return error_response("file_rename_missing_fields", 400)

        try:
            chatroom_obj_id = ObjectId(chatroom_id)
        except InvalidId:
            return error_response("invalid_chatroom_id", 400)

        room = chat_rooms.find_one({
            "_id": chatroom_obj_id,
            "user_id": g.user_id,
        })
        if not room:
            return error_response("chat_room_not_found", 404)

        try:
            uploads.update_one(
                {"chatroom_id": chatroom_id, "filename": old_filename},
                {"$set": {
                    "filename": new_filename,
                    "original_name": new_original_name
                }}
            )

            chat_rooms.update_one(
                {"_id": chatroom_obj_id, "uploaded_files.filename": old_filename},
                {"$set": {
                    "uploaded_files.$.filename": new_filename,
                    "uploaded_files.$.original_name": new_original_name
                }}
            )

            documents.update_many(
                {"chat_id": chatroom_obj_id, "source": old_filename},
                {"$set": {
                    "source": new_filename,
                    "title": new_original_name.rsplit(".", 1)[0]
                }}
            )
        except Exception as e:
            current_app.logger.error(f"❌ Veritabanı update hatası (rename_file): {e}")
            return error_response("file_rename_failed", 500)

        try:
            old_path = _safe_upload_path(old_filename)
            new_path = _safe_upload_path(new_filename)
            if not old_path or not new_path:
                return error_response("invalid_file_name", 400)

            if old_filename != new_filename and os.path.exists(old_path):
                os.rename(old_path, new_path)
        except Exception as e:
            current_app.logger.warning(f"❗ Dosya yeniden adlandırılamadı: {e}")

        return success_response("file_rename_success")

    except Exception as e:
        current_app.logger.error(f"Dosya yeniden adlandırma hatası: {e}")
        return error_response("file_rename_failed", 500)
