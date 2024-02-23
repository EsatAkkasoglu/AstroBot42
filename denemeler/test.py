from moviepy.editor import ImageSequenceClip
import os
import asyncio
import time
import tempfile
from typing import List, Optional
from datetime import datetime, timedelta
from PIL import Image
from starplot import ZenithPlot
from starplot.styles import PlotStyle, extensions,MarkerStyle,FillStyleEnum,LabelStyle,MarkerSymbolEnum
from zipfile import ZipFile, ZIP_DEFLATED
import matplotlib
matplotlib.use('Agg')
import sys
sys.path.append('')
import src.Astro_files.queryFunctions as qf

class ZenithPlotManager:
    """
    A class that manages zenith plots for multiple users. It can save zenith plots for a date range, create a GIF from saved plots, and more.

    Attributes:
    - city (str): The name of the city for which the zenith plots are generated. DEFAULT IS ISTANBUL
    - user_id (int): The ID of the user for whom the zenith plots are generated. DEFAULT IS 0

    Methods:
    - plot_style(): Returns the plot style for zenith plots.
    - get_zenith_plot(date): Returns a zenith plot for the given date.
    - save_plots_for_date_range(start_date, end_date): Saves zenith plots for a date range.
    - create_mp4(fps): Creates a GIF from saved plots using ImageMagick.
    """
    def __init__(self, city="Istanbul", user_id=0):
        self.city = city
        self.user_id = user_id
        self.base_path = f"denemeler/zenith_plot/{user_id}/"

    async def plot_style(self):
        style = PlotStyle().extend(extensions.BLUE_MEDIUM, extensions.MAP)
        style.constellation.label.font_size = 11
        style.constellation.line.width= 6
        style.constellation.line.zorder = -1
        style.star.label.font_family= "monospace"
        style.star.label.font_size= 10
        style.star.marker.size= 50
        style.ecliptic.line.visible = True
        
        # DSO Configuration
        dso_marker_style = MarkerStyle(
            color="red",
            symbol=MarkerSymbolEnum.TRIANGLE,
            size=10,
            fill=FillStyleEnum.FULL,
            alpha=0.6,
            visible=True,
            zorder=-1,
        )
        dso_label_style = LabelStyle(
            font_color="red",
            font_size=11,
            font_weight="normal",
            font_family="sans-serif",
            line_spacing=-1,
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
            font_size=10,
            font_weight="bold",
            font_family="sans-serif",
            line_spacing=1.0,
            zorder=1,
        )
        style.planets.label = planet_label_style
        style.planets.marker = planet_marker_style

        style 
        # Moon Configuration
        style.moon.marker.visible = True
        return style

    async def get_zenith_plot(self, date: str,resolution:int=3096):
        """Returns a zenith plot for the given date asynchronously using to_thread for synchronous parts.
        Args:
        - date (datetime): The date for which the zenith plot is generated.

        Returns:
        - ZenithPlot: A zenith plot object.
        """
        observer, localtime = await qf.get_observer_and_local_time(self.city, date)
        style = await self.plot_style()

        # Use asyncio.to_thread to run the synchronous ZenithPlot constructor in a separate thread
        p = ZenithPlot(lat=observer.latitude.degree, lon=observer.longitude.degree,
                                    dt=localtime, limiting_magnitude=5, style=style,
                                    adjust_text=False, include_info_text=True, ephemeris="de440.bsp", resolution=resolution, rasterize_stars=False, hide_colliding_labels=False)
        return p

    async def save_plots_for_date_range(self, start_date: datetime, end_date: datetime):
        """Save plots for a given range of dates
        Args:
        - start_date (datetime): The start date of the range.
        - end_date (datetime): The end date of the range.

        Returns:
        - str: A success message if the plots are saved successfully.
        """
        # Create the directory if it doesn't exist already
        os.makedirs(self.base_path, exist_ok=True)

        # Clear all png files in the directory
        [os.remove(os.path.join(self.base_path, file)) for file in os.listdir(self.base_path) if file.endswith(".png")]

        # Determine the gap between plot generations based on the date range
        # Including both start and end date
        date_difference = (end_date - start_date).days + 1

        # Calculate gap in terms of hours for more granularity
        if date_difference <= 1:
            gap_hours = 1  # Every 30 minutes
        elif date_difference <= 5:
            gap_hours = 4  # Every 2 hours
        elif date_difference <= 60:
            gap_hours = 24*5  # Daily for up to 2 months
        elif date_difference <= 365 * 2:
            gap_hours = 24 * 14  # Every two weeks for up to 2 years
        elif date_difference <= 365 * 5:
            gap_hours = 24 * 30  # Monthly for up to 5 years
        else:
            # If the range is beyond 5 years, notify the user to narrow down the range
            output_text_fail = (
                "\n## Türkçe 🇹🇷 :\nTarih aralığı çok uzun. Lütfen aralığı daraltın. 🛑\n\n"
                "## English 🏴:\nThe date range is too long. Please consider narrowing down the range. 🛑"
            )
            return output_text_fail

        # The rest of your code for plotting...

        total_hours = (end_date - start_date).total_seconds() / 3600
        number_of_plots = int(total_hours / gap_hours) + 1
        import matplotlib
        matplotlib.use('Agg')  # Use the 'Agg' backend to save plots without displaying them
        print(date_difference)

        dates = [start_date + timedelta(hours=i * gap_hours) for i in range(number_of_plots)]
        print('Dates:',dates)
        queue = asyncio.Queue()
        for date in dates:
            await queue.put(date)
        
        async def process_queue():
            while not queue.empty():
                date = await queue.get()
                plot = await self.get_zenith_plot(date)
                filename = f"{self.base_path}{date.strftime('%Y-%m-%d_%H-%M')}_{self.city}_zenithPlot.png"
                print("AAA")
                try:
                    await asyncio.to_thread(plot.export, filename)
                except Exception as e:
                    print(f"Failed to export plot: {e}")
                finally:
                    queue.task_done()
        
        tasks = []
        for _ in range(10):  # Belirli sayıda işlemci oluştur
            task = asyncio.create_task(process_queue())
            tasks.append(task)
        print(f"Plots successfully saved! ({start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')})")
        await asyncio.gather(**tasks)
        
        output_text_sucess = (
            f"🌠 **Sky Voyage Recorded** 🌠\n"
            f"- **Start Date**: `{start_date.strftime('%Y-%m-%d %H:%M:%S')}`\n"
            f"- **End Date**: `{end_date.strftime('%Y-%m-%d %H:%M:%S')}`\n"
            f"- **Status**: Sky maps saved temporarily.\n"
            f"- **Expiry**: Data transforms into stardust after 24 hours.\n"
            f"🚀 Keep exploring the cosmos! 🚀"
        )
        return output_text_sucess
    
    #zip file with all plots
    async def create_zip(self):
        """Create a ZIP file containing all the optimized saved plots"""
        zip_path = f"{self.base_path}zenith_plots.zip"
        
        with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zipf:
            for file in os.listdir(self.base_path):
                if file.endswith(".png"):
                    file_path = os.path.join(self.base_path, file)
                    # Compress and optionally resize the image before adding to ZIP
                    optimized_path = await self.optimize_and_compress_image(file_path)
                    zipf.write(optimized_path, file)
                    # Optionally, remove the temporary optimized file if you created one
                    os.remove(optimized_path)

        output_text_success = ("Your celestial journey has been archived in a cosmic ZIP file! 🌌📚 "
                               "But remember, like the stars, it's not permanent. **In 24 hours**, "
                               "it will be drifting into **a black hole** deep in the universe. 🚮")
        return output_text_success, zip_path
    
    async def optimize_and_compress_image(self, image_path):
        """Optimize and compress an image for ZIP storage."""
        # Use a temporary file to avoid altering the original
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        try:
            with Image.open(image_path) as img:
                # Optional: resize the image - img = img.resize((new_width, new_height), Image.ANTIALIAS)
                img.save(temp_file.name, format='PNG', optimize=True)
            return temp_file.name
        finally:
            temp_file.close()

    async def create_mp4(self,fps: int = 5):
        """Create a GIF from saved plots using ImageMagick"""
        video_path = f"{self.base_path}sky_plot.mp4"
        if os.path.exists(video_path):
            os.remove(video_path)
        # List all image files in the directory
        imgs = [os.path.join(self.base_path, img) for img in os.listdir(self.base_path) if img.endswith(('.png', '.jpg', '.jpeg'))]
        imgs.sort()  # Ensure the images are sorted if necessary

        # Create video clip from images
        clip = ImageSequenceClip(imgs, fps=fps)

        # Write the video file
        clip.write_videofile(video_path, codec='libx264', audio=False)
        #user return notification
        output_text_success = (
            "🌌 **Universe's Rhythm** 🌌\n"
            "Your celestial video 🎥 now glows amidst stardust! 🌠\n"
            "**Duration**: Lasts for **24 hours** before succumbing to a black hole's grasp. 🕳️🚮"
        )

        return output_text_success,video_path
    async def create_gif(self):
        # If exists, remove the existing GIF file
        gif_path = f"{self.base_path}sky_plot.gif"
        if os.path.exists(gif_path):
            os.remove(gif_path)
        # Create the frames, filtering for appropriate file extensions and sorting by modification date
        imgs = [os.path.join(self.base_path, img) for img in os.listdir(self.base_path) if img.endswith(('.png', '.jpg', '.jpeg'))]
        imgs.sort(key=lambda x: os.path.getmtime(x))  # Sort files by modification time
        
        frames = [Image.open(img) for img in imgs]
        
        # Save into a GIF file that loops forever

        frames[0].save(gif_path, format='GIF',
                        append_images=frames[1:],
                        save_all=True,
                        duration=300, loop=0)
        #user return notification
        output_text_success = (
            "🌠 **Cosmic Symphony** 🌠\n"
            "Behold, your celestial GIF 🎥 now basks in cosmic light! ✨\n"
            "**Lifetime**: Illuminates for **24 hours** before being engulfed by the shadows of a black hole. 🕳️✨"
        )

        return output_text_success,gif_path


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
    manager = ZenithPlotManager(city="Istanbul", user_id=278558027160748033)
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 1, 3)
    await manager.save_plots_for_date_range(start_date, end_date)
    await manager.create_gif()
    await manager.create_mp4()
# Run the main coroutine

if __name__ == "__main__":
    asyncio.run(main())
    #asyncio.run(main2())
 