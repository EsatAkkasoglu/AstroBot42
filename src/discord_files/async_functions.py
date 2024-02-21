import os 
import sys
import re
import io
import warnings
import math
import asyncio
import time
import numpy as np
import pandas as pd 
import csv
import aiohttp
import feedparser
import datetime
from io import BytesIO
from random import randrange
from requests import get
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from time import mktime, strftime
sys.path.append('')
from astropy.time import Time
from src.log_files import logger
from src.Astro_files import queryFunctions as qf
import database.local_save
import discord
from discord import app_commands
from discord.ui import Button,View,Modal,TextInput
Logger = logger.CustomLogger('astrobot', 'src/log_files/async_discord.log')


#test qf.SolarSystemObjects(object_name).get_formatted_data()

import discord
import re
import time

async def object_query(interaction: discord.Interaction, object_names: str, city: str = "Istanbul", date: str = None):
    await interaction.response.defer()
    delimiter = ",;|"
    object_names = re.split(f"[{re.escape(delimiter)}]", object_names)
    observer_input, local_time = await qf.get_observer_and_local_time(city)

    for object_name in object_names:
        embed, files = await process_object(interaction, object_name.strip(), observer_input, local_time, date,city)
        msg = await interaction.followup.send(embed=embed, files=files)
        await add_reactions(msg)

async def process_object(interaction, object_name, observer_input, local_time, date,city):
    start_time = time.time()
    AstroCom_logo_file = discord.File("database/images/logos/AstroCom_logo.png", filename="AstroCom_logo.png")
    embed = discord.Embed(title=f"Information for {object_name.capitalize()}", color=discord.Color.blurple(), timestamp=local_time)
    embed.set_footer(text="By AstroCom",icon_url=f"attachment://{AstroCom_logo_file.filename}")
    try:
        return_dict, is_simbad_data = await fetch_object_data(object_name)
        files = await prepare_embed(embed, return_dict, object_name, observer_input, date, is_simbad_data, AstroCom_logo_file)
    except Exception as e:
        handle_exception(embed, e, object_name, interaction)
        files = [AstroCom_logo_file]

    end_time = time.time()
    log_query_info(interaction, object_name, city, start_time, end_time)
    return embed, files

async def fetch_object_data(object_name):
    try:
        return_dict = await qf.SolarSystemObjects(object_name).get_formatted_data()
        return return_dict, False
    except:
        return_dict = await qf.get_object_info_simbad(object_name)
        return return_dict, True

async def prepare_embed(embed, return_dict, object_name, observer_input, date, is_simbad_data, AstroCom_logo_file):
    files = [AstroCom_logo_file]
    object_ra, object_dec = None, None

    for key, value in return_dict.items():
        embed.add_field(name=value['definition'] if not is_simbad_data else key.capitalize(), 
                        value=f"**{value['symbol']}:** {value['value']} {value['unit']}" if not is_simbad_data else f"{value:.3f}" if isinstance(value, float) else str(value), 
                        inline=True)
        if key in ("ra_hms", "ra"):
            object_ra = value['value'] if not is_simbad_data else value
        if key in ("dec_dms", "dec"):
            object_dec = value['value'] if not is_simbad_data else value
    
    # Generate altitude plot if coordinates are available
    if object_dec and object_ra:
        visibility_image = await qf.create_altitude_plot(object_name, RA=object_ra, DEC=object_dec, observer=observer_input, date=date)
        visibility_file = discord.File(visibility_image, filename=f"{object_name.upper()}_visibility_plot.png")
        embed.set_image(url=f"attachment://{visibility_file.filename}")
        files.append(visibility_file)

        if is_simbad_data:
            # Additional handling for SIMBAD data, if needed
            area_image = await qf.create_area_image(object_name, RA=object_ra, DEC=object_dec)
            area_file = discord.File(area_image, filename=f"{object_name.upper()}_area_plot.png")
            embed.set_thumbnail(url=f"attachment://{area_file.filename}")
            files.append(area_file)

    return files

def handle_exception(embed, e, object_name, interaction):
    embed.clear_fields()
    embed.title = f"Error for {object_name.capitalize()}"
    embed.color = discord.Color.red()
    embed.add_field(name="Error Occurred", value=f"An error occurred while processing the object '{object_name}'. Please check the object name and try again.\n**Error:** {e}", inline=False)
    Logger.error(f"object_query for {object_name.upper()} by {interaction.user.name}({interaction.user.id})\n ERROR: {e}")

def log_query_info(interaction, object_name, city, start_time, end_time):
    elapsed_time = end_time - start_time
    Logger.info(
        f"\nCommand: 'object_query'\n"
        f"Query: '{object_name}' + '{city}'\n"
        f"User: {interaction.user.name} (ID: {interaction.user.id})\n"
        f"Channel: {interaction.channel.name} (ID: {interaction.channel.id})\n"
        f"Elapsed Time: {elapsed_time:.2f} seconds\n"
        f"Server: {interaction.guild.name} (ID: {interaction.guild.id})\n"
        f"{'*'*50}"
    )

