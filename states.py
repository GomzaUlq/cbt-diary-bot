from aiogram.fsm.state import State, StatesGroup


class DiaryStates(StatesGroup):
    """Состояния для ведения дневника с группами эмоций"""

    # Основные состояния
    waiting_for_situation = State()  # Шаг 1: Ожидание описания ситуации
    waiting_for_emotion_group = State()  # Шаг 2: Выбор группы эмоций (НОВОЕ!)
    waiting_for_emotions = State()  # ⚠️ ОСТАВЛЯЕМ для обратной совместимости
    waiting_for_subemotion = State()  # Шаг 2.1: Выбор конкретной эмоции из группы (НОВОЕ!)
    waiting_for_emotion_intensity = State()  # Шаг 3: Оценка интенсивности эмоций
    waiting_for_thought = State()  # Шаг 4: Автоматическая мысль
    waiting_for_response = State()  # Шаг 5: Рациональная реакция
    waiting_for_emotion_reassessment = State()  # Шаг 6: Переоценка эмоций

    # Дополнительные состояния
    choosing_draft_entry = State()  # Выбор записи для продолжения
    waiting_for_result = State()  # Ожидание комментария к результату (если нужно)