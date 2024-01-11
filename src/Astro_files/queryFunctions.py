import io
import math
import requests
from datetime import datetime,timedelta
import pytz
from timezonefinder import TimezoneFinder
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import Normalize
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
from geopy.geocoders import Nominatim
from PIL import Image
import ephem 
from astroquery.simbad import Simbad
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time
import astropy.units as u
import astroplan
from astroplan import FixedTarget, Observer,is_observable,is_always_observable
from astroplan.plots import plot_altitude,plot_finder_image,plot_sky
from astroplan import AltitudeConstraint, AirmassConstraint,AtNightConstraint
from dateutil import parser


class SolarSystemObjects:
    """
    This class is used to get data about a solar system objects from the https://api.le-systeme-solaire.net/rest/bodies/object_name

    Attributes:
        - SS_object_name (str): The name of the solar system objects you want to get data from
        - units (dict): The units of the data returned by the API

    Methods:
        - filter_dict: Filters the dictionary returned by the API to remove empty values
        - get_SS_object_data: Gets the data from the API
        - get_formatted_data: Formats the data returned by the API to make it more readable

    Arg:
        - SS_object_name (str): The name of the solar system objects  you want to get data from
    
    Returns:
        - formatted_data (dict): A dictionary containing the data of the solar system objects 
    
    Example:
    >>> SS_object_name = "venus"  # Replace with the solar system objects  you're interested in
    >>> SS_object_info = SolarSystemObjects(SS_object_name).get_formatted_data()
    >>> print(SS_object_info)
    {'id': {'symbol': 'ID', 'definition': 'ID', 'value': 'venus', 'unit': ''}, 'name': {'symbol': '', 'definition': 'name', 'value': 'Vénus', 'unit': ''}, ...}
    >>> print(SS_object_info['semimajorAxis'])
    {'symbol': 'a', 'definition': 'semi-major axis', 'value': '0.723', 'unit': 'AU'}
    >>> print(f"{SS_object_info['semimajorAxis']['value']} {SS_object_info['semimajorAxis']['unit']}")
    0.723 AU

    Notes:
    -----
    All **non-empty** results for the called object are returned. The values in the API have changed according to usage.\n
    It may not be a suitable call for mathematical calculations, please NOTE that units change!\n
    For more detailed information please click https://api.le-systeme-solaire.net/en/
    """
    def __init__(self, SS_object_name:str):
        self.SS_object_name = SS_object_name
        self.SS_object_name = SS_object_name
        self.param = {
            "source": {"symbol": "", "definition": "object url", "unit": "url", "value": None},
            "aphelion": {"symbol": "ad", "definition": "aphelion", "unit": "km", "value": None},
            #adding alternativeName
            "alternativeName": {"symbol": "", "definition": "alternativeName", "unit": "", "value": None},
            "aroundPlanet": {"symbol": "", "definition": "aroundPlanet", "unit": "", "value": None},
            "argPeriapsis": {"symbol": "ω", "definition": "argument of perihelion", "unit": "°", "value": None},
            "avgTemp": {"symbol": "T", "definition": "average temperature", "unit": "°C", "value": None},
            "axialTilt": {"symbol": "ε", "definition": "axial tilt", "unit": "°", "value": None},
            "bodyType": {"symbol": "", "definition": "body type", "unit": "", "value": None},
            "density": {"symbol": "ρ", "definition": "density", "unit": "g/cm³", "value": None},
            "discoveredBy": {"symbol": "", "definition": "discoveredBy", "unit": "", "value": None},
            "moons": {"symbol": "", "definition": "moons", "unit": "", "value": None},
            "discoveryDate": {"symbol": "", "definition": "discoveryDate", "unit": "", "value": None},
            "eccentricity": {"symbol": "e", "definition": "eccentricity", "unit": "", "value": None},
            "englishName": {"symbol": "", "definition": "Name", "unit": "", "value": None},
            "equaRadius": {"symbol": "R_eq", "definition": "equatorial radius", "unit": "km", "value": None},
            "escape": {"symbol": "v_esc", "definition": "escape velocity", "unit": "m/s", "value": None},
            "flattening": {"symbol": "f", "definition": "flattening", "unit": "", "value": None},
            "gravity": {"symbol": "g", "definition": "surface gravity", "unit": "m/s²", "value": None},
            "id": {"symbol": "ID", "definition": "ID", "unit": "", "value": None},
            "inclination": {"symbol": "i", "definition": "orbital inclination", "unit": "°", "value": None},
            "isPlanet": {"symbol": "", "definition": "is planet", "unit": "", "value": None},
            "longAscNode": {"symbol": "Ω", "definition": "longitude of ascending node", "unit": "°", "value": None},
            "mainAnomaly": {"symbol": "M", "definition": "mean anomaly", "unit": "°", "value": None},
            "mass": {"symbol": "m", "definition": "mass", "unit": "kg", "value": None},
            "meanRadius": {"symbol": "R_mean", "definition": "mean radius", "unit": "km", "value": None},
            "name": {"symbol": "", "definition": "name", "unit": "", "value": None},
            "perihelion": {"symbol": "q", "definition": "perihelion", "unit": "km", "value": None},
            "polarRadius": {"symbol": "R_polar", "definition": "polar radius", "unit": "km", "value": None},
            "semimajorAxis": {"symbol": "a", "definition": "semi-major axis", "unit": "km", "value": None},
            "sideralOrbit": {"symbol": "T_sideral_orbit", "definition": "sideral orbit period", "unit": "days", "value": None},
            "sideralRotation": {"symbol": "T_sideral_rotation", "definition": "sideral rotation period", "unit": "hours", "value": None},
            "vol": {"symbol": "V", "definition": "volume", "unit": "m³", "value": None},
        }

    async def get_ra_dec_from_common_name(self,object_name):
        """
        This function is used to get the RA and DEC of an object using its common name

        Arg:
            - object_name (str): The name of the EPHEM object
        
        Returns:
            - ra_hms (str): The right ascension of the object in hours, minutes and seconds
            - dec_dms (str): The declination of the object in degrees, minutes and seconds
            - ra_deg (float): The right ascension of the object in degrees
            - dec_deg (float): The declination of the object in degrees
            - constellation (str): Which constellation the object is currently in
        """
        obj = getattr(ephem, object_name.capitalize())()
        obj.compute()
        ra = ephem.hours(obj.ra)
        dec = ephem.degrees(obj.dec)
        ra_deg= math.degrees(ra)
        dec_deg = math.degrees(dec) 
        ra_hms = str(ephem.hours(obj.ra)).split(":")
        ra_hms= f"{ra_hms[0]}h {ra_hms[1]}m {float(ra_hms[2]):.2f}s"
        
        dec_dms = str(ephem.degrees(obj.dec)).split(":")
        dec_dms = f"{dec_dms[0]}° {dec_dms[1]}' {float(dec_dms[2]):.2f}\""    

        constellation = ephem.constellation(obj)[1]
        return ra_hms, dec_dms,ra_deg, dec_deg,constellation 

                
    async def filter_dict(self, dictionary):
        filtered_dict = {}
        for key, value in dictionary.items():
            if value is not None and value != 0 and value != "":
                filtered_dict[key] = value
        return filtered_dict

    async def get_formatted_data(self):
        SS_object_data = await self.get_SS_object_data()
        formatted_data = {}
        for key, value in SS_object_data.items():
            unit_info = self.param.get(key, {"unit": "", "value": ""})
            unit = unit_info["unit"]
            formatted_value = value
            if isinstance(value, dict):
                if "massExponent" in value and "massValue" in value:
                    formatted_value = f"{value['massValue'] * 10**value['massExponent']:.2e}"
                    unit = "kg"
                elif "radiusExponent" in value and "radiusValue" in value:
                    formatted_value = f"{value['radiusValue'] * 10**value['radiusExponent']:.2e}"
                    unit = "km"
                elif "volExponent" in value and "volValue" in value:
                    formatted_value = "{:.2e}".format(float(value['volValue'] * 10**value['volExponent']))
                    unit = "m³"
            elif key in {"aphelion", "semimajorAxis", "perihelion"} and value > 1000000:
                formatted_value = f"{value / 149597870.5:.3f}"
                unit = "AU"
            elif key == "avgTemp":
                formatted_value = f"{value - 273.15:.2f}"
                unit = "degC"
            elif key == "sideralOrbit" and 30 <= value <= 360:
                formatted_value = f"{value / 30:.2f}"
                unit = "months"
            elif key == "sideralOrbit" and value > 360:
                formatted_value = f"{value / 365.25:.2f}"
                unit = "years"
            elif key == "sideralRotation":
                if float(value) < 0:
                    value = float(f"{-value:.2f}")
                else:
                    value = float(f"{value:.2f}")

                if value >= (24 * 30):
                    formatted_value = f"{value / (24 * 30):.2f}"
                    unit = "months"
                elif value >= 24 * 7:
                    formatted_value = f"{value / (24 * 7):.2f}"
                    unit = "weeks"
                elif value >= 24:
                    formatted_value = f"{value / 24:.2f}"
                    unit = "days"
                else:
                    formatted_value = f"{value:.2f}"
                    unit = "hours"
            
            # Use the value from self.param
            formatted_data[key] = {
                "symbol": self.param[key]["symbol"],
                "definition": self.param[key]["definition"],
                "value": formatted_value,
                "unit": unit
            }
        
        # Add the "source" entry using the value from self.param
        formatted_data["source"] = {"symbol": "","definition" : "",
            "value": f"https://api.le-systeme-solaire.net/rest/bodies/{self.SS_object_name}",
            "unit": "url"
        }
        #object_name=formatted_data['']
        #ra dec control 
        try:
            ra_hms,dec_dms,ra_deg,dec_deg,constellation = await self.get_ra_dec_from_common_name(self.SS_object_name)
            formatted_data["ra_hms"] = {
                "symbol": "ra",
                "definition": "right ascension",
                "value": ra_hms,
                "unit": ""
            }
            formatted_data["dec_dms"] = {
                "symbol": "dec",
                "definition": "declination",
                "value": dec_dms,
                "unit": ""
            }
            formatted_data["RA_d_A_ICRS_J2000_2000"] = {
                "symbol": "ra",
                "definition": "right ascension",
                "value": ra_deg,
                "unit": "deg"
            }
            formatted_data["DEC_d_D_ICRS_2000"] = {
                "symbol": "dec",
                "definition": "declination",
                "value": dec_deg,
                "unit": "deg"
            }
            formatted_data["constellation"] = {
                "symbol": "",
                "definition": "constellation",
                "value": constellation,
                "unit": ""
            }
        except:
            pass
        
        keys_to_remove = ['id', 'name', 'englishName', 'aroundPlanet', 'moons', 'isPlanet','source','DEC_d_D_ICRS_2000','RA_d_A_ICRS_J2000_2000']

        for key in keys_to_remove:
            formatted_data.pop(key, None)

        return formatted_data
    
    async def get_SS_object_data(self):
        url = f"https://api.le-systeme-solaire.net/rest/bodies/{self.SS_object_name}"
        response = requests.get(url)
        if response.status_code == 200:
            SS_object_data = response.json()
            filter_dict= await self.filter_dict(SS_object_data)
            return filter_dict
        else:
            return None
    

