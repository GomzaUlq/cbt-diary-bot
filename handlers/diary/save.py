"""Сохранение записи в БД с шифрованием, валидацией и проверкой лимитов"""

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, delete
from datetime import datetime

from database.engine import AsyncSessionLocal
from database.models import Entry, EntryEmotion, User
from keyboards import get_main_menu
from config import config

import logging

logger = logging.getLogger(__name__)

diary_router = Router()


async def save_diary_entry(message: types.Message, state: FSMContext, status="completed", reassessment_done=False):
    """Сохранение или обновление записи в БД с проверкой лимитов, валидацией и шифрованием"""
    try:
        data = await state.get_data()
        user_id = message.from_user.id

        logger.info(f"💾 Попытка сохранения записи user_id={user_id}, status={status}")

        # ====== ВАЛИДАЦИЯ ДАННЫХ ПЕРЕД СОХРАНЕНИЕМ ======
        emotions = data.get('emotions', [])
        emotion_intensities = data.get('emotion_intensities', {})

        # 1. Проверка количества эмоций
        if len(emotions) > config.MAX_EMOTIONS_PER_ENTRY:
            logger.warning(f"⚠️ User {user_id} превысил лимит эмоций: {len(emotions)} > {config.MAX_EMOTIONS_PER_ENTRY}")
            await message.answer(
                f"❌ Слишком много эмоций. Максимум {config.MAX_EMOTIONS_PER_ENTRY}.\n"
                "Пожалуйста, выберите основные эмоции и создайте новую запись.",
                reply_markup=get_main_menu()
            )
            await state.clear()
            return

        # 2. Проверка валидности интенсивностей
        for emotion_name in emotions:
            intensity = emotion_intensities.get(emotion_name)
            if intensity is None:
                logger.error(f"❌ У эмоции '{emotion_name}' нет интенсивности")
                await message.answer(
                    "❌ Ошибка данных: у некоторых эмоций отсутствует интенсивность.\n"
                    "Пожалуйста, создайте запись заново.",
                    reply_markup=get_main_menu()
                )
                await state.clear()
                return

            if not isinstance(intensity, int) or intensity < 0 or intensity > 100:
                logger.error(f"❌ Неверная интенсивность для '{emotion_name}': {intensity}")
                await message.answer(
                    "❌ Ошибка данных: неверная интенсивность эмоций.\n"
                    "Пожалуйста, создайте запись заново.",
                    reply_markup=get_main_menu()
                )
                await state.clear()
                return

        async with AsyncSessionLocal() as session:
            # ====== ПРОВЕРКА ЛИМИТОВ ПОЛЬЗОВАТЕЛЯ ======
            try:
                user_result = await session.execute(
                    select(User).where(User.telegram_id == user_id)
                )
                user = user_result.scalar_one()

                if not data.get('entry_id'):
                    count_result = await session.execute(
                        select(func.count(Entry.id)).where(Entry.user_id == user.id)
                    )
                    entries_count = count_result.scalar() or 0

                    if entries_count >= config.MAX_ENTRIES_PER_USER:
                        logger.warning(f"⚠️ User {user_id} достиг лимита записей: {entries_count}")
                        await message.answer(
                            f"❌ Достигнут лимит записей ({config.MAX_ENTRIES_PER_USER}).\n\n"
                            "Что можно сделать:\n"
                            "1. Удалите старые записи через меню\n"
                            "2. Экспортируйте данные для архивации\n"
                            "3. Свяжитесь с поддержкой для увеличения лимита",
                            reply_markup=get_main_menu()
                        )
                        await state.clear()
                        return
            except Exception as e:
                logger.error(f"❌ Ошибка при проверке лимитов пользователя {user_id}: {e}")

            # ====== ОСНОВНАЯ ЛОГИКА СОХРАНЕНИЯ ======
            existing_entry_id = data.get('entry_id')

            try:
                # ====== ПОДГОТОВКА И ШИФРОВАНИЕ ДАННЫХ ======
                situation = data.get('situation', '')
                thought = data.get('thought', '')
                response = data.get('response', '')
                result = data.get('result', '')

                situation_encrypted = config.encrypt_text(situation) if situation else None
                thought_encrypted = config.encrypt_text(thought) if thought else None
                response_encrypted = config.encrypt_text(response) if response else None
                result_encrypted = config.encrypt_text(result) if result else None

                if existing_entry_id:
                    logger.info(f"🔄 Обновление записи ID={existing_entry_id} для user_id={user_id}")

                    entry_result = await session.execute(
                        select(Entry).where(Entry.id == existing_entry_id, Entry.user_id == user.id)
                    )
                    entry = entry_result.scalar_one_or_none()

                    if not entry:
                        logger.error(f"🚨 Попытка обновить чужую запись: user_id={user_id}, entry_id={existing_entry_id}")
                        await message.answer(
                            "❌ Ошибка: запись не найдена или у вас нет к ней доступа.\n"
                            "Возможно, она была удалена.",
                            reply_markup=get_main_menu()
                        )
                        await state.clear()
                        return

                    entry.situation = situation_encrypted
                    entry.automatic_thought = thought_encrypted
                    entry.rational_response = response_encrypted
                    entry.result = result_encrypted
                    entry.status = status
                    entry.updated_at = datetime.now()

                    logger.info(f"✅ Запись {existing_entry_id} обновлена, новый статус: {status}")

                    await session.execute(
                        delete(EntryEmotion).where(EntryEmotion.entry_id == existing_entry_id)
                    )

                else:
                    logger.info(f"🆕 Создание новой записи для user_id={user_id}")

                    entry = Entry(
                        user_id=user.id,
                        situation=situation_encrypted,
                        automatic_thought=thought_encrypted,
                        rational_response=response_encrypted,
                        result=result_encrypted,
                        status=status,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    session.add(entry)

                await session.commit()
                await session.refresh(entry)

                logger.info(f"✅ Запись сохранена/обновлена, ID: {entry.id}")

                # ====== СОХРАНЕНИЕ ЭМОЦИЙ ======
                reassessment_intensities = data.get('reassessment_intensities', {})
                saved_emotions_count = 0

                for emotion_name in emotions:
                    original_intensity = emotion_intensities.get(emotion_name)

                    if original_intensity is None or not isinstance(original_intensity, int):
                        logger.warning(f"⚠️ Исправление интенсивности для '{emotion_name}' у записи {entry.id}")
                        original_intensity = 50

                    reassessment_value = None
                    if reassessment_done:
                        reassessment_value = reassessment_intensities.get(emotion_name)
                        if reassessment_value is not None:
                            if not isinstance(reassessment_value, int) or reassessment_value < 0 or reassessment_value > 100:
                                reassessment_value = original_intensity
                                logger.warning(f"⚠️ Исправлена неверная переоценка для '{emotion_name}'")

                    emotion_record = EntryEmotion(
                        entry_id=entry.id,
                        emotion_name=emotion_name,
                        intensity=original_intensity,
                        reassessment_intensity=reassessment_value,
                        created_at=datetime.now()
                    )
                    session.add(emotion_record)
                    saved_emotions_count += 1

                await session.commit()
                logger.info(f"✅ Сохранено {saved_emotions_count} эмоций для записи {entry.id}")

                # ====== ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ ======
                verify_result = await session.execute(
                    select(func.count(Entry.id)).where(Entry.id == entry.id)
                )
                if verify_result.scalar() == 0:
                    raise Exception("Запись не была сохранена в БД")

                # ====== СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЮ ======
                await state.clear()

                if status == "completed":
                    situation_preview = situation[:80]
                    thought_preview = thought[:80]
                    response_preview = response[:80]

                    completion_text = f"""
✨ *Запись успешно {'обновлена' if existing_entry_id else 'сохранена'}!* ✨

✅ *Статус:* Завершена

📋 *Ситуация:* {situation_preview}{'...' if len(situation) > 80 else ''}

🎭 *Эмоции:* {len(emotions)} шт.
"""
                    for emotion_name in emotions:
                        original = emotion_intensities.get(emotion_name, "?")
                        reassessment = reassessment_intensities.get(emotion_name)

                        if reassessment is not None:
                            change = reassessment - original if isinstance(original, int) else 0
                            completion_text += f"   • {emotion_name}: {original}% → {reassessment}% ({change:+}%)\n"
                        else:
                            completion_text += f"   • {emotion_name}: {original}%\n"

                    completion_text += f"""
💭 *Автоматическая мысль:* {thought_preview}{'...' if len(thought) > 80 else ''}

🧠 *Рациональная реакция:* {response_preview}{'...' if len(response) > 80 else ''}

🎯 Отличная работа! Анализ ситуации завершён.
"""
                    if existing_entry_id:
                        completion_text += "\n🔄 Эта запись больше не будет отображаться в 'Продолжить записи'."

                    await message.answer(completion_text, parse_mode="Markdown", reply_markup=get_main_menu())

                else:
                    draft_text = f"""
📋 *Запись сохранена как черновик!*

{'✏️ Запись можно будет продолжить позже через "🔄 Продолжить записи".' if not existing_entry_id else '✏️ Запись обновлена, можно продолжить позже.'}

📊 *Прогресс:*
   • Ситуация: ✅
   • Эмоции: ✅ ({len(emotions)} шт.)
   • Автоматическая мысль: ✅
   • Рациональная реакция: {'⏰ ОТЛОЖЕНО' if response.startswith('[ОТЛОЖЕНО') else '✅'}
   • Переоценка эмоций: {'⏰ ОТЛОЖЕНО' if not reassessment_done else '✅'}
"""
                    await message.answer(draft_text, parse_mode="Markdown", reply_markup=get_main_menu())

                logger.info(f"✅ Успешное сохранение записи {entry.id} для user_id={user_id}")

            except Exception as save_error:
                await session.rollback()
                logger.error(f"❌ Ошибка сохранения записи для user_id={user_id}: {save_error}")
                raise save_error

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в save_diary_entry для user_id={user_id}: {error_msg}")

        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Трассировка ошибки:\n{error_trace[:500]}")

        user_friendly_msg = (
            "❌ Произошла ошибка при сохранении записи.\n\n"
            "Возможные причины:\n"
            "• Проблемы с подключением к базе данных\n"
            "• Недостаточно памяти\n"
            "• Технические работы на сервере\n\n"
            "Пожалуйста:\n"
            "1. Попробуйте создать запись заново\n"
            "2. Если ошибка повторяется, подождите 15 минут\n"
            "3. Обратитесь в поддержку, если проблема не решается"
        )

        await message.answer(user_friendly_msg, reply_markup=get_main_menu())
        await state.clear()