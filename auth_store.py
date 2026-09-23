import json
import bcrypt
from azure_clients import get_blob_container

USERS_BLOB_NAME = "auth/users.json"

def _normalize_username(username: str) -> str:
    return username.strip().lower()

def _load_users() -> dict:
    container = get_blob_container()
    blob_client = container.get_blob_client(USERS_BLOB_NAME)
    if not blob_client.exists():
        return {}
    data = blob_client.download_blob().readall()
    return json.loads(data)

def _save_users(users: dict) -> None:
    container = get_blob_container()
    container.upload_blob(USERS_BLOB_NAME, json.dumps(users, indent=2), overwrite=True)

def create_user(username: str, password: str) -> tuple[bool, str]:
    username = _normalize_username(username)
    if not username or not password:
        return False, "Username and password are required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    users = _load_users()
    if username in users:
        return False, "That username is already taken."
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    users[username] = {"password_hash": password_hash}
    _save_users(users)
    return True, "Account created. You can now log in."

def verify_login(username: str, password: str) -> bool:
    username = _normalize_username(username)
    users = _load_users()
    user = users.get(username)
    if not user:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8"))