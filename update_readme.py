import sys
import ssl
import json
import posixpath
import urllib.request

def update_readme(lat,lon,open_weather_api_key):
    fid = open("README.md","w")
    with open('readme.ini','r') as f:
        fid.write(f.read())

    # get weather from UW atmos roof station
    roof_url = 'https://roof.atmos.washington.edu/roof.txt'
    roof_request = urllib.request.Request(roof_url)
    response = urllib.request.urlopen(roof_request,context=ssl.SSLContext())
    roof_content = response.read().decode('utf-8').split()
    roof_time = roof_content[0]
    roof_temperature = roof_content[1]
    roof_wind_direction = roof_content[2]
    roof_wind_speed = roof_content[3]
    roof_pressure = roof_content[4]
    roof_relative_humidity = roof_content[5]

    # get weather from open weather API at coordinates of UW atmos building
    args = (lat,lon,open_weather_api_key)
    open_url = ['http://api.openweathermap.org','data','2.5',
        'weather?lat={0}&lon={1}&appid={2}'.format(*args)]
    open_request = urllib.request.Request(posixpath.join(*open_url))
    response = urllib.request.urlopen(open_request,context=ssl.SSLContext())
    open_content = json.loads(response.read())
    open_temperature = round(9.0*open_content['main']['temp']/5.0 - 459.67)
    open_pressure = open_content['main']['pressure']
    open_humidity = open_content['main']['humidity']
    open_wind_speed = round(3600.0*open_content['wind']['speed']/1609.34)
    compass = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW',
        'WSW','W','WNW','NW','NNW','N']
    compass_point = round(16.0*open_content['wind']['deg']/360.0)
    open_wind_direction = compass[compass_point]

    # print current weather at the University of Washington
    # include link to UW Red Square live weather cambots
    fid.write("\n#### [Current Weather at the University of Washington]")
    fid.write("(https://www.washington.edu/cambots/camera1_l.jpg)\n")
    descriptions = []
    icons = []
    for i,ow in enumerate(open_content['weather']):
        descriptions.append(ow['description'].capitalize())
        p=['http://openweathermap.org','img','wn','{0}@2x.png'.format(ow['icon'])]
        icons.append('![weather]({0})'.format(posixpath.join(*p)))
    fid.write('{0}  \n'.format(''.join(icons)))
    fid.write('**Conditions:** {0}  \n'.format(', '.join(descriptions)))
    # use open weather data if roof station returns invalid data
    if (roof_pressure == '0%'):
        fid.write('**Temperature:** {0:0.0f}F  \n'.format(open_temperature))
        fid.write('**Humidity:** {0:0.0f}%  \n'.format(open_humidity))
        fid.write('**Wind:** {0:0.0f}mph {1}  \n'.format(open_wind_speed,open_wind_direction))
        fid.write('**Pressure:** {0:0.0f}mb  \n'.format(open_pressure))
    else:
        fid.write('**Temperature:** {0}  \n'.format(roof_temperature))
        fid.write('**Humidity:** {0}  \n'.format(roof_relative_humidity))
        fid.write('**Wind:** {0} {1}  \n'.format(roof_wind_speed,roof_wind_direction))
        fid.write('**Pressure:** {0}  \n'.format(roof_pressure))

#-- run update readme with seattle weather program
if __name__ == '__main__':
	update_readme(47.653889, -122.309444, sys.argv[1])
