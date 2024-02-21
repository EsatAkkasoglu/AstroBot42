from datetime import timedelta,datetime
from pytz import timezone
import sys
sys.path.append('')
import src.Astro_files.queryFunctions as qf
import asyncio
import os
import time 
from moviepy.editor import ImageSequenceClip
from PIL import Image
from starplot import ZenithPlot, SkyObject
from starplot.styles import PlotStyle, extensions,MarkerStyle,FillStyleEnum,LabelStyle,MarkerSymbolEnum



# Assuming all necessary imports are done correctly
async def plot_style():
    style = PlotStyle().extend(extensions.BLUE_MEDIUM, extensions.MAP)
    style.constellation.label.font_size = 6
    style.ecliptic.line.visible = True

    # DSO Configuration
    dso_marker_style = MarkerStyle(
        color="red",
        symbol=MarkerSymbolEnum.TRIANGLE,
        size=6,
        fill=FillStyleEnum.FULL,
        alpha=0.8,
        visible=True,
        zorder=-1,
    )
    dso_label_style = LabelStyle(
        font_color="red",
        font_size=6,
        font_weight="normal",
        font_family="monospace",
        line_spacing=1.0,
        zorder=1,
    )
    style.dso.label = dso_label_style
    style.dso.marker = dso_marker_style

    # Planet Configuration
    planet_marker_style = MarkerStyle(
        color="#C0AD00",
        symbol=MarkerSymbolEnum.CIRCLE,
        size=6,
        fill=FillStyleEnum.FULL,
        alpha=0.8,
        visible=True,
        zorder=-1,
    )
    planet_label_style = LabelStyle(
        font_color="#C0AD00",
        font_size=6,
        font_weight="bold",
        font_family="monospace",
        line_spacing=1.0,
        zorder=1,
    )
    style.planets.label = planet_label_style
    style.planets.marker = planet_marker_style

    # Moon Configuration
    style.moon.marker.visible = True
    return style

async def get_zenith_plot(city: str="Istanbul",date: datetime = datetime.utcnow()):
    """Get a plot for the given location asynchronously.
    Args:
        city (str): The city for which to get the plot.
    Returns:
        ZenithPlot: The zenith plot for the given location.
    """
    date=str(date)
    observer, localtime = await qf.get_observer_and_local_time(city,date)
    style = await plot_style()
    # ZenithPlot Creation
    p = ZenithPlot(
        lat=observer.latitude.degree,
        lon=observer.longitude.degree,
        dt=localtime,  # UTC+3,
        limiting_magnitude=4.6,
        style=style,
        adjust_text=True,
        include_info_text=True,
        ephemeris="de440.bsp"
    )
    print(f"Creating a graph for {city} on {date}")
    return p

async def save_plots_for_date_range(city: str, start_date: datetime, end_date: datetime, user_id: int = 0):
    """Save zenith plots for a given city and date range asynchronously.

    Args:
        city (str): The city for which to get the plots.
        start_date (datetime): The start date of the range.
        end_date (datetime): The end date of the range.
        user_id (int, optional): User identifier for directory naming. Defaults to 0.
    """
    base_path = f"denemeler/zenith_plot/{user_id}/"
    os.makedirs(base_path, exist_ok=True)

    # Clear all png files in the directory
    [os.remove(os.path.join(base_path, file)) for file in os.listdir(base_path) if file.endswith(".png")]

    # Determine the gap between plot generations based on the date range
    date_difference = (end_date - start_date).days + 1  # Including both start and end date

    # Define gap days based on the date difference
    if date_difference < 2:
        gap_days = 1 / 24  # Generate plot every hour for less than 2 days
    elif date_difference <= 60:
        gap_days = 1  # Daily for up to 2 months
    elif date_difference <= 365 * 2:
        gap_days = 30  # Every two weeks for up to 2 years
    elif date_difference <= 365 * 5:
        gap_days =60  # Monthly for up to 5 years
    else:
        # If the range is beyond 5 years, consider adjusting your strategy or notifying the user
        output_text_fail="Date range is too long. Please consider narrowing down the range."
        return output_text_fail # Optionally, adjust this part based on your application's needs

    tasks = []
    current_date = start_date
    while current_date <= end_date:
        tasks.append(get_zenith_plot(city, current_date))
        current_date += timedelta(days=gap_days)

    # Execute all tasks concurrently
    for i, plot in enumerate(await asyncio.gather(*tasks)):
        plot_date = start_date + timedelta(days=gap_days * i)
        filename = f"{base_path}{plot_date.strftime('%Y-%m-%d_%H-%M')}_{city}_zenithPlot.png"
        # Assuming `plot` has an export method
        plot.export(filename)
        output_text_sucess=f"Saved plot for {plot_date.strftime('%Y-%m-%d_%H-%M')} as {filename}"
        print(output_text_sucess)
        return output_text_sucess
