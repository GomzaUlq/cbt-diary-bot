"""Продолжение незавершённых записей (черновиков)"""

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, desc

from database.engine import AsyncSessionLocal
from database.models import Entry, EntryEmotion, User
from keyboards import get_main_menu, get_response_keyboard_with_back, format_emotion_display
from states import DiaryStates
from config import config
from .save import save_diary_entry

import logging

logger = logging.getLogger(__name__)

diary_router = Router()


@diary_router.message(F.text == "🔄 Продолжить записи")
async def continue_entries(message: types.Message, state: FSMContext):
    """Показываем незавершённые записи пользователя"""
    logger.info(f"📋 КНОПКА 'Продолжить записи' нажата user_id={message.from_user.id}")

    await state.clear()

    user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            await message.answer(
                "❌ У вас нет незавершённых записей.\n"
                "Создайте новую запись через меню.",
                reply_markup=get_main_menu()
            )
            return

        entries_result = await session.execute(
            select(Entry)
            .where(Entry.user_id == user.id, Entry.status == "draft")
            .order_by(desc(Entry.created_at))
        )
        draft_entries = entries_result.scalars().all()

        if not draft_entries:
            await message.answer(
                "✅ У вас нет незавершённых записей!\n"
                "Все записи завершены или вы ещё не начинали.",
                reply_markup=get_main_menu()
            )
            return

        entries_text = "📋 *Ваши незавершённые записи:*\n\n"
        entries_list = []

        for i, entry in enumerate(draft_entries[:10], 1):
            situation_decrypted = config.decrypt_text(entry.situation) if entry.situation else ""
            situation_preview = situation_decrypted[:80] + "..." if situation_decrypted and len(situation_decrypted) > 80 else situation_decrypted or "Без описания"
            date_str = entry.created_at.strftime("%d.%m.%Y %H:%M")

            entries_text += f"{i}. *{date_str}*\n"
            entries_text += f"   📝 {situation_preview}\n\n"

            entries_list.append((entry.id, f"{i}. {date_str} - {situation_preview}"))

        await state.update_data(
            draft_entries=entries_list,
            draft_count=len(entries_list)
        )

        await state.set_state(DiaryStates.choosing_draft_entry)

        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

        keyboard_buttons = []
        for i, (entry_id, entry_text) in enumerate(entries_list, 1):
            button_text = entry_text.split(" - ")[0] if " - " in entry_text else f"{i}. Запись"
            keyboard_buttons.append([KeyboardButton(text=button_text)])

        keyboard_buttons.append([KeyboardButton(text="⬅️ Назад в меню")])

        choose_keyboard = ReplyKeyboardMarkup(
            keyboard=keyboard_buttons,
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await message.answer(
            entries_text + "\n➡️ *Выберите запись для продолжения:*",
            parse_mode="Markdown",
            reply_markup=choose_keyboard
        )


@diary_router.message(DiaryStates.choosing_draft_entry)
async def process_draft_choice(message: types.Message, state: FSMContext):
    """Обработка выбора записи для продолжения с ПОЛНЫМ текстом"""
    try:
        if message.text == "⬅️ Назад в меню":
            await state.clear()
            await message.answer("Возвращаемся в главное меню:", reply_markup=get_main_menu())
            return

        choice_text = message.text

        if '. ' in choice_text:
            choice_num = int(choice_text.split('. ')[0])
        else:
            choice_num = int(choice_text)

        data = await state.get_data()
        entries_list = data.get('draft_entries', [])

        if 1 <= choice_num <= len(entries_list):
            entry_id, _ = entries_list[choice_num - 1]

            async with AsyncSessionLocal() as session:
                entry_result = await session.execute(
                    select(Entry).where(Entry.id == entry_id)
                )
                entry = entry_result.scalar_one()

                emotions_result = await session.execute(
                    select(EntryEmotion).where(EntryEmotion.entry_id == entry_id)
                )
                entry_emotions = emotions_result.scalars().all()

                emotions = [emotion.emotion_name for emotion in entry_emotions]
                emotion_intensities = {emotion.emotion_name: emotion.intensity for emotion in entry_emotions}

                situation_decrypted = config.decrypt_text(entry.situation) if entry.situation else ""
                thought_decrypted = config.decrypt_text(entry.automatic_thought) if entry.automatic_thought else ""
                response_decrypted = config.decrypt_text(entry.rational_response) if entry.rational_response else ""

                await state.update_data(
                    entry_id=entry.id,
                    situation=situation_decrypted,
                    thought=thought_decrypted,
                    response=response_decrypted,
                    emotions=emotions,
                    emotion_intensities=emotion_intensities
                )

                if response_decrypted == "[ОТЛОЖЕНО - ответить позже]":
                    await state.set_state(DiaryStates.waiting_for_response)

                    intensity_text = "\n".join([f"{emoji}: {intensity}%" for emoji, intensity in emotion_intensities.items()])

                    await message.answer(
                        f"🔄 *Продолжение записи от {entry.created_at.strftime('%d.%m.%Y %H:%M')}*\n\n"
                        f"📋 *Ситуация:*\n{situation_decrypted}\n\n"
                        f"🎭 *Эмоции:*\n{intensity_text}\n\n"
                        f"💭 *Автоматическая мысль:*\n{thought_decrypted}\n\n"
                        "🧠 *Шаг 6 из 7: Рациональная реакция*\n\n"
                        "Какой рациональный ответ ты можешь дать этой мысли?\n"
                        "(Что бы ты сказал другу в такой ситуации?)",
                        parse_mode="Markdown",
                        reply_markup=get_response_keyboard_with_back()
                    )
                else:
                    await state.set_state(DiaryStates.waiting_for_emotion_reassessment)

                    await message.answer(
                        f"🔄 *Продолжение записи от {entry.created_at.strftime('%d.%m.%Y %H:%M')}*\n\n"
                        f"📋 *Ситуация:*\n{situation_decrypted}\n\n"
                        f"💭 *Автоматическая мысль:*\n{thought_decrypted}\n\n"
                        f"🧠 *Рациональная реакция:*\n{response_decrypted}\n\n"
                        "🔄 Теперь давай переоценим эмоции после анализа:",
                        parse_mode="Markdown"
                    )

                    from .steps import ask_emotion_reassessment
                    await ask_emotion_reassessment(message, state)

        else:
            await message.answer(
                "❌ Неверный номер записи. Попробуйте снова.",
                reply_markup=get_main_menu()
            )
            await state.clear()

    except (ValueError, IndexError):
        await message.answer(
            "❌ Пожалуйста, выберите запись из списка выше.",
            reply_markup=get_main_menu()
        )
        await state.clear()
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке выбора черновика: {e}")
        await message.answer(
            "❌ Произошла ошибка при загрузке записи.\nПожалуйста, попробуйте снова.",
            reply_markup=get_main_menu()
        )
        await state.clear()
        