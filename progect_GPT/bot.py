import telebot
import logging
import datetime
from data import save_data, load_data
from telebot import types
from config import TOKEN
from stringing import DATA_PATH, MAX_SESSIONS, MAX_USERS, MAX_TOKENS_PER_SESSION, USERS_HISTORY
from gpt import count_tokens, ask_gpt, create_prompt

bot = telebot.TeleBot(token=TOKEN)

# curl -H Metadata-Flavor:Google 169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token

logging.basicConfig(filename="logs.txt",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%y-%m-%d %H:%M:%S',
                    level=logging.NOTSET)
logger = logging.getLogger('urbanGUI')


def resp_continue(collection, max_tokens, mode):
    # response = ask_gpt(collection=collection, max_tokens=max_tokens, mode=mode)
    response = "1"
    collection.append({'role': 'assistant', 'content': response})
    return response, collection


def create_keyboard(buttons_list):
    keyboard_custom = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    keyboard_custom.add(*buttons_list)
    return keyboard_custom


keyboard = types.ReplyKeyboardMarkup(
    row_width=2,
    resize_keyboard=True
)
keyboard.add(*["/autocomplete"])


@bot.message_handler(commands=['debug'])
def debug_command(message):
    chat_id = message.from_user.id
    with open('logs.txt', 'rb') as f:
        bot.send_document(chat_id, f)


@bot.message_handler(commands=['debug_mode'])
def debug_mode(message):
    user_id = str(message.from_user.id)
    data = load_data(DATA_PATH)
    if str(user_id) in data:
        debug_mode_text = data[user_id]["debug_mode"]
        if debug_mode_text == "False":
            data[user_id]["debug_mode"] = "True"
            save_data(data, DATA_PATH)
            bot.send_message(user_id, "Режим отладки: Включен")
            logging.info(f"INFO: У пользователя {message.from_user.id} был включён режим отладки")
        elif debug_mode_text == "True":
            data[user_id]["debug_mode"] = "False"
            save_data(data, DATA_PATH)
            bot.send_message(user_id, "Режим отладки: Выключен")
            logging.info(f"INFO: У пользователя {message.from_user.id} был выключен режим отладки")
        else:
            bot.send_message(user_id, "Ошибка! Вы по-нормальному сюда вообще попасть не можете!\n"
                                      "Пожалуйста, попробуйте ещё раз, запустив старт")
    else:
        new_user = {str(user_id): {"sessions": 0, "use_all_tokens": 0, "tokens_left_for_session": 300,
                                   "debug_mode": "False", "genre": "", "character": "", "setting": "",
                                   "mode": "continue", "is_error": "False", "response_gpt": ""}}
        data.update(new_user)
        data['users'] += 1
        save_data(data, DATA_PATH)
        logging.info(f"INFO: Пользователь {user_id} зарегистрирован")
        bot.send_message(user_id, "Вас нет в базе данных, сейчас я вас в неё добавлю и после вы сможете изменить "
                                  "режим отладки. Стандартно выставлено в состояние выключено")


@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id
        data = load_data(DATA_PATH)
        if str(user_id) in data:
            debug_mode_text = data[str(user_id)]["debug_mode"]
            if debug_mode_text == "True":
                bot.send_message(user_id, "Пользователь ввёл команду 'старт'")
        logging.info(f"INFO: {user_id} ввёл команду 'старт'")
        bot.send_message(user_id, f'Здравия, {message.from_user.first_name}! Я - бот, способный '
                                  f'начинать историю, писать с твоими правками и заканчивать писать.')
    except:
        print("json пуст")
        logging.info(f"INFO: json пуст")
        user_id = message.from_user.id
        bot.send_message(user_id, f'Здравия, {message.from_user.first_name}! Я - бот, способный '
                                  f'начинать историю, писать с твоими правками и заканчивать писать.')


