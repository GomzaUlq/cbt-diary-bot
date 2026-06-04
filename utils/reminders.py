import asyncio
from datetime import datetime, timedelta
from database.engine import AsyncSessionLocal
from database.models import Entry, User
from sqlalchemy import select
from aiogram import Bot
from config import config
import logging

logger = logging.getLogger(__name__)


async def check_and_send_reminders(bot: Bot):
    """Проверяет и отправляет напоминания"""
    try:
        current_time = datetime.now().strftime("%H:%M")

        async with AsyncSessionLocal() as session:
            # Находим пользователей, у которых сейчас время напоминаний
            users_result = await session.execute(
                select(User).where(User.reminder_time == current_time)
            )
            users = users_result.scalars().all()

            for user in users:
                # Находим незавершённые записи пользователя
                entries_result = await session.execute(
                    select(Entry)
                    .where(
                        Entry.user_id == user.id,
                        Entry.status == "draft"
                    )
                    .order_by(Entry.created_at.desc())
                    .limit(5)
                )
                draft_entries = entries_result.scalars().all()

                if draft_entries:
                    # Формируем сообщение
                    reminder_text = f"""
🔔 *Напоминание!*

У вас есть незавершённые записи в КПТ-дневнике.

📋 *Незавершённые записи:*
"""

                    for i, entry in enumerate(draft_entries[:3], 1):
                        date_str = entry.created_at.strftime("%d.%m.%Y")
                        preview = entry.situation[:50] + "..." if entry.situation and len(
                            entry.situation) > 50 else entry.situation or "Без описания"
                        reminder_text += f"{i}. *{date_str}* - {preview}\n"

                    if len(draft_entries) > 3:
                        reminder_text += f"...и ещё {len(draft_entries) - 3} записей\n"

                    reminder_text += """
➡️ Продолжите записи через меню "🔄 Продолжить записи"
"""

                    try:
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=reminder_text,
                            parse_mode="Markdown"
                        )
                        logger.info(f"📨 Отправлено напоминание пользователю {user.telegram_id}")
                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки напоминания пользователю {user.telegram_id}: {e}")

    except Exception as e:
        logger.error(f"❌ Ошибка в системе напоминаний: {e}")


async def reminder_scheduler(bot: Bot):
    """Планировщик напоминаний (запускать в отдельной задаче)"""
    logger.info("⏰ Запущен планировщик напоминаний")

    while True:
        try:
            await check_and_send_reminders(bot)
        except Exception as e:
            logger.error(f"❌ Ошибка в планировщике: {e}")

        # Проверяем каждую минуту
        await asyncio.sleep(60)