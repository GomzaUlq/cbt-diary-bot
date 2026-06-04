import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from database.engine import init_db
from config import config

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG if config.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """
    Основная функция запуска бота.
    """
    logger.info("Запуск CBT Diary Bot...")

    # 1️⃣ Инициализация базы данных
    await init_db()
    logger.info("✅ База данных инициализирована")

    # 2️⃣ Инициализация бота и диспетчера
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode="HTML",
            link_preview_is_disabled=True
        )
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # 3️⃣ Импорт и регистрация роутеров
    from handlers.start import start_router
    from handlers.diary import diary_router
    from handlers.settings import settings_router
    from handlers.stats import stats_router

    dp.include_router(start_router)
    dp.include_router(diary_router)
    dp.include_router(stats_router)
    dp.include_router(settings_router)

    # 4️⃣ Запуск фоновых задач (если нужно)
    try:
        from utils.reminders import reminder_scheduler
        asyncio.create_task(reminder_scheduler(bot))
        logger.info("⏰ Планировщик напоминаний запущен")
    except Exception as e:
        logger.warning(f"Не удалось запустить напоминания: {e}")

    # 5️⃣ Запуск поллинга
    logger.info("🤖 Бот запущен и ожидает сообщений...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        sys.exit(1)