import logging
import asyncio
from telegram import Update, Poll
from telegram.ext import Application, CommandHandler, PollAnswerHandler, ContextTypes
import os
import sys

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота (получите у @BotFather)
TOKEN = 'ВАШ_ТОКЕН_СЮДА'

# Вопросы для викторины
QUIZ_QUESTIONS = [
    {
        'question': 'Какая планета самая большая в Солнечной системе?',
        'options': ['Марс', 'Юпитер', 'Сатурн', 'Нептун'],
        'correct_option_id': 1  # Юпитер (индексация с 0)
    },
    {
        'question': 'Сколько будет 2 + 2 * 2?',
        'options': ['4', '6', '8', '10'],
        'correct_option_id': 1  # 6
    },
    {
        'question': 'Кто написал роман "Война и мир"?',
        'options': ['Достоевский', 'Толстой', 'Чехов', 'Пушкин'],
        'correct_option_id': 1  # Толстой
    },
    {
        'question': 'Какой газ самый распространенный в атмосфере Земли?',
        'options': ['Кислород', 'Углекислый газ', 'Азот', 'Водород'],
        'correct_option_id': 2  # Азот
    },
    {
        'question': 'Столица Франции?',
        'options': ['Лондон', 'Берлин', 'Мадрид', 'Париж'],
        'correct_option_id': 3  # Париж
    }
]

# Словарь для хранения результатов пользователей
# Формат: {user_id: {'correct': 0, 'total': 0, 'current_question': 0, 'message_id': None}}
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение и начинает викторину."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! 🎯\n"
        f"Я бот для викторин. Я задам тебе 5 вопросов.\n"
        f"После ответа на все вопросы ты узнаешь свой результат.\n"
        f"Для начала викторины используй команду /quiz"
    )

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает викторину."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Сбрасываем сессию пользователя
    user_sessions[user_id] = {
        'correct': 0,
        'total': 0,
        'current_question': 0,
        'message_id': None
    }
    
    # Отправляем первый вопрос
    await send_question(update, context, user_id, chat_id)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
    """Отправляет вопрос викторины."""
    session = user_sessions[user_id]
    question_index = session['current_question']
    
    if question_index >= len(QUIZ_QUESTIONS):
        # Викторина закончена, показываем результат
        await show_result(update, context, user_id, chat_id)
        return
    
    question_data = QUIZ_QUESTIONS[question_index]
    
    # Отправляем опрос
    message = await context.bot.send_poll(
        chat_id=chat_id,
        question=question_data['question'],
        options=question_data['options'],
        type=Poll.QUIZ,  # Тип "викторина"
        correct_option_id=question_data['correct_option_id'],
        is_anonymous=False,  # Видим, кто отвечает
        allows_multiple_answers=False
    )
    
    # Сохраняем ID сообщения с опросом
    session['message_id'] = message.message_id

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ответы на опросы."""
    answer = update.poll_answer
    user_id = answer.user.id
    
    # Получаем сессию пользователя
    session = user_sessions.get(user_id)
    if not session:
        return
    
    # Получаем информацию об опросе
    poll = answer.poll
    
    # Проверяем правильность ответа
    selected_option = answer.option_ids[0]
    question_data = QUIZ_QUESTIONS[session['current_question']]
    
    if selected_option == question_data['correct_option_id']:
        session['correct'] += 1
    session['total'] += 1
    
    # Переходим к следующему вопросу
    session['current_question'] += 1
    
    # Отправляем следующий вопрос
    await send_question(update, context, user_id, update.effective_chat.id)

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
    """Показывает итоговый результат."""
    session = user_sessions[user_id]
    
    # Формируем сообщение с результатом
    result_text = (
        f"🎉 Викторина завершена!\n\n"
        f"Правильных ответов: {session['correct']} из {session['total']}\n"
        f"Процент правильных: {(session['correct']/session['total'])*100:.1f}%\n\n"
    )
    
    # Добавляем оценку
    if session['correct'] == session['total']:
        result_text += "🌟 Идеально! Ты гений!"
    elif session['correct'] >= session['total'] * 0.8:
        result_text += "👍 Отлично! Ты много знаешь!"
    elif session['correct'] >= session['total'] * 0.6:
        result_text += "👌 Хорошо! Но есть куда расти"
    else:
        result_text += "📚 Попробуй еще раз, чтобы улучшить результат!"
    
    # Очищаем сессию
    del user_sessions[user_id]
    
    await context.bot.send_message(chat_id=chat_id, text=result_text)
    
    # Предлагаем начать заново
    await context.bot.send_message(
        chat_id=chat_id,
        text="Хочешь попробовать снова? Используй команду /quiz"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку."""
    help_text = (
        "📚 Доступные команды:\n\n"
        "/start - Начать работу с ботом\n"
        "/quiz - Начать викторину\n"
        "/help - Показать это сообщение"
    )
    await update.message.reply_text(help_text)

def main():
    """Запускает бота."""
    print("Бот запускается...")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик ответов на опросы
    application.add_handler(PollAnswerHandler(handle_poll_answer))
    
    # Запускаем бота
    print("Бот запущен и готов к работе!")
    
    # Используем простой run_polling без параметров
    application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)
