import os
from dotenv import load_dotenv
from database.data_user import UserDB

load_dotenv()

connection = os.getenv("DB_CONNECTION")
connector = os.getenv("DB_CONNECTOR")
username = os.getenv("DB_USERNAME")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
db_name = os.getenv("DB_DATABASE")

user_DB = UserDB(connection, connector, username, password, host, port, db_name)