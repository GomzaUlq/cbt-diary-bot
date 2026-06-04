from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    builder = ReplyKeyboardBuilder()

    # Первый ряд
    builder.add(KeyboardButton(text="📝 Новая запись"))
    builder.add(KeyboardButton(text="🔄 Продолжить записи"))

    # Второй ряд
    builder.add(KeyboardButton(text="📊 Статистика"))
    builder.add(KeyboardButton(text="📊 Мои записи"))

    # Третий ряд
    builder.add(KeyboardButton(text="🗑️ Удалить запись"))
    builder.add(KeyboardButton(text="⚙️ Настройки"))

    # Четвертый ряд
    builder.add(KeyboardButton(text="📤 Экспорт в Excel"))

    builder.adjust(2)

    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )


# ====== ЭМОЦИИ С ПОДГРУППАМИ ======

def get_emotion_groups_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с группами эмоций (терапевтический список)"""
    builder = ReplyKeyboardBuilder()

    emotion_groups = [
        "😠 Гнев",
        "😨 Страх",
        "😢 Грусть",
        "😊 Радость",
        "❤️ Любовь",
        "😳 Стыд/Вина"
    ]

    for group in emotion_groups:
        builder.add(KeyboardButton(text=group))

    builder.adjust(2)
    builder.row(KeyboardButton(text="✅ Готово"))
    builder.row(KeyboardButton(text="⬅️ Назад"))

    return builder.as_markup(resize_keyboard=True)


def get_subemotions_keyboard(main_emotion: str) -> ReplyKeyboardMarkup:
    """Клавиатура с подэмоциями для выбранной группы"""
    builder = ReplyKeyboardBuilder()

    # Терапевтический список
    subemotions_dict = {
        "😠 Гнев": [
            "💢 Злость",
            "😤 Раздражение",
            "💔 Обида",
            "🤬 Возмущение",
            "⚠️ Негодование"
        ],
        "😨 Страх": [
            "😰 Тревога",
            "🤯 Беспокойство",
            "😳 Испуг",
            "⚠️ Опасение",
            "😱 Паника"
        ],
        "😢 Грусть": [
            "💔 Печаль",
            "🌫️ Тоска",
            "🌧️ Безнадёжность",
            "👤 Одиночество",
            "☁️ Подавленность"
        ],
        "😊 Радость": [
            "✨ Радость",
            "👍 Удовлетворение",
            "☮️ Умиротворение",
            "🌈 Надежда",
            "🔍 Интерес"
        ],
        "❤️ Любовь": [
            "💖 Нежность",
            "🙏 Благодарность",
            "🤝 Доверие",
            "😌 Спокойствие",
            "💕 Симпатия"
        ],
        "😳 Стыд/Вина": [
            "😳 Стыд",
            "😞 Вина",
            "🤭 Смущение",
            "😖 Неловкость",
            "😓 Унижение"
        ]
    }

    # Получаем подэмоции для выбранной группы
    subemotions = subemotions_dict.get(main_emotion, [])

    # Добавляем кнопки подэмоций
    for sub in subemotions:
        builder.add(KeyboardButton(text=sub))

    builder.adjust(2)
    builder.row(KeyboardButton(text="⬅️ Назад к группам"))
    builder.row(KeyboardButton(text="✅ Завершить выбор"))

    return builder.as_markup(resize_keyboard=True)


def format_emotion_display(emotion_name: str) -> str:
    """Форматирует эмоцию для отображения (обратная совместимость)"""
    if not emotion_name:
        return ""

    if ":" in emotion_name:
        # Новый формат: "😠 Гнев: 💢 Злость"
        parts = emotion_name.split(":", 1)
        group = parts[0].strip()
        sub_emotion = parts[1].strip()

        # Убираем эмодзи из подэмоции для чистого отображения
        emoji_list = ["😠", "😨", "😢", "😊", "❤️", "😳", "💢", "😤", "💔", "🤬", "⚠️",
                      "😰", "🤯", "😳", "😱", "💔", "🌫️", "🌧️", "👤", "☁️", "✨", "👍",
                      "☮️", "🌈", "🔍", "💖", "🙏", "🤝", "😌", "💕", "😞", "🤭", "😖", "😓"]

        # Убираем первый эмодзи если он есть
        if sub_emotion and sub_emotion[0] in emoji_list:
            sub_emotion_clean = sub_emotion[1:].strip()
        else:
            sub_emotion_clean = sub_emotion

        return f"{group} - {sub_emotion_clean}"
    else:
        # Старый формат: "😊 Радость"
        return emotion_name


# ====== ОСТАЛЬНЫЕ КЛАВИАТУРЫ ======

def get_intensity_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора интенсивности 0-100"""
    builder = ReplyKeyboardBuilder()

    intensities = ["0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100"]

    for intensity in intensities:
        builder.add(KeyboardButton(text=intensity))

    builder.adjust(3)
    return builder.as_markup(resize_keyboard=True)


