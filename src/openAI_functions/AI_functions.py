import os  # Import the os module for setting environment variables
import aiohttp
import io
import sys
from PIL import Image
import pandas as pd
import matplotlib.pyplot as plt

# Import statements for LangChain modules
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import (PyPDFLoader, Docx2txtLoader, TextLoader)
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.text_splitter import CharacterTextSplitter
from langchain.agents.agent import AgentType
from langchain.callbacks import get_openai_callback

# Create a custom class called PandasDataFrameAgent


class PandasDataFrameAgent:
    """
    Interact with the OpenAI API for data analysis tasks using a Pandas DataFrame.

    Constructor:
    
    __init__(self, api_key, data_file_path, model="gpt-3.5-turbo-0613", temperature=0)

    Methods:
    run_query(self, query)

    Output (dict):
    - Total_Cost_(USD) (float): Total cost in USD for running queries.
    - Total_Tokens (int): Total number of tokens used during the analysis.
    - Tool_Input (list): Tool inputs for each analysis step.
    - Image (PIL.Image) | None: Optional image output generated during the analysis.

    Usage:
    >>> api_key = "your_openai_api_key"
    >>> data_agent = PandasDataFrameAgent(api_key, data_file_path='/path/to/your/data.(csv/xls/xlsx/json/xml)')
    >>> query = "Summarize the data. Make some bar graph"
    >>> result = data_agent.run_query(query)
    >>> print(result)
    >>> print(result["Total_Tokens"])

    This class allows you to interact with the OpenAI API to analyze data contained in a specified file.
    """
    def __init__(self, api_key, data_file_path, model="gpt-3.5-turbo-0613", temperature=0):
        """
        Initialize the PandasDataFrameAgent.

        Args:
            api_key (str): Your OpenAI API key.
            data_file_path (str): The path to the CSV, XLS, XLSX, JSON, or XML data file.
            model (str): The GPT-3.5 model to use (default is "gpt-3.5-turbo-0613").
            temperature (int): The temperature for response generation (default is 0).

        This class allows you to interact with the OpenAI API to analyze data contained in a specified file.
        """
        # Set the OpenAI API key
        os.environ['OPENAI_API_KEY'] = api_key

        # Determine the file format and load the data into a Pandas DataFrame
        file_extension = os.path.splitext(data_file_path)[-1].lower()
        if file_extension == '.csv':
            self.df = pd.read_csv(data_file_path)
        elif file_extension in ('.xls', '.xlsx'):
            self.df = pd.read_excel(data_file_path)
        elif file_extension == '.json':
            self.df = pd.read_json(data_file_path)
        elif file_extension == '.xml':
            self.df = pd.read_xml(data_file_path)
        # Add support for more data formats as needed

        # Initializing the agent for data analysis
        self.agent = create_pandas_dataframe_agent(
            ChatOpenAI(model=model, temperature=temperature),
            self.df, verbose=True,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            return_intermediate_steps=True
        )

    def run_query(self, query):
        """
        Analyze the data using the provided query.

        Args:
            query (str): The analysis query to be executed.

        Returns:
            dict: A dictionary containing analysis results.

        This method sends the query to the agent, executes it, and captures the results, including any images generated.
        """
        original_stdout = sys.stdout
        sys.stdout = io.StringIO()

        with get_openai_callback() as cb:
            # Send the query to the agent
            response = self.agent({"input": "ACTION: python_repl_ast " + query + " Must use tool python_repl_ast"})

            # Retrieve total tokens and total cost from the callback
            total_tokens = cb.total_tokens
            total_cost_usd = cb.total_cost

        tool_inputs = {}  # Create an empty dictionary to store tool inputs

        # Retrieve intermediate steps from the response
        response_intermediate = response['intermediate_steps']

        image = None
        for i in range(int(len(response_intermediate))):
            tool_input = str(response_intermediate[i][0].tool_input)
            # Remove unwanted characters from tool input
            tool_input = tool_input.replace("`", "")
            tool_input = tool_input.replace("plt.show()", "")

            # Add tool input to the dictionary
            tool_inputs[f"Step {i + 1}"] = tool_input

            try:
                text_for_exec = f"{tool_input}"
                
                # Execute the tool input code and capture its output
                exec(text_for_exec)

                buffer = io.BytesIO()
                plt.savefig(buffer, format='jpg')
                buffer.seek(0)
                result = buffer.getvalue()
                image = Image.open(io.BytesIO(result))

            except:
                pass

        sys.stdout = original_stdout
        # Return the results as a dictionary
        return {
            "Total_Cost_(USD)": total_cost_usd,
            "Total_Tokens": total_tokens,
            "Tool_Input": tool_inputs,  # Return the dictionary of tool inputs
            "Image": image  # Include any generated image in the results
        }

