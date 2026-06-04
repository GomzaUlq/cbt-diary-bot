from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.engine import AsyncSessionLocal
from database.models import User
from sqlalchemy import select, update
from keyboards import get_main_menu, get_settings_menu
import re

settings_router = Router()


class SettingsStates(StatesGroup):
    waiting_for_reminder_time = State()


@settings_router.message(F.text == "⚙️ Настройки")
async def show_settings(message: types.Message):
    """Показ меню настроек"""
    await message.answer(
        "⚙️ *Настройки бота*\n\n"
        "Выберите, что хотите настроить:",
        parse_mode="Markdown",
        reply_markup=get_settings_menu()
    )


@settings_router.message(F.text == "⏰ Время напоминаний")
async def set_reminder_time(message: types.Message, state: FSMContext):
    """Настройка времени напоминаний"""
    user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        current_time = user.reminder_time if user else "20:00"

    await state.set_state(SettingsStates.waiting_for_reminder_time)

    await message.answer(
        f"⏰ *Настройка времени напоминаний*\n\n"
        f"Текущее время: *{current_time}*\n\n"
        f"Введите новое время в формате *ЧЧ:ММ*\n"
        f"(например: 21:30 или 09:00)\n\n"
        f"Бот будет напоминать вам о незавершённых записях в это время.",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )


@settings_router.message(SettingsStates.waiting_for_reminder_time)
async def process_reminder_time(message: types.Message, state: FSMContext):
    """Обработка введённого времени"""
    time_text = message.text.strip()

    # Проверяем формат времени (ЧЧ:ММ)
    time_pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'

    if not re.match(time_pattern, time_text):
        await message.answer(
            "❌ *Неверный формат времени!*\n\n"
            "Пожалуйста, введите время в формате *ЧЧ:ММ*\n"
            "Например: 21:30 или 09:00",
            parse_mode="Markdown"
        )
        return

    user_id = message.from_user.id

    try:
        async with AsyncSessionLocal() as session:
            # Обновляем время напоминаний
            await session.execute(
                update(User)
                .where(User.telegram_id == user_id)
                .values(reminder_time=time_text)
            )
            await session.commit()

        await state.clear()

        await message.answer(
            f"✅ *Время напоминаний установлено!*\n\n"
            f"Теперь бот будет напоминать вам о незавершённых записях каждый день в *{time_text}*.\n\n"
            f"Вы можете изменить время в любой момент в настройках.",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при сохранении настроек: {str(e)[:100]}",
            reply_markup=get_main_menu()
        )
        await state.clear()


@settings_router.message(F.text == "📋 Мои настройки")
async def show_my_settings(message: types.Message):
    """Показ текущих настроек пользователя"""
    user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            await message.answer(
                "❌ Настройки не найдены. Пожалуйста, начните с команды /start",
                reply_markup=get_main_menu()
            )
            return

        settings_text = f"""
⚙️ *Ваши текущие настройки:*

👤 *Профиль:*
   • Имя: {user.full_name or 'Не указано'}
   • Username: @{user.username or 'Не указан'}

⏰ *Напоминания:*
   • Время напоминаний: {user.reminder_time}
   • Напоминания включены: {'✅' if user.reminder_time != '00:00' else '❌'}

📊 *Статистика профиля:*
   • Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}
"""

        await message.answer(settings_text, parse_mode="Markdown", reply_markup=get_main_menu())


@settings_router.message(F.text == "🏠 Главное меню")
async def back_to_main_menu(message: types.Message, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await message.answer(
        "Возвращаемся в главное меню:",
        reply_markup=get_main_menu()
    )