async def add_reactions(msg):
    reactions = ["🪐", "⭐", "💖"]
    for reaction in reactions:
        await msg.add_reaction(reaction)

async def object_info_from_file(interaction: discord.Interaction, file: discord.Attachment, object_header: int = 0, epoch_header: str = "Epoch", period_header: str = "Period", city: str = "Istanbul", date: str = None):
  # File extension check
  await interaction.response.defer()
  start_time = time.time()
  file_extension = file.filename.split(".")[-1]
  if file_extension not in ["csv", "xlsx"]:
      await interaction.followup.send("Please upload a csv or excel file.")
      return
  observer_input,local_time= await qf.get_observer_and_local_time(city)
  # Read the file into a DataFrame
  main_df = pd.read_csv(io.BytesIO(await file.read()), header=object_header) if file_extension == "csv" else pd.read_excel(io.BytesIO(await file.read()), header=object_header)

  # Get astronomical data
  sun_data = await qf.get_sunset_sunrise(observer_input, date)
  sun_set, sun_rise, night_duration, day_duration = sun_data.sunset, sun_data.sunrise, sun_data.night_duration, sun_data.day_duration

  # Iterate over object names
  for object_name in main_df.iloc[:, object_header].dropna():
      # Filter the dataframe based on the object name
      object_row = main_df[main_df.iloc[:, object_header] == object_name]

      # Check if a row for the object name exists

      # Access epoch and period values
      epoch, period = object_row[epoch_header].values[0], object_row[period_header].values[0]

      # Adjust epoch
      if epoch < 2400000:
        epoch += 2400000

      # Perform calculations for the observation
      sunrise_jd, sunset_jd = sun_rise.jd, sun_set.jd

      # Calculate phase values
      sunset_min_phase = (sunset_jd - epoch) / period
      sunrise_min_phase = (sunrise_jd - epoch) / period
      total_phase = sunrise_min_phase - sunset_min_phase
      first_min_phase = (math.ceil(sunset_min_phase) * period) + epoch
      end_min_phase = first_min_phase+ period 
      while (end_min_phase+period) < sunrise_jd:
        print(f"{object_name.upper()} added")
        end_min_phase += period
    
      # Get additional information from Simbad
      simbad_dict =await qf.get_object_info_simbad(object_name)

      # Update DataFrame with calculated valuesd
      main_df.loc[main_df.iloc[:, object_header] == object_name, "sunset_nautical_dawn"] = sun_set.datetime
      main_df.loc[main_df.iloc[:, object_header] == object_name, "sunrise_nautical_dawn"] = sun_rise.datetime
      main_df.loc[main_df.iloc[:, object_header] == object_name, "sunset_min_phase"] = sunset_min_phase
      main_df.loc[main_df.iloc[:, object_header] == object_name, "sunrise_min_phase"] = sunrise_min_phase
      main_df.loc[main_df.iloc[:, object_header] == object_name, "total_phase"] = total_phase
      main_df.loc[main_df.iloc[:, object_header] == object_name, "first_min_phase_jd"] = first_min_phase
      main_df.loc[main_df.iloc[:, object_header] == object_name, "first_min_phase_date"]= Time(first_min_phase, format='jd', scale='utc').to_datetime()
      main_df.loc[main_df.iloc[:, object_header] == object_name, "end_min_phase_jd"] = end_min_phase
      main_df.loc[main_df.iloc[:, object_header] == object_name, "end_min_phase_date"]= Time(end_min_phase, format='jd', scale='utc').to_datetime()
      is_observable=await qf.is_observable_object(simbad_dict.get('ra'), simbad_dict.get('dec'), observer_input, date)
      main_df.loc[main_df.iloc[:, object_header] == object_name, "is_observable"] = is_observable
      #good for observation
      if first_min_phase<sunrise_jd  and 0.98<total_phase and sunset_min_phase:
        main_df.loc[main_df.iloc[:, object_header] == object_name, "good_for_observation"] = True
      else:
        main_df.loc[main_df.iloc[:, object_header] == object_name, "good_for_observation"] = False
        

  # Save DataFrame to a BytesIO CSV file
  main_file_buffer=BytesIO()
  main_df.to_csv(main_file_buffer,index=False)
  main_file_buffer.seek(0)
  observable_file_buffer=BytesIO()
  filtered_df = main_df[(main_df['is_observable'] == True)]
  filtered_df.to_csv(observable_file_buffer,index=False)
  observable_file_buffer.seek(0)
  observable_file=discord.File(observable_file_buffer,filename="observable_file.csv")
  
  main_file=discord.File(main_file_buffer,filename="main_file.csv")
  #visualisation
  sunset_sunrise_image=await qf.observable_star_sunset_sunrise(main_df)
  sunset_sunrise_file= discord.File(sunset_sunrise_image, filename=f"{local_time}_area_plot.png")

  embed = discord.Embed(title="🌟 Object Info From File", color=discord.Color.blurple(), timestamp=datetime.utcnow())
  embed.add_field(name="🌆 City", value=f"{observer_input.name}", inline=True)
  embed.add_field(name="🌇 Sunset", value=f"{(str(sun_set.iso).rsplit('.',1)[0])} ", inline=True)
  embed.add_field(name="🌅 Sunrise", value=f"{(str(sun_rise.iso).rsplit('.',1)[0])} ", inline=True)
  embed.add_field(name="🌃 Night Duration", value=f"{(str(night_duration.datetime).rsplit('.',1)[0])}", inline=True)
  embed.add_field(name="🌞 Day Duration", value=f"{(str(day_duration.datetime).rsplit('.',1)[0])}", inline=True)
  embed.add_field(name="🔭 Total Observable Objects", value=f"{len(filtered_df)}", inline=True)
  embed.add_field(name="🌌 Total Objects", value=f"{len(main_df)}", inline=True)
  embed.add_field(name="👀 Observable Objects", value=f"{len(filtered_df)/len(main_df)*100:.2f}%", inline=True)
  embed.add_field(name="📅 Date", value=f"{local_time.strftime('%d/%m/%Y')}", inline=True)
  embed.add_field(name="🕒 Time", value=f"{local_time.strftime('%H:%M:%S')}", inline=True)

  await interaction.followup.send(embed=embed,files=[main_file,observable_file,sunset_sunrise_file])
  end_time = time.time() 
  elapsed_time = end_time - start_time
  Logger.info(
  f"\nCommand: 'object_info_from_file'\n"
  f"Query: '{file}' + '{city}'\n"
  f"User: {interaction.user.name} (ID: {interaction.user.id})\n"
  f"Channel: {interaction.channel.name} (ID: {interaction.channel.id})\n"
  f"Elapsed Time: {elapsed_time:.2f} seconds\n"
  f"Server: {interaction.guild.name} (ID: {interaction.guild.id})\n"
  f"{'*'*50}"
  )


