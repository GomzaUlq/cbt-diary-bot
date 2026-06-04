from aiogram import Router, types, F
from aiogram.filters import Command
from database.engine import AsyncSessionLocal
from database.models import Entry, EntryEmotion, User
from sqlalchemy import select, func, desc, text
from datetime import datetime, timedelta
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from utils.export import export_to_excel_combined
from keyboards import get_main_menu, get_stats_menu, format_emotion_display  # ← ДОБАВИЛ format_emotion_display

stats_router = Router()


@stats_router.message(F.text == "📊 Общая статистика")
async def cmd_stats(message: types.Message):
    """УПРОЩЁННАЯ статистика"""
    user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        try:
            # 1. Находим пользователя
            user_result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                await message.answer("❌ У вас ещё нет записей.")
                return

            print(f"👤 Пользователь найден: {user.id}")

            # 2. Простая статистика записей
            total_result = await session.execute(
                select(func.count(Entry.id)).where(Entry.user_id == user.id)
            )
            total_entries = total_result.scalar() or 0

            print(f"📝 Всего записей: {total_entries}")

            # 3. Статистика по эмоциям (упрощённая)
            emotions_result = await session.execute(
                select(EntryEmotion.emotion_name, func.count(EntryEmotion.id))
                .join(Entry)
                .where(Entry.user_id == user.id)
                .group_by(EntryEmotion.emotion_name)
                .order_by(func.count(EntryEmotion.id).desc())
                .limit(5)
            )
            emotions_stats = emotions_result.all()

            # 4. Формируем ответ
            stats_text = f"📊 *Статистика пользователя {user.full_name}*\n\n"
            stats_text += f"📝 *Всего записей:* {total_entries}\n\n"

            if emotions_stats:
                stats_text += "🎭 *Топ эмоций:*\n"
                for emotion_name, count in emotions_stats:
                    # Форматируем для отображения
                    display_name = format_emotion_display(emotion_name)
                    stats_text += f"  • {display_name}: {count} раз\n"
            else:
                stats_text += "🎭 *Эмоций ещё нет*\n"

            # 5. Статистика по переоценке
            reassessment_result = await session.execute(
                select(func.count(EntryEmotion.id))
                .join(Entry)
                .where(
                    Entry.user_id == user.id,
                    EntryEmotion.reassessment_intensity.is_not(None)
                )
            )
            reassessment_count = reassessment_result.scalar() or 0

            if reassessment_count > 0:
                stats_text += f"\n🔄 *Переоценено эмоций:* {reassessment_count}\n"

            await message.answer(stats_text, parse_mode="Markdown")

        except Exception as e:
            print(f"❌ Ошибка в статистике: {e}")
            import traceback
            traceback.print_exc()
            await message.answer("❌ Ошибка при получении статистики.")


@stats_router.message(F.text == "📈 Статистика по периодам")
async def period_stats(message: types.Message):
    """Статистика по неделям/месяцам"""
    user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            await message.answer("❌ У вас ещё нет записей.")
            return

        # Статистика по месяцам (PostgreSQL) — ИСПРАВЛЕННЫЙ ЗАПРОС
        monthly_result = await session.execute(
            select(
                func.to_char(Entry.created_at, 'YYYY-MM').label('month'),
                func.count(Entry.id).label('count')
            )
            .where(Entry.user_id == user.id)
            .group_by('month')  # ← Используем алиас из label
            .order_by(desc('month'))  # ← И здесь тоже алиас
            .limit(6)
        )
        monthly_stats = monthly_result.all()

        text = "📅 *Статистика по месяцам:*\n\n"

        if monthly_stats:
            for month, count in monthly_stats:
                # Форматируем месяц
                year, month_num = month.split('-')
                month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
                               'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
                month_name = month_names[int(month_num) - 1]

                text += f"🗓 *{month_name} {year}:*\n"
                text += f"   📝 Записей: {count}\n\n"
        else:
            text += "Записей ещё нет.\n"

        # Общее количество записей
        total_result = await session.execute(
            select(func.count(Entry.id)).where(Entry.user_id == user.id)
        )
        total = total_result.scalar() or 0

        text += f"📊 *Общая статистика:*\n"
        text += f"   • Всего записей: {total}\n"

        # Самые частые эмоции (если нужно)
        try:
            emotions_result = await session.execute(
                select(
                    EntryEmotion.emotion_name,
                    func.count(EntryEmotion.id).label('count')
                )
                .join(Entry).where(Entry.user_id == user.id)
                .group_by(EntryEmotion.emotion_name)
                .order_by(desc('count'))
                .limit(5)
            )
            top_emotions = emotions_result.all()

            if top_emotions:
                text += f"   • Топ эмоций:\n"
                for emotion, count in top_emotions:
                    display_name = format_emotion_display(emotion)
                    text += f"     {display_name}: {count} раз\n"
        except:
            pass  # Пропускаем, если таблицы эмоций нет или ошибка

        await message.answer(text, parse_mode="Markdown")
        
        
