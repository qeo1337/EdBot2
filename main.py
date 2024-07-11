import telebot
from telebot import types
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sqlite3
import logging
from telebot import types
from datetime import datetime
import threading
import time
# Токен вашего Telegram бота
TOKEN = '6753326373:AAHgglAIYrg_jJe4RCEoFzw2Y93S9IIDLXI'  # Замените на ваш токен бота
bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
AUTHORIZED_USERS = ['qeo13378', 'y-a-varfolome', 'natanikitenko', 'mozgovaya31', 'eka-n-berezi', 'e-shchanova', 'irina-san1995', 'e-e-stasyuk', 'yanchy', 'y-a-varfolome', 'sashafursova', 'anbelskya']

skip_keywords = ['Команда мечты',
    'Клиентское направление',
    'Курьерское направление',
    'Партнёрское направление',
    'Дообучение',
    'Контент',
    'Группа сопровождения найма',
    'Наставничество'
]
# Путь к вашему JSON файлу с учетными данными
CREDENTIALS_FILE = 'E:\\Новая папка (2)\\true-server-424707-i3-d86c854f72f5.json'  # Замените на путь к вашему JSON файлу

# URL вашей Google Таблицы
SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1K78LBzr1pgEvMSdmMUgMWkvXCMaigmW9cqqNR8OL6FA/edit?usp=sharing'

# Настраиваем соединение с Google Таблицами
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_url(SPREADSHEET_URL)
sheet = spreadsheet.sheet1


def create_date_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2)
    today = types.KeyboardButton('Сегодня')
    tomorrow = types.KeyboardButton('Завтра')
    day_after_tomorrow = types.KeyboardButton('Послезавтра')
    select_date = types.KeyboardButton('Выбрать день')
    back = types.KeyboardButton('Назад')
    markup.add(today, tomorrow, day_after_tomorrow, select_date, back)
    return markup
def create_main_menu_keyboard(user_login):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    item1 = types.KeyboardButton('Профиль')
    item2 = types.KeyboardButton('Задачи')
    item3 = types.KeyboardButton('Загрузить задачи')
    item4 = types.KeyboardButton('Посмотреть документ')

    # Добавляем кнопки только для авторизованных пользователей
    if user_login in AUTHORIZED_USERS:
        markup.add(item1, item2, item3, item4)
    else:
        markup.add(item1, item2)  # Добавляем только кнопку "Профиль" для неавторизованных пользователей

    return markup
# Обработчик кнопки "Назад"
@bot.message_handler(func=lambda message: message.text == 'Назад')
def go_back(message):
    user_login = get_user_login(message.from_user.id)
    markup = create_main_menu_keyboard(user_login)
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=markup)


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    create_tables()
    user_login = get_user_login(message.from_user.id)
    markup = create_main_menu_keyboard(user_login)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

# Сохранение текущего состояния графика перед загрузкой новых данных
def save_previous_tasks():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT date, user, task, comment FROM tasks")
    previous_tasks = cursor.fetchall()
    conn.close()
    return previous_tasks

# Сравнение текущего и предыдущего состояний графика и отправка уведомления, если есть изменения
import sqlite3
import logging

def compare_and_notify_changes(user_id, user_login, previous_tasks):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT task, comment FROM tasks WHERE user=?", (user_login,))
    new_tasks = cursor.fetchall()
    conn.close()

    user_previous_tasks = [task[2] for task in previous_tasks if task[1] == user_login]  # Собираем только описания задач для текущего пользователя
    new_task_descriptions = [task[0] for task in new_tasks]  # Собираем только описания задач из новых данных

    logging.info(f"User {user_login} previous task descriptions: {user_previous_tasks}")
    logging.info(f"User {user_login} new task descriptions: {new_task_descriptions}")

    if set(user_previous_tasks) != set(new_task_descriptions):
        # Если описания задач изменились, отправьте уведомление
        bot.send_message(user_id, "Ваш график задач был обновлен. Пожалуйста, проверьте новые задачи.")
        logging.info(f"Notification sent to user {user_login} for updated tasks.")
    else:
        logging.info(f"No changes in tasks for user {user_login}. No notification sent.")

def get_all_users():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, login FROM users")
    users = cursor.fetchall()
    conn.close()
    return users