async def serverinfo(interaction: discord.Interaction,client):
  if interaction.response.is_done() == False:
      asyncio.sleep(2)
  await interaction.response.defer()
  guild = interaction.guild
  online = sum(m.status != discord.Status.offline for m in guild.members)

  embed = discord.Embed(
      title=f"{guild.name} Server Info 🌟",
      description=f"Details about **{guild.name}**",
      color=discord.Color.blue(), # Change color based on your preference
      timestamp=interaction.created_at)

  embed.set_footer(text=f"Server ID: {guild.id}", icon_url=guild.icon.url)

  embed.add_field(
      name="👥 Members",
      value=f"Total: {guild.member_count}\nOnline: {online} ({online/guild.member_count:.1%})")
  embed.add_field(
      name="📚 Channels",
      value=f"💬 {len(guild.text_channels)} Text | 🎤 {len(guild.voice_channels)} Voice | 🗣️ {len(guild.forums)} Forums",)
  embed.add_field(
      name="🌈 Roles",
      value=f"{len(guild.roles)} Total")
  embed.add_field(
      name="👑 Owner",
      value=guild.owner.mention)
  embed.add_field(
      name="📝 Description",
      value=guild.description or "No description.")
  embed.add_field(
      name="📅 Created At",
      value=guild.created_at.strftime("%a, %b %d, %Y, %I:%M %p UTC"))
  embed.add_field(
      name="🚀 Boost Status",
      value=f"Level {guild.premium_tier} with {guild.premium_subscription_count} Boosts")
  embed.add_field(
      name="🔒 Verification Level",
      value=str(guild.verification_level))
  embed.add_field(
      name="🔒 MFA Level",
      value=str(guild.mfa_level.name))
  embed.add_field(
      name="💖 Emoji Count",
      value=str(len(guild.emojis)))
  
  # Define buttons
  view = View()

  roles_button = Button(label="Show Roles", style=discord.ButtonStyle.green)
  view.add_item(roles_button)

  commands_button = Button(label="Show Commands", style=discord.ButtonStyle.blurple)
  view.add_item(commands_button)

  # Button callbacks
  async def on_roles_button_click(interaction: discord.Interaction):
      roles_description = "\n".join([f"- **{role.name}**" for role in interaction.guild.roles])
      await interaction.response.send_message(f"**Roles in {interaction.guild.name}:**\n{roles_description}", ephemeral=True)

  async def on_commands_button_click(interaction: discord.Interaction):
      commands_description = "\n".join([f"- `{command.name}`: {command.description}" for command in client.tree.get_commands()])
      await interaction.response.send_message(f"**Commands:**\n {commands_description}", ephemeral=True)

  roles_button.callback = on_roles_button_click
  commands_button.callback = on_commands_button_click
  msg = await interaction.followup.send(embed=embed, view=view)

  # Get custom emojis or default to a smile emoji
  custom_emojis = interaction.guild.emojis
  default_emoji = "😊"

  # Add each emoji as a reaction
  if custom_emojis:
    #insert 5 random emojis 
    for i in range(5):
      await msg.add_reaction(np.random.choice(custom_emojis))
  else:
      await msg.add_reaction(default_emoji)