# create a gif with png files generated from file address
async def create_gif(gif_name: str,file_address: str="database/skyPlot/", user_id:int=0):
    # If exists, remove the existing GIF file
    file_address= f"{file_address}{user_id}/"
    gif_path = f"{file_address}{gif_name}.gif"
    if os.path.exists(gif_path):
        os.remove(gif_path)
    print(gif_path)
    # Create the frames, filtering for appropriate file extensions and sorting by modification date
    imgs = [os.path.join(file_address, img) for img in os.listdir(file_address) if img.endswith(('.png', '.jpg', '.jpeg'))]
    imgs.sort(key=lambda x: os.path.getmtime(x))  # Sort files by modification time
    
    frames = [Image.open(img) for img in imgs]
    
    # Save into a GIF file that loops forever

    frames[0].save(gif_path, format='GIF',
                    append_images=frames[1:],
                    save_all=True,
                    duration=300, loop=0)
    print(f"GIF file is created as {gif_path}")


# create a mp4 video with png files generated from file address
async def create_mp4(video_name: str,file_address: str="database/skyPlot/",user_id:int=0, fps: int = 5):
    """
    Creates an MP4 video from a sequence of images stored in a directory.

    Args:
    - file_address: The directory containing the image frames.
    - video_name: The name of the output video file, without extension.
    - fps: Frames per second for the output video. Defaults to 10.
    """

    # Check and remove existing MP4 file
    file_address= f"{file_address}{user_id}/"
    video_path = f"{file_address}{video_name}.mp4"
    if os.path.exists(video_path):
        os.remove(video_path)
    print(video_path)
    # List all image files in the directory
    imgs = [os.path.join(file_address, img) for img in os.listdir(file_address) if img.endswith(('.png', '.jpg', '.jpeg'))]
    imgs.sort()  # Ensure the images are sorted if necessary

    # Create video clip from images
    clip = ImageSequenceClip(imgs, fps=fps)

    # Write the video file
    clip.write_videofile(video_path, codec='libx264', audio=False)
