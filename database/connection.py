import mysql.connector
from configparser import ConfigParser

class DatabaseConnection:
    def __init__(self):
        self.config_file_path = 'database/database_config.ini'
        self.config = self.read_config(self.config_file_path)
    
    def read_config(self, config_file_path):
        config = ConfigParser()
        config.read(config_file_path)
        return config['DATABASE']
    
    def connect(self):
        try:
            connection = mysql.connector.connect(
                host=self.config['host'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password'],
                port=self.config['port']
            )
            if connection.is_connected():
                return connection
        except mysql.connector.Error as err:
            print("Error:", err)
            return None

# Usage example
db_connection = DatabaseConnection().connect()