def get_response_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для рациональной реакции"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📝 Записать рациональную реакцию"))
    builder.add(KeyboardButton(text="⏰ Ответить позже"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_result_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для завершения переоценки"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💬 Добавить комментарий"))
    builder.add(KeyboardButton(text="⏰ Пропустить"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_continue_entries_keyboard(entries_list):
    """Клавиатура для выбора записи для продолжения"""
    keyboard = []

    for entry_id, display_text in entries_list:
        keyboard.append([types.KeyboardButton(text=display_text)])

    keyboard.append([types.KeyboardButton(text="⬅️ Назад в меню")])

    return types.ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_stats_menu() -> ReplyKeyboardMarkup:
    """Меню статистики"""
    builder = ReplyKeyboardBuilder()

    builder.add(KeyboardButton(text="📊 Общая статистика"))
    builder.add(KeyboardButton(text="📈 Статистика по периодам"))
    builder.add(KeyboardButton(text="🎭 Статистика эмоций"))
    builder.add(KeyboardButton(text="📊 Статистика по группам"))  # НОВОЕ!
    builder.add(KeyboardButton(text="📤 Экспорт в Excel"))
    builder.row(KeyboardButton(text="🏠 Главное меню"))

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_settings_menu() -> ReplyKeyboardMarkup:
    """Меню настроек"""
    builder = ReplyKeyboardBuilder()

    builder.add(KeyboardButton(text="⏰ Время напоминаний"))
    builder.add(KeyboardButton(text="📋 Мои настройки"))
    builder.add(KeyboardButton(text="🏠 Главное меню"))

    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура только с кнопкой Назад"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="⬅️ Назад"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_intensity_keyboard_with_back() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора интенсивности с кнопкой Назад"""
    builder = ReplyKeyboardBuilder()

    intensities = ["0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100"]

    for intensity in intensities:
        builder.add(KeyboardButton(text=intensity))

    builder.adjust(3)
    builder.row(KeyboardButton(text="⬅️ Назад"))

    return builder.as_markup(resize_keyboard=True)


def get_response_keyboard_with_back() -> ReplyKeyboardMarkup:
    """Клавиатура для рациональной реакции с кнопкой Назад"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📝 Записать рациональную реакцию"))
    builder.add(KeyboardButton(text="⏰ Ответить позже"))
    builder.row(KeyboardButton(text="⬅️ Назад"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


# ====== ФУНКЦИИ ДЛЯ УДАЛЕНИЯ ЗАПИСЕЙ ======

def get_simple_delete_keyboard(entries_data, page: int = 1):
    """
    Простая клавиатура для удаления: номера записей в ряд по 2-3 кнопки
    """
    keyboard = []
    current_row = []

    # Показываем номера текущей страницы
    for i, (entry_id, display_text) in enumerate(entries_data, 1):
        # Номер с учетом страницы: (страница-1)*10 + i
        global_num = (page - 1) * 10 + i

        # Добавляем кнопку в текущий ряд
        current_row.append(types.KeyboardButton(text=f"{global_num}"))

        # Если в ряду 2 кнопки (или это последняя запись), добавляем ряд в клавиатуру
        if len(current_row) == 2 or i == len(entries_data):
            keyboard.append(current_row)
            current_row = []

    # Кнопка отмены (на отдельной строке)
    keyboard.append([types.KeyboardButton(text="⬅️ Назад в меню")])

    return types.ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Введите номер записи..."
    )


def get_delete_pagination_keyboard(page: int, total_pages: int, has_entries: bool = True):
    """Клавиатура пагинации для удаления"""
    builder = InlineKeyboardBuilder()

    if has_entries:
        # Кнопки пагинации
        if page > 1:
            builder.add(InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"delete_page_{page - 1}"
            ))

        builder.add(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="current_page"
        ))

        if page < total_pages:
            builder.add(InlineKeyboardButton(
                text="Вперед ▶️",
                callback_data=f"delete_page_{page + 1}"
            ))

        builder.adjust(3)

    # Кнопка отмены
    builder.row(InlineKeyboardButton(
        text="❌ Отмена удаления",
        callback_data="cancel_delete"
    ))

    return builder.as_markup()


def get_delete_actions_keyboard():
    """Клавиатура действий после выбора записи"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🗑️ Удалить",
        callback_data="confirm_delete"
    ))
    builder.add(InlineKeyboardButton(
        text="🔍 Посмотреть",
        callback_data="view_entry"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="cancel_delete"
    ))
    builder.adjust(2)
    return builder.as_markup()


