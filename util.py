from base64 import b64decode, b64encode
from hashlib import sha256
import math
import requests
from urllib import request
import time
from datetime import datetime
import sys
import random
import platform
from shapepoint import ShapePoint
from zipfile import ZipFile

EARTH_RADIUS_IN_FEET = 20902231
FEET_PER_LAT_DEGREE = 364000
FEET_PER_LONG_DEGREE = 288200
FEET_PER_MILE = 5280

debug_callback = None

# UI colors
LIGHT            = 'ffc0c0c0'
DARK             = 'ff000020'
DANGER           = 'ffa00000'
MAP_POINT        = 'ff00ff00'
MAP_POINT_MISSED = 'ffff0000'

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    STANDARD = '\033[37m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def to_b64(s):
    return b64encode(str(s).encode('utf-8')).decode('utf-8')

def from_b64(s):
    return b64decode(s).decode('utf-8')

def signum(x):
    return math.copysign(1, x)

def get_current_time_millis():
    return int(round(time.time() * 1000))

def now():
    return get_current_time_millis()

def get_seconds_since_midnight(seconds = None):
    if seconds is None:
        now = datetime.now()
    else:
        now = datetime.fromtimestamp(seconds)

    return int((now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())

def hhmmss_to_seconds(s):
    arr = s.split(':')
    seconds = int(arr[0]) * 60 * 60
    seconds += int(arr[1]) * 60
    seconds += int(arr[2])
    return seconds

def seconds_to_hhmm(s):
    hours = int(s / 60 / 60)
    s -= hours * 60 * 60
    minutes = int(s / 60)
    return f'{hours}:{str(minutes).zfill(2)}'

def seconds_to_hhmmss(s):
    hours = int(s / 60 / 60)
    s -= hours * 60 * 60
    minutes = int(s / 60)
    s -= minutes * 60
    return f'{hours}:{str(minutes).zfill(2)}:{str(s).zfill(2)}'

def seconds_to_ampm_hhmm(s):
    ampm = 'am'
    hours = int(s / 60 / 60)
    s -= hours * 60 * 60

    if hours == 0:
        hours = 12
    else:
        if hours >= 12:
            ampm = 'pm'
            hours -= 12

    minutes = int(s / 60)
    s -= minutes * 60
    return f'{hours}:{str(minutes).zfill(2)} {ampm}'

# get whole seconds since 01/01/1970 for input string `s`
# `s` is assumed to be one of the following:
# - `None`: get seconds since epoch for current date and time
# - yyyymmdd: get seconds since epoch for given date
# - yyyy-mm-dd: get seconds since epoch for given date
def get_epoch_seconds(s = None):
    if s is None:
        return int(datetime.now().timestamp())
    else:
        t = s.replace('-', '')
        return int(datetime.strptime(t, '%Y%m%d').timestamp())

def get_feet_as_lat_degrees(feet):
    return feet / FEET_PER_LAT_DEGREE

def get_feet_as_long_degrees(feet):
    return feet / FEET_PER_LONG_DEGREE

def get_display_distance(feet):
    if feet < FEET_PER_MILE:
        return f'{feet} FEET'
    elif feet < 10 * FEET_PER_MILE:
        v = feet / FEET_PER_MILE
        return f'{v:.1f} MILES'
    else:
        return f'{int(feet / FEET_PER_MILE)} MILES'

# converts coordinates from lat/long to x/y given
# display width and height, an area instance
# and a shapepoint instance
def lat_long_to_x_y(display_width, display_height, a, p):
    fraction_lat = a.get_lat_fraction(p.lat)
    fraction_long = a.get_long_fraction(p.lon);

    ratio = a.get_aspect_ratio();
    return (int(display_width * fraction_long), int(display_height * fraction_lat))

# return the Haversine distance between two lat/long
# pairs in feet
def haversine_distance(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lam = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) * math.sin(delta_phi / 2)
        + math.cos(phi1) * math.cos(phi2)
        * math.sin(delta_lam / 2) * math.sin(delta_lam / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_IN_FEET * c

def distance(x0, y0, x1, y1):
    xd = x1 - x0
    yd = y1 - y0

    return math.sqrt(xd * xd + yd * yd)

def get_distance_string(feet):
    if (feet < FEET_PER_MILE):
        return f'{feet} ft'
    else:
        return f'{int(feet / FEET_PER_MILE)} mi'

def set_debug_callback(cb):
    global debug_callback
    debug_callback = cb

def debug(s):
    ts = datetime.now().strftime('%H:%M:%S ')

    if debug_callback is None:
        print(ts + str(s))
        sys.stdout.flush()
    else:
        debug_callback(s)

def error(s):
    print(f'*** {s}')
    sys.stdout.flush()

def early_exit():
    error('early exit')
    exit(1)

def to_decimal(v, dir):
    #debug('to_decimal()')
    #debug(f'- v: {v}')
    slen = len(v)
    #debug(f'- slen: {slen}')
    min = v[-9:]
    #debug(f'- min: {min}')
    deg = v[0:len(v) - len(min)]
    #debug(f'- deg: {deg}')
    dec = int(deg) + float(min) / 60
    #debug(f'- dec: {dec}')

    mul = 1
    if dir == 'S' or dir == 'W':
        mul = -1

    return dec * mul

def get_random_int(low, high):
    return int(low + (random.random() * (high - low)))

def get_random_point(area):
    lat_delta = area.bottom_right.lat - area.top_left.lat
    lon_delta = area.bottom_right.lon - area.top_left.lon

    return ShapePoint(
        area.top_left.lat + (random.random() * lat_delta),
        area.top_left.lon + (random.random() * lon_delta)
    )

def sign(str, sk):
    #debug('elliptic_curve.sign()')
    #debug(f'- str: {str}')
    #debug(f'- sk: {sk}')
    try:
        sig = sk.sign(str.encode('utf-8'), hashfunc=sha256)
        #debug(f'- sig: {sig}')
        return b64encode(sig).decode('utf-8')
    except:
        debug(f'*** signature failure: {sys.exc_info()[0]}')
        return None

def get_property(filename, name):
    key = name + ': '

    with platform.get_text_file_contents(filename) as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            i = line.find(key)
            if i == 0:
                return line[len(key):]

    return None


def update_cache_if_needed(cache_path, url):
    debug(f'update_cache_if_needed()')
    debug(f'- cache_path: {cache_path}')
    debug(f'- url: {url}')

    platform.ensure_resource_path(cache_path)

    file_name = cache_path + 'gtfs.zip'

    if url.startswith('http://') or url.startswith('https://'):
        headers = {'User-Agent': 'python-3'}
        r = requests.head(url, headers=headers, allow_redirects=True)
        debug(f'- r.headers: {r.headers}')
        url_time = r.headers.get('last-modified', None)
        debug(f'- url_time: {url_time}')

        if url_time is None:
            debug(f'* can\'t access static GTFS URL {url}, aborting cache update')
            return

        url_date = datetime.strptime(url_time, '%a, %d %b %Y %H:%M:%S %Z')
        file_date = datetime.fromtimestamp(0, url_date.tzinfo)
        if platform.resource_exists(file_name):
            file_date = datetime.fromtimestamp(platform.get_mtime(file_name))

        if datetime.timestamp(url_date) <= datetime.timestamp(file_date):
            debug('+ gtfs.zip up-to-date, nothing to do')
            return

        debug('+ gtfs.zip out of date, downloading...')

        r = requests.get(url)
        debug(f'- r.status_code: {r.status_code}')

        platform.write_to_file(file_name, r.content)
    else:
        # assume url is in fact a path to a local file
        ts_archive = platform.get_mtime(url)
        try:
            ts_cache = platform.get_mtime(file_name)
        except:
            print(f'* cached gtfs file {file_name} not accessible, forcing update')
            ts_cache = -1

        if ts_archive < ts_cache:
            debug('+ gtfs.zip up-to-date, nothing to do')
            return

        platform.copy_file(url, file_name)

    debug('+ gtfs.zip downloaded')
    names = ['calendar.txt', 'routes.txt', 'stops.txt', 'stop_times.txt', 'shapes.txt', 'trips.txt']
    platform.unpack_zip(file_name, cache_path, names)