async def get_object_info_simbad(object_name:str):
    """
    Retrieves information about a celestial object from the Simbad database.

    Args:
        - object_name (str): The name of the celestial object.

    Returns:
        - dict: A dictionary containing information about the object.
    
    Usage:
        >>> get_object_info_simbad("M1")
        {'Main_name': 'Crab Nebula', 'IDS_name': 'NAME Crab Nebula', 'object_type': 'SNR', 'SP_type': 'Pulsar', 'ra': '05 34 30.9', 'dec': '+22 00 53', 'mag_U': 13.99, 'mag_B': 13.74, 'mag_V': 13.01, 'mag_R': 12.42, 'mag_I': 11.9, 'mag_G': 13.011, 'mag_J': 10.81, 'mag_H': 10.4, 'mag_K': 10.2, 'mag_u': 14.2, 'mag_g': 13.1, 'mag_r': 12.4, 'mag_i': 11.9, 'mag_z': 11.5, 'Z_value': 0.000226, 'rvz_radvel': -0.00068, 'parallax': 2.2963, 'Fe_H_Teff': 0.0, 'Fe_H_log_g': 0.0, 'Fe_H_Fe_H': 0.0, 'Fe_H_CompStar': 0.0, 'RA_d_A_ICRS_J2000_2000': 83.63308333, 'DEC_d_D_ICRS_2000': 22.0145, 'distance_pc': 435.3712296983751, 'distance_ly': 1419.024173997686}
        >>> object_info['ra']
        '05 34 30.9'
    
    """
    custom_simbad = Simbad()
    custom_simbad.add_votable_fields(
        "otype","sptype",
        "flux(U)", "flux(B)", "flux(V)", "flux(R)", "flux(I)", 
        "flux(G)", "flux(J)", "flux(H)", "flux(K)", "flux(u)", 
        "flux(g)", "flux(r)", "flux(i)", "flux(z)",
        'ra(d;A;ICRS;J2000;2000)','dec(d;D;ICRS;2000)',
        'plx','rvz_radvel','rvz_type','z_value','fe_h',
        "ids"
    )
    result_table_simbad = custom_simbad.query_object(object_name)

    if result_table_simbad is None:
        return None

    column_mappings = {
        "MAIN_ID": "Main_name",
        "IDS": "IDS_name",
        "OTYPE": "object_type",
        "SP_TYPE": "SP_type",
        "RA": "ra",
        "DEC": "dec",
        "FLUX_U": "mag_U",
        "FLUX_B": "mag_B",
        "FLUX_V": "mag_V",
        "FLUX_R": "mag_R",
        "FLUX_I": "mag_I",
        "FLUX_G": "mag_G",
        "FLUX_J": "mag_J",
        "FLUX_H": "mag_H",
        "FLUX_K": "mag_K",
        "FLUX_u": "mag_u",
        "FLUX_g": "mag_g",
        "FLUX_r": "mag_r",
        "FLUX_i": "mag_i",
        "FLUX_z": "mag_z",
        "Z_VALUE": "Z_value",
        "RVZ_RADVEL": "rvz_radvel",
        "PLX_VALUE": "parallax",
        "Fe_H_Teff": "Fe_H_Teff",
        "Fe_H_log_g": "Fe_H_log_g",
        "Fe_H_Fe_H": "Fe_H_Fe_H",
        "Fe_H_CompStar": "Fe_H_CompStar",
        "RA_d_A_ICRS_J2000_2000": "RA_d_A_ICRS_J2000_2000",
        "DEC_d_D_ICRS_2000": "DEC_d_D_ICRS_2000"
    }
    object_info_simbad = {key: None for key in column_mappings.values()}

    for column_name, key in column_mappings.items():
        if column_name in result_table_simbad.colnames:
            if key == "IDS_name":
                ids_values = result_table_simbad[column_name][0].split("|")
                object_info_simbad[key] = next((name.strip() for name in ids_values if name.startswith("NAME")), "")
            else:
                object_info_simbad[key] = result_table_simbad[column_name][0]
    if object_info_simbad["parallax"] is not None and object_info_simbad["parallax"] >10:
        object_info_simbad["distance_pc"] = 1 / (object_info_simbad["parallax"] / 1000)
        object_info_simbad["distance_ly"] = object_info_simbad["distance_pc"] * 3.26156

    object_info_simbad = {key: value for key, value in object_info_simbad.items() if value is not None and value != 'masked' and value != "" and value != 0}

    return object_info_simbad