# ====== ФУНКЦИИ ДЛЯ ПРОСМОТРА ЗАПИСЕЙ ======

def get_entries_pagination_keyboard(page: int, total_pages: int):
    """Клавиатура пагинации для просмотра записей"""
    builder = InlineKeyboardBuilder()

    # Кнопки навигации
    if page > 1:
        builder.add(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"entries_page_{page - 1}"
        ))

    builder.add(InlineKeyboardButton(
        text=f"{page}/{total_pages}",
        callback_data="current_entries_page"
    ))

    if page < total_pages:
        builder.add(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"entries_page_{page + 1}"
        ))

    builder.adjust(3)

    # Кнопка возврата
    builder.row(InlineKeyboardButton(
        text="🏠 Главное меню",
        callback_data="back_to_main_from_entries"
    ))

    return builder.as_markup()


# ====== ФУНКЦИИ ДЛЯ СТАРЫХ ЗАПИСЕЙ (обратная совместимость) ======

def get_emotions_keyboard() -> ReplyKeyboardMarkup:
    """Старая клавиатура эмоций (для обратной совместимости)"""
    return get_emotion_groups_keyboard()


def get_emotions_keyboard_with_back() -> ReplyKeyboardMarkup:
    """Старая клавиатура с кнопкой Назад (для обратной совместимости)"""
    return get_emotion_groups_keyboard()


def get_old_emotions_keyboard() -> ReplyKeyboardMarkup:
    """Оригинальная старая клавиатура (если где-то используется)"""
    builder = ReplyKeyboardBuilder()

    old_emotions = [
        "😊 Радость", "😢 Грусть", "😠 Гнев",
        "😨 Страх", "😖 Тревога", "😐 Спокойствие",
        "😳 Удивление", "🤢 Отвращение", "😔 Скука",
        "💪 Уверенность", "💔 Обида", "🏃‍♂️ Нетерпение"
    ]

    for emotion in old_emotions:
        builder.add(KeyboardButton(text=emotion))

    builder.adjust(2)
    builder.row(KeyboardButton(text="✅ Готово"))
    builder.row(KeyboardButton(text="⬅️ Назад"))

    return builder.as_markup(resize_keyboard=True)


# ====== ФУНКЦИИ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ ======

def get_emotions_keyboard_with_back() -> ReplyKeyboardMarkup:
    """Клавиатура выбора эмоций с кнопкой Назад (для обратной совместимости)"""
    return get_emotion_groups_keyboard()
