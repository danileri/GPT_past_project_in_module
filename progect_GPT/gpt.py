import requests
from data import load_data, save_data
from config import FOLDER_ID, IAM_TOKEN
from stringing import temperature, max_tokens_in_task, DATA_PATH, URL
from stringing import SYSTEM_PROMPT, CONTINUE_STORY, END_STORY


def count_tokens(text):
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }
    json = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest",
        "maxTokens": max_tokens_in_task,
        "text": text
    }
    tokens = len(
        requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenize",
            json=json,
            headers=headers
        ).json()['tokens']
    )
    return tokens


def create_prompt(data=dict, user_id=int):
    promt = SYSTEM_PROMPT
    promt += (
        f"Напиши начало истории в стиле {data[str(user_id)]['genre']}"
        f" с главным героем, {data[str(user_id)]['character']}. "
        f"Вот начальный сеттинг: {data[str(user_id)]['setting']}. "
        "Начало должно быть коротким, 1-3 предложения."
    )
    promt += "Не пиши никакие подсказки пользователю, что делать дальше. Он сам знает, что делать."

    return promt

def past_prompt(data=dict, user_id=int):
    promt = SYSTEM_PROMPT

    promt += (f"История в стиле {data[str(user_id)]['genre']}"
              f" с главным героем, {data[str(user_id)]['character']}. "
              f"Вот начальный сеттинг: {data[str(user_id)]['setting']}. ")


def ask_gpt(collection, max_tokens, mode='continue'):
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }
    json = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": max_tokens
        },
        "messages": []
    }

    for row in collection:
        content = row['content']

        # Добавление инструкций в зависимости от режима работы
        if mode == 'continue' and row['role'] == 'user':
            content += '\n' + CONTINUE_STORY
        elif mode == 'end' and row['role'] == 'user':
            content += '\n' + END_STORY

        # Формирование сообщения для отправки
        json["messages"].append({
            "role": row["role"],  # Роль отправителя (пользователь или система)
            "text": content  # Текст сообщения
        })

    # Проверяем, не произошла ли ошибка при запросе
    try:
        response = requests.post(URL, headers=headers, json=json)  # Отправка запроса
        if response.status_code != 200:
            result = f"Status code {response.status_code}."  # Обработка ошибки статуса
            return result
        # Получение и возврат результата из ответа
        result = response.json()['result']['alternatives'][0]['message']['text']
        return result
    except Exception as e:
        # Обработка исключения при запросе
        result = f"Ошибка {e}"
        return result