class DateCalculator:
    """
    A class for calculating Astropy Time and Heliocentric Julian Date.

    Attributes:
    - greenwich (EarthLocation): The Earth location for Greenwich.

    Methods:
    - calculate_astropy_time(date)
    - calculate_hjd(date, RA, DEC)
    """

    def __init__(self):
        """
        Initialize the DateCalculator.

        Attributes:
        - greenwich (EarthLocation): The Earth location for Greenwich.
        """
        self.greenwich = EarthLocation.of_site('greenwich')

    async def calculate_astropy_time(self, date):
        """
        Calculate Astropy Time object from the given date.

        Args:
        - date (str): The date string.

        Returns:
        - astropy_date (Time): Astropy Time object.

        Usage:
        >>> astropy_time = DateCalculator().calculate_astropy_time('2023-01-01 12:00:00')
    
        """
        try:
            redate_object = parser.parse(date)
            date_str = redate_object.strftime("%Y-%m-%d %H:%M:%S")
            astropy_date = Time(date_str, format="iso", scale="utc", location=self.greenwich)
            return astropy_date
        except ValueError as e:
            raise ValueError(f"Error calculating Astropy Time: {str(e)}")

    async def calculate_hjd(self, date, RA, DEC):
        """
        Calculate Heliocentric Julian Date (HJD) from the given date, right ascension, and declination.

        Args:
        - date (str): The date string.
        - RA (str): Right ascension.
        - DEC (str): Declination.

        Returns:
        - helio_jd (float): Heliocentric Julian Date.

        Usage:
        >>> hjd = DateCalculator().calculate_hjd('2023-01-01 12:00:00', '10h30m00s', '+45d00m00s')
        """
        try:
            astropy_date = self.calculate_astropy_time(date)
            ip_peg = SkyCoord(ra=RA, dec=DEC, unit=(u.deg, u.deg), frame='icrs')
            ltt_helio = astropy_date.light_travel_time(ip_peg, 'heliocentric')
            helio_jd = astropy_date.jd + ltt_helio.value
            return helio_jd
        except ValueError as e:
            raise ValueError(f"Error calculating HJD: {str(e)}")
        
