import logging
import asyncio
import sys
import types
from telegram import Update, Poll
from telegram.ext import Application, CommandHandler, PollAnswerHandler, ContextTypes
import os

# Костыль для отсутствующего модуля imghdr в Python 3.14
if 'imghdr' not in sys.modules:
    imghdr = types.ModuleType('imghdr')
    
    def what(file, h=None):
        return None
    
    imghdr.what = what
    sys.modules['imghdr'] = imghdr

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = '8041853834:AAEQPmh2E3jzHQRm9eUMdQvDHe8uW8qE1Zg'

# Вопросы для викторины
QUIZ_QUESTIONS = [
    {
        'question': 'Какая планета самая большая в Солнечной системе?',
        'options': ['Марс', 'Юпитер', 'Сатурн', 'Нептун'],
        'correct_option_id': 1
    },
    {
        'question': 'Сколько будет 2 + 2 * 2?',
        'options': ['4', '6', '8', '10'],
        'correct_option_id': 1
    },
    {
        'question': 'Кто написал роман "Война и мир"?',
        'options': ['Достоевский', 'Толстой', 'Чехов', 'Пушкин'],
        'correct_option_id': 1
    },
    {
        'question': 'Какой газ самый распространенный в атмосфере Земли?',
        'options': ['Кислород', 'Углекислый газ', 'Азот', 'Водород'],
        'correct_option_id': 2
    },
    {
        'question': 'Столица Франции?',
        'options': ['Лондон', 'Берлин', 'Мадрид', 'Париж'],
        'correct_option_id': 3
    }
]

# Словарь для хранения результатов пользователей
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение."""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! 🎯\n"
        f"Я бот для викторин. Используй /quiz для начала."
    )

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает викторину."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    user_sessions[user_id] = {
        'correct': 0,
        'total': 0,
        'current_question': 0,
        'message_id': None
    }
    
    await send_question(update, context, user_id, chat_id)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
    """Отправляет вопрос викторины."""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    question_index = session['current_question']
    
    if question_index >= len(QUIZ_QUESTIONS):
        await show_result(update, context, user_id, chat_id)
        return
    
    question_data = QUIZ_QUESTIONS[question_index]
    
    try:
        message = await context.bot.send_poll(
            chat_id=chat_id,
            question=question_data['question'],
            options=question_data['options'],
            type=Poll.QUIZ,
            correct_option_id=question_data['correct_option_id'],
            is_anonymous=False,
            allows_multiple_answers=False
        )
        
        session['message_id'] = message.message_id
    except Exception as e:
        logger.error(f"Ошибка при отправке опроса: {e}")

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ответы на опросы."""
    answer = update.poll_answer
    user_id = answer.user.id
    
    session = user_sessions.get(user_id)
    if not session:
        return
    
    question_data = QUIZ_QUESTIONS[session['current_question']]
    
    if answer.option_ids[0] == question_data['correct_option_id']:
        session['correct'] += 1
    session['total'] += 1
    
    session['current_question'] += 1
    
    # Отправляем следующий вопрос
    await send_question(update, context, user_id, update.effective_chat.id)

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
    """Показывает итоговый результат."""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    result_text = (
        f"🎉 Викторина завершена!\n\n"
        f"Правильных ответов: {session['correct']} из {session['total']}\n"
        f"Процент: {(session['correct']/session['total'])*100:.1f}%\n\n"
    )
    
    if session['correct'] == session['total']:
        result_text += "🌟 Идеально! Ты гений!"
    elif session['correct'] >= session['total'] * 0.8:
        result_text += "👍 Отлично! Ты много знаешь!"
    elif session['correct'] >= session['total'] * 0.6:
        result_text += "👌 Хорошо! Но есть куда расти"
    else:
        result_text += "📚 Попробуй еще раз, чтобы улучшить результат!"
    
    # Удаляем сессию после показа результатов
    del user_sessions[user_id]
    
    await context.bot.send_message(chat_id=chat_id, text=result_text)
    await context.bot.send_message(chat_id=chat_id, text="Хочешь попробовать снова? Используй /quiz")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку."""
    await update.message.reply_text(
        "📚 Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/quiz - Начать викторину\n"
        "/help - Показать это сообщение"
    )

async def run_bot():
    """Асинхронная функция запуска бота."""
    print("Бот запускается...")
    
    # Создаем и настраиваем event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(PollAnswerHandler(handle_poll_answer))
    
    print("Бот запущен и готов к работе!")
    
    # Запускаем бота
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Держим бота запущенным
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

def main():
    """Главная функция."""
    try:
        # Создаем новый event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Запускаем бота
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        print("\nБот остановлен")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            loop.close()
        except:
            pass

if __name__ == '__main__':
    main()


