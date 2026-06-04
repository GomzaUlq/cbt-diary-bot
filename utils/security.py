import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Optional
import secrets
from config import config


class SecurityManager:
    """Менеджер безопасности для работы с ключами и шифрованием"""

    @staticmethod
    def generate_csrf_token(user_id: int) -> str:
        """Генерация CSRF-токена для пользователя"""
        timestamp = int(datetime.now().timestamp())
        message = f"{user_id}:{timestamp}:{secrets.token_hex(8)}"
        signature = hmac.new(
            config.SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        return base64.urlsafe_b64encode(f"{message}:{signature.hex()}").decode()

    @staticmethod
    def validate_csrf_token(token: str, user_id: int, max_age: int = 3600) -> bool:
        """Валидация CSRF-токена"""
        try:
            decoded = base64.urlsafe_b64decode(token).decode()
            message, signature_hex = decoded.rsplit(':', 1)

            # Проверяем подпись
            expected_signature = hmac.new(
                config.SECRET_KEY.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature_hex, expected_signature):
                return False

            # Проверяем содержимое
            parts = message.split(':')
            if len(parts) != 3:
                return False

            token_user_id, timestamp_str, _ = parts
            if int(token_user_id) != user_id:
                return False

            # Проверяем срок действия
            token_time = datetime.fromtimestamp(int(timestamp_str))
            if datetime.now() - token_time > timedelta(seconds=max_age):
                return False

            return True

        except Exception:
            return False

    @staticmethod
    def hash_password(password: str) -> str:
        """Хеширование пароля (если добавите аутентификацию)"""
        salt = secrets.token_bytes(16)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            100000,
            dklen=32
        )
        return f"{salt.hex()}:{key.hex()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Проверка пароля"""
        try:
            salt_hex, key_hex = hashed.split(':')
            salt = bytes.fromhex(salt_hex)
            stored_key = bytes.fromhex(key_hex)

            new_key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt,
                100000,
                dklen=32
            )
            return hmac.compare_digest(new_key, stored_key)
        except Exception:
            return False


security = SecurityManager()