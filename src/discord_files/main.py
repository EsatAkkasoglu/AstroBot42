import os 
import sys
import csv
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd 
import asyncio
import time
sys.path.append('')
from datetime import datetime ,timezone,timedelta,time
from src.log_files import logger
from dotenv import load_dotenv
load_dotenv("config.env")
from src.Astro_files import queryFunctions as qf
from src.discord_files import async_functions as async_func
import src.openAI_functions.AI_functions as aiFunc
import database.local_save 
import discord
from discord import Activity, ActivityType, Status,app_commands
from discord.ext import commands,tasks
from itertools import cycle

discord_token=os.getenv("discord_token")  
Logger = logger.CustomLogger('astroclient', 'src/log_files/discord.log')
embed = discord.Embed()
client = commands.Bot(command_prefix="!", intents=discord.Intents.all())
# Configure the generative AI model


async def my_long_running_task():
    # Uzun süren işlemler burada yapılır
    await asyncio.sleep(10)  # Örnek olarak 10 saniye sürecek bir işlem


activities = cycle([
    [0, 'With the stars'], [2, 'The Sounds Of The Universe'], [3, 'Cosmos'],
    [0, 'With a bunch of Neutron stars'], [2, '/help'],
    [3, 'How The Universe Works'], [0, 'Life of A Star'],
    [2, 'Richard Feynman talk about bongos'], 
    [3, 'Milky Way and Andromeda collide'], 
    [3, 'The James Webb Space Telescope'], [2, 'Your .iss requests']
])

@tasks.loop(hours=6)
async def set_activity(client):
    global activities

    activity_type, activity_name = next(activities)

    if activity_type == 0:
        activity = Activity(type=ActivityType.playing, name=activity_name)
    elif activity_type == 2:
        activity = Activity(type=ActivityType.listening, name=activity_name)
    elif activity_type == 3:
        activity = Activity(type=ActivityType.watching, name=activity_name)
    else:
        activity = Activity(type=ActivityType.custom, name=activity_name)

    await client.change_presence(status=Status.idle, activity=activity)

def call_set_activity(client):
    if not set_activity.is_running():
        set_activity.start(client)

# Create loop for auto thread 
auto_news_manager = database.local_save.CsvManager("database/csv/auto_news.csv")
apod_time=time(hour=6, minute=51, second=0,tzinfo=timezone.utc)
@tasks.loop(time=apod_time)
async def send_autos(client):
    channel_infos = await auto_news_manager.read_channel_list()
    for channel_info in channel_infos:
        server_id = channel_info['server_id']
        channel_id = channel_info['channel_id']
        channel = client.get_channel(int(channel_id))
        if channel and isinstance(channel, discord.ForumChannel):
            today_date = datetime.utcnow().strftime('%d %B %Y')
            thread_name = f"News on {today_date}"
            try:
                apod_embed, apod_view = await async_func.apod_non_interaction()
                subheading, initial_message = await channel.create_thread(name=thread_name, embed=apod_embed)
                await auto_news_manager.update_channel_info(server_id, channel_info['server_name'], channel_id, subheading.id, channel_info['user_name'])
                Logger.info(f"Created thread {subheading.id} on {server_id} for {channel_id}")
            except discord.Forbidden:
                error_msg=f"Failed to post in channel {channel_id}: insufficient permissions."
                Logger.error(error_msg)
            except discord.HTTPException as e:
                Logger.error(f"Failed to post in channel {channel_id}: {e}")
        else:
            Logger.error(f"Channel with ID {channel_id} not found or not a forum channel on {server_id}.")
            await auto_news_manager.remove_channel(channel_id)

# Create an loop of NewsManager     
self_news = async_func.NewsManager(database.local_save) 
@tasks.loop(hours=6)
async def send_per6_hours_news(client):
    channel_infos = await auto_news_manager.read_channel_list()
    news_tasks = []  # List to hold coroutine objects
    for channel_info in channel_infos:
        thread_id = channel_info['thread_id']
        thread = client.get_channel(int(thread_id))
        if thread and isinstance(thread, discord.Thread):
            # Create coroutine object and add to the tasks list
            task = async_func.NewsManager.send_news(self_news,thread=thread, unsent_news_csv="database/csv/unset_news.csv")
            task1=async_func.NewsManager.remove_duplicate_rows_async(self_news,'database/csv/news_links.csv')
            news_tasks.append(task)
            news_tasks.append(task1)
            # lOGGER INFO
            Logger.info(f'Sent news at {datetime.now()} on ThreadID: {thread_id} | ThreadName: {thread.name} | ServerID: {channel_info["server_id"]} | ServerName: {channel_info["server_name"]}')
        else:
            Logger.error(f"Thread with ID {thread_id} not found or not a thread.")
    
    # Check if tasks list is not empty before calling asyncio.gather
    if news_tasks:
        await asyncio.gather(*news_tasks)
    else:
        Logger.error("No tasks to execute.")

