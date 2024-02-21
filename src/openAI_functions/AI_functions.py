import os  # Import the os module for setting environment variables
import aiohttp
import io
import sys
from PIL import Image
import pandas as pd
import matplotlib.pyplot as plt


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