# Создание таблиц в базе данных, если они еще не существуют, и добавление столбца birth_date
def create_tables():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (user_id INTEGER PRIMARY KEY,
                       login TEXT UNIQUE,
                       birth_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       date TEXT,
                       user TEXT,
                       task TEXT,
                       comment TEXT)''')

    # Проверка и добавление столбца birth_date, если он отсутствует
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'birth_date' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN birth_date TEXT")

    conn.commit()
    conn.close()


# Обработчик кнопки "Задачи"
# Обработчик кнопки "Задачи"
@bot.message_handler(func=lambda message: message.text == 'Задачи')
def tasks_menu(message):
    bot.send_message(message.chat.id, "Выберите дату:", reply_markup=create_date_keyboard())




# Обработчик кнопки "Загрузить задачи"
@bot.message_handler(func=lambda message: message.text == 'Загрузить задачи')
def upload_tasks(message):
    user_login = get_user_login(message.from_user.id)
    if user_login in AUTHORIZED_USERS:
        bot.send_message(message.chat.id, "Загрузка задач из Google Таблицы...")
        try:
            users = get_all_users()
            previous_tasks = save_previous_tasks()
            load_tasks_from_google_sheet()

            for user_id, login in users:
                compare_and_notify_changes(user_id, login, previous_tasks)

            bot.send_message(message.chat.id, "Задачи успешно загружены.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Произошла ошибка при загрузке задач: {e}")
            logging.error(f"Error loading tasks: {e}")


def load_tasks_from_google_sheet():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks")

    # Получаем данные из таблицы
    data = sheet.get_all_values()
    logging.info(f"Data from sheet: {data}")

    # Получаем даты из первой строки (начиная с четвертого столбца)
    dates = [datetime.strptime(cell, '%d.%m').strftime('%d.%m') if cell else None for cell in data[0][3:]]
    logging.info(f"Dates extracted: {dates}")

    # Получаем примечания из таблицы
    notes = sheet.get_notes()
    logging.info(f"Notes from sheet: {notes}")

    for row_index, row in enumerate(data[1:], start=1):
        if any(keyword in row for keyword in skip_keywords):
            continue

        user = row[2]
        previous_task = None  # Переменная для хранения предыдущей задачи
        previous_comment = None  # Переменная для хранения предыдущего комментария

        for i, task in enumerate(row[3:], start=0):
            comment = notes[row_index][i + 3] if (row_index < len(notes) and len(notes[row_index]) > i + 4) else None

            if task:
                # Если есть задача, сохраняем ее и комментарий
                cursor.execute("INSERT INTO tasks (date, user, task, comment) VALUES (?, ?, ?, ?)",
                               (dates[i], user, task, comment))
                previous_task = task  # Сохраняем текущую задачу как предыдущую
                previous_comment = comment  # Сохраняем текущий комментарий как предыдущий
            elif comment:
                # Если задача пустая, но есть комментарий, сохраняем только комментарий
                cursor.execute("INSERT INTO tasks (date, user, task, comment) VALUES (?, ?, ?, ?)",
                               (dates[i], user, '', comment))
            elif previous_task:
                # Если задача пустая и комментария нет, дублируем задачу и комментарий из предыдущего дня
                cursor.execute("INSERT INTO tasks (date, user, task, comment) VALUES (?, ?, ?, ?)",
                               (dates[i], user, previous_task, previous_comment))

    conn.commit()
    conn.close()

# Обработчик команды /set_login
@bot.message_handler(commands=['set_login'])
def set_login(message):
    bot.send_message(message.chat.id, "Пожалуйста, введите свой логин:")
    bot.register_next_step_handler(message, process_login_step)


# Обработчик для ввода логина
def process_login_step(message):
    try:
        login = message.text.strip()
        user_id = message.from_user.id
        # Проверка, что логин уникален
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE login=?', (login,))
        result = cursor.fetchone()
        if result:
            bot.send_message(message.chat.id, "Этот логин уже занят. Пожалуйста, выберите другой логин.")
        else:
            cursor.execute("REPLACE INTO users (user_id, login) VALUES (?, ?)", (user_id, login))
            conn.commit()
            bot.send_message(message.chat.id, f"Логин '{login}' успешно сохранен.")
        conn.close()
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка при сохранении логина: {e}")
        logging.error(e)


# Функция для получения задач на определенный день для пользователя
def get_tasks_for_date(date, user):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT task, comment FROM tasks WHERE date=? AND user=?", (date, user))
    tasks_list = cursor.fetchall()
    conn.close()
    return tasks_list


# Функция для получения логина пользователя
def get_user_login(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT login FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


# Функция для получения даты рождения пользователя
def get_user_birth_date(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT birth_date FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


# Обработчик кнопки "Выбрать день"
@bot.message_handler(func=lambda message: message.text == 'Выбрать день')
def select_date(message):
    msg = bot.send_message(message.chat.id, "Введите дату в формате ДД.ММ:")
    bot.register_next_step_handler(msg, process_selected_date)


# Обработчик для обработки введенной пользователем даты
def process_selected_date(message):
    try:
        selected_date = datetime.strptime(message.text, "%d.%m").strftime("%d.%m")

        # Получаем логин пользователя
        user_id = message.from_user.id
        user_login = get_user_login(user_id)

        if user_login:
            tasks = get_tasks_for_date(selected_date, user_login)
            if tasks:
                tasks_message = f"Задачи на {selected_date}:\n"
                for task, comment in tasks:
                    tasks_message += f"- {task}"
                    if comment:
                        tasks_message += f" (Комментарий: {comment})"
                    tasks_message += "\n"
                bot.send_message(message.chat.id, tasks_message)
            else:
                bot.send_message(message.chat.id, f"На {selected_date} задач нет.")
        else:
            bot.send_message(message.chat.id,
                             "Не удалось найти ваш логин. Пожалуйста, убедитесь, что вы ввели логин с помощью команды /set_login.")
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат даты. Введите дату в формате ДД.ММ.")
# Обработчик кнопок с датами
@bot.message_handler(func=lambda message: message.text in ['Сегодня', 'Завтра', 'Послезавтра'])
def send_tasks(message):
    user_id = message.from_user.id
    user = get_user_login(user_id)

    if user:
        if message.text == 'Сегодня':
            date = datetime.now().strftime('%d.%m')
        elif message.text == 'Завтра':
            date = (datetime.now() + timedelta(days=1)).strftime('%d.%m')
        elif message.text == 'Послезавтра':
            date = (datetime.now() + timedelta(days=2)).strftime('%d.%m')

        tasks = get_tasks_for_date(date, user)
        if tasks:
            tasks_message = f"Задачи на {date}:\n"
            for task, comment in tasks:
                tasks_message += f"- {task}"
                if comment:
                    tasks_message += f" (Комментарий: {comment})"
                tasks_message += "\n"
            bot.send_message(message.chat.id, tasks_message)
        else:
            bot.send_message(message.chat.id, f"На {date} задач нет.")
    else:
        bot.send_message(message.chat.id,
                         "Не удалось найти ваш логин. Пожалуйста, убедитесь, что вы ввели логин с помощью команды /set_login.")


# Обработчик кнопки "Посмотреть документ"
@bot.message_handler(func=lambda message: message.text == 'Посмотреть документ')
def view_document(message):
    bot.send_message(message.chat.id, "Посмотреть документ нельзя")


# Обработчик кнопки "Профиль"
@bot.message_handler(func=lambda message: message.text == 'Профиль')
def profile(message):
    user_id = message.from_user.id
    user_login = get_user_login(user_id)
    user_birth_date = get_user_birth_date(user_id)

    if user_login:
        bot.send_message(message.chat.id, f"Ваш логин: {user_login}")
    else:
        bot.send_message(message.chat.id, "Ваш логин не установлен.")

    if user_birth_date:
        bot.send_message(message.chat.id, f"Ваша дата рождения: {user_birth_date}")
    else:
        bot.send_message(message.chat.id, "Ваша дата рождения не установлена.")

    markup = types.ReplyKeyboardMarkup(row_width=3)
    set_login_btn = types.KeyboardButton('Изменить логин')
    set_birth_date_btn = types.KeyboardButton('Установить дату рождения')
    back = types.KeyboardButton('Назад')
    markup.add(set_login_btn, set_birth_date_btn, back)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


# Обработчик кнопки "Изменить логин"
@bot.message_handler(func=lambda message: message.text == 'Изменить логин')
def change_login(message):
    bot.send_message(message.chat.id, "Пожалуйста, введите новый логин:")
    bot.register_next_step_handler(message, process_login_step)


# Обработчик кнопки "Установить дату рождения"
@bot.message_handler(func=lambda message: message.text == 'Установить дату рождения')
def set_birth_date(message):
    bot.send_message(message.chat.id, "Пожалуйста, введите вашу дату рождения (в формате ДД.ММ.ГГГГ):")
    bot.register_next_step_handler(message, process_birth_date_step)


# Обработчик для ввода даты рождения
def process_birth_date_step(message):
    try:
        birth_date = datetime.strptime(message.text.strip(), '%d.%m.%Y').strftime('%d.%m.%Y')
        user_id = message.from_user.id

        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET birth_date=? WHERE user_id=?", (birth_date, user_id))
        conn.commit()
        conn.close()

        bot.send_message(message.chat.id, f"Дата рождения '{birth_date}' успешно сохранена.")
    except ValueError:
        bot.send_message(message.chat.id, "Неправильный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка при сохранении даты рождения: {e}")
        logging.error(e)
def clear_database():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks")  # Очищаем таблицу tasks
    cursor.execute("DELETE FROM users")  # Очищаем таблицу users
    conn.commit()
    conn.close()


# Обработчик команды /clear_db
@bot.message_handler(commands=['clear_db'])
def clear_db(message):
    try:
        clear_database()
        bot.send_message(message.chat.id, "База данных успешно очищена.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка при очистке базы данных: {e}")
        logging.error(f"Error clearing database: {e}")


def schedule_task_update():
    while True:
        logging.info("Scheduled task update: Loading tasks from Google Sheet...")
        try:
            users = get_all_users()
            previous_tasks = save_previous_tasks()
            load_tasks_from_google_sheet()

            for user_id, login in users:
                compare_and_notify_changes(user_id, login, previous_tasks)

            logging.info("Scheduled task update: Tasks successfully updated.")
        except Exception as e:
            logging.error(f"Error in scheduled task update: {e}")

        # Ждем 15 минут перед следующим обновлением
        time.sleep(900)
# Запуск задачи обновления каждые 15 минут


# Запуск бота
if __name__ == "__main__":
    create_tables()

    # Запуск функции обновления задач в отдельном потоке
    update_thread = threading.Thread(target=schedule_task_update)
    update_thread.daemon = True
    update_thread.start()

    # Запуск бота
    bot.polling(none_stop=True)