#send daily link    
link_time= time(hour=13, minute=50, second=0,tzinfo=timezone.utc)
@tasks.loop(time=link_time)
async def send_daily_link(client):
    """Send one news article per day"""
    links_tasks = []  # List to hold coroutine objects
    channel_infos = await auto_news_manager.read_channel_list()
    for channel_info in channel_infos:
        thread_id = channel_info['thread_id']
        thread = client.get_channel(int(thread_id))
        if thread and isinstance(thread, discord.Thread):
            # Create coroutine object and add to the tasks list
            task = async_func.send_daily_links(thread=thread)
            links_tasks.append(task)
            # lOGGER INFO
            Logger.info(f'Sent daily links at {datetime.now()} on ThreadID: {thread_id} | ThreadName: {thread.name} | ServerID: {channel_info["server_id"]} | ServerName: {channel_info["server_name"]}')
        else:
            Logger.error(f"Thread with ID {thread_id} not found or not a thread.")
    if links_tasks:
        await asyncio.gather(*links_tasks)
    else:
        Logger.error("No tasks to execute.")
@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord!')
    Logger.info(f'{client.user.name} has connected to Discord!')
    try:
        synced = await client.tree.sync()
        Logger.info(f"synced {len(synced)} command(s)")
        send_autos.start(client)  # Start the task
        send_per6_hours_news.start(client)
        send_daily_link.start(client)
        call_set_activity(client)
    except Exception as e:
        Logger.error(f"error syncing commands: {e}")


@client.event
async def on_message(message):
  if "hello there" in message.content.lower():
    embed.set_image(url="https://i.pinimg.com/originals/b2/33/a5/b233a5ecc876839556a3914b077d8e14.gif"),
    msg= await message.channel.send(embed=embed) 
    await msg.add_reaction("🫡")
  elif "captain amarika" in message.content.lower() or "kaptan amerika" in message.content.lower():
    embed.set_image(url="https://media2.giphy.com/media/tnYri4n2Frnig/giphy.gif")
    msg=await message.channel.send(embed=embed)
    await msg.add_reaction("🛡️")
  elif "unlimited power" in message.content.lower():
    embed.set_image(url="https://i.giphy.com/media/hokMyu1PAKfJK/giphy.gif")
    msg=await message.channel.send(embed=embed)
    await msg.add_reaction("⚡")
  elif "gandalf" in message.content.lower()  or "white beard" in message.content.lower() or "beyaz sakal" in message.content.lower():
    embed.set_image(url="https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExMmQ0MDNmMWYzMjE5NmY2OTRiM2JmZGQxZmY1NjRlMGJjM2JlNjMxNSZlcD12MV9pbnRlcm5hbF9naWZzX2dpZklkJmN0PWc/TcdpZwYDPlWXC/giphy.gif")
    msg=await message.channel.send(embed=embed)
    await msg.add_reaction("🧙")
  elif "may the force be with you"in message.content.lower() or "star wars"in message.content.lower():
    embed.set_image(url="https://media.tenor.com/kRYZCtb8R1MAAAAC/sw-starwars.gif")
    msg=await message.channel.send(embed=embed)
    await msg.add_reaction("🪐")
  elif "voldemort" in message.content.lower():
    embed.set_image(url="https://i.giphy.com/media/LLxwPAjfpLak8/giphy.gif")
    msg=await message.channel.send(embed=embed)
    await msg.add_reaction("🐍")
  elif "dark side" in message.content.lower():
    embed.set_image(url="https://media.tenor.com/zTPgy19_A4wAAAAC/star-wars-dark-side.gif")
    msg=await message.channel.send(embed=embed)
    await msg.add_reaction("🌑")
  elif "this is where the fun begins" in message.content.lower():
    embed.set_image(url="https://giphy.com/gifs/star-wars-han-solo-rHR8qP1mC5V3G?utm_source=media-link&utm_medium=landing&utm_campaign=Media%20Links&utm_term=")
    msg=await message.channel.send(embed=embed)
    await msg.add_reaction("🤠")
  elif "good soldiers follow orders" in message.content.lower():
    embed.set_image(url="https://media.tenor.com/TB6fbPYApQEAAAAC/good-soldiers-starwars.gif")
    msg=await message.channel.send(embed=embed)
    await msg.add_reaction("👮")
  elif "this is the way" in message.content.lower():
    embed.set_image(url="https://media1.giphy.com/media/6UFgdU9hirj1pAOJyN/giphy.gif?cid=ecf05e47f1njz98vcxzxk05jqpliunerc6t7taqwzhdv3mgl&rid=giphy.gif&ct=g")
    msg=await message.channel.send(embed=embed)
    await msg.add_reaction("👽")
  elif "dumbledore" in message.content.lower():
    embed.set_image(url="https://c.tenor.com/2lCoAAOAvUsAAAAC/dumbledore-frustrated.gif")
    msg=await message.channel.send(embed=embed)
    await msg.add_reaction("🧙")
  elif "jon snow" in message.content.lower():
    embed.set_image(url="https://giphy.com/gifs/jon-snow-ygritte-you-know-nothing-NCTbhL8AG2s8g?utm_source=media-link&utm_medium=landing&utm_campaign=Media%20Links&utm_term=")
    msg=await message.channel.send(embed=embed)
    await msg.add_reaction("🫅")

  # Ignore messages sent by the client
  if message.author == client.user:
      return
  # Check if the client is mentioned or the message is a DM
  if client.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
    await aiFunc.handle_message(message,client)
  await client.process_commands(message)




