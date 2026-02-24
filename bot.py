import logging
import sys
import types
import asyncio
from telegram import Update, Poll
from telegram.ext import Application, CommandHandler, PollAnswerHandler, ContextTypes

# Фикс для Python 3.14
if sys.version_info >= (3, 14):
    # Создаем недостающие модули
    if 'imghdr' not in sys.modules:
        imghdr = types.ModuleType('imghdr')
        def what(file, h=None):
            return None
        imghdr.what = what
        sys.modules['imghdr'] = imghdr

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = '8041853834:AAEQPmh2E3jzHQRm9eUMdQvDHe8uW8qE1Zg'

# Вопросы
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

user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! 🎯\n"
        f"Используй /quiz для начала викторины."
    )

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    user_sessions[user_id] = {
        'correct': 0,
        'total': 0,
        'current_question': 0
    }
    
    await send_question(update, context, user_id, chat_id)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
    session = user_sessions.get(user_id)
    if not session:
        return
    
    if session['current_question'] >= len(QUIZ_QUESTIONS):
        await show_result(update, context, user_id, chat_id)
        return
    
    question = QUIZ_QUESTIONS[session['current_question']]
    
    try:
        await context.bot.send_poll(
            chat_id=chat_id,
            question=question['question'],
            options=question['options'],
            type=Poll.QUIZ,
            correct_option_id=question['correct_option_id'],
            is_anonymous=False
        )
    except Exception as e:
        logger.error(f"Ошибка отправки опроса: {e}")

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    user_id = answer.user.id
    
    session = user_sessions.get(user_id)
    if not session:
        return
    
    question = QUIZ_QUESTIONS[session['current_question']]
    
    if answer.option_ids[0] == question['correct_option_id']:
        session['correct'] += 1
    session['total'] += 1
    session['current_question'] += 1
    
    await send_question(update, context, user_id, update.effective_chat.id)

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
    session = user_sessions.pop(user_id, None)
    if not session:
        return
    
    percent = (session['correct'] / session['total']) * 100
    
    result = f"🎉 Викторина завершена!\n\n"
    result += f"Правильных ответов: {session['correct']} из {session['total']}\n"
    result += f"Процент: {percent:.1f}%\n\n"
    
    if percent == 100:
        result += "🌟 Идеально!"
    elif percent >= 80:
        result += "👍 Отлично!"
    elif percent >= 60:
        result += "👌 Хорошо!"
    else:
        result += "📚 Попробуй еще!"
    
    await context.bot.send_message(chat_id=chat_id, text=result)
    await context.bot.send_message(chat_id=chat_id, text="Хочешь еще? Используй /quiz")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды:\n"
        "/start - Приветствие\n"
        "/quiz - Начать викторину\n"
        "/help - Помощь"
    )

def main():
    print("Бот запускается...")
    
    # Создаем event loop для Python 3.14
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(PollAnswerHandler(handle_poll_answer))
    
    print("Бот запущен!")
    application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