geolocator = Nominatim(user_agent="my-app", timeout=15)       

async def get_observer_and_local_time(city: str):
    location = geolocator.geocode(city, timeout=15)
    lat = location.latitude
    long = location.longitude

    # Get timezone
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=lat, lng=long)
    timezone = pytz.timezone(timezone_str)

    earth_location = EarthLocation(lat=lat, lon=long)
    observer = Observer(location=earth_location, name=city, timezone=timezone)

    # Get current local time at the location
    local_time = datetime.now(timezone)

    return observer, local_time


  
async def get_sunset_sunrise(observer:astroplan.observer.Observer,date:str=None):
    """
    Args:
        - observer (Observer): The observer for which the sunset and sunrise times are calculated. Must use get_observer("city")
        - date (str, optional): The date of the observation. Defaults to `datetime.utcnow()`.

    Returns:
        - tuple (collections.namedtuple): A tuple containing the day and night duration of the city
    
    Usage:
        >>> get_observer("istanbul")
        <Observer: name='unnamed', location (lon, lat, el)=(+28.9831228 deg, +41.0082376 deg, 0.0 m), timezone=<UTC>>
        >>> get_sunset_sunrise(get_observer("istanbul"))
        NightDayInfo(sunrise=<Time object: scale='utc' format='jd' value=2460289.6995399697>, sunset=<Time object: scale='utc' format='jd' value=2460290.1293182494>, night_duration=<TimeDelta object: scale='tai' format='jd' value=-0.42977827973663807>, day_duration=<TimeDelta object: scale='tai' format='jd' value=1.429778279736638>)    
        >>> deneme=get_sunset_sunrise(get_observer("istanbul")).sunrise
        >>> print(deneme.datetime)
        2023-12-11 04:47:20.700451
    """
    if date is not None:
        time = await DateCalculator().calculate_astropy_time(date)
    else:
        time = await DateCalculator().calculate_astropy_time(f"{datetime.utcnow()}")
    observer.date = time
    # Gün doğumu ve gün batımı zamanlarını al
    sunrise = observer.sun_rise_time(time, which='next',horizon=-10*u.deg)
    sunset = observer.sun_set_time(time, which='next',horizon=-10*u.deg)
    if sunset>sunrise:
        sunset = observer.sun_set_time(time, which='previous',horizon=-6*u.deg)
    night_duration=sunrise-sunset
    day_duration = timedelta(hours=24) - night_duration
    from collections import namedtuple
    NightDayInfo = namedtuple('NightDayInfo', ['sunrise', 'sunset', 'night_duration', 'day_duration'])

    return NightDayInfo(sunrise, sunset, night_duration , day_duration)

