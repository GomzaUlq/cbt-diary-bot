from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
import logging

from database.models import User
from database.engine import AsyncSessionLocal
from keyboards import get_main_menu, get_stats_menu

logger = logging.getLogger(__name__)
start_router = Router()


@start_router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()

    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    async with AsyncSessionLocal() as session:
        # Проверяем, есть ли пользователь
        user_result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            # Создаём нового пользователя
            user = User(
                telegram_id=user_id,
                username=username,
                full_name=full_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"👤 Создан новый пользователь при /start: {user_id}")

    await message.answer(
        "👋 *Добро пожаловать в Cognitive Diary!*\n\n"
        "Этот бот поможет тебе вести дневник когнитивно-поведенческой терапии.\n\n"
        "📝 Используй *'Новая запись'* чтобы начать анализ ситуации.\n"
        "📊 Смотри статистику в *'Мои записи'*.\n"
        "⏰ Настрой напоминания в *'Напоминания'*.\n\n"
        "Главное меню ниже 👇",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )


@start_router.message(Command("menu"))
async def cmd_menu(message: types.Message):
    """Команда /menu для показа главного меню"""
    await message.answer("Главное меню:", reply_markup=get_main_menu())


@start_router.message(F.text == "🏠 Главное меню")
async def show_main_menu(message: types.Message, state: FSMContext):
    """Показ главного меню в любой момент"""
    await state.clear()
    await message.answer(
        "Выберите действие:",
        reply_markup=get_main_menu()
    )


@start_router.message(F.text == "📊 Статистика")
async def show_stats_menu(message: types.Message):
    """Показ меню статистики"""
    await message.answer(
        "📊 Выберите тип статистики:",
        reply_markup=get_stats_menu()
    )


# В handlers/start.py добавь:
