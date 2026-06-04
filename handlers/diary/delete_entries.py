"""Удаление записей с пагинацией"""

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, desc

from database.engine import AsyncSessionLocal
from database.models import Entry, EntryEmotion, User
from keyboards import (
    get_main_menu, get_simple_delete_keyboard, get_delete_pagination_keyboard,
    get_delete_actions_keyboard, format_emotion_display
)
from config import config
from utils.deletion_utils import delete_entry_simple

import logging

logger = logging.getLogger(__name__)

diary_router = Router()


@diary_router.message(F.text == "🗑️ Удалить запись")
async def start_delete_with_pagination(message: types.Message, state: FSMContext):
    """Начинаем режим удаления с пагинацией"""
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
                "📭 У вас нет записей для удаления.",
                reply_markup=get_main_menu()
            )
            return

        PAGE_SIZE = 10
        total_pages = (total_entries + PAGE_SIZE - 1) // PAGE_SIZE

        entries_result = await session.execute(
            select(Entry)
            .where(Entry.user_id == user.id)
            .order_by(desc(Entry.created_at))
            .limit(PAGE_SIZE)
            .offset(0)
        )
        entries = entries_result.scalars().all()

        entries_text = f"🗑️ *Удаление записей*\n\n"
        entries_text += f"📊 Всего записей: {total_entries}\n"
        entries_text += f"📄 Страница 1/{total_pages}\n\n"

        entries_list = []
        global_index = 1

        for entry in entries:
            situation = config.decrypt_text(entry.situation) if entry.situation else ""
            situation_preview = situation[:25] + "..." if len(situation) > 25 else situation or "Без описания"
            date_str = entry.created_at.strftime("%d.%m %H:%M")

            entries_text += f"*{global_index}.* {date_str} - {situation_preview}\n"
            entries_list.append((entry.id, f"{global_index}"))
            global_index += 1

        entries_text += f"\n📌 *Как удалить:*\n"
        entries_text += f"1. Введите номер записи (1-{min(total_entries, PAGE_SIZE)})\n"
        entries_text += f"2. Подтвердите удаление\n\n"

        if total_pages > 1:
            entries_text += f"🔄 Используйте кнопки ниже для навигации"

        await state.update_data(
            delete_entries=entries_list,
            entries_full_info=entries,
            current_page=1,
            total_pages=total_pages,
            total_entries=total_entries,
            page_size=PAGE_SIZE,
            user_db_id=user.id
        )

        await message.answer(
            entries_text,
            parse_mode="Markdown",
            reply_markup=get_delete_pagination_keyboard(1, total_pages)
        )

        await message.answer(
            "⌨️ *Введите номер записи:*",
            parse_mode="Markdown",
            reply_markup=get_simple_delete_keyboard(entries_list, page=1)
        )