####################################
#For Doc Langchain Bot 
####################################
import os
from langchain.document_loaders import (PyPDFLoader, Docx2txtLoader, TextLoader,PythonLoader,NotebookLoader,WikipediaLoader,YoutubeLoader)
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.text_splitter import CharacterTextSplitter
from langchain.callbacks import get_openai_callback
class DocBot:
    def __init__(self, openAI_api_key:str, file_paths:list =None,text_input:str="None"):
        """
        Initialize the DocBot.

        Args:
            openAI_api_key (str): OpenAI api Key
            file_paths (list): List of file paths for various document types.

        Methods:
        process_query(self, query)

        Output (dict):
        - "question": The question asked to the bot.
        - "result": The answer to the query.
        - "Total_Tokens": Total number of tokens used during the analysis.
        - "Total_Cost_(USD)": Total cost in USD for running queries.

        Usage:
        >>> doc_bot = DocBot(openAI_api_key="sk-xxx",pdf_path='/path/to/your/pdf/file.pdf', docx_path=None, txt_path='/path/to/your/txt/file.txt')
        >>> query = "What is ImageBind-LLM?"
        >>> result = doc_bot.process_query(query)
        >>> print(result)
        >>> print(result["Total_Tokens"])
        
        """
        self.file_paths = file_paths
        self.text_input = text_input
        self.main_documents = []
        os.environ["OPENAI_API_KEY"] = openAI_api_key
        self.load_documents()
        self.initialize_models()
    def load_documents(self):
        """
        Load the documents from the specified paths.

        """
        if self.file_paths:
            for file_path in self.file_paths:
                file_extension = file_path.split(".")[-1].lower()
                if file_extension == "pdf":
                    loader = PyPDFLoader(file_path)
                elif file_extension == "docx":
                    loader = Docx2txtLoader(file_path)
                elif file_extension == "txt":
                    loader = TextLoader(file_path)
                elif file_extension == "py":
                    loader = PythonLoader(file_path)
                elif file_extension == "ipynb":
                    loader = NotebookLoader(file_path)
                self.main_documents.extend(loader.load_and_split())
        if "https://www.youtube" in self.text_input:
            loader=YoutubeLoader.from_youtube_url(youtube_url=self.text_input,add_video_info=True)
            self.main_documents.extend(loader.load_and_split())
        elif self.text_input != "None":
            loader=WikipediaLoader(self.text_input)
            self.main_documents.extend(loader.load_and_split())
        else:
            pass



        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        self.splited_document = text_splitter.split_documents(self.main_documents)
        print(self.splited_document)
    def initialize_models(self):   
        """
        Initialize the models for the DocBot.
        """
        
        self.vectordb = Chroma.from_documents(documents=self.splited_document, embedding=OpenAIEmbeddings())
        self.pdf_qa = ConversationalRetrievalChain.from_llm(
            llm=ChatOpenAI(temperature=0.4, model_name="gpt-3.5-turbo-16k"),
            retriever=self.vectordb.as_retriever(search_kwargs={'k': 7}),
            verbose=True,
            condense_question_llm = ChatOpenAI(temperature=0, model='gpt-3.5-turbo')
        )
    def process_query(self, query:str):
        """
        Process the query and return the result.

        Args:
            query (str): The query to be processed.

        Returns:
            dict: The result of the query.
        """
        
        chat_history=[]
        with get_openai_callback() as cb:
            result = self.pdf_qa({"question": query+" Context","chat_history":chat_history})
            try:
                self.vectordb.delete_collection()
            except:
                pass
            return {
                "question": query,
                "result": result,
                "Total_Tokens": cb.total_tokens,
                "Total_Cost_(USD)": cb.total_cost
            }


#example usage open ai api = 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 and path "https://raw.githubusercontent.com/smaameri/multi-doc-chatbot/91e63f6dd2dbc6f1493d6595583c230372a975dc/docs/JuanGarciaCV.txt"
#deneme

# Create an instance of the PandasDataFrameAgent class
#api_key = "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"
#data_file_path = "https://gist.githubusercontent.com/stungeye/a3af50385215b758637e73eaacac93a3/raw/c1f936ae9dedc4d80398e6c11dbc95835c3c8f20/movies.csv"
#data_agent = PandasDataFrameAgent(api_key, data_file_path)
#query = "Group the total number of changing years into groups of 10. Add the duration sum values of all groups. Visualize with a bar chart"
#result = data_agent.run_query(query)
#print(result)
#print(result["Total_Tokens"])
# Create an instance of the DocBot class