@stats_router.message(F.text == "🎭 Статистика эмоций")
async def emotions_stats(message: types.Message):
    """Детальная статистика по эмоциям"""
    user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        try:
            user_result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                await message.answer("❌ У вас ещё нет записей.")
                return

            # Полная статистика по эмоции
            stats_result = await session.execute(
                select(
                    EntryEmotion.emotion_name,
                    func.count(EntryEmotion.id).label('count'),
                    func.avg(EntryEmotion.intensity).label('avg_original'),
                    func.avg(EntryEmotion.reassessment_intensity).label('avg_reassessment')
                )
                .join(Entry)
                .where(Entry.user_id == user.id)
                .group_by(EntryEmotion.emotion_name)
                .order_by(desc('count'))
            )
            all_stats = stats_result.all()

            if not all_stats:
                await message.answer("🎭 У вас ещё нет эмоций в записях.")
                return

            text = "🎭 *Статистика по эмоциям:*\n\n"

            for emotion_name, count, avg_orig, avg_reass in all_stats:
                # Форматируем для отображения
                display_name = format_emotion_display(emotion_name)
                text += f"*{display_name}:*\n"
                text += f"  📊 Встречается: {count} раз\n"

                if avg_orig:
                    text += f"  📈 Средняя интенсивность: {int(avg_orig)}%\n"

                if avg_reass:
                    change = int(avg_reass - avg_orig) if avg_orig else 0
                    text += f"  🔄 После переоценки: {int(avg_reass)}% ({change:+}%)\n"

                text += "\n"

            await message.answer(text, parse_mode="Markdown")

        except Exception as e:
            print(f"❌ Ошибка в статистике эмоций: {e}")
            await message.answer("❌ Ошибка при получении статистики эмоций.")