async def create_altitude_plot(object_name:str, RA:str, DEC:str, observer:astroplan.observer.Observer,date:str=None):
    """
    Creates an altitude plot for a celestial object's visibility.

    Args:
       - object_name (str): The name of the celestial object.
       - RA (str): The right ascension of the object in hourangle.
       - DEC (str): The declination of the object in degrees.
       - observer (Observer): The observer for which the visibility plot is generated. Must use get_observer("city")
       - date (str, optional): The date of the observation. Defaults to `None`.
    Returns:
       - PIL.Image.Image: An image containing the altitude plot.

    Usage:
        >>> create_altitude_plot("M1",'10h30m00s', '+45d00m00s',get_observer("istanbul"))
        <PIL.PngImagePlugin.PngImageFile image mode=RGBA size=640x480 at 0x...>
    """
    #time use date time formating
    
    if date is not None:
        time = await DateCalculator().calculate_astropy_time(date)
    else:
        time =await DateCalculator().calculate_astropy_time(f"{datetime.utcnow()}")

    object_coord = SkyCoord(ra=RA, dec=DEC,  unit=(u.hourangle, u.deg), frame='icrs')
    target = FixedTarget(coord=object_coord, name=object_coord)
    observer.date=time
    plot_altitude(target, observer, time, brightness_shading=True)

    # Add a title to the plot
    plt.title(f'Visibility Plot for {object_name.upper()} in {str(observer.name).capitalize()}')
    # Add a legend
    plt.legend([object_name])
    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    result_image = buffer.getvalue()
    airmass_plot = io.BytesIO(result_image)
    return airmass_plot