@diary_router.callback_query(F.data.startswith("delete_page_"))
async def change_delete_page(callback: types.CallbackQuery, state: FSMContext):
    """Смена страницы при удалении"""
    try:
        page = int(callback.data.replace("delete_page_", ""))
        data = await state.get_data()

        total_pages = data.get('total_pages', 1)
        user_db_id = data.get('user_db_id')
        page_size = data.get('page_size', 10)

        if page < 1 or page > total_pages:
            await callback.answer("❌ Неверная страница")
            return

        async with AsyncSessionLocal() as session:
            offset = (page - 1) * page_size
            entries_result = await session.execute(
                select(Entry)
                .where(Entry.user_id == user_db_id)
                .order_by(desc(Entry.created_at))
                .limit(page_size)
                .offset(offset)
            )
            entries = entries_result.scalars().all()

            if not entries:
                await callback.answer("❌ На этой странице нет записей")
                return

            entries_text = f"🗑️ *Удаление записей*\n\n"
            entries_text += f"📄 Страница {page}/{total_pages}\n\n"

            entries_list = []
            global_index = (page - 1) * page_size + 1

            for entry in entries:
                situation = config.decrypt_text(entry.situation) if entry.situation else ""
                situation_preview = situation[:25] + "..." if len(situation) > 25 else situation or "Без описания"
                date_str = entry.created_at.strftime("%d.%m %H:%M")

                entries_text += f"*{global_index}.* {date_str} - {situation_preview}\n"
                entries_list.append((entry.id, f"{global_index}"))
                global_index += 1

            entries_text += f"\n📌 *Как удалить:*\n"
            entries_text += f"1. Введите номер записи ({global_index-page_size}-{global_index-1})\n"
            entries_text += f"2. Подтвердите удаление"

            await state.update_data(
                delete_entries=entries_list,
                entries_full_info=entries,
                current_page=page
            )

            await callback.message.edit_text(
                entries_text,
                parse_mode="Markdown",
                reply_markup=get_delete_pagination_keyboard(page, total_pages)
            )

            await callback.message.answer(
                "⌨️ *Введите номер записи:*",
                parse_mode="Markdown",
                reply_markup=get_simple_delete_keyboard(entries_list, page=page)
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"❌ Ошибка при смене страницы: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@diary_router.message(F.text.regexp(r'^\d+$'))
async def process_entry_selection_with_pagination(message: types.Message, state: FSMContext):
    """Обработка выбора номера записи с учетом пагинации"""
    data = await state.get_data()
    entries_full = data.get('entries_full_info', [])
    current_page = data.get('current_page', 1)
    page_size = data.get('page_size', 10)
    total_entries = data.get('total_entries', 0)

    try:
        choice = int(message.text)

        if 1 <= choice <= total_entries:
            index_on_page = (choice - 1) % page_size

            if 0 <= index_on_page < len(entries_full):
                entry = entries_full[index_on_page]

                situation = config.decrypt_text(entry.situation) if entry.situation else ""
                thought = config.decrypt_text(entry.automatic_thought) if entry.automatic_thought else ""
                date_str = entry.created_at.strftime("%d.%m.%Y %H:%M")

                async with AsyncSessionLocal() as session:
                    emotions_result = await session.execute(
                        select(EntryEmotion).where(EntryEmotion.entry_id == entry.id)
                    )
                    emotions = emotions_result.scalars().all()

                    emotions_text = ""
                    if emotions:
                        emotions_text = "\n🎭 *Эмоции:*\n"
                        for emotion in emotions:
                            intensity_info = f"{emotion.intensity}%"
                            if emotion.reassessment_intensity is not None:
                                change = emotion.reassessment_intensity - emotion.intensity
                                intensity_info += f" → {emotion.reassessment_intensity}% ({change:+}%)"
                            display_name = format_emotion_display(emotion.emotion_name)
                            emotions_text += f"• {display_name}: {intensity_info}\n"

                await state.update_data(selected_entry_id=entry.id)

                await message.answer(
                    f"📋 *Запись #{choice} от {date_str}*\n\n"
                    f"📝 *Ситуация:*\n{situation[:300]}{'...' if len(situation) > 300 else ''}\n\n"
                    f"💭 *Мысль:*\n{thought[:200]}{'...' if len(thought) > 200 else ''}\n"
                    f"{emotions_text}\n"
                    f"Статус: {entry.status}\n\n"
                    "❓ *Удалить эту запись?*\n"
                    "❌ Действие необратимо!",
                    parse_mode="Markdown",
                    reply_markup=get_delete_actions_keyboard()
                )
            else:
                await message.answer(f"❌ Запись #{choice} не найдена.", reply_markup=get_main_menu())
        else:
            await message.answer(f"❌ Неверный номер. Введите от 1 до {total_entries}", reply_markup=get_main_menu())

    except ValueError:
        await message.answer("❌ Пожалуйста, введите только номер записи")


@diary_router.callback_query(F.data == "confirm_delete")
async def confirm_simple_delete(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления"""
    data = await state.get_data()
    entry_id = data.get('selected_entry_id')
    user_id = callback.from_user.id

    if not entry_id:
        await callback.answer("❌ Запись не выбрана", show_alert=True)
        return

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
                "✅ Запись успешно удалена!",
                reply_markup=get_main_menu()
            )
            await callback.message.delete()
        else:
            await callback.answer("❌ Не удалось удалить запись", show_alert=True)

    await state.clear()
    await callback.answer()


@diary_router.callback_query(F.data == "view_entry")
async def view_entry_full(callback: types.CallbackQuery, state: FSMContext):
    """Просмотр полной записи с расшифровкой данных"""
    data = await state.get_data()
    entry_id = data.get('selected_entry_id')

    if not entry_id:
        await callback.answer("❌ Запись не выбрана", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        entry_result = await session.execute(
            select(Entry).where(Entry.id == entry_id)
        )
        entry = entry_result.scalar_one_or_none()

        if entry:
            situation = config.decrypt_text(entry.situation) if entry.situation else ""
            thought = config.decrypt_text(entry.automatic_thought) if entry.automatic_thought else ""
            response = config.decrypt_text(entry.rational_response) if entry.rational_response else ""
            result = config.decrypt_text(entry.result) if entry.result else ""
            date_str = entry.created_at.strftime("%d.%m.%Y %H:%M")

            emotions_result = await session.execute(
                select(EntryEmotion).where(EntryEmotion.entry_id == entry_id)
            )
            emotions = emotions_result.scalars().all()

            full_text = f"📋 *Полная запись от {date_str}*\n\n"

            if situation:
                full_text += f"📝 *Ситуация:*\n{situation}\n\n"
            if thought:
                full_text += f"💭 *Автоматическая мысль:*\n{thought}\n\n"
            if emotions:
                full_text += "🎭 *Эмоции:*\n"
                for emotion in emotions:
                    intensity_info = f"{emotion.intensity}%"
                    if emotion.reassessment_intensity is not None:
                        change = emotion.reassessment_intensity - emotion.intensity
                        intensity_info += f" → {emotion.reassessment_intensity}% ({change:+}%)"
                    display_name = format_emotion_display(emotion.emotion_name)
                    full_text += f"• {display_name}: {intensity_info}\n"
                full_text += "\n"
            if response:
                full_text += f"🧠 *Рациональный ответ:*\n{response}\n\n"
            if result:
                full_text += f"📊 *Результат:*\n{result}\n\n"
            full_text += f"Статус: {entry.status}"

            if len(full_text) > 4000:
                for i in range(0, len(full_text), 4000):
                    await callback.message.answer(
                        full_text[i:i+4000],
                        parse_mode="Markdown",
                        reply_markup=get_delete_actions_keyboard() if i + 4000 >= len(full_text) else None
                    )
            else:
                await callback.message.answer(
                    full_text,
                    parse_mode="Markdown",
                    reply_markup=get_delete_actions_keyboard()
                )

    await callback.answer()


@diary_router.callback_query(F.data == "cancel_delete")
@diary_router.message(F.text == "❌ Отмена")
@diary_router.message(F.text == "⬅️ Назад в меню")
async def cancel_simple_delete(event: types.Message | types.CallbackQuery, state: FSMContext):
    """Отмена удаления"""
    await state.clear()

    if isinstance(event, types.Message):
        await event.answer("❌ Удаление отменено.", reply_markup=get_main_menu())
    else:
        await event.message.answer("❌ Удаление отменено.", reply_markup=get_main_menu())
        await event.answer()