@bot.message_handler(commands=['autocomplete'])
def autocomplete(message):
    user_id = message.from_user.id
    data = load_data(DATA_PATH)
    if data == {}:
        data = {"users": 0}
        save_data(data, DATA_PATH)
    logging.info(f"INFO: {user_id} ввёл команду 'autocomplete'")

    if str(user_id) not in data:
        if data['users'] == MAX_USERS:
            bot.send_message(user_id, "К сожалению лимит участников заполнен, возвращайтесь, когда его увеличат "
                                      "или очистят.")
            logging.info(f"INFO: Отклонён новый пользователь по причине: Лимит участников заполнен")

        elif data['users'] < MAX_USERS:
            new_user = {str(user_id): {"sessions": 0, "use_all_tokens": 0, "tokens_left_for_session": 0,
                                       "tokens_left_for_session": 300, "debug_mode": "False", "genre": "",
                                       "character": "", "setting": "", "mode": "continue", "response_gpt": ""}}
            data.update(new_user)
            data['users'] += 1
            save_data(data, DATA_PATH)
            logging.info(f"INFO: Пользователь {user_id} зарегистрирован")
            bot.send_message(user_id, "Успешная регистрация!")
            start_session(message)


    elif str(user_id) in data:
        sessions = data[str(user_id)]['sessions']
        debug_mode_text = data[str(user_id)]['debug_mode']
        if sessions < MAX_SESSIONS:
            data[str(user_id)]['sessions'] += 1
            save_data(data, DATA_PATH)
            logging.info(f"INFO: Пользователь {user_id} подключен к новой сессии")
            if debug_mode_text == "True":
                bot.send_message(user_id, f"INFO: Пользователь {user_id} подключен к новой сессии")
                bot.send_message(user_id, "INFO: Успешно начата новая сессия!")
            bot.send_message(user_id, "Успешный вход, запущена новая сессия.")
            start_session(message)

        elif sessions == MAX_SESSIONS:
            logging.info(f"INFO: Отклонён пользователь {user_id} по причине: Лимит сессий")
            if debug_mode_text == "True":
                bot.send_message(user_id, f"INFO: Отклонён пользователь {user_id} по причине: Лимит сессий")
            bot.send_message(user_id, "К сожалению лимит сессий подошёл к концу, возвращайтесь, когда его "
                                      "увеличат")


def start_session(message):
    user_id = message.from_user.id
    data = load_data(DATA_PATH)
    if data[str(user_id)]['debug_mode'] == "True":
        bot.send_message(user_id, "Пользователь начал сессию, выбирает жанр")
    bot.send_message(user_id, "Выбери жанр:",
                     reply_markup=create_keyboard(['фентези', 'драма', 'комедия']))
    logging.info("INFO: Пользователь начал запрос, выбрал жанр")
    bot.register_next_step_handler(message, choose_genre)


def choose_genre(message):
    user_id = message.from_user.id
    genre = message.text
    if genre == "фентези" or genre == "драма" or genre == "комедия":
        data = load_data(DATA_PATH)
        data[str(user_id)]["genre"] = genre
        save_data(data, DATA_PATH)
        bot.send_message(user_id, "Выбери героя:",
                         reply_markup=create_keyboard(['мужчина качёк', 'мужчина слабак', 'женщина качёк',
                                                       'женщина слабак']))
        logging.info("INFO: Пользователь выбрал пол")
        bot.register_next_step_handler(message, choose_setting)
    else:
        bot.send_message(user_id, "Ты неправильно ввёл жанр. Попробуйте ещё раз.")
        logging.info("INFO: Пользователь не правильно ввёл жанр")
        bot.register_next_step_handler(message, choose_genre,
                                       reply_markup=create_keyboard(['фентези', 'драма', 'комедия']))