#is_observble 
async def is_observable_object(RA:str, DEC:str,observer:astroplan.observer.Observer,date:str=None):
    """
    Checks if a celestial object is observable from a city.

    Args:
        - RA (str): The right ascension of the object in hourangle.
        - DEC (str): The declination of the object in degrees.
        - observer (Observer): The observer for which the visibility plot is generated. Must use get_observer("city")
        - date (str, optional): The date of the observation. Defaults to `None`.
    
    Returns:W
        - bool: `True` if the object is observable, `False` otherwise.

    Usage:
        >>> is_observable_object('10h30m00s', '+45d00m00s',get_observer("istanbul"))
        True
    """
    sun_set = await get_sunset_sunrise(observer, date)
    time_range = Time([sun_set.sunset, sun_set.sunrise])
    object_coord = SkyCoord(ra=RA, dec=DEC, unit=(u.hourangle, u.deg), frame='icrs')
    target = FixedTarget(coord=object_coord, name=object_coord)
    constraints = [AltitudeConstraint(12*u.deg, 89.6*u.deg)]
    return is_always_observable(constraints, observer, target, time_range=time_range)


#example 

async def create_sky_plot(object_names: list, RAs: list, DECs: list, observer:astroplan.observer.Observer, date: str = None) -> Image.Image:
    """
    Creates a sky plot for a list of celestial objects.

    Args:
        - object_names (list): A list of object names.
        - RAs (list): A list of right ascensions in hourangle.
        - DECs (list): A list of declinations in degrees.
        - city (str): The name of the city for which the visibility plot is generated.
        - date (str, optional): The date of the observation. Defaults to `None`.
    
    Returns:
        PIL.Image.Image: An image containing the sky plot.

    Usage:
        >>> create_sky_plot(["M1", "M2"], ['10h30m00s', '+45d00m00s'], ['12h50m00s', '+05d00m00s'],get_observer("istanbul"))
        <PIL.JpegImagePlugin.JpegImageFile image mode=RGB size=640x480 at 0x...>
    """
    if date is not None:
        time = await DateCalculator().calculate_astropy_time(date)
    else:
        time = await DateCalculator().calculate_astropy_time(f"{datetime.utcnow()}")
    
    observer.date=time
    # Calculate 12 hours ahead
    end_time = time + 12 * u.hour

    # Create time window
    time_window = time + (end_time - time) * np.linspace(0, 1, 12)

    for object_name, RA, DEC in zip(object_names, RAs, DECs):
        object_coord = SkyCoord(ra=RA, dec=DEC,  unit=(u.deg, u.deg), frame='icrs')
        target = FixedTarget(coord=object_coord, name=object_name)
        plot_sky(target, observer, time_window, style_kwargs={'marker': '*'})

    plt.legend(loc='center left', bbox_to_anchor=(1.25, 0.5))
    plt.title(f'Sky Plot for {", ".join(object_names)} in {str(observer.name).capitalize()}')
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='JPEG')
    buffer.seek(0)
    plt.close()

    result_image = buffer.getvalue()
    altitude_plot = io.BytesIO(result_image)
    return altitude_plot

