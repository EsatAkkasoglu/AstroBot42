import unittest
import os
from PIL import Image
from dotenv import load_dotenv
load_dotenv("config.env")
from database.connection import DatabaseConnection 
from src.openAI_functions.AI_functions import  PandasDataFrameAgent,DocBot
from src.log_files.logger import Logger
red = "\033[1;37;41m"
green = "\033[1;37;42m"
reset = "\033[0;0m"

class TestDatabaseConnection(unittest.TestCase):
    def setUp(self):
        # Create the necessary samples before each test
        #data Base Connection
        self.db_connection = DatabaseConnection()
        # OpenAI Agent
        apiKey=os.getenv("openAI_api")
        dataFilePath="https://gist.githubusercontent.com/stungeye/a3af50385215b758637e73eaacac93a3/raw/c1f936ae9dedc4d80398e6c11dbc95835c3c8f20/movies.csv"
        self.agent = PandasDataFrameAgent(apiKey, dataFilePath)
        # DocBot
        text_path= "https://raw.githubusercontent.com/smaameri/multi-doc-chatbot/91e63f6dd2dbc6f1493d6595583c230372a975dc/docs/JuanGarciaCV.txt"
        self.docbot=DocBot(openAI_api_key=apiKey,file_paths=list(text_path))

    def test_database_connect(self):
        # Check if you can successfully connect to the database
        connection = self.db_connection.connect()
        self.assertIsNotNone(connection)
        self.assertTrue(connection.is_connected())
        database_connect_result=green+"Database Connection Successful"+reset
        print(database_connect_result)
        return database_connect_result
    def test_pandasDFagent(self):
        # Test a query and verify the results
        query = "Group the total number of changing years intoğ groups of 10. Add the duration sum values of all groups. Visualize with a bar chart"
        result = self.agent.run_query(query)
        # Assert the results based on your expectations
        self.assertIsInstance(result, dict)
        self.assertIn("Total_Cost_(USD)", result)
        self.assertIn("Total_Tokens", result)       
        self.assertIn("Tool_Input", result)      
        image = result.get("Image")
        if image is not None:
            self.assertIsInstance(image, Image.Image)
        result_pandasDFagent=green+"PandasDataFrameAgent Successful"+reset
        print(result_pandasDFagent)
        return result_pandasDFagent
    def test_docbot(self):
        # Test a query and verify the results
        query = "What is your name?"
        result = self.docbot.process_query(query)
        # Assert the results based on your expectations
        self.assertIsInstance(result, dict)
        self.assertIn("Total_Cost_(USD)", result)
        self.assertIn("Total_Tokens", result)       
        self.assertIn("result", result)      
        self.assertIn("question",result)
        result_docbot=green+"DocBot Successful"+reset
        print(result_docbot)
        return result_docbot
if __name__ == "__main__":
    unittest.main()
    