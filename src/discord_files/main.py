import os 
import sys
import re
import io
import aiohttp
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd 
import asyncio
sys.path.append('')
from src.log_files import logger
from dotenv import load_dotenv
load_dotenv("config.env")
from src.Astro_files import queryFunctions as qf
from src.discord_files import async_functions as async_func
import src.openAI_functions.AI_functions as aiFunc
import discord
from discord import app_commands
from discord.ext import commands

discord_token=os.getenv("discord_token")  
Logger = logger.CustomLogger('astroclient', 'src\log_files\discord.log')
embed = discord.Embed()
client = commands.Bot(command_prefix="!", intents=discord.Intents.all())
# Configure the generative AI model



async def my_long_running_task():
    # Uzun süren işlemler burada yapılır
    await asyncio.sleep(10)  # Örnek olarak 10 saniye sürecek bir işlem

@client.event
async def on_ready():
  print(f'{client.user.name} has connected to Discord!')
  Logger.info(f'{client.user.name} has connected to Discord!')
  try:
      synced = await client.tree.sync()
      Logger.info(f"synced {len(synced)} command(s)")
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
#####SERVER INFO  ###########################################
@client.tree.command(name="serverinfo",
                     description="Sends information on the server")
async def serverinfo(interaction: discord.Interaction):
  await async_func.serverinfo(interaction,client=client)

#####HELP  ###########################################
@client.tree.command(name="help", description="Shows the help menu")
async def help(interaction: discord.Interaction):
  await async_func.help(interaction,client)


print(discord_token)
client.run(discord_token)