# ====== НОВАЯ СТАТИСТИКА ПО ГРУППАМ ЭМОЦИЙ ======
@stats_router.message(F.text == "📊 Статистика по группам")
async def emotion_groups_stats(message: types.Message):
    """Статистика по группам эмоций"""
    user_id = message.from_user.id
    
    async with AsyncSessionLocal() as session:
        try:
            user_result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                await message.answer("❌ У вас ещё нет записей.")
                return
            
            # Статистика за последние 30 дней
            start_date = datetime.now() - timedelta(days=30)
            
            # Запрос для получения статистики по группам
            query = text("""
            SELECT 
                CASE 
                    WHEN emotion_name LIKE '😠%' THEN '😠 Гнев'
                    WHEN emotion_name LIKE '😨%' THEN '😨 Страх'
                    WHEN emotion_name LIKE '😢%' THEN '😢 Грусть'
                    WHEN emotion_name LIKE '😊%' THEN '😊 Радость'
                    WHEN emotion_name LIKE '❤️%' THEN '❤️ Любовь'
                    WHEN emotion_name LIKE '😳%' THEN '😳 Стыд/Вина'
                    ELSE 'Другие'
                END as emotion_group,
                COUNT(*) as count,
                ROUND(AVG(intensity)) as avg_intensity,
                COUNT(CASE WHEN reassessment_intensity IS NOT NULL THEN 1 END) as reassessed_count,
                ROUND(AVG(reassessment_intensity)) as avg_reassessment
            FROM entry_emotions ee
            JOIN entries e ON ee.entry_id = e.id
            WHERE e.user_id = :user_id 
            AND e.created_at >= :start_date
            GROUP BY 
                CASE 
                    WHEN emotion_name LIKE '😠%' THEN '😠 Гнев'
                    WHEN emotion_name LIKE '😨%' THEN '😨 Страх'
                    WHEN emotion_name LIKE '😢%' THEN '😢 Грусть'
                    WHEN emotion_name LIKE '😊%' THEN '😊 Радость'
                    WHEN emotion_name LIKE '❤️%' THEN '❤️ Любовь'
                    WHEN emotion_name LIKE '😳%' THEN '😳 Стыд/Вина'
                    ELSE 'Другие'
                END
            ORDER BY count DESC
            """)
            
            result = await session.execute(
                query,
                {"user_id": user.id, "start_date": start_date}
            )
            
            stats = result.fetchall()
            
            if not stats:
                await message.answer(
                    "📊 У вас нет записей с эмоциями за последние 30 дней.",
                    reply_markup=get_stats_menu()
                )
                return
            
            # Формируем ответ
            total_emotions = sum(row[1] for row in stats)
            
            response = "📊 *Статистика по группам эмоций (за 30 дней):*\n\n"
            
            for row in stats:
                group_name = row[0]
                count = row[1]
                avg_intensity = row[2] or 0
                reassessed_count = row[3] or 0
                avg_reassessment = row[4] or 0
                
                percentage = round((count / total_emotions * 100), 1) if total_emotions > 0 else 0
                reassessed_percent = round((reassessed_count / count * 100), 1) if count > 0 else 0
                
                # ЛЁГКАЯ ИНДИКАЦИЯ ТОЧКАМИ (5 точек максимум)
                dot_count = min(int(percentage / 20), 5)  # 0-20% = 1 точка, 20-40% = 2 точки и т.д.
                dots = "•" * dot_count
                spaces = " " * (5 - dot_count)
                
                response += f"**{group_name}** {dots}{spaces} {percentage}%\n"
                response += f"  📊 {count} эмоций"
                response += f" | ⌀{avg_intensity}%"
                
                if reassessed_count > 0:
                    reassessed_percent = round((reassessed_count / count * 100), 1)
                    response += f" | 🔄{reassessed_percent}%"
                    if avg_reassessment > 0:
                        change = avg_reassessment - avg_intensity
                        response += f" ({change:+}%)"
                
                response += "\n\n"
            
            response += f"📈 *Итого за 30 дней:*\n"
            response += f"  • Всего эмоций: {total_emotions}\n"
            response += f"  • Среднее на запись: {round(total_emotions / len(stats), 1) if stats else 0}\n"
            
            # Самые частые подэмоции
            subemotions_query = text("""
            SELECT emotion_name, COUNT(*) as count
            FROM entry_emotions ee
            JOIN entries e ON ee.entry_id = e.id
            WHERE e.user_id = :user_id 
            AND e.created_at >= :start_date
            GROUP BY emotion_name
            ORDER BY count DESC
            LIMIT 5
            """)
            
            sub_result = await session.execute(
                subemotions_query,
                {"user_id": user.id, "start_date": start_date}
            )
            
            top_subemotions = sub_result.fetchall()
            
            if top_subemotions:
                response += f"\n🎯 *Самые частые эмоции:*\n"
                for emotion_name, count in top_subemotions:
                    display_name = format_emotion_display(emotion_name)
                    response += f"  • {display_name}: {count} раз\n"
            
            await message.answer(
                response,
                parse_mode="Markdown",
                reply_markup=get_stats_menu()
            )
            
        except Exception as e:
            print(f"❌ Ошибка в статистике по группам: {e}")
            import traceback
            traceback.print_exc()
            await message.answer(
                "❌ Ошибка при получении статистики по группам.",
                reply_markup=get_stats_menu()
            )


