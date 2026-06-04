import time
from collections import defaultdict
from typing import Dict, Tuple, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Ограничитель запросов для защиты от спама и DoS-атак"""

    def __init__(self, max_requests_per_minute: int = 30, ban_threshold: int = 100):
        self.max_requests = max_requests_per_minute
        self.ban_threshold = ban_threshold
        self.requests: Dict[int, List[float]] = defaultdict(list)
        self.banned_users: Dict[int, float] = {}
        self.ban_duration = 3600  # 1 час в секундах

    def is_allowed(self, user_id: int) -> Tuple[bool, int]:
        """
        Проверяет, можно ли выполнить запрос
        Возвращает (разрешено, время_ожидания_в_секундах)
        """
        now = time.time()

        # Проверка бана
        if user_id in self.banned_users:
            ban_time = self.banned_users[user_id]
            if now - ban_time < self.ban_duration:
                wait_time = int(self.ban_duration - (now - ban_time))
                logger.warning(f"🚨 Заблокированный пользователь пытается отправить запрос: user_id={user_id}")
                return False, wait_time
            else:
                # Снятие бана
                del self.banned_users[user_id]

        # Очистка старых запросов (старше 1 минуты)
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < 60
        ]

        # Проверка текущего лимита
        if len(self.requests[user_id]) >= self.max_requests:
            # Если превышен порог для бана
            if len(self.requests[user_id]) >= self.ban_threshold:
                self.banned_users[user_id] = now
                logger.warning(f"🚨 Пользователь забанен за спам: user_id={user_id}")
                return False, self.ban_duration

            # Просто превышение лимита
            # Находим время, когда можно будет отправить следующий запрос
            oldest_request = min(self.requests[user_id])
            wait_time = int(60 - (now - oldest_request))
            return False, wait_time

        # Запрос разрешен
        self.requests[user_id].append(now)
        return True, 0

    def cleanup_old_data(self):
        """Очистка старых данных для экономии памяти"""
        now = time.time()
        cutoff = now - 3600  # 1 час

        # Очистка запросов
        for user_id in list(self.requests.keys()):
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if req_time > cutoff
            ]
            if not self.requests[user_id]:
                del self.requests[user_id]

        # Очистка банов
        for user_id in list(self.banned_users.keys()):
            if now - self.banned_users[user_id] > self.ban_duration:
                del self.banned_users[user_id]


rate_limiter = RateLimiter()