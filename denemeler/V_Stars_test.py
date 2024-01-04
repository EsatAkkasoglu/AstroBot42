#test this list Stars= ["V1918 Cyg", "EP And", "V700 Cyg", "VW Cep", "V402 Aur", "AP Tau", "SW Lac", "V1107 Cas", "AO Cam", "LR Cam", "RZ Tau", "GZ And", "ER Ori", "AH Aur", "V592 Per", "V410 Aur", "FBS 1345+796", "GK Cep", "DV Psc", "U Peg", "SW Lac", "RT Lmi", "EH Cnc", "V351 Peg", "LR Cun", "V376 And", "YY Eri", "YY Gem", "V471 Tau", "BS UMa", "XY Leo", "MR Del", "BV Eri"]

# Path: src/Astro_files/Stars_test.py
Stars= ["V1918 Cyg", "EP And", "V700 Cyg", "VW Cep", "V402 Aur", "AP Tau", "SW Lac", "V1107 Cas", "AO Cam", "LR Cam", "RZ Tau", "GZ And", "ER Ori", "AH Aur", "V592 Per", "V410 Aur", "FBS 1345+796", "GK Cep", "DV Psc", "U Peg", "SW Lac", "RT Lmi", "EH Cnc", "V351 Peg", "V376 And", "YY Eri", "YY Gem", "V471 Tau", "BS UMa", "XY Leo", "MR Del", "BV Eri"]

##queryFunctions use, Create a special folder for each star in a folder named VStars. add queryFunction outputs to the contents of each star's folder.

from src.Astro_files import queryFunctions
import os
import json 
import sys
sys.path.append('')
# test from queryFunctions 
"""#add tests
if __name__ == "__main__":
    print(SolarSystemObjects("Venus").get_formatted_data())
    print(get_object_info_simbad("96 Vir"))
    create_altitude_plot("M1",get_object_info_simbad("96 Vir")['RA_d_A_ICRS_J2000_2000'],22.0145,"istanbul").show()
    create_area_image("M1",83.63308333,22.0145).show()
    create_sky_plot(["M1","M2"],[83.63308333,100.9514],[22.0145,02.0145],"istanbul").show()"""

import numpy as np 
for star in Stars:
    star_directory = "src/Astro_files/VStars/" + star
    
    # Create the directory for each star if it doesn't exist
    if not os.path.exists(star_directory):
        os.makedirs(star_directory)
    
    # Get the data for each star
    data = queryFunctions.get_object_info_simbad(star)
    
    # Convert float32 and int32 values to float and int in the data dictionary
    for key, value in data.items():
        if isinstance(value, np.float32):
            data[key] = float(value)
        elif isinstance(value, np.int32):
            data[key] = int(value)
    
    # Create a text file for each star
    with open(os.path.join(star_directory, "data.json"), "w") as outfile:
        json.dump(data, outfile, indent=4)
    #create an altitude plot for each star
    # Create an altitude plot for each star
    import matplotlib.pyplot as plt 
    alt_plot = queryFunctions.create_altitude_plot(star, data['RA_d_A_ICRS_J2000_2000'], data['DEC_d_D_ICRS_2000'], "istanbul")
        # Save the PIL image to a file
    alt_plot.save(os.path.join(star_directory, "altitude.png"))

    
    #create an area image for each star
    area_image = queryFunctions.create_area_image(star, data['RA_d_A_ICRS_J2000_2000'], data['DEC_d_D_ICRS_2000'])
    area_image.save(os.path.join(star_directory, "area.png"))
    #create a sky plot for each star
    print(star,"bitti")