async def help(interaction: discord.Interaction,client):
  await interaction.response.defer()
  commands = client.tree.get_commands()
  sorted_commands = sorted(commands, key=lambda c: c.name)
  embed = discord.Embed(title="Help",
                        description="Here's a list of commands you can use",
                        color=discord.Color.green())
  for command in sorted_commands:
    embed.add_field(name=f"**```/{command.name}```**",
                    value=command.description,
                    inline=False)
  await interaction.followup.send(embed=embed)

async def apod_dict(date: str = None):
    
    # If no specific date is given, use today's date or the stored daily date
    if date == None:
        #date=now make url now 
        calculated_date= await qf.DateCalculator().calculate_astropy_time(f"{datetime.utcnow()}")
        formatted_date = calculated_date.strftime("%y%m%d")

        url = f'https://apod.nasa.gov/apod/ap{formatted_date}.html'

    elif date.lower() == 'random':
        # Generate a random date between the start date and today
        start_date = datetime(1995, 6, 16)
        delta = mktime(datetime.now().timetuple()) - mktime(start_date.timetuple())
        random_date = datetime.utcfromtimestamp(mktime(start_date.timetuple()) + randrange(int(delta)))
        url = f'https://apod.nasa.gov/apod/ap{random_date.strftime("%y%m%d")}.html'
    else:
        # Convert the given date to the required format

        calculated_date = await qf.DateCalculator().calculate_astropy_time(date)
        formatted_date = calculated_date.strftime("%y%m%d")
        url = f'https://apod.nasa.gov/apod/ap{formatted_date}.html'

    # Request the webpage
    response = get(url)
    if not response.ok:
        return False

    soup = BeautifulSoup(response.text, 'lxml')

    apod_data = {
        'date': soup.find_all('p')[1].text.split('<')[0].strip(),
        'url':url,
        'video': bool(soup.find('iframe')),
        'title': f"{soup.find('b').text.strip()}",
        'image_link': '',
        'credits': '',
        'desc': soup.find_all('p')[2].text.replace('\n', ' ').strip().replace('Explanation:', '').strip(),

    }

    # Determine the link based on whether it's a video or image
    if apod_data['video']:
        apod_data['image_link'] = soup.find('iframe')['src']
    else:
        apod_data['image_link'] = 'https://apod.nasa.gov/apod/' + soup.find_all('a')[1]['href']

    # Extract credits
    credits_list = [f'[{i.text}]({i["href"]})' for i in soup.find_all('center')[1].findChildren() if i.name == 'a' and i.text != 'Copyright']
    apod_data['credits'] = ', '.join(credits_list)
    # Create the embed
    embed = discord.Embed(title=apod_data['title'], url=apod_data['url'], description=f"{apod_data['desc']}\nCredits: {apod_data['credits']}", color=discord.Color.orange(), timestamp=datetime.now())
    embed.set_footer(text=f"NASA-APOD", icon_url="https://gpm.nasa.gov/themes/pmm_bs/images/nasa-logo-large-v1.png")
        # Add image to the embed if it's not a video
    if not apod_data['video']:
        embed.set_image(url=apod_data['image_link'])
    return embed
