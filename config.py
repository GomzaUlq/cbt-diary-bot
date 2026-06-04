import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv
import base64
import urllib.parse

# Загружаем переменные из .env файла
load_dotenv()


@dataclass
class Config:
    """
    Конфигурация приложения.
    Все настройки берутся из переменных окружения.
    """

    # ==== ОБЯЗАТЕЛЬНЫЕ ПЕРЕМЕННЫЕ ====
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

    # ==== БАЗА ДАННЫХ (ВСЁ ИЗ .env) ====
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    # ==== АДМИНИСТРАТОРЫ ====
    ADMIN_IDS: List[int] = field(default_factory=list)

    # ==== РЕЖИМ РАБОТЫ ====
    DEBUG: bool = os.getenv("DEBUG", "True") == "True"

    # ==== ЛИМИТЫ ДЛЯ ЗАЩИТЫ ====
    MAX_ENTRIES_PER_USER: int = int(os.getenv("MAX_ENTRIES_PER_USER", "1000"))
    MAX_EMOTIONS_PER_ENTRY: int = int(os.getenv("MAX_EMOTIONS_PER_ENTRY", "10"))
    MAX_SITUATION_LENGTH: int = int(os.getenv("MAX_SITUATION_LENGTH", "2000"))
    MAX_THOUGHT_LENGTH: int = int(os.getenv("MAX_THOUGHT_LENGTH", "1000"))
    MAX_RESPONSE_LENGTH: int = int(os.getenv("MAX_RESPONSE_LENGTH", "1000"))

    # ==== ВРЕМЕННЫЕ НАСТРОЙКИ ====
    SESSION_LIFETIME: int = 3600
    RATE_LIMIT_PER_MINUTE: int = 30

    def __post_init__(self):
        """Инициализация после создания конфига"""
        if not self.BOT_TOKEN:
            raise ValueError("❌ BOT_TOKEN не найден в .env файле!")

        # Проверка наличия обязательных параметров БД
        if not self.DB_NAME or not self.DB_USER:
            raise ValueError("❌ DB_NAME или DB_USER не найдены в .env файле!")

        if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
            import secrets
            self.SECRET_KEY = secrets.token_urlsafe(32)

        # Инициализируем Fernet один раз
        if not self.ENCRYPTION_KEY:
            try:
                from cryptography.fernet import Fernet
                key = Fernet.generate_key()
                self.ENCRYPTION_KEY = key.decode()
            except ImportError:
                print("⚠️  Модуль cryptography не установлен, шифрование отключено")
                self.ENCRYPTION_KEY = ""

        admin_ids_env = os.getenv("ADMIN_IDS")
        if admin_ids_env:
            try:
                self.ADMIN_IDS = [int(id.strip()) for id in admin_ids_env.split(",")]
            except ValueError:
                print("⚠️ Неверный формат ADMIN_IDS в .env файле")
                self.ADMIN_IDS = []

    @property
    def fernet(self):
        """Инициализация Fernet для шифрования данных"""
        if not self.ENCRYPTION_KEY:
            return None

        try:
            from cryptography.fernet import Fernet
            return Fernet(self.ENCRYPTION_KEY.encode())
        except ImportError:
            print("⚠️  Модуль cryptography не установлен, шифрование отключено")
            return None
        except Exception as e:
            print(f"⚠️  Ошибка инициализации Fernet: {e}")
            return None

    def encrypt_text(self, text: str) -> str:
        """Простое шифрование текста"""
        if not text or not self.fernet:
            return text

        try:
            encrypted = self.fernet.encrypt(text.encode())
            return encrypted.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"❌ Ошибка шифрования: {e}")
            return text

    def decrypt_text(self, encrypted_text: str) -> str:
        """Упрощенная расшифровка текста"""
        if not encrypted_text or not self.fernet:
            return encrypted_text

        # Если это не похоже на зашифрованные данные Fernet
        if not encrypted_text.startswith('gAAAA'):
            # Пробуем декодировать как base64 (старый формат)
            try:
                if len(encrypted_text) % 4 == 0:
                    decoded = base64.b64decode(encrypted_text)
                    result = decoded.decode('utf-8', errors='ignore')
                    return result
            except:
                pass
            return encrypted_text

        try:
            decrypted = self.fernet.decrypt(encrypted_text.encode())
            return decrypted.decode('utf-8', errors='ignore')
        except:
            return encrypted_text

    @property
    def DB_URL(self) -> str:
        """URL для PostgreSQL"""
        password = urllib.parse.quote_plus(self.DB_PASSWORD)
        return f"postgresql+asyncpg://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


# Создаём глобальный объект конфигурации
config = Config()