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
import datetime
from io import BytesIO
from random import randrange
from requests import get
from bs4 import BeautifulSoup
from datetime import datetime
from time import mktime, strftime
sys.path.append('')
from astropy.time import Time
from src.log_files import logger
from src.Astro_files import queryFunctions as qf
import discord
from discord import app_commands
from discord.ui import Button,View
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

  embed = discord.Embed(title="🌟 Object Info From File", color=discord.Color.blurple(), timestamp=datetime.datetime.utcnow())
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
  await interaction.response.defer(thinking=True)
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
        print(formatted_date)
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

    return apod_data
#adding for discord embed 
async def  apod_embed(interaction: discord.Interaction,date:str=None):
    
    await interaction.response.defer()
    apod=await apod_dict(date)
    # Create the embed
    embed = discord.Embed(title=apod['title'],url=apod['url'], description=f"{apod['desc']}\nCredits:{apod['credits']}", color=discord.Color.orange(),timestamp=datetime.now())
    embed.set_footer(text=f"NASA-APOD",icon_url="https://gpm.nasa.gov/themes/pmm_bs/images/nasa-logo-large-v1.png")

    # Define buttons
    view = View()
    auto_button = Button(label="Automatically share on this server every day 🔄️", style=discord.ButtonStyle.green)
    
    # Button callbacks
    async def on_auto_button_click(interaction: discord.Interaction):
        if interaction.user.guild_permissions.manage_messages:
            #save a auto_apod.csv file 
            #check if already exist
            if os.path.isfile("database/csv/auto_apod.csv"):
                #check if already in file
                df=pd.read_csv("database/csv/auto_apod.csv")
                if interaction.guild.id in df['server_id'].values:
                    await interaction.response.send_message(f"Your server already in **automation** list! ❌", ephemeral=True)
                else:
                    new_row = {'server_id': interaction.guild.id, 'channel_id': interaction.channel.id}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_csv("database/csv/auto_apod.csv",index=False)
                    await interaction.response.send_message(f"Your server has been successfully added to the **automation** list! ✅", ephemeral=True)
            else:
                df=pd.DataFrame(columns=['server_id','channel_id'])
                new_row = {'server_id': interaction.guild.id, 'channel_id': interaction.channel.id}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv("database/csv/auto_apod.csv",index=False)
                await interaction.response.send_message(f"Your server has been successfully added to the **automation** list! ✅", ephemeral=True)
        else:
            await interaction.response.send_message(f"You don't have permission to do that! ❌", ephemeral=True)   
    auto_button.callback = on_auto_button_click
    #add button to view
    view.add_item(auto_button)
    #eğer resim varsa set_image 
    if not apod['video']:
        embed.set_image(url=apod['image_link'])
        await interaction.followup.send(embed=embed,view=view)
    else :
        await interaction.followup.send(embed=embed,view=view)
        await interaction.followup.send(apod['video'])
      # Define buttons

#test for async 
if __name__ == "__main__":
    import asyncio
    async def main():
        print(await apod_dict())
    asyncio.run(main())