# Constants and configurations
import google.generativeai as genai 
import re
import discord
genai.configure(api_key="AIzaSyDr7Ey5Nx8Vlb2jN5JTlhMnX8lkSJnZuWI")
text_generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 512,
}
image_generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 512,
}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
]
text_model = genai.GenerativeModel(model_name="gemini-pro", generation_config=text_generation_config, safety_settings=safety_settings)
image_model = genai.GenerativeModel(model_name="gemini-pro-vision", generation_config=image_generation_config, safety_settings=safety_settings)
message_history = {}
MAX_HISTORY = 15
SUPPORTED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
RESPONSE_CHAR_LIMIT = 1700

#---------------------------------------------AI Generation History-------------------------------------------------       
async def generate_response_with_text(message_text):
    prompt_parts = [message_text]
    print("Got textPrompt: " + message_text)
    response = text_model.generate_content(prompt_parts)
    if(response._error):
        return "❌" +  str(response._error)
    return response.text

async def generate_response_with_image_and_text(image_data, text):
    image_parts = [{"mime_type": "image/jpeg", "data": image_data}]
    prompt_parts = [image_parts[0], f"\n{text if text else 'What is this a picture of?'}"]
    response = image_model.generate_content(prompt_parts)
    if(response._error):
        return "❌" +  str(response._error)
    return response.text

#---------------------------------------------Message History-------------------------------------------------
def update_message_history(user_id, text):
    # Check if user_id already exists in the dictionary
    if user_id in message_history:
        # Append the new message to the user's message list
        message_history[user_id].append(text)
        # If there are more than 12 messages, remove the oldest one
        if len(message_history[user_id]) > MAX_HISTORY:
            message_history[user_id].pop(0)
    else:
        # If the user_id does not exist, create a new entry with the message
        message_history[user_id] = [text]
        
def get_formatted_message_history(user_id):
    """
    Function to return the message history for a given user_id with two line breaks between each message.
    """
    if user_id in message_history:
        # Join the messages with two line breaks
        return '\n\n'.join(message_history[user_id])
    else:
        return "No messages found for this user."
    
#---------------------------------------------Sending Messages-------------------------------------------------
async def split_and_send_messages(message_system, text, max_length):

    # Split the string into parts
    messages = []
    for i in range(0, len(text), max_length):
        sub_message = text[i:i+max_length]
        messages.append(sub_message)

    # Send each part as a separate message
    for string in messages:
        await message_system.channel.send(string)    

def clean_discord_message(input_string):
    # Create a regular expression pattern to match text between < and >
    bracket_pattern = re.compile(r'<[^>]+>')
    # Replace text between brackets with an empty string
    cleaned_content = bracket_pattern.sub('', input_string)
    return cleaned_content  

async def is_supported_image(filename):
    return filename.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS)


async def download_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            return await response.read()


async def process_image_attachment(message, cleaned_text):
    for attachment in message.attachments:
        if await is_supported_image(attachment.filename):
            await message.add_reaction('🎨')
            image_data = await download_image(attachment.url)
            if image_data is None:
                await message.channel.send('Unable to download the image.')
                return
            response_text = await generate_response_with_image_and_text(image_data, cleaned_text)
            await split_and_send_messages(message, response_text, RESPONSE_CHAR_LIMIT)


async def process_text_message(message, cleaned_text):
    if "RESET" in cleaned_text:
        if message.author.id in message_history:
            del message_history[message.author.id]
        await message.channel.send(f"🤖 History Reset for user: {message.author.name}")
        return

    await message.add_reaction('💬')
    if MAX_HISTORY == 0:
        response_text = await generate_response_with_text(cleaned_text)
    else:
        update_message_history(message.author.id, cleaned_text)
        response_text = await generate_response_with_text(get_formatted_message_history(message.author.id))
        update_message_history(message.author.id, response_text)

    await split_and_send_messages(message, response_text, RESPONSE_CHAR_LIMIT)


async def handle_message(message,client):
    if message.author == client.user:
        return

    if client.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        cleaned_text = clean_discord_message(message.content)
        async with message.channel.typing():
            if message.attachments:
                await process_image_attachment(message, cleaned_text)
            else:
                await process_text_message(message, cleaned_text)
