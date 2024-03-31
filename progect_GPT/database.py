import sqlite3
import logging

DB_DIR = 'db'
DB_NAME = 'GPT_past_module_progect.db'
DB_TABLE_USERS_NAME = 'users'


class Database:
    def __init__(self, sql_query, value, user_id):
        self.table_name = DB_TABLE_USERS_NAME
        self.sql_query = sql_query
        self.value = value
        self.user_id = user_id

    # Функция для подключения к базе данных или создания новой, если её ещё нет
    def create_db(self, database_name):
        db_path = f'{database_name}'
        connection = sqlite3.connect(db_path)
        connection.close()

        logging.info(f'DATABASE: Execute query: База данных {db_path} успешно создана')

    # Функция для выполнения любого sql-запроса для изменения данных
    def execute_query(self, sql_query, data=None, db_path=f'{DB_NAME}'):
        logging.info(f'DATABASE: Execute query:  {sql_query}')

        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        if data:
            cursor.execute(sql_query, data)
        else:
            cursor.execute(sql_query)

        connection.commit()
        connection.close()

    # Функция для выполнения любого sql-запроса для получения данных (возвращает значение)
    def execute_selection_query(self, sql_query, data=None, db_path=f'{DB_NAME}'):
        logging.info(f'DATABASE: Execute query: {sql_query}')

        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        print(data)
        if data:
            cursor.execute(sql_query, data)
        else:
            cursor.execute(sql_query)
        rows = cursor.fetchall()
        connection.close()
        print(rows)
        return rows

    # Функция для создания новой таблицы (если такой ещё нет)
    # Получает название и список колонок в формате ИМЯ: ТИП
    # Создаёт запрос CREATE TABLE IF NOT EXISTS имя_таблицы (колонка1 ТИП, колонка2 ТИП)
    def create_table(self, table_name):
        sql_query = f'CREATE TABLE IF NOT EXISTS {table_name} ' \
                    f'(id INTEGER PRIMARY KEY, ' \
                    f'user_id INTEGER,' \
                    f'timestamp TEXT,' \
                    f'text TEXT, '
        Database.execute_query(sql_query)

    # Функция для вывода всей таблицы (для проверки)
    # Создаёт запрос SELECT * FROM имя_таблицы
    def get_all_rows(self, table_name):
        rows = Database.execute_selection_query(f'SELECT * FROM {table_name}')
        for row in rows:
            print(row)

    # Функция для вставки новой строки в таблицу
    # Принимает список значений для каждой колонки и названия колонок
    # Создаёт запрос INSERT INTO имя_таблицы (колонка1, колонка2) VALUES (?, ?)[значение1, значение2]
    def insert_row(self, values):
        columns = '(user_id, subject, level, task, answer)'
        sql_query = f'INSERT INTO {DB_TABLE_USERS_NAME} {columns} VALUES (?,?,?,?,?)'
        Database.execute_query(sql_query, values)

    # Функция для проверки, есть ли элемент в указанном столбце таблицы
    # Создаёт запрос SELECT колонка FROM имя_таблицы WHERE колонка == значение LIMIT 1
    def is_value_in_table(self, table_name, column_name, value):
        sql_query = f'SELECT {column_name} FROM {table_name} WHERE {column_name} =? LIMIT 1'
        rows = Database.execute_selection_query(sql_query, [value])
        return any(rows) > 0

    # Функция для получения данных для указанного пользователя
    def get_data_for_user(self, user_id):
        user_id = int(user_id)
        if Database.is_value_in_table(DB_TABLE_USERS_NAME, "user_id", user_id):
            sql_query = (f'SELECT user_id, subject, level, task, answer '
                         f'FROM {DB_TABLE_USERS_NAME} '
                         f'WHERE user_id = ? '
                         f'LIMIT 1')
            row = Database.execute_selection_query(sql_query, [user_id])[0]
            return {
                'subject': row[1],
                'level': row[2],
                'task': row[3],
                'answer': row[4]
            }
        else:
            logging.info(f'DATABASE: Не найден пользователь с id {user_id}')
            print(f'DATABASE: Не найден пользователь с id {user_id}')
            return {
                'subject': "",
                'level': "",
                'task': "",
                'answer': ""
            }
