import logging
from database.engine import AsyncSessionLocal
from database.models import Entry, EntryEmotion
from sqlalchemy import delete

logger = logging.getLogger(__name__)


async def delete_entry_simple(entry_id: int, user_id: int) -> bool:
    """
    Простое удаление записи дневника
    
    Args:
        entry_id: ID записи для удаления
        user_id: ID пользователя (для проверки владения)
        
    Returns:
        bool: True если удаление успешно, False если ошибка
    """
    async with AsyncSessionLocal() as session:
        try:
            # 1. Проверяем, существует ли запись и принадлежит ли пользователю
            from sqlalchemy import select
            result = await session.execute(
                select(Entry).where(
                    Entry.id == entry_id,
                    Entry.user_id == user_id
                )
            )
            entry = result.scalar_one_or_none()
            
            if not entry:
                logger.warning(f"Запись {entry_id} не найдена или не принадлежит пользователю {user_id}")
                return False
            
            # 2. Удаляем эмоции записи (каскадное удаление должно сработать, но на всякий случай)
            await session.execute(
                delete(EntryEmotion).where(EntryEmotion.entry_id == entry_id)
            )
            
            # 3. Удаляем саму запись
            await session.delete(entry)
            await session.commit()
            
            logger.info(f"✅ Запись {entry_id} успешно удалена для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении записи {entry_id}: {e}")
            await session.rollback()
            return False