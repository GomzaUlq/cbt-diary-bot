"""Дополнительные callback-хендлеры для просмотра записей"""

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database.engine import AsyncSessionLocal
from database.models import Entry, EntryEmotion, User
from keyboards import get_main_menu, format_emotion_display
from config import config
from utils.deletion_utils import delete_entry_simple

import logging

logger = logging.getLogger(__name__)

diary_router = Router()


@diary_router.callback_query(F.data.startswith("view_details_"))
async def view_entry_details(callback: types.CallbackQuery, state: FSMContext):
    """Просмотр деталей конкретной записи"""
    try:
        entry_id = int(callback.data.replace("view_details_", ""))

        async with AsyncSessionLocal() as session:
            entry_result = await session.execute(
                select(Entry).where(Entry.id == entry_id)
            )
            entry = entry_result.scalar_one_or_none()

            if not entry:
                await callback.answer("❌ Запись не найдена", show_alert=True)
                return

            situation = config.decrypt_text(entry.situation) if entry.situation else ""
            thought = config.decrypt_text(entry.automatic_thought) if entry.automatic_thought else ""
            response = config.decrypt_text(entry.rational_response) if entry.rational_response else ""
            result = config.decrypt_text(entry.result) if entry.result else ""
            date_str = entry.created_at.strftime("%d.%m.%Y %H:%M")

            emotions_result = await session.execute(
                select(EntryEmotion).where(EntryEmotion.entry_id == entry_id)
            )
            emotions = emotions_result.scalars().all()

            details_text = f"📋 *Запись от {date_str}*\n\n"
            details_text += f"🆔 ID: {entry.id}\n"
            details_text += f"📊 Статус: {entry.status}\n\n"

            if situation:
                details_text += f"📝 *Ситуация:*\n{situation}\n\n"
            if thought:
                details_text += f"💭 *Автоматическая мысль:*\n{thought}\n\n"
            if emotions:
                details_text += "🎭 *Эмоции:*\n"
                for emotion in emotions:
                    intensity_info = f"{emotion.intensity}%"
                    if emotion.reassessment_intensity is not None:
                        change = emotion.reassessment_intensity - emotion.intensity
                        intensity_info += f" → {emotion.reassessment_intensity}% ({change:+}%)"
                    details_text += f"• {format_emotion_display(emotion.emotion_name)}: {intensity_info}\n"
                details_text += "\n"
            if response:
                details_text += f"🧠 *Рациональный ответ:*\n{response}\n\n"
            if result:
                details_text += f"📊 *Результат:*\n{result}\n\n"
            details_text += f"📅 Создано: {entry.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            if entry.updated_at != entry.created_at:
                details_text += f"✏️ Обновлено: {entry.updated_at.strftime('%d.%m.%Y %H:%M')}"

            await callback.message.answer(
                details_text,
                parse_mode="Markdown",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text="🗑️ Удалить эту запись",
                                callback_data=f"delete_from_view_{entry_id}"
                            ),
                            types.InlineKeyboardButton(
                                text="⬅️ Назад к списку",
                                callback_data="back_to_entries_list"
                            )
                        ]
                    ]
                )
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"❌ Ошибка при просмотре деталей: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@diary_router.callback_query(F.data.startswith("delete_from_view_"))
async def delete_from_entries_view(callback: types.CallbackQuery):
    """Удаление записи из просмотра"""
    try:
        entry_id = int(callback.data.replace("delete_from_view_", ""))
        user_id = callback.from_user.id

        async with AsyncSessionLocal() as session:
            user_result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                await callback.answer("❌ Ошибка", show_alert=True)
                return

            success = await delete_entry_simple(entry_id, user.id)

            if success:
                await callback.message.answer(
                    f"✅ Запись успешно удалена!",
                    reply_markup=get_main_menu()
                )
                await callback.message.delete()
            else:
                await callback.answer("❌ Не удалось удалить запись", show_alert=True)

        await callback.answer()

    except Exception as e:
        logger.error(f"❌ Ошибка при удалении из просмотра: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@diary_router.callback_query(F.data == "back_to_entries_list")
async def back_to_entries_list(callback: types.CallbackQuery):
    """Возврат к списку записей"""
    await callback.message.delete()
    await callback.answer()


@diary_router.callback_query(F.data == "back_to_main_from_entries")
async def back_to_main_from_entries(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню из просмотра записей"""
    await state.clear()
    await callback.message.answer(
        "🏠 Возвращаемся в главное меню:",
        reply_markup=get_main_menu()
    )
    await callback.message.delete()
    await callback.answer()


@diary_router.message(F.text == "📄 Политика конфиденциальности")
async def show_privacy_policy(message: types.Message):
    """Показывает политику конфиденциальности"""
    try:
        with open("privacy_policy.txt", "r", encoding="utf-8") as f:
            policy = f.read()
        await message.answer(policy[:4000])
    except:
        await message.answer(
            "📄 *Политика конфиденциальности*\n\n"
            "Ваши данные защищены и используются только для работы сервиса.\n"
            "Полная версия политики доступна на нашем сайте.",
            parse_mode="Markdown"
        )