def choose_setting(message):
    user_id = message.from_user.id
    character = message.text
    if (character == "мужчина качёк" or character == "мужчина слабак" or
            character == "женщина качёк" or character == "женщина слабак"):
        data = load_data(DATA_PATH)
        data[str(user_id)]["character"] = character
        save_data(data, DATA_PATH)
        bot.send_message(user_id, "Выбери сеттинг:\n"
                                  "Бескрайняя пустыня - это место, где есть только песок и такие же как и ты, "
                                  "одинокие путники.\n"
                                  "Мегаполис - это место, где царит безумье, порок, и обман.\n Город мрачных трущоб,\n"
                                  " Весь изглоданный злом,\n по ночам его мгла накрывает крылом.\n"
                                  " И в глазницы домов смотрит ночь,  словно ворон,\n"
                                  " этот город безукоризненно чёрен.\n"
                                  " Только толпы нищих,\n только Темзы река - Этот город страшней,\n чем оживший "
                                  "мертвец.\n И в роскошных небоскрёбах вечный холод и тлен,\n  и часы мертвецам "
                                  "отбивает Биг-Бен.\n"
                                  "Пустота - это место, где нет ничего.\n "
                                  "Абсолютно ничего нет, пустая локация.\n "
                                  "Только ты и Пустота.")
        bot.send_message(user_id, "Выбери сеттинг:",
                         reply_markup=create_keyboard(['Бескрайняя пустыня', 'Мегаполис', 'Пустота']))
        logging.info("INFO: Пользователь выбрал сеттинг")
        bot.register_next_step_handler(message, asc_gpt_to_gpt)
    else:
        bot.send_message(user_id, "Ты неправильно ввёл сеттинг. Попробуйте ещё раз.")
        logging.info("INFO: Пользователь не правильно ввёл сеттинг")
        bot.register_next_step_handler(message, choose_genre,
                                       reply_markup=create_keyboard(['мужчина качёк', 'мужчина слабак',
                                                                     'женщина качёк', 'женщина слабак']))


def asc_gpt_to_gpt(message):
    user_id = message.from_user.id
    setting = message.text
    data = load_data(DATA_PATH)
    if setting == "Бескрайняя пустыня":
        setting_to_save = "Бескрайняя пустыня - это место, где есть только песок и такие же как и ты, одинокие путники."
        data[str(user_id)]["setting"] = setting_to_save
        save_data(data, DATA_PATH)
        ask_to_gpt(message)
    elif setting == "Мегаполис":
        setting_to_save = ("Мегаполис - это место, где царит безумье, порок, и обман. Город мрачных трущоб, весь "
                           "изглоданный злом, по ночам его мгла накрывает крылом. И в глазницы домов смотрит ночь, "
                           "словно ворон, этот город безукоризненно чёрен. Только толпы нищих, только Темзы река - "
                           "Этот город страшней, чем оживший мертвец. И в роскошных небоскрёбах вечный холод и тлен, "
                           "и часы мертвецам отбивает Биг-Бен.")
        data[str(user_id)]["setting"] = setting_to_save
        save_data(data, DATA_PATH)
        ask_to_gpt(message)
    elif setting == "Пустота":
        setting_to_save = ("Пустота - это место, где нет ничего. "
                           "Абсолютно ничего нет, пустая локация. "
                           "Только ты и Пустота.")
        data[str(user_id)]["setting"] = setting_to_save
        save_data(data, DATA_PATH)
        ask_to_gpt(message)
    else:
        bot.send_message(user_id, "Ты неправильно ввёл сеттинг. Попробуйте ещё раз.")
        logging.info("INFO: Пользователь не правильно ввёл сеттинг")
        bot.register_next_step_handler(message, choose_genre)