class ZenithPlotManager:
    def __init__(self, city="Istanbul", user_id=0):
        self.city = city
        self.user_id = user_id
        self.base_path = f"denemeler/zenith_plot/{user_id}/"

    async def plot_style(self):
        style = PlotStyle().extend(extensions.BLUE_MEDIUM, extensions.MAP)
        style.constellation.label.font_size = 6
        style.ecliptic.line.visible = True

        # DSO Configuration
        dso_marker_style = MarkerStyle(
            color="red",
            symbol=MarkerSymbolEnum.TRIANGLE,
            size=6,
            fill=FillStyleEnum.FULL,
            alpha=0.8,
            visible=True,
            zorder=-1,
        )
        dso_label_style = LabelStyle(
            font_color="red",
            font_size=6,
            font_weight="normal",
            font_family="monospace",
            line_spacing=1.0,
            zorder=1,
        )
        style.dso.label = dso_label_style
        style.dso.marker = dso_marker_style

        # Planet Configuration
        planet_marker_style = MarkerStyle(
            color="#C0AD00",
            symbol=MarkerSymbolEnum.CIRCLE,
            size=6,
            fill=FillStyleEnum.FULL,
            alpha=0.8,
            visible=True,
            zorder=-1,
        )
        planet_label_style = LabelStyle(
            font_color="#C0AD00",
            font_size=6,
            font_weight="bold",
            font_family="monospace",
            line_spacing=1.0,
            zorder=1,
        )
        style.planets.label = planet_label_style
        style.planets.marker = planet_marker_style

        # Moon Configuration
        style.moon.marker.visible = True
        return style

    async def get_zenith_plot(self, date: datetime):
        date = str(date)
        observer, localtime = await qf.get_observer_and_local_time(self.city, date)
        style = await self.plot_style()
        p = ZenithPlot(lat=observer.latitude.degree, lon=observer.longitude.degree,
                       dt=localtime, limiting_magnitude=4.6, style=style,
                       adjust_text=True, include_info_text=True, ephemeris="de440.bsp")
        return p

    async def save_plots_for_date_range(self, start_date: datetime, end_date: datetime):
        os.makedirs(self.base_path, exist_ok=True)

        # Clear all png files in the directory
        [os.remove(os.path.join(self.base_path, file)) for file in os.listdir(self.base_path) if file.endswith(".png")]

        # Determine the gap between plot generations based on the date range
        date_difference = (end_date - start_date).days + 1  # Including both start and end date

        # Define gap days based on the date difference
        if date_difference < 2:
            gap_days = 1 / 24  # Generate plot every hour for less than 2 days
        elif date_difference <= 60:
            gap_days = 1  # Daily for up to 2 months
        elif date_difference <= 365 * 2:
            gap_days = 30  # Every two weeks for up to 2 years
        elif date_difference <= 365 * 5:
            gap_days =60  # Monthly for up to 5 years
        else:
            # If the range is beyond 5 years, consider adjusting your strategy or notifying the user
            output_text_fail="Date range is too long. Please consider narrowing down the range."
            return output_text_fail # Optionally, adjust this part based on your application's needs

        tasks = []
        current_date = start_date
        while current_date <= end_date:
            tasks.append(self.get_zenith_plot(current_date))
            current_date += timedelta(days=gap_days)

        # Execute all tasks concurrently
        for i, plot in enumerate(await asyncio.gather(*tasks)):
            plot_date = start_date + timedelta(days=gap_days * i)
            filename = f"{self.base_path}{plot_date.strftime('%Y-%m-%d_%H-%M')}_{self.city}_zenithPlot.png"
            # Assuming `plot` has an export method
            plot.export(filename)
        output_text_sucess=f"Saved plots for {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} in {self.base_path}"
        return output_text_sucess

    async def create_mp4(self,fps: int = 5):
        """Create a GIF from saved plots using ImageMagick"""
        video_path = f"{self.base_path}sky_plot.mp4"
        if os.path.exists(video_path):
            os.remove(video_path)
        print(video_path)
        # List all image files in the directory
        imgs = [os.path.join(self.base_path, img) for img in os.listdir(self.base_path) if img.endswith(('.png', '.jpg', '.jpeg'))]
        imgs.sort()  # Ensure the images are sorted if necessary

        # Create video clip from images
        clip = ImageSequenceClip(imgs, fps=fps)

        # Write the video file
        clip.write_videofile(video_path, codec='libx264', audio=False)

    async def create_gif(self):
        # If exists, remove the existing GIF file
        gif_path = f"{self.base_path}sky_plot.gif"
        if os.path.exists(gif_path):
            os.remove(gif_path)
        print(gif_path)
        # Create the frames, filtering for appropriate file extensions and sorting by modification date
        imgs = [os.path.join(self.base_path, img) for img in os.listdir(self.base_path) if img.endswith(('.png', '.jpg', '.jpeg'))]
        imgs.sort(key=lambda x: os.path.getmtime(x))  # Sort files by modification time
        
        frames = [Image.open(img) for img in imgs]
        
        # Save into a GIF file that loops forever

        frames[0].save(gif_path, format='GIF',
                        append_images=frames[1:],
                        save_all=True,
                        duration=300, loop=0)
async def main2():
    #start time 
    start = time.time()
    start_date = datetime(2023, 1, 1)  # Example start date
    end_date = datetime(2023, 1, 3)  # Example end date
    await save_plots_for_date_range("Istanbul", start_date, end_date)
    #await create_gif("zenith_plots","denemeler/zenith_plot/")
    #await create_mp4("zenith_plots","denemeler/zenith_plot/",fps=10)
    end = time.time()
    print(f"Time taken: {end - start} seconds")
async def main():
    manager = ZenithPlotManager(city="Istanbul", user_id=0)
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 1, 3)
    await manager.save_plots_for_date_range(start_date, end_date)
    await manager.create_gif()
    await manager.create_mp4()
# Run the main coroutine
if __name__ == "__main__":
    asyncio.run(main())
 