import re
from typing import Optional, Tuple
from config import config


class InputValidator:
    """Класс для валидации пользовательского ввода"""

    @staticmethod
    def validate_situation_text(text: str) -> Tuple[bool, Optional[str]]:
        """
        Валидация текста ситуации
        Возвращает (is_valid, error_message)
        """
        if len(text) > config.MAX_SITUATION_LENGTH:
            return False, f"Слишком длинный текст. Максимум {config.MAX_SITUATION_LENGTH} символов."

        if not text.strip():
            return False, "Текст не может быть пустым."

        # Проверка на опасные HTML/JS инъекции
        dangerous_patterns = [
            r'<script.*?>', r'javascript:', r'onload=', r'onerror=',
            r'onclick=', r'alert\(', r'prompt\(', r'confirm\(',
            r'document\.', r'window\.', r'eval\(', r'exec\(', r'system\('
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False, "Текст содержит недопустимые символы."

        # Проверка на повторяющиеся символы (спам)
        if re.search(r'(.)\1{10,}', text):
            return False, "Текст содержит подозрительные повторения."

        return True, None

    @staticmethod
    def validate_thought_text(text: str) -> Tuple[bool, Optional[str]]:
        """Валидация текста автоматической мысли"""
        if len(text) > config.MAX_THOUGHT_LENGTH:
            return False, f"Слишком длинный текст. Максимум {config.MAX_THOUGHT_LENGTH} символов."

        if not text.strip():
            return False, "Текст не может быть пустым."

        return True, None

    @staticmethod
    def validate_response_text(text: str) -> Tuple[bool, Optional[str]]:
        """Валидация текста рациональной реакции"""
        if len(text) > config.MAX_RESPONSE_LENGTH:
            return False, f"Слишком длинный текст. Максимум {config.MAX_RESPONSE_LENGTH} символов."

        if not text.strip():
            return False, "Текст не может быть пустым."

        return True, None

    @staticmethod
    def validate_emotion_name(emotion: str) -> bool:
        """
        Валидация названия эмоции (НОВЫЙ ФОРМАТ)
        Поддерживает:
        1. Старый формат: "😊 Радость"
        2. Новый формат: "😠 Гнев: 💢 Злость"
        3. Группы эмоций: "😠 Гнев"
        4. Подэмоции: "💢 Злость"
        """
        # Список допустимых групп эмоций
        valid_groups = [
            "😠 Гнев", "😨 Страх", "😢 Грусть",
            "😊 Радость", "❤️ Любовь", "😳 Стыд/Вина"
        ]

        # Список допустимых подэмоций (все возможные)
        valid_subemotions = [
            # Гнев
            "💢 Злость", "😤 Раздражение", "💔 Обида", "🤬 Возмущение", "⚠️ Негодование",
            # Страх
            "😰 Тревога", "🤯 Беспокойство", "😳 Испуг", "⚠️ Опасение", "😱 Паника",
            # Грусть
            "💔 Печаль", "🌫️ Тоска", "🌧️ Безнадёжность", "👤 Одиночество", "☁️ Подавленность",
            # Радость
            "✨ Радость", "👍 Удовлетворение", "☮️ Умиротворение", "🌈 Надежда", "🔍 Интерес",
            # Любовь
            "💖 Нежность", "🙏 Благодарность", "🤝 Доверие", "😌 Спокойствие", "💕 Симпатия",
            # Стыд/Вина
            "😳 Стыд", "😞 Вина", "🤭 Смущение", "😖 Неловкость", "😓 Унижение"
        ]

        # 1. Проверка: это полный формат "Группа: Подэмоция"
        if ":" in emotion:
            group_part, sub_part = emotion.split(":", 1)
            group_part = group_part.strip()
            sub_part = sub_part.strip()

            # Проверяем группу
            if group_part in valid_groups:
                # Проверяем подэмоцию (учитывая, что эмодзи может быть или не быть)
                for valid_sub in valid_subemotions:
                    if sub_part == valid_sub or sub_part == valid_sub[2:]:  # без эмодзи
                        return True
                # Также проверяем, что подэмоция не пустая
                if sub_part:
                    return True
            return False

        # 2. Проверка: это группа эмоций
        if emotion in valid_groups:
            return True

        # 3. Проверка: это подэмоция (без группы)
        if emotion in valid_subemotions:
            return True

        # 4. Проверка: подэмоция без эмодзи
        for valid_sub in valid_subemotions:
            if emotion == valid_sub[2:]:  # убираем эмодзи (2 символа)
                return True

        # 5. Для обратной совместимости: старый список эмоций
        old_emotions = [
            "😊 Радость", "😢 Грусть", "😠 Гнев",
            "😨 Страх", "😖 Тревога", "😐 Спокойствие",
            "😳 Удивление", "🤢 Отвращение", "😔 Скука",
            "💪 Уверенность", "💔 Обида", "🏃‍♂️ Нетерпение"
        ]
        if emotion in old_emotions:
            return True

        return False

    @staticmethod
    def validate_emotion_group(group: str) -> bool:
        """Валидация группы эмоций"""
        valid_groups = [
            "😠 Гнев", "😨 Страх", "😢 Грусть",
            "😊 Радость", "❤️ Любовь", "😳 Стыд/Вина"
        ]
        return group in valid_groups

    @staticmethod
    def validate_intensity(intensity: str) -> Tuple[bool, Optional[int]]:
        """Валидация интенсивности (0-100)"""
        try:
            value = int(intensity.replace('%', ''))
            if 0 <= value <= 100:
                return True, value
            return False, None
        except:
            return False, None


validator = InputValidator()