#adding for discord embed 
# Function to create the APOD embed
async def create_apod_embed(embed, interaction:discord.Interaction):
    csv_manager = database.local_save.CsvManager('database/csv/auto_news.csv')
    file_exists = os.path.exists("database/csv/auto_news.csv")
    async def on_delete_button_click(interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            user = interaction.user
            guild = interaction.guild
            forum_channel_name = "news-📰"


            # Find the forum channel by name
            forum_channel = discord.utils.get(guild.channels, name=forum_channel_name, type=discord.ChannelType.forum)
            
            if forum_channel:
                try:
                    # Delete the forum channel
                    await csv_manager.remove_channel(forum_channel.id)
                    await forum_channel.delete(reason=f"Forum removal requested by {user.name}")
                    await interaction.response.send_message(f"🗑️ The forum '{forum_channel_name}' has been successfully deleted! 🎉", ephemeral=True)


                    # Confirm deletion to the user
                    await interaction.followup.send(f"✅ The forum '{forum_channel_name}' has been removed from automation and deleted.", ephemeral=True)
                    #log
                    Logger.info(f"Forum channel '{forum_channel_name}' deleted by {user} in {guild}.")
                except discord.Forbidden:
                    await interaction.response.send_message("❌ I do not have permissions to delete the forum.", ephemeral=True)
                except discord.HTTPException as e:
                    await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Could not find the forum named '{forum_channel_name}'.", ephemeral=True)

    async def on_forum_button_click(interaction: discord.Interaction):
        csv_manager = database.local_save.CsvManager('database/csv/auto_news.csv')
        file_exists = os.path.exists("database/csv/auto_news.csv")
        #if file not exist create file 
        if not file_exists:
            open("database/csv/auto_news.csv", "w")
        # Ensure that the interaction type is a button press and user has manage_messages permissions
        if interaction.type == discord.InteractionType.component and interaction.user.guild_permissions.manage_messages:
            user = interaction.user
            guild = interaction.guild
            forum_channel_name = "news-📰"

            # Try to find an existing forum channel by name
            forum_channel = discord.utils.get(guild.channels, name=forum_channel_name, type=discord.ChannelType.forum)


            # If the forum channel does not exist, create it
            if forum_channel is None:
                try:
                    forum_channel = await guild.create_forum(
                        name=forum_channel_name,
                        category=None, 
                        reason="Creating a forum channel for news",
                        topic="A forum channel for news",
                        nsfw=False,
                        default_reaction_emoji="📰",
                        default_auto_archive_duration=4320,
                        default_layout=discord.ForumLayoutType.gallery_view
                    )

                    thread_name = f"News on {datetime.utcnow().strftime('%d %B %Y')}"
                    # Use CsvManager to update the channel info
                    apod_embed, apod_view = await apod_non_interaction()
                    
                    subheading, initial_message = await forum_channel.create_thread(name=thread_name, embed=apod_embed)
                    await csv_manager.update_channel_info(guild.id, guild.name, forum_channel.id,subheading.id, user_name=user.name)
                    await interaction.response.send_message(f"✅ Forum channel '{forum_channel_name}' created!", ephemeral=True)
                    Logger.info(f"Forum channel '{forum_channel_name}' created by {user} in {guild}.")

                except discord.DiscordException as e:
                    await interaction.response.send_message(f"❌ Failed to create forum channel: {e}", ephemeral=True)
                    Logger.info(f"Failed to create forum channel '{forum_channel_name}' by {user} in {guild}.", exc_info=1)
                    return
            else:
                # Inform the user that the forum already exists
                await interaction.response.send_message(f"ℹ️ Forum channel '{forum_channel_name}' already exists.", ephemeral=True)
        else:
            # Inform the user that they don't have the required permissions
            await interaction.response.send_message("❌ You don't have permission to do that! ❌", ephemeral=True)
    # Define buttons
    view = View()
    btn_forum = Button(label="Adding NEWS Forum to get the news every day", style=discord.ButtonStyle.green)
    delete_button = Button(label="Remove this server from the list 🗑️", style=discord.ButtonStyle.red)

    # Assign callbacks
    delete_button.callback = on_delete_button_click
    btn_forum.callback = on_forum_button_click

    # Add buttons to the view
    view.add_item(btn_forum)
    view.add_item(delete_button)

    return embed, view
# Function to interact with the APOD command
async def apod_interaction(interaction: discord.Interaction, date: str = None):
    await interaction.response.defer()
    apod = await apod_dict(date)
    embed, view = await create_apod_embed(apod, interaction)
    await interaction.followup.send(embed=embed, view=view)

# Function to use APOD without interaction
async def apod_non_interaction(date: str = None):
    apod = await apod_dict(date)
    embed, view = await create_apod_embed(apod, None)
    return embed, view

class NewsManager:
    """
    Manages fetching, filtering, and sending news items.
    It interacts with local CSV files to keep track of seen and new news items.

    Attributes
    ----------
    local_save : database.local_save.LocalSave

    Methods
    -------
    fetch_and_filter_news(source, url, seen_news_links)
        Fetches news from a given URL and filters out already seen news links.
    send_news(ctx, channel, news_items, source)
        Sends the news to a specified channel and updates the CSV files accordingly.
    remove_duplicate_rows(input_csv_file)
        Removes duplicate rows from the specified CSV file.
    get_seen_news(source)
        Returns a list of seen news items for the specified source.
    ...
    
    """

    def __init__(self, database: database.local_save):
        self.local_save = database
    async def fetch_and_filter_news(self, source, url, seen_news_links):
        """
        Fetches news from a given URL and filters out already seen news links.
        """
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)
                    new_news_items = [item for item in feed.entries if item.link not in seen_news_links]
                    return source, new_news_items
                else:
                    Logger.warning(f"HTTP Error {response.status} for {url}")
                    return source, []

    async def send_news(self, thread, unsent_news_csv):
        """
        Sends the news to a specified thread and updates the CSV files accordingly.
        """
        seen_news_links = self._load_seen_news_links()
        tasks = [self.fetch_and_filter_news(source, url, seen_news_links) for source, url in self.local_save.rss_urls.items()]
        news_results = await asyncio.gather(*tasks)
        new_news_items = self._prepare_new_news_items(news_results, seen_news_links)
        self._save_news_items(new_news_items, unsent_news_csv, seen_news_links)
        await self._send_news_items(thread, unsent_news_csv)

    def _load_seen_news_links(self):
        """
        Loads seen news links from the local CSV file.
        """
        seen_news_links = set()
        if os.path.exists(self.local_save.news_csv_file):
            with open(self.local_save.news_csv_file, mode='r', newline='') as csv_file:
                csv_reader = csv.DictReader(csv_file)
                for row in csv_reader:
                    seen_news_links.add(row['link'])
        return seen_news_links

    def _prepare_new_news_items(self, news_results, seen_news_links):
        """
        Prepares new news items that are not in seen_news_links.
        """
        new_news_items = []
        for source, items in news_results:
            for item in items:
                if item['link'] not in seen_news_links:
                    new_news_items.append(item)
                    seen_news_links.add(item['link'])
        return new_news_items

    def _save_news_items(self, new_news_items, unsent_news_csv, seen_news_links):
        """
        Saves new unseen news items to the specified CSV files.
        """
        with open(unsent_news_csv, mode='w', newline='') as unsent_file, \
             open(self.local_save.news_csv_file, mode='a', newline='') as seen_file:
            unsent_writer = csv.DictWriter(unsent_file, fieldnames=['link', 'title', 'published'])
            seen_writer = csv.DictWriter(seen_file, fieldnames=['link', 'title', 'published'])
            
            unsent_writer.writeheader()
            seen_writer.writeheader()

            for item in new_news_items:
                unsent_writer.writerow({'link': item['link'], 'title': item['title'], 'published': item['published']})
                seen_writer.writerow({'link': item['link'], 'title': item['title'], 'published': item['published']})

    async def _send_news_items(self, thread, unsent_news_csv):
        """
        Sends the news items from the specified CSV file to a thread.
        """
        with open(unsent_news_csv, mode='r', newline='') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                message = f"**{row['title']}**\n   Link: {row['link']}\n   Published: {row['published']}\n"
                await thread.send(message)

        # Reset unsent_news.csv
        open(unsent_news_csv, 'w').close()
        with open(unsent_news_csv, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=['link', 'title', 'published'])
            writer.writeheader()

    async def remove_duplicate_rows_async(self, input_csv_file):
        """
        Removes duplicate rows from the specified CSV file.
        """
        seen_links = set()
        output_rows = []

        with open(input_csv_file, mode='r', newline='') as input_file:
            reader = csv.DictReader(input_file)
            fieldnames = reader.fieldnames or ['link', 'title', 'published']

            for row in reader:
                if row['link'] not in seen_links:
                    output_rows.append(row)
                    seen_links.add(row['link'])

        with open(input_csv_file, mode='w', newline='') as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)






