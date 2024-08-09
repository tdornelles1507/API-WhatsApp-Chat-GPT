import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        connection = mysql.connector.connect(
            host='',
            user='',
            password='',
            database=''
        )
        return connection
    except Error as e:
        print("Erro ao conectar ao MySQL", e)
        return None
s