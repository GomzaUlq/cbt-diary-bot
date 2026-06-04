"""Просмотр записей с пагинацией и деталями"""

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, desc

from database.engine import AsyncSessionLocal
from database.models import Entry, EntryEmotion, User
from keyboards import get_main_menu, get_entries_pagination_keyboard, format_emotion_display
from config import config
from utils.deletion_utils import delete_entry_simple

import logging

logger = logging.getLogger(__name__)

diary_router = Router()


@diary_router.message(F.text == "📊 Мои записи")
async def show_my_entries(message: types.Message, state: FSMContext):
    """Показывает записи пользователя с пагинацией"""
    await state.clear()

    user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            await message.answer(
                "❌ У вас ещё нет записей.",
                reply_markup=get_main_menu()
            )
            return

        count_result = await session.execute(
            select(func.count(Entry.id)).where(Entry.user_id == user.id)
        )
        total_entries = count_result.scalar() or 0

        if total_entries == 0:
            await message.answer(
                "📭 У вас ещё нет записей.\nСоздайте первую запись!",
                reply_markup=get_main_menu()
            )
            return

        PAGE_SIZE = 5
        total_pages = (total_entries + PAGE_SIZE - 1) // PAGE_SIZE
        current_page = 1

        entries_result = await session.execute(
            select(Entry)
            .where(Entry.user_id == user.id)
            .order_by(desc(Entry.created_at))
            .limit(PAGE_SIZE)
            .offset((current_page - 1) * PAGE_SIZE)
        )
        entries = entries_result.scalars().all()

        response = f"📊 *Ваши записи*\n\n"
        response += f"📈 Всего записей: {total_entries}\n"
        response += f"📄 Страница {current_page}/{total_pages}\n\n"

        for i, entry in enumerate(entries, 1):
            emotions_result = await session.execute(
                select(EntryEmotion).where(EntryEmotion.entry_id == entry.id)
            )
            emotions = emotions_result.scalars().all()

            date_str = entry.created_at.strftime("%d.%m.%Y %H:%M")
            situation = config.decrypt_text(entry.situation) if entry.situation else "Без описания"
            situation_preview = situation[:40] + "..." if len(situation) > 40 else situation

            global_num = (current_page - 1) * PAGE_SIZE + i

            response += f"*{global_num}. {date_str}*\n"
            response += f"📋 *Ситуация:* {situation_preview}\n"
            response += f"📝 *Статус:* {entry.status}\n"

            if emotions:
                emotion_names = [format_emotion_display(e.emotion_name) for e in emotions[:2]]
                response += f"🎭 *Эмоции:* {', '.join(emotion_names)}"
                if len(emotions) > 2:
                    response += f" и ещё {len(emotions) - 2}"
                response += "\n"

            response += f"🔍 ID: {entry.id}\n\n"

        response += f"📌 *Как пользоваться:*\n"
        response += f"• Используйте кнопки ниже для навигации\n"
        response += f"• Нажмите на номер записи для подробного просмотра\n"
        response += f"• Удалить запись можно через '🗑️ Удалить запись'\n"

        await state.update_data(
            entries_view_page=current_page,
            entries_total_pages=total_pages,
            entries_total=total_entries,
            entries_user_id=user.id,
            entries_current_list=[(entry.id, entry.created_at) for entry in entries]
        )

        await message.answer(
            response,
            parse_mode="Markdown",
            reply_markup=get_entries_pagination_keyboard(current_page, total_pages)
        )


@diary_router.callback_query(F.data.startswith("entries_page_"))
async def change_entries_page(callback: types.CallbackQuery, state: FSMContext):
    """Смена страницы при просмотре записей"""
    try:
        page = int(callback.data.replace("entries_page_", ""))
        data = await state.get_data()

        total_pages = data.get('entries_total_pages', 1)
        user_id = data.get('entries_user_id')
        page_size = 5

        if page < 1 or page > total_pages:
            await callback.answer("❌ Неверная страница")
            return

        async with AsyncSessionLocal() as session:
            offset = (page - 1) * page_size
            entries_result = await session.execute(
                select(Entry)
                .where(Entry.user_id == user_id)
                .order_by(desc(Entry.created_at))
                .limit(page_size)
                .offset(offset)
            )
            entries = entries_result.scalars().all()

            response = f"📊 *Ваши записи*\n\n"
            response += f"📄 Страница {page}/{total_pages}\n\n"

            for i, entry in enumerate(entries, 1):
                emotions_result = await session.execute(
                    select(EntryEmotion).where(EntryEmotion.entry_id == entry.id)
                )
                emotions = emotions_result.scalars().all()

                date_str = entry.created_at.strftime("%d.%m.%Y %H:%M")
                situation = config.decrypt_text(entry.situation) if entry.situation else "Без описания"
                situation_preview = situation[:40] + "..." if len(situation) > 40 else situation

                global_num = (page - 1) * page_size + i

                response += f"*{global_num}. {date_str}*\n"
                response += f"📋 *Ситуация:* {situation_preview}\n"
                response += f"📝 *Статус:* {entry.status}\n"

                if emotions:
                    emotion_names = [format_emotion_display(e.emotion_name) for e in emotions[:2]]
                    response += f"🎭 *Эмоции:* {', '.join(emotion_names)}"
                    if len(emotions) > 2:
                        response += f" и ещё {len(emotions) - 2}"
                    response += "\n"

                response += f"🔍 ID: {entry.id}\n\n"

            response += f"📌 *Как пользоваться:*\n"
            response += f"• Используйте кнопки ниже для навигации\n"
            response += f"• Нажмите на номер записи для подробного просмотра\n"

            await state.update_data(
                entries_view_page=page,
                entries_current_list=[(entry.id, entry.created_at) for entry in entries]
            )

            await callback.message.edit_text(
                response,
                parse_mode="Markdown",
                reply_markup=get_entries_pagination_keyboard(page, total_pages)
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"❌ Ошибка при смене страницы записей: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


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
async def back_to_entries_list(callback: types.CallbackQuery, state: FSMContext):
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