############################################################################################################

class CreationButtonsView(View):
    def __init__(self, plot_manager: qf.ZenithPlotManager):
        super().__init__(timeout=1800)  # Timeout for button interaction (in seconds)
        self.plot_manager = plot_manager

    @discord.ui.button(label='Create MP4', style=discord.ButtonStyle.blurple, emoji='🎥')
    async def create_mp4_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        #bu özelliğimiz test aşamasındadır mesajını gönder
        await interaction.followup.send("This feature is currently in testing. Maybe you'll be able to use it soon, or maybe in another universe.", ephemeral=True)

        #success_message,video_path = await self.plot_manager.create_mp4()
        #video_file = discord.File(video_path, filename="zenith_plot.mp4")
        #await interaction.followup.send(success_message,file=video_file)

    @discord.ui.button(label='Create GIF', style=discord.ButtonStyle.green, emoji='🌌')
    async def create_gif_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        #waitng massage 
        waitn_msg=await interaction.followup.send("Creating the GIF... This may take a while.", ephemeral=True)
        await waitn_msg.delete()
        success_message,gif_path = await self.plot_manager.create_gif()
        gif_file = discord.File(gif_path, filename="zenith_plot.gif")
        await interaction.followup.send(success_message, file=gif_file)

    #zip file buton 
    @discord.ui.button(label='Create ZIP', style=discord.ButtonStyle.red, emoji='📦')
    async def create_zip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        #waitn msg
        waitn_msg=await interaction.followup.send("Creating the ZIP file... This may take a while.", ephemeral=True)
        await waitn_msg.delete()
        success_message,zip_path = await self.plot_manager.create_zip()
        zip_file = discord.File(zip_path, filename="zenith_plots.zip")
        await interaction.followup.send(success_message, file=zip_file)


class DateRangeModal(Modal):
    def __init__(self):
        super().__init__(title="Enter Date Range")
        self.add_item(TextInput(
            label="Start Date",
            placeholder="YYYY-MM-DD h:m:s",
            style=discord.TextStyle.short,
            required=True
        ))
        self.add_item(TextInput(
            label="End Date",
            placeholder="YYYY-MM-DD h:m:s",
            style=discord.TextStyle.short,
            required=True
        ))

    async def on_submit(self, interaction: discord.Interaction):
        start_date_str = self.children[0].value
        end_date_str = self.children[1].value

        try:
            await interaction.response.defer()
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')

            # Send a waiting message asynchronously
            await interaction.followup.send(
                "## Türkçe 🇹🇷:\n"
                "Yıldız tozları arasından grafiklerinizi topluyoruz... Hazır olunca sizi çağıracağız! 🚀\n\n"
                "## English 🏴:\n"
                "Gathering your charts from the stardust... We'll summon you once ready! 🛸",
                ephemeral=True
            )

            # Assuming plot generation and saving are asynchronous and can be parallelized
            plot_manager = qf.ZenithPlotManager(user_id=interaction.user.id)
            # Here, modify `save_plots_for_date_range` to be async and possibly break down into smaller async tasks if applicable

            success_message = await plot_manager.save_plots_for_date_range(start_date, end_date)

            saves_view = CreationButtonsView(plot_manager)
            await interaction.followup.send(interaction.user.mention + success_message, view=saves_view)

        except ValueError:
            await interaction.followup.send("Incorrect date format. Please use YYYY-MM-DD HH:MM:SS.", ephemeral=True)