@stats_router.message(F.text == "📤 Экспорт в Excel")
async def export_to_excel_handler(message: types.Message):
    """Экспорт данных в Excel"""
    user_id = message.from_user.id
    
    try:
        # Показываем пользователю, что идет процесс
        wait_msg = await message.answer("⏳ Формируем Excel файл...")
        
        # Получаем данные из БД НАПРЯМУЮ
        async with AsyncSessionLocal() as session:
            # 1. Находим пользователя
            user_result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                await message.answer("❌ У вас нет записей.")
                return
            
            # 2. Получаем ВСЕ записи пользователя с эмоциями
            entries_result = await session.execute(
                select(Entry)
                .where(Entry.user_id == user.id)
                .order_by(Entry.created_at.desc())
            )
            entries = entries_result.scalars().all()
            
            if not entries:
                await message.answer(
                    "📭 У вас пока нет записей для экспорта.",
                    reply_markup=get_main_menu()
                )
                return
            
            # 3. Преобразуем записи в словари с РАСШИФРОВАННЫМИ данными
            entries_data = []
            for entry in entries:
                # Расшифровываем данные
                from config import config
                
                entry_dict = {
                    'id': entry.id,
                    'created_at': entry.created_at,
                    'situation': config.decrypt_text(entry.situation) if entry.situation else '',
                    'automatic_thought': config.decrypt_text(entry.automatic_thought) if entry.automatic_thought else '',
                    'rational_response': config.decrypt_text(entry.rational_response) if entry.rational_response else '',
                    'result': config.decrypt_text(entry.result) if entry.result else '',
                    'status': entry.status,
                    'is_completed': entry.status == 'completed'
                }
                
                # Получаем эмоции для этой записи
                emotions_result = await session.execute(
                    select(EntryEmotion)
                    .where(EntryEmotion.entry_id == entry.id)
                )
                emotions = emotions_result.scalars().all()
                
                # Формируем словарь эмоций
                emotions_dict = {}
                for emotion in emotions:
                    emotions_dict[emotion.emotion_name] = {
                        'intensity': emotion.intensity,
                        'reassessment': emotion.reassessment_intensity
                    }
                
                entry_dict['emotions'] = emotions_dict
                entries_data.append(entry_dict)
        
        # 4. Создаем Excel файл с НОВОЙ ФУНКЦИЕЙ
        excel_buffer = export_to_excel_combined(entries_data)  # ← ИЗМЕНИЛ ВЫЗОВ
        
        # 5. Создаем имя файла с датой
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"cbt_diary_{date_str}.xlsx"
        
        # 6. Создаем объект файла для Telegram
        from aiogram.types import BufferedInputFile
        excel_file = BufferedInputFile(
            file=excel_buffer.getvalue(),
            filename=filename
        )
        
        # 7. Отправляем файл пользователю
        await message.answer_document(
            document=excel_file,
            caption=f"📊 Ваш дневник КПТ\n"
                   f"📅 Экспорт от {date_str}\n"
                   f"📋 Записей: {len(entries)}\n\n"
                   f"✅ Файл готов!",
            reply_markup=get_main_menu()
        )
        
        # 8. Удаляем сообщение "Формируем..."
        await wait_msg.delete()
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Export error details: {error_details}")
        
        await message.answer(
            f"❌ Ошибка при экспорте: {str(e)[:200]}\n"
            "Попробуйте позже или обратитесь к администратору.",
            reply_markup=get_main_menu()
        )