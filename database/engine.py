from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
import logging

from config import config
from database.models import Base

logger = logging.getLogger(__name__)

# Создаем движок БД
engine: AsyncEngine = create_async_engine(
    config.DB_URL,
    echo=config.DEBUG,  # SQL запросы в логах только в режиме DEBUG
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_recycle=3600,  # Переподключение каждые 60 минут
)

# Создаем фабрику сессий
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Инициализация базы данных (создание таблиц)"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Таблицы базы данных созданы/проверены")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании таблиц: {e}")
        raise


from sqlalchemy import text


async def check_db_connection() -> bool:
    """Проверка подключения к базе данных"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("✅ Подключение к БД успешно")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        return False


async def get_session():
    """Получение сессии БД (для dependency injection)"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()