class DateRangeButton(Button):
    def __init__(self, label: str, modal: Modal):
        super().__init__(style=discord.ButtonStyle.primary, label=label)
        self.modal = modal

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(self.modal)

class ZenithPlotView(View):
    def __init__(self):
        super().__init__(timeout=18000)
        self.add_item(DateRangeButton('Enter a date range!', DateRangeModal()))


#zenith plot async function
async def zenith_plot(interaction:discord.Interaction,city: str, date: str):
    #defer
    await interaction.response.defer()
        # Define a task for fetching the Zenith Plot
    async def fetch_zenith_plot(city, date):
        return await qf.ZenithPlotManager(city).get_zenith_plot(date)
    
    # Start fetching the zenith plot asynchronously
    fetch_plot_task = asyncio.create_task(fetch_zenith_plot(city, date))

    # Wait for all asynchronous operations to complete
    results = await asyncio.gather(fetch_plot_task)

    # Unpack the results
    p = results[0]

    # Bellekte bir PNG dosyası oluştur
    with BytesIO() as image_binary:
        p.export(image_binary, format='PNG') # p'nin export metodu BytesIO nesnesini kabul etmeli ve formatı belirtmeli
        image_binary.seek(0) 
        discord_file = discord.File(fp=image_binary, filename=f"{city}_zenith_plot.png")
        # Embed oluştur
        embed = discord.Embed(
                title=f"Zenith Plot for {city}",
                description=f"Here's the zenith plot for {city} on {date}. This chart provides a visual representation of the celestial object's zenith position, allowing you to observe astronomical events.",
                colour=discord.Colour.purple()  # Mor renk ekleniyor
                )
        embed.set_image(url=f"attachment://{city}_zenith_plot.png")
        
        #clear buffer 
        #send
        view = ZenithPlotView()  # Create the view with the date range button
        await interaction.followup.send(embed=embed, file=discord_file, view=view)

import aiohttp
from bs4 import BeautifulSoup
image_types = ["2048_0193", "2048_0171", "2048_0304", "2048_HMIIC", "2048_211193171", "2048_HMIBC", "2048_HMIB", "2048_1700"]
async def get_latest_image_url(date: datetime) -> list:
    """Get the URL of the latest image from a given date on SDO gsfc asynchronously.
    Args:
        date: The date for which to retrieve the latest image.
    Returns:
        A list of URLs for the latest images of specified types, or an empty list if no images are found.
    """
    base_url = "https://sdo.gsfc.nasa.gov/assets/img/browse/"
    date_str = date.strftime('%Y/%m/%d')
    directory_url = f"{base_url}{date_str}/"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(directory_url) as response:
            content = await response.text()
            soup = BeautifulSoup(content, 'html.parser')
            links = soup.find_all('a')
            
            latest_images = []

            for image_type in image_types:
                image_links = [link.get('href') for link in links if image_type in link.get('href')]
                if image_links:
                    # Sort and take the latest image link of this type
                    latest_image_link = sorted(image_links)[-1]
                    latest_images.append(f"{directory_url}{latest_image_link}")

            return latest_images