def ask_to_gpt(message):
    # try:
    user_id = message.from_user.id
    data = load_data(DATA_PATH)
    prompt = create_prompt(data, user_id)
    # 'continue' 'end'
    mode = data[str(user_id)]['mode']
    collection = [{'role': 'user', 'content': prompt}]
    maximus_tokenus = count_tokens(data[str(user_id)]["save_collection"][0]["content"])
    maximus_tokenus2 = count_tokens(data[str(user_id)]["save_collection"][1]["content"])
    maximus_tokenus3 = maximus_tokenus + maximus_tokenus2
    tokens_left_for_session = data[str(user_id)]['tokens_left_for_session']
    if maximus_tokenus3 > tokens_left_for_session:
        bot.send_message(user_id, "Ты превысил лимит токенов на сессию. Начни новую сессию.")
        logging.info("INFO: Пользователь превысил лимит токенов на сессию")
        return None
    else:
        max_tokens = tokens_left_for_session - maximus_tokenus3
        data[str(user_id)]['tokens_left_for_session'] = max_tokens
        save_data(data, DATA_PATH)
    response, collection = resp_continue(collection=collection, max_tokens=maximus_tokenus3, mode=mode)
    if response == int:
        if data[str(user_id)]['debug_mode'] == "True":
            bot.send_message(user_id, f"Ошибка {response}")
            logging.error(f"ERROR: Ошибка при обработке ответа от нейросети! Код: {response}")
    history_new = {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
                       data[str(user_id)]["save_collection"][0]["content"]}
    history = load_data(USERS_HISTORY)
    if user_id not in history:
        new_user_history = {str(user_id): history_new}
        history.update(new_user_history)
    else:
        pass
    bot.send_message(user_id, response)
    data[str(user_id)]['save_collection'] = collection
    save_data(data, DATA_PATH)
    if data[str(user_id)]['mode'] == "end":
        bot.send_message(user_id, "Вы закончили сессию, напишите /autocomplete, чтобы начать новую")
        logging.info("INFO: Пользователь закончил сессию")
        data[str(user_id)]['tokens_left_for_session'] = MAX_TOKENS_PER_SESSION
        data[str(user_id)]['mode'] = "continue"
        save_data(data, DATA_PATH)
        return None
    bot.send_message(user_id, "Продолжить или закончить?",
                     reply_markup=create_keyboard(['/continue', '/end']))


# except:
#     bot.send_message(message.from_user.id, "Вы не должны были вводить эту команду.")


@bot.message_handler(commands=['continue'])
def continue_command(message):
    user_id = message.from_user.id
    data = load_data(DATA_PATH)
    if data[str(user_id)]['debug_mode'] == "True":
        bot.send_message(user_id, "Пользователь нажал продолжить")
    bot.send_message(user_id, "Введи свою небольшую часть истории.")
    bot.register_next_step_handler(message, continue_command2)


def continue_command2(message):
    # try:
    data = load_data(DATA_PATH)
    user_id = message.from_user.id
    print(message.text)
    tokens = count_tokens(data[str(user_id)]["save_collection"][0]["content"])
    if tokens >= data[str(message.from_user.id)]['tokens_left_for_session']:
        bot.send_message(message.from_user.id, "Вы превысили лимит токенов на сессию.\n "
                                               "Напишите короче, чтобы продолжить сессию, либо начните новую."
                                               f"У вас осталось {tokens}")
        bot.register_next_step_handler(message, continue_command)
    else:
        data[str(user_id)]['tokens_left_for_session'] -= tokens
        data[str(user_id)]['use_all_tokens'] += tokens

        tokens = count_tokens(data[str(user_id)]["save_collection"][0]["content"])
        data[str(user_id)]['tokens_left_for_session'] -= tokens
        data[str(user_id)]['use_all_tokens'] += tokens
        save_data(data, DATA_PATH)

        data = load_data(DATA_PATH)
        prompt = create_prompt(data, user_id)
        collection = data[str(user_id)]['save_collection']
        collection.append({'role': 'user', 'content': prompt})
        data[str(user_id)]["save_collection"] = collection
        save_data(data, DATA_PATH)

    mode = 'continue'
    data[str(message.from_user.id)]['mode'] = mode
    save_data(data, DATA_PATH)
    ask_to_gpt(message)


# except:
#     bot.send_message(message.from_user.id, "Вы не должны были вводить эту команду.")


@bot.message_handler(commands=['end'])
def end_command(message):
    try:
        data = load_data(DATA_PATH)
        mode = 'end'
        data[str(message.from_user.id)]['mode'] = mode
        save_data(data, DATA_PATH)
        ask_to_gpt(message)
    except:
        bot.send_message(message.from_user.id, "Вы не должны были вводить эту команду.")


if __name__ == "__main__":
    bot.polling()
    logging.info("Бот запущен")
