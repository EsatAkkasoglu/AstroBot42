from connection import DatabaseConnection
import mysql.connector
def run_query(sql_query):
    db_connection = DatabaseConnection().connect()
    try:
        cursor = db_connection.cursor()
        cursor.execute(sql_query)
        result = cursor.fetchall()
        cursor.close()
        db_connection.close()
        return result
    except mysql.connector.Error as err:
        print("Error:", err)
        db_connection.close()
        return None

# Usage example
query = """CREATE TABLE  (
    id INT PRIMARY KEY,
    discord_id VARCHAR(255) NOT NULL,
    discord_name VARCHAR(255) NOT NULL,
    total_token INT 
);
"""
query_result = run_query(query)
if query_result:
    for row in query_result:
        print(row)