async def create_area_image(object_name:str,RA:str,DEC:float):
    """
    Creates an image of the area around a celestial object.

    Args:
        - object_name (str): The name of the celestial object.
        - RA (str): The right ascension of the object in hourangle.
        - DEC (str): The declination of the object in degrees.
    
    Returns:
        - PIL.Image.Image: An image containing the area around the celestial object.
    
    Usage:
        >>> create_area_image("M1",83.63308333,22.0145)
        <PIL.JpegImagePlugin.JpegImageFile image mode=RGB size=79x79 at 0x...>
    """
    object_coord = SkyCoord(ra=RA, dec=DEC,  unit=(u.hourangle, u.deg), frame='icrs')
    target = FixedTarget(coord=object_coord,name=object_name)
    try:
        plot_finder_image(target, fov_radius=60*u.arcmin, reticle=True)
    except:
        plot_finder_image(target, fov_radius=60*u.arcmin, reticle=True)

    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='JPEG')
    buffer.seek(0)
    plt.close()

    result_image = buffer.getvalue()
    area_plot = io.BytesIO(result_image)
    return area_plot

async def observable_star_sunset_sunrise(data:pd.DataFrame):
    """
    Creates a plot of the observable stars between sunset and sunrise.

    Args:
        - data (pd.DataFrame): The data of the stars.
        
    Returns:
        - PIL.Image.Image: An image containing the plot.
    
    Required Column Names
    ---------------------
    - sunset_nautical_dawn
    - sunrise_nautical_dawn
    - first_min_phase_date
    - end_min_phase_date
    - total_phase
    - is_observable
    - good_for_observation
    - Star Name
    
    Usage:
        >>> import pandas as pd
        >>> df = pd.read_csv('data.csv')
        >>> observable_star_sunset_sunrise(df)
        <PIL.PngImagePlugin.PngImageFile image mode=RGBA size=960x640 at 0x...>
        >>> image = Image.open(plot_buffer)
        >>> # Display the image
        >>> plt.imshow(image)
        >>> plt.axis('off')  # Disable axes
        >>> plt.show()
    """

    # Filter the data for stars that are observable and good for observation
    data['sunset_nautical_dawn'] = pd.to_datetime(data['sunset_nautical_dawn'])
    data['sunrise_nautical_dawn'] = pd.to_datetime(data['sunrise_nautical_dawn'])
    data['first_min_phase_date'] = pd.to_datetime(data['first_min_phase_date'])
    data['end_min_phase_date'] = pd.to_datetime(data['end_min_phase_date'])

    # Filter the data for stars that are observable and good for observation
    observable_stars = data[data['is_observable'] & data['good_for_observation']]

    # Setting up the plot with the specified requirements
    fig, ax = plt.subplots(figsize=(15, 10))
    observable_star_names = observable_stars['Star Name'].unique()
    y_values_observable = {name: i for i, name in enumerate(observable_star_names)}

    #A value is trying to be set on a copy of a slice from a DataFrame.
    pd.options.mode.chained_assignment = None 
    observable_stars.loc[:, 'y_value'] = observable_stars['Star Name'].map(y_values_observable)

    norm = Normalize(vmin=observable_stars['total_phase'].min(), vmax=observable_stars['total_phase'].max())
    cmap = mcolors.LinearSegmentedColormap.from_list("", ["black", "blue", "cyan"])

    for _, row in observable_stars.iterrows():
        # Color for the line based on total_phase
        line_color = cmap(norm(row['total_phase']))

        # Draw line between the points
        line1,= ax.plot([row['first_min_phase_date'], row['end_min_phase_date']], [row['y_value'], row['y_value']], color=line_color, linewidth=2, zorder=2,label="Period")

        # Plot first and end min phase points
        line2 = ax.scatter(row['first_min_phase_date'], row['y_value'], color='green', s=100, marker="<", zorder=3, label="First Min Phase")  # First min phase
        if row['sunset_nautical_dawn'] <= row['end_min_phase_date'] <= row['sunrise_nautical_dawn']:
            line3 = ax.scatter(row['end_min_phase_date'], row['y_value'], color='red', s=100, marker=">", zorder=3, label="End Min Phase")  # End min phase

    # Set y-axis labels
    ax.set_yticks(ticks=range(len(observable_star_names)))
    ax.set_yticklabels(observable_star_names)

    # Set the x-axis limits
    min_sunset = observable_stars['sunset_nautical_dawn'].min()
    max_sunrise = observable_stars['sunrise_nautical_dawn'].max()

    ax.set_xlim(min_sunset, max_sunrise)

    # Format x-axis to display dates
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))

    # Rotate date labels for better readability
    plt.xticks(rotation=45)
    ax.set_xlabel('Date and Time [UTC] (Sunset and Sunrise according to Nautical dawn)')
    ax.set_ylabel('Star Name')
    ax.set_title('Observable Stars Between Sunset and Sunrise (Line Colored by Total Phase)',fontsize=15)
    ax.grid(True)

    # Adding legends
    ax.legend(handles=[line1,line2,line3], loc='upper right', bbox_to_anchor=(1.1, 1.15))

    # Add a colorbar for total phase
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = plt.colorbar(sm)
    cbar.set_label('Max Phase in 1 Night')

    plt.tight_layout()

    # Save the plot to a bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    result_image = buffer.getvalue()
    observable_star_sunset_sunrise = io.BytesIO(result_image)
    return observable_star_sunset_sunrise

