"""Шаги создания новой записи: ситуация, эмоции, интенсивность, мысль, реакция, переоценка"""

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from states import DiaryStates
from keyboards import (
    get_main_menu, get_emotion_groups_keyboard, get_subemotions_keyboard,
    get_intensity_keyboard_with_back, get_response_keyboard_with_back,
    get_back_keyboard, format_emotion_display
)
from utils.validators import validator
from .save import save_diary_entry

import logging

logger = logging.getLogger(__name__)

diary_router = Router()


# ====== ШАГ 1: Начало новой записи ======
@diary_router.message(F.text == "📝 Новая запись")
async def start_new_entry(message: types.Message, state: FSMContext):
    logger.info(f"🚀 КНОПКА 'Новая запись' нажата user_id={message.from_user.id}")

    await state.clear()
    await state.set_state(DiaryStates.waiting_for_situation)

    await message.answer(
        "📝 *Шаг 1 из 8: Ситуация*\n\n"
        "Опиши ситуацию, которая вызвала эмоции:\n"
        "(Что именно произошло? Где? Когда?)\n\n"
        "Используйте '⬅️ Назад' для отмены.",
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )


# ====== ОБРАБОТЧИКИ КНОПКИ "НАЗАД" ======
@diary_router.message(DiaryStates.waiting_for_situation, F.text == "⬅️ Назад")
async def back_from_situation(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Создание записи отменено.", reply_markup=get_main_menu())


@diary_router.message(DiaryStates.waiting_for_emotion_group, F.text == "⬅️ Назад")
async def back_from_emotion_group(message: types.Message, state: FSMContext):
    await state.set_state(DiaryStates.waiting_for_situation)
    data = await state.get_data()
    situation = data.get('situation', '')

    await message.answer(
        "↩️ Возвращаемся к описанию ситуации.\n\n"
        f"📝 *Текущее описание:*\n{situation[:200]}...\n\n"
        "Можете изменить его или оставить как есть:",
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )


@diary_router.message(DiaryStates.waiting_for_subemotion, F.text == "⬅️ Назад к группам")
async def back_from_subemotion(message: types.Message, state: FSMContext):
    await state.set_state(DiaryStates.waiting_for_emotion_group)
    await message.answer(
        "↩️ Возвращаемся к выбору группы эмоций.",
        parse_mode="Markdown",
        reply_markup=get_emotion_groups_keyboard()
    )


@diary_router.message(DiaryStates.waiting_for_emotion_intensity, F.text == "⬅️ Назад")
async def back_from_intensity(message: types.Message, state: FSMContext):
    await state.set_state(DiaryStates.waiting_for_emotion_group)

    data = await state.get_data()
    selected_emotions = data.get('emotions', [])
    emotions_text = "✅ Выбраны: " + ", ".join(selected_emotions) if selected_emotions else "❌ Эмоции не выбраны"

    await message.answer(
        "↩️ Возвращаемся к выбору эмоций.\n\n"
        f"{emotions_text}\n\n"
        "🎭 Выберите эмоции (можно несколько, затем нажмите '✅ Готово'):",
        parse_mode="Markdown",
        reply_markup=get_emotion_groups_keyboard()
    )


@diary_router.message(DiaryStates.waiting_for_thought, F.text == "⬅️ Назад")
async def back_from_thought(message: types.Message, state: FSMContext):
    data = await state.get_data()
    emotions = data.get('emotions', [])
    current_index = data.get('current_emotion_index', 0)

    if current_index > 0:
        await state.update_data(current_emotion_index=current_index - 1)

    await state.set_state(DiaryStates.waiting_for_emotion_intensity)
    await ask_emotion_intensity(message, state)


@diary_router.message(DiaryStates.waiting_for_response, F.text == "⬅️ Назад")
async def back_from_response(message: types.Message, state: FSMContext):
    data = await state.get_data()
    thought = data.get('thought', '')

    await state.set_state(DiaryStates.waiting_for_thought)

    await message.answer(
        "↩️ Возвращаемся к автоматической мысли.\n\n"
        f"💭 *Текущая мысль:*\n{thought[:200]}...\n\n"
        "Можете изменить её или оставить как есть:",
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )


@diary_router.message(DiaryStates.waiting_for_emotion_reassessment, F.text == "⬅️ Назад")
async def back_from_reassessment(message: types.Message, state: FSMContext):
    await state.set_state(DiaryStates.waiting_for_response)

    await message.answer(
        "↩️ Возвращаемся к рациональной реакции.\n\n"
        "🧠 Вы можете изменить рациональный ответ:",
        parse_mode="Markdown",
        reply_markup=get_response_keyboard_with_back()
    )


# ====== ШАГ 2: Получение ситуации ======
@diary_router.message(DiaryStates.waiting_for_situation)
async def process_situation(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return

    is_valid, error_msg = validator.validate_situation_text(message.text)
    if not is_valid:
        await message.answer(f"❌ {error_msg}\n\nПожалуйста, введите текст заново:")
        return

    logger.info(f"📝 process_situation user_id={message.from_user.id}")

    await state.update_data(situation=message.text)
    await state.set_state(DiaryStates.waiting_for_emotion_group)

    await message.answer(
        "🎭 *Шаг 2 из 8: Выбор группы эмоций*\n\n"
        "Какая группа эмоций наиболее подходит?\n"
        "(Выбери одну группу, затем конкретную эмоцию)",
        parse_mode="Markdown",
        reply_markup=get_emotion_groups_keyboard()
    )


# ====== ШАГ 2.1: Выбор группы эмоций ======
@diary_router.message(DiaryStates.waiting_for_emotion_group)
async def process_emotion_group(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(DiaryStates.waiting_for_situation)
        data = await state.get_data()
        situation = data.get('situation', '')
        await message.answer(
            "↩️ Возвращаемся к описанию ситуации.\n\n"
            f"📝 *Текущее описание:*\n{situation[:200]}...",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard()
        )
        return

    if message.text == "✅ Готово":
        await finish_emotions_selection(message, state)
        return

    valid_groups = ["😠 Гнев", "😨 Страх", "😢 Грусть", "😊 Радость", "❤️ Любовь", "😳 Стыд/Вина"]

    if message.text not in valid_groups:
        await message.answer("❌ Пожалуйста, выберите группу эмоций из списка выше.")
        return

    selected_group = message.text

    await state.update_data(current_emotion_group=selected_group)
    await state.set_state(DiaryStates.waiting_for_subemotion)

    await message.answer(
        f"🎭 *Выбрана группа: {selected_group}*\n\n"
        "Теперь выберите конкретную эмоцию из этой группы:",
        parse_mode="Markdown",
        reply_markup=get_subemotions_keyboard(selected_group)
    )


# ====== ШАГ 2.2: Выбор конкретной эмоции ======
@diary_router.message(DiaryStates.waiting_for_subemotion)
async def process_subemotion(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад к группам":
        await state.set_state(DiaryStates.waiting_for_emotion_group)
        await message.answer(
            "↩️ Возвращаемся к выбору группы эмоций.",
            parse_mode="Markdown",
            reply_markup=get_emotion_groups_keyboard()
        )
        return

    if message.text == "✅ Завершить выбор":
        await finish_emotions_selection(message, state)
        return

    data = await state.get_data()
    current_group = data.get('current_emotion_group', '')
    selected_emotions = data.get('emotions', [])

    full_emotion_name = f"{current_group}: {message.text}"

    if full_emotion_name not in selected_emotions:
        selected_emotions.append(full_emotion_name)
        await state.update_data(emotions=selected_emotions)

        display_name = format_emotion_display(full_emotion_name)
        await message.answer(f"✅ Добавлено: {display_name}\nВыбрано: {len(selected_emotions)}")

        await state.set_state(DiaryStates.waiting_for_emotion_group)
        await message.answer(
            "🎭 *Добавить ещё эмоцию?*\n\n"
            "Выберите следующую группу эмоций или нажмите '✅ Готово':",
            parse_mode="Markdown",
            reply_markup=get_emotion_groups_keyboard()
        )
    else:
        display_name = format_emotion_display(full_emotion_name)
        await message.answer(f"⚠️ Эмоция '{display_name}' уже выбрана")

        await state.set_state(DiaryStates.waiting_for_emotion_group)
        await message.answer(
            "🎭 Выберите следующую группу эмоций:",
            parse_mode="Markdown",
            reply_markup=get_emotion_groups_keyboard()
        )


async def finish_emotions_selection(message: types.Message, state: FSMContext):
    data = await state.get_data()
    selected_emotions = data.get('emotions', [])

    logger.info(f"✅ Завершён выбор эмоций: {selected_emotions}")

    if not selected_emotions:
        await message.answer("❌ Выбери хотя бы одну эмоцию!")
        return

    formatted_emotions = [format_emotion_display(e) for e in selected_emotions]

    await state.update_data(
        emotions=selected_emotions,
        emotion_intensities={},
        current_emotion_index=0
    )

    await state.set_state(DiaryStates.waiting_for_emotion_intensity)

    emotions_text = "✅ *Выбраны эмоции:*\n" + "\n".join(formatted_emotions)

    await message.answer(
        f"{emotions_text}\n\n"
        "📊 *Шаг 3 из 8: Интенсивность эмоций*\n\n"
        "Теперь оценим интенсивность каждой эмоции:",
        parse_mode="Markdown"
    )

    await ask_emotion_intensity(message, state)


async def ask_emotion_intensity(message: types.Message, state: FSMContext):
    data = await state.get_data()
    emotions = data.get('emotions', [])
    current_index = data.get('current_emotion_index', 0)

    if current_index >= len(emotions):
        await state.set_state(DiaryStates.waiting_for_thought)
        intensities = data.get('emotion_intensities', {})

        intensity_text = "\n".join([
            f"{format_emotion_display(emoji)}: {intensities.get(emoji, '?')}%"
            for emoji in emotions
        ])

        await message.answer(
            f"🎯 *Интенсивность эмоций:*\n{intensity_text}\n\n"
            f"💭 *Шаг 4 из 8: Автоматическая мысль*\n\n"
            f"Какая мысль пришла тебе в голову сразу после ситуации?",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard()
        )
        return

    current_emotion = emotions[current_index]
    display_name = format_emotion_display(current_emotion)

    await message.answer(
        f"📊 *Интенсивность эмоции:* {display_name}\n\n"
        f"Насколько сильно ты чувствовал эту эмоцию? (0-100)\n"
        f"({current_index + 1} из {len(emotions)})",
        parse_mode="Markdown",
        reply_markup=get_intensity_keyboard_with_back()
    )


# ====== ШАГ 4: Интенсивность эмоций ======
@diary_router.message(DiaryStates.waiting_for_emotion_intensity)
async def process_intensity(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return

    try:
        intensity_text = message.text.replace('%', '')
        intensity = int(intensity_text)

        if intensity < 0 or intensity > 100:
            raise ValueError
    except:
        await message.answer("❌ Выбери число от 0 до 100 (можно нажать кнопку)")
        return

    data = await state.get_data()
    emotions = data.get('emotions', [])
    current_index = data.get('current_emotion_index', 0)
    intensities = data.get('emotion_intensities', {})

    current_emotion = emotions[current_index]
    intensities[current_emotion] = intensity

    await state.update_data(
        emotion_intensities=intensities,
        current_emotion_index=current_index + 1
    )

    display_name = format_emotion_display(current_emotion)
    await message.answer(f"✅ {display_name}: {intensity}%")

    await ask_emotion_intensity(message, state)


# ====== ШАГ 5: Автоматическая мысль ======
@diary_router.message(DiaryStates.waiting_for_thought)
async def process_thought(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return

    is_valid, error_msg = validator.validate_thought_text(message.text)
    if not is_valid:
        await message.answer(f"❌ {error_msg}\n\nПожалуйста, введите текст заново:")
        return

    await state.update_data(thought=message.text)
    await state.set_state(DiaryStates.waiting_for_response)

    await message.answer(
        "🧠 *Шаг 6 из 7: Рациональная реакция*\n\n"
        "Какой рациональный ответ ты можешь дать этой мысли?\n"
        "(Что бы ты сказал другу в такой ситуации?)",
        parse_mode="Markdown",
        reply_markup=get_response_keyboard_with_back()
    )


# ====== ШАГ 6: Рациональная реакция ======
@diary_router.message(DiaryStates.waiting_for_response, F.text == "⏰ Ответить позже")
async def postpone_response(message: types.Message, state: FSMContext):
    await state.update_data(response="[ОТЛОЖЕНО - ответить позже]")
    await save_diary_entry(message, state, status="draft", reassessment_done=False)


@diary_router.message(DiaryStates.waiting_for_response, F.text == "📝 Записать рациональную реакцию")
async def write_response_now(message: types.Message, state: FSMContext):
    await message.answer("📝 Напиши рациональную реакцию:", reply_markup=get_back_keyboard())


@diary_router.message(DiaryStates.waiting_for_response)
async def process_response_text(message: types.Message, state: FSMContext):
    if message.text in ["⏰ Ответить позже", "📝 Записать рациональную реакцию", "⬅️ Назад"]:
        return

    is_valid, error_msg = validator.validate_response_text(message.text)
    if not is_valid:
        await message.answer(f"❌ {error_msg}\n\nПожалуйста, введите текст заново:")
        return

    await state.update_data(response=message.text)
    await ask_emotion_reassessment(message, state)


# ====== ШАГ 7: Переоценка эмоций ======
async def ask_emotion_reassessment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    emotions = data.get('emotions', [])
    original_intensities = data.get('emotion_intensities', {})

    if not emotions:
        await save_diary_entry(message, state, status="completed", reassessment_done=False)
        return

    await state.update_data(
        original_intensities=original_intensities.copy(),
        reassessment_intensities={},
        current_reassessment_index=0
    )

    await state.set_state(DiaryStates.waiting_for_emotion_reassessment)
    await ask_single_emotion_reassessment(message, state)


async def ask_single_emotion_reassessment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    emotions = data.get('emotions', [])
    current_index = data.get('current_reassessment_index', 0)
    original_intensities = data.get('original_intensities', {})

    if current_index >= len(emotions):
        await process_reassessment_complete(message, state)
        return

    current_emotion = emotions[current_index]
    original_intensity = original_intensities.get(current_emotion, "?")

    await message.answer(
        f"🔄 *Переоценка эмоции:* {current_emotion}\n\n"
        f"Было: {original_intensity}%\n"
        f"Как изменилась интенсивность после анализа?\n"
        f"({current_index + 1} из {len(emotions)})",
        parse_mode="Markdown",
        reply_markup=get_intensity_keyboard_with_back()
    )


@diary_router.message(DiaryStates.waiting_for_emotion_reassessment)
async def process_reassessment(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return

    try:
        intensity_text = message.text.replace('%', '')
        new_intensity = int(intensity_text)
        if new_intensity < 0 or new_intensity > 100:
            raise ValueError
    except:
        await message.answer("❌ Выбери число от 0 до 100")
        return

    data = await state.get_data()
    emotions = data.get('emotions', [])
    current_index = data.get('current_reassessment_index', 0)
    reassessment_intensities = data.get('reassessment_intensities', {})

    current_emotion = emotions[current_index]
    reassessment_intensities[current_emotion] = new_intensity

    await state.update_data(
        reassessment_intensities=reassessment_intensities,
        current_reassessment_index=current_index + 1
    )

    original_intensities = data.get('original_intensities', {})
    original = original_intensities.get(current_emotion, "?")
    change = new_intensity - original if isinstance(original, int) else "?"
    change_text = f"({change:+}%)" if isinstance(change, int) else ""

    await message.answer(f"✅ {current_emotion}: {original}% → {new_intensity}% {change_text}")

    await ask_single_emotion_reassessment(message, state)


async def process_reassessment_complete(message: types.Message, state: FSMContext):
    data = await state.get_data()
    emotions = data.get('emotions', [])
    original_intensities = data.get('original_intensities', {})
    reassessment_intensities = data.get('reassessment_intensities', {})

    result_text = "🔄 *Результат переоценки:*\n"
    for emotion in emotions:
        original = original_intensities.get(emotion, "?")
        new = reassessment_intensities.get(emotion, "?")
        if isinstance(original, int) and isinstance(new, int):
            change = new - original
            result_text += f"{emotion}: {original}% → {new}% ({change:+}%)\n"
        else:
            result_text += f"{emotion}: {original}% → {new}%\n"

    await state.update_data(
        result=result_text,
        reassessment_intensities=reassessment_intensities
    )

    await save_diary_entry(message, state, status="completed", reassessment_done=True)