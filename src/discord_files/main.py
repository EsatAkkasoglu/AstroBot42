import os 
import sys
import csv
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd 
import asyncio
import time
import json
sys.path.append('')
from datetime import datetime ,timezone,timedelta
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

# Create instances of CsvManager
auto_news_manager = database.local_save.CsvManager("database/csv/auto_news.csv")

@tasks.loop(hours=24)
async def send_autos(client):
    channel_infos = await auto_news_manager.read_channel_list()
    for channel_info in channel_infos:
        server_id = channel_info['server_id']
        channel_id = channel_info['channel_id']
        channel = client.get_channel(int(channel_id))
        if channel and isinstance(channel, discord.ForumChannel):
            today_date = datetime.now().strftime('%d %B %Y')
            thread_name = f"News on {today_date}"
            try:
                apod_embed, apod_view = await async_func.apod_non_interaction()
                subheading, initial_message = await channel.create_thread(name=thread_name, embed=apod_embed)
                await auto_news_manager.update_channel_info(server_id, channel_info['server_name'], channel_id, subheading.id, channel_info['user_name'])
            except discord.Forbidden:
                error_msg=f"Failed to post in channel {channel_id}: insufficient permissions."
                Logger.error(error_msg)
            except discord.HTTPException as e:
                Logger.error(f"Failed to post in channel {channel_id}: {e}")
        else:
            Logger.error(f"Channel with ID {channel_id} not found or not a forum channel on {server_id}.")
            await auto_news_manager.remove_channel(channel_id)
        await asyncio.sleep(1)
local_save= database.local_save
# Dictionary to store news from all feeds

# Send the news items in a formatted way using thread
async def send_news(thread):
    # Load seen news items from the CSV file
    seen_news_links = set()
    if os.path.exists(local_save.news_csv_file):
        with open(local_save.news_csv_file, mode='r', newline='') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                seen_news_links.add(row['link'])

    all_news = {}

    for source, url in local_save.rss_urls.items():
        new_news_items = []
        news_items = local_save.fetch_news(url)
        for item in news_items:
            if item['link'] not in local_save.seen_news and item['link'] not in seen_news_links:
                new_news_items.append(item)
                local_save.seen_news.add(item['link'])

        all_news[source] = new_news_items

    # Save the news data as a JSON file
    with open(local_save.news_csv_file, 'w') as json_file:
        json.dump(list(local_save.seen_news), json_file)


    if all_news:
        for source, news_items in all_news.items():
            if news_items:  # Check if there are new news items
                message = f""
                for i, item in enumerate(news_items[:5], 1):
                    message += f"{i}. **{item['title']}**\n   Link: {item['link']}\n   Published: {item['published']}\n"
                await thread.send(message)
                await asyncio.sleep(1)  # Sleep to avoid rate limits, adjust as necessary
            else:
                # Optionally, you can send a message that there are no new news items.
                # await thread.send(f"No new news items from {source}.")
                pass
    else:
        # Log or handle the case when there are no news items at all
        Logger.info("No news items to send.")

@tasks.loop(hours=6)
async def send_good_morning(client):


    channel_infos = await auto_news_manager.read_channel_list()
    for channel_info in channel_infos:
        server_id = channel_info['server_id']
        thread_id = channel_info['thread_id']
        thread = client.get_channel(int(thread_id))
        if thread and isinstance(thread, discord.Thread):
            try:
                await send_news(thread)
            except discord.Forbidden:
                Logger.error(f"Failed to post in thread {thread_id}: insufficient permissions.")
            except discord.HTTPException as e:
                Logger.error(f"Failed to post in thread {thread_id}: {e}")
        else:
            Logger.error(f"Thread with ID {thread_id} not found or not a thread on {server_id}.")
            await auto_news_manager.remove_channel(thread_id)

#Calculate the time until 5 o'clock UTC
now = datetime.now(timezone.utc)
five_oclock_utc = now.replace(hour=5, minute=0, second=0, microsecond=0)
if now >= five_oclock_utc:
    five_oclock_utc += timedelta(days=1)
time_until_five = (five_oclock_utc - now).total_seconds()
@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord!')
    Logger.info(f'{client.user.name} has connected to Discord!')
    try:
        synced = await client.tree.sync()
        Logger.info(f"synced {len(synced)} command(s)")
        send_autos.after_loop(client.wait_until_ready)
        send_autos.change_interval(seconds=time_until_five)
        send_autos.start(client)  # Start the task
        send_good_morning.start(client)
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
  await async_func.object_query(interaction,object_names,city,date)

#####FROM FILE TO EMBED  ###########################################
@client.tree.command(name="object_info_from_file",
                      description="Sends information on the object. Star,Black Hole,Planet,Pulsars etc.")
async def object_info_from_file(interaction: discord.Interaction, file: discord.Attachment, object_header: int = 0, epoch_header: str = "Epoch", period_header: str = "Period", city: str = "Istanbul", date: str = None):
  await async_func.object_info_from_file(interaction,file,object_header,epoch_header,period_header,city,date)

#####APOD  ###########################################
@client.tree.command(name='apod', description='Returns the Astronomy Picture Of The Day')
@app_commands.describe(date="Date for APOD. Default: NOW. Accepts YYYY-MM-DD format or 'random'")
async def apod(interaction: discord.Interaction, date: str = None):
  await async_func.apod_interaction(interaction,date)
#####SERVER INFO  ###########################################
@client.tree.command(name="serverinfo",
                     description="Sends information on the server")
async def serverinfo(interaction: discord.Interaction):
  await async_func.serverinfo(interaction,client=client)

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

print(discord_token)
client.run(discord_token)