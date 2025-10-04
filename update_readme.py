import sys
import io
import re
import ssl
import json
import pandas
import datetime
import posixpath
import urllib.request

def convert_delta_time(delta_time, epoch1=None, epoch2=None, scale=1.0):
    """
    Convert delta time from seconds since epoch1 to time since epoch2

    Arguments
    ---------
    delta_time: seconds since epoch1

    Keyword arguments
    -----------------
    epoch1: epoch for input delta_time
    epoch2: epoch for output delta_time
    scale: scaling factor for converting time to output units
    """
    epoch1 = datetime.datetime(*epoch1)
    epoch2 = datetime.datetime(*epoch2)
    delta_time_epochs = (epoch2 - epoch1).total_seconds()
    # subtract difference in time and rescale to output units
    return scale*(delta_time - delta_time_epochs)

def update_readme(lat, lon, open_weather_api_key):
    # open readme file
    fid = open("README.md","w")
    with open('readme.ini','r') as f:
        fid.write(f.read())
    # update ICESat-2 shot count and Seattle weather
    update_shot_count(fid)
    # update_seattle_weather(fid, lat, lon, open_weather_api_key)
    # close readme file
    fid.close()

def update_shot_count(fid):
    # estimate ICESat-2 live shot count
    fid.write("\n#### [ICESat-2 Shot Counter](./assets/XAlIAMV.jpeg)  \n")
    # estimate of number of shots during prelaunch testing
    prelaunch_shots = 18419770000
    # number of GPS seconds between the GPS epoch and ATLAS SDP epoch
    atlas_sdp_gps_epoch = 1198800018.0
    # number of GPS seconds since the GPS epoch for first ATLAS data point
    atlas_gps_start_time = atlas_sdp_gps_epoch + 24710205.39202261
    # convert from GPS time to UNIX
    atlas_start_time = convert_delta_time(atlas_gps_start_time,
        epoch1=(1980,1,6,0,0,0),epoch2=(1970,1,1,0,0,0))
    # present day
    present_time = datetime.datetime.now(tz=datetime.timezone.utc)
    # regular expression string for extracting duration for cells with days
    rx = re.compile(r'(\d+)\sday[s]?,\s+(\d+)\:(\d+)\:(\d+)', re.VERBOSE)
    # try downloading and reading the ATLAS data gap file
    try:
        # download excel file with ATLAS data gaps
        atlas_data_gap_url = ['https://nsidc.org','sites','nsidc.org',
            'files','technical-references','ICESat-2_data_gaps.xlsx']
        atlas_request = urllib.request.Request(posixpath.join(*atlas_data_gap_url))
        response = urllib.request.urlopen(atlas_request,context=ssl.SSLContext())
        # read data gap file
        atlas_data_gap = pandas.read_excel(io.BytesIO(response.read()),header=2,
            engine='openpyxl')
        # parse each row and calculate the total data gap
        gap_duration = 0.0
        TIME = [None,None]
        for i,row in atlas_data_gap.iterrows():
            # end iteration if all are empty
            if pandas.isnull(row.values).all():
                break
            # extract start time
            try:
                TIME[0] = datetime.datetime.combine(row['DATE'],row['START (UTC)'])
            except TypeError:
                pass
            # extract end time
            try:
                TIME[1] = datetime.datetime.combine(row['DATE'],row['END (UTC)'])
            except TypeError:
                pass
            # duration for row
            DURATION = 0
            try:
                DURATION = datetime.timedelta(
                    hours=row['GAP DURATION'].hour,
                    minutes=row['GAP DURATION'].minute,
                    seconds=row['GAP DURATION'].second).total_seconds()
            except:
                days,hours,minutes,seconds = rx.findall(row['GAP DURATION']).pop()
                DURATION = datetime.timedelta(days=int(days),
                    hours=int(hours),minutes=int(minutes),
                    seconds=int(seconds)).total_seconds()

            # if there is a start and end time
            # there can be neither a start or end time for an empty row
            # there can be a start time and no end time for the start of a large gap
            # there can be a end time and no start time for the end of a large gap
            if DURATION:
                gap_duration += DURATION
            elif all(TIME):
                # calculate the duration between the start and end times
                DURATION = (TIME[1] - TIME[0]).total_seconds()
                # for short gaps near midnight the times may be on the same line
                if (DURATION < 0):
                    gap_duration += (DURATION + 86400.0)
                else:
                    gap_duration += DURATION
                # reset time list
                TIME = [None,None]
    except:
        # read json to get previously calculated gap duration
        # to be read in case of NSIDC downtime or other url access error
        with open('IS2-shot-count.json','r') as f:
            atlas_shot_count = json.load(f)
        gap_duration = float(atlas_shot_count['gap-duration'])

    # calculate total number of shots
    operational_time = present_time.timestamp() - atlas_start_time - gap_duration
    shot_total = 1e4*round(operational_time) + prelaunch_shots
    now = present_time.strftime('%Y-%m-%d %I%p %Z')
    fid.write('**Estimate:** {0:0.0f} (updated {1})  \n'.format(shot_total,now))
    # fid.write('**Note:** does not take into account shots from pre-launch testing  \n')
    # print to json for using as badge
    shot_dict = {"label": "ICESat-2 shots",
        "message":str(int(shot_total)),
        "start-time":str(atlas_start_time),
        "gap-duration":str(gap_duration),
        "last-modified":now}
    with open('IS2-shot-count.json','w') as f:
        print(json.dumps(shot_dict), file=f)

def update_seattle_weather(fid, lat, lon, open_weather_api_key):
    # get weather from UW atmos roof station
    # https://atmos.uw.edu/wp-content/themes/coenv-atmos/js/forecast_new.js
    roof_url = 'https://roof.atmos.washington.edu/roof.txt'
    try:
        roof_request = urllib.request.Request(roof_url)
        response = urllib.request.urlopen(roof_request,context=ssl.SSLContext())
        roof_content = response.read().decode('utf-8').split()
        roof_temperature = roof_content[1]
        roof_wind_direction = roof_content[2]
        roof_wind_speed = roof_content[3]
        roof_pressure = roof_content[4]
        roof_relative_humidity = roof_content[5]
    except:
        roof_pressure = ''

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
    if roof_pressure in ('','0%'):
        fid.write('**Temperature:** {0:0.0f}F  \n'.format(open_temperature))
        fid.write('**Humidity:** {0:0.0f}%  \n'.format(open_humidity))
        fid.write('**Wind:** {0:0.0f}mph {1}  \n'.format(open_wind_speed,open_wind_direction))
    else:
        fid.write('**Temperature:** {0}  \n'.format(roof_temperature))
        fid.write('**Humidity:** {0}  \n'.format(roof_relative_humidity))
        fid.write('**Wind:** {0} {1}  \n'.format(roof_wind_speed,roof_wind_direction))
    # use open weather data if roof station returns invalid pressure data
    if roof_pressure in ('','0%','0.00mb'):
        fid.write('**Pressure:** {0:0.0f}mb  \n'.format(open_pressure))
    else:
        fid.write('**Pressure:** {0}  \n'.format(roof_pressure))

# run update readme with ICESat-2 shot and Seattle weather program
if __name__ == '__main__':
	update_readme(47.653889, -122.309444, sys.argv[1])