#-----QUERY FUNCTIONS-------------------------
  
#####SolarSystemObjects ###########################################
@client.tree.command(name="object_query",
                      description="Sends information on the object. Star,Black Hole,Planet,Pulsars etc.")
@app_commands.describe(object_names="List of objects. Delimiter must be one of `, ; |`. ACCEPTS SINGLE INPUT"
                      ,city="City name for visibility plot. Default: Istanbul"
                      ,date="Date for visibility plot. Default: NOW "
)
async def object_query(interaction: discord.Interaction,object_names:str,city:str="Istanbul",date:str = None):
  query_task=[]
  query_task.append(async_func.object_query(interaction,object_names,city,date))
  await asyncio.gather(*query_task)

#####FROM FILE TO EMBED  ###########################################
@client.tree.command(name="object_info_from_file",
                      description="Sends information on the object. Star,Black Hole,Planet,Pulsars etc.")
async def object_info_from_file(interaction: discord.Interaction, file: discord.Attachment, object_header: int = 0, epoch_header: str = "Epoch", period_header: str = "Period", city: str = "Istanbul", date: str = None):
  from_file_task=[]
  from_file_task.append(async_func.object_info_from_file(interaction,file,object_header,epoch_header,period_header,city,date))
  await asyncio.gather(*from_file_task)

#####APOD  ###########################################
@client.tree.command(name='apod', description='Returns the Astronomy Picture Of The Day')
@app_commands.describe(date="Date for APOD. Default: NOW. Accepts YYYY-MM-DD format or 'random'")
async def apod(interaction: discord.Interaction, date: str = None):
  await async_func.apod_interaction(interaction,date)

##### ZENITH PLOT  ##########################################
@client.tree.command(name="zenith_plot", description="Plots the zenith of the celestial object")
async def zenith_plot(interaction: discord.Interaction, city: str = "Istanbul", date: str = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"):
  await async_func.zenith_plot(interaction,city,date)
#####SERVER INFO  ###########################################
@client.tree.command(name="serverinfo",
                     description="Sends information on the server")
async def serverinfo(interaction: discord.Interaction):
  await async_func.serverinfo(interaction,client=client)

##### FUNNY  ###########################################
import Levenshtein as lev
def closest_match(input_str, possibilities):
    closest = None
    min_distance = float('inf')
    for possibility in possibilities:
        distance = lev.distance(input_str.lower(), possibility.lower())
        if distance < min_distance:
            min_distance = distance
            closest = possibility
    return closest
@client.tree.command(name="weight_on_planets", description="Calculate your weight on different celestial bodies")
async def weight_on_planets(interaction: discord.Interaction, earth_weight: float, celestial_body: str):
    celestial_body = closest_match(celestial_body,  qf.GRAVITY.keys())
    celestial_bodies = [celestial_body]  # Since the function expects a list
    weights = await qf.calculate_weight_on_celestial_bodies(earth_weight, celestial_bodies)

    if weights[celestial_body] == "Unknown celestial body":
        await interaction.response.send_message(f"Sorry, I don't have data for {celestial_body}.", ephemeral=False)
    else:
        weight = weights[celestial_body]
        await interaction.response.send_message(f"Your weight on {celestial_body} would be approximately {weight:.2f} kg.", ephemeral=False)

#####HELP  ###########################################
@client.tree.command(name="help", description="Shows the help menu")
async def help(interaction: discord.Interaction):
  await async_func.help(interaction,client)

@client.event
async def on_slash_command_error(ctx, error):
  if isinstance(error,commands.CommandOnCooldown):
    embed = discord.Embed(title = "UPSS", description = f"Something went wrong! But don't worry, we've logged this error! I hope it gets resolved!")
    await ctx.response.send_message(embed = embed)
  else:
    print(error)

async def main():
  await client.start(discord_token)


asyncio.run(main())