#buffer object show
#night day duration with ephem 

#tests __main__
"""
if __name__ == "__main__":
    #test all function 
    #test SolarSystemObjects
    SS_object_name = "venus"  # Replace with the solar system objects  you're interested in
    SS_object_info = SolarSystemObjects(SS_object_name).get_formatted_data()
    print(SS_object_info)
    print("*" * 50)
    #test simbad
    object_info = get_object_info_simbad("ygnus A")
    print(object_info)
    print("*" * 50)

    #test date calculator
    astropy_time = DateCalculator().calculate_astropy_time('2023-01-01 12:00:00')
    print(astropy_time)
    print("*" * 50)

    hjd = DateCalculator().calculate_hjd('2023-01-01 12:00:00', '10h30m00s', '+45d00m00s')
    print(hjd)
    print("*" * 50)

    #test observer
    observer_istanbul = get_observer("istanbul")
    print(observer_istanbul)
    print("*" * 50)

    #test sunset sunrise
    result = get_sunset_sunrise(observer_istanbul)
    print(result)
    print("*" * 50)

    #test altitude plot
    altitude_plot = create_altitude_plot("M1",83.63308333,22.0145,observer_istanbul)
    print(altitude_plot)
    print("*" * 50)
    #test is observable
    print(is_observable_object("05 13 24.4522","+37 05 59.235",observer_istanbul))
    print("*" * 50)
    #test sky plot
    sky_plot = create_sky_plot(["M1", "M2"], [83.63308333, 100.9514], [22.0145, 02.0145], observer_istanbul)
    print(sky_plot)
    print("*" * 50)
    #test area plot
    area_plot = create_area_image("M1",83.63308333,22.0145)
    print(area_plot)
    print("*" * 50)
"""