async def send_daily_links(thread, date: datetime=datetime.utcnow()):
    # Fetch the latest image URLs for the given date
    
    latest_image_urls = await get_latest_image_url(date)
    
    # Define descriptions for each image type
    descriptions = {
    "2048_0193": "# The Sun Now \nThe Sun's outer atmosphere, including hot flare plasma, with bright regions for active areas and dark areas known as coronal holes, which are key sources of solar wind particles.\n**Where:** Corona and hot flare plasma\n**Wavelength:** Extreme Ultraviolet\n",
    "2048_0171": "## Solar Coronas and Magnetic Loops\nCoronal loops, which are arcs extending off the Sun where plasma moves along magnetic field lines. The brightest spots indicate exceptionally strong magnetic fields near the Sun's surface.\n**Where:** Quiet corona and upper transition region\n**Wavelength:** Extreme Ultraviolet (171 angstroms)\n**Primary ions seen:** 8 times ionized iron (Fe IX)\n**Characteristic temperature:** 1 million K (1.8 million F)",
    "2048_0304": "## Solar Flares and Active Regions\nShowing areas where cooler dense plumes of plasma (filaments and prominences) are located above the visible surface of the Sun. Many of these features either can't be seen or appear as dark lines in the other channels.\n**Where:** Chromosphere (the active areas above the Sun's surface)\n**Wavelength:** Extreme Ultraviolet (304 angstroms)\n**Primary ions seen:** 2 times ionized helium (He II)\n**Characteristic temperature:** 60,000 K (107,540 F)",
    "2048_HMIIC": "## Solar Active Regions and Sunspots\nSunspots, which are cooler, darker areas on the Sun created by strong magnetic fields. They are often the source of solar flares and coronal mass ejections.\n**Where:** Photosphere (the visible surface of the Sun)\n**Wavelength:** Visible light\n**Primary ions seen:** None (visible light)\n**Characteristic temperature:** 6,000 K (10,760 F)",
    "2048_211193171": "Each highlights a different part of the corona.",
    "2048_HMIBC": "[Read information on colorized magnetograms.](https://sdo.gsfc.nasa.gov/assets/docs/HMI_M.ColorTable.pdf)",
    "2048_HMIB": "Placeholder description for 2048_HMIB image type.",
    "2048_1700": "Placeholder description for 2048_1700 image type.",
    }


    # Replace links in links_with_descriptions with the latest ones
    updated_links_with_descriptions = []
    for image_url in latest_image_urls:
        # Extract the image type from the URL
        image_type = image_url.split('/')[-1].split('_')[2]  # Adjust this indexing based on actual URL format
        description = descriptions.get(image_type, "Description not found.")
        updated_links_with_descriptions.append((description, image_url))
    
    # Send the updated links with descriptions
    for description, link in updated_links_with_descriptions:
        message = f"\n{description}\n{link}"
        await thread.send(message)
async def send_daily_links2(thread, date: datetime):
    """
    Sends a set of predefined links with descriptions to the specified thread.
    """
    now = datetime.utcnow()
    links_with_descriptions = [
        ("# The Sun Now \nThe Sun's outer atmosphere, including hot flare plasma, with bright regions for active areas and dark areas known as coronal holes, which are key sources of solar wind particles.\n**Where:** Corona and hot flare plasma\n**Wavelength:** Extreme Ultraviolet\n",
            "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_2048_0193.jpg"),
        ("## Solar Coronas and Magnetic Loops\nCoronal loops, which are arcs extending off the Sun where plasma moves along magnetic field lines. The brightest spots indicate exceptionally strong magnetic fields near the Sun's surface.\n**Where:** Quiet corona and upper transition region\n**Wavelength:** Extreme Ultraviolet (171 angstroms)\n**Primary ions seen:** 8 times ionized iron (Fe IX)\n**Characteristic temperature:** 1 million K (1.8 million F)",
            "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_2048_0171.jpg"),
        ("## Solar Flares and Active Regions\nShowing areas where cooler dense plumes of plasma (filaments and prominences) are located above the visible surface of the Sun. Many of these features either can't be seen or appear as dark lines in the other channels.\n**Where:** Chromosphere (the active areas above the Sun's surface)\n**Wavelength:** Extreme Ultraviolet (304 angstroms)\n**Primary ions seen:** 2 times ionized helium (He II)\n**Characteristic temperature:** 60,000 K (107,540 F)",
            "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_2048_0304.jpg"),
        ("## Solar Active Regions and Sunspots\nSunspots, which are cooler, darker areas on the Sun created by strong magnetic fields. They are often the source of solar flares and coronal mass ejections.\n**Where:** Photosphere (the visible surface of the Sun)\n**Wavelength:** Visible light\n**Primary ions seen:** None (visible light)\n**Characteristic temperature:** 6,000 K (10,760 F)",
            "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_HMIIC.jpg"),
        ("Each highlights a different part of the corona.",
            "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_2048_211193171.jpg"),
        ("[Read information on colorized magnetograms.](https://sdo.gsfc.nasa.gov/assets/docs/HMI_M.ColorTable.pdf)",
            "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_2048_HMIBC.jpg"),
        ("## LYRA 3-Day Quicklook", 
            "https://proba2.sidc.be/lyra/data/3DayQuicklook/LyraCalSWClatest.png"),
        ("## Latest SWAP Movie", 
            "https://proba2.sidc.be/swap/data/mpg/movies/latest_swap_movie.mp4"),
        ("## Carrington Rotations - Latest Yellow Movie", 
            "https://proba2.sidc.be/swap/data/mpg/movies/carrington_rotations/latest_cr_movie_yellow.mp4"),
        ("## Latest SWAP Synoptic Map",
            "https://proba2.sidc.be/swap/data/SWAPsynopticMap/LatestSWAPsynopticMap.png"),
        ("## Latest SWAP Polar Image with Edge\n", 
            "http://proba2.oma.be/swap/data/polar_sun/SWAPpolarImageWithEdge/LatestSWAPpolarImageWithEdge.png"),
    ]

    for description, link in links_with_descriptions:
        message = f"\n{description}\n{link}"
        await thread.send(message) 

#
#test for async 
if __name__ == "__main__":
    import asyncio
    async def main():
        print(await apod_dict())
    asyncio.run(main())