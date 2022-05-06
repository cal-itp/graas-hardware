import os
import RPi.GPIO as GPIO
from config import Config
from inference import TripInference
from grid import Grid
import ecdsa
import json
from datetime import datetime
import sys
from urllib import request, parse
import requests
from requests import get
import serial
import time
import traceback
import uuid
from area import Area
from shapepoint import ShapePoint
import util
import util
import rcanvas
import socket
import threading
from rcanvas import RCanvas
from led import set_led_pattern, start_led
from acc import start_acc, acc_snapshot

APP_VERSION = 'graas 0.1 (gulper)'
INVALID_GPS = 9999
startseconds = int(util.get_current_time_millis() / 1000)
hostname = None
config = None

def initialize_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

def start_waveshare():
    # D6 controls Waveshare power
    # when so jumpered
    GPIO.setup(6, GPIO.OUT)
    GPIO.output(6, GPIO.HIGH)

def get_agent_string():
    return f'raspberry {hostname} {APP_VERSION}'

#def dms_to_decimals(deg, min, sec):
#    return deg + util.sign(deg) * (min / 60) + util.sign(deg) * (sec / 3600)

def send_gps_data(gps, trip_id, sk):
    #util.debug('send_gps_data()')
    #util.debug(f'- gps: {gps}')
    msg = {
        'uuid': config.get_property('uuid'),
        'agent': get_agent_string(),
        'timestamp': int(util.get_current_time_millis() / 1000),
        'lat': gps['lat'],
        'long': gps['lon'],
        'speed': gps['speed'],
        'heading': gps['heading'],
        'accuracy': gps['accuracy'],
        'trip-id': trip_id,
        'agency-id': config.get_property('agency_name'),
        'vehicle-id': config.get_property('vehicle_id'),
        'pos-timestamp': gps['timestamp']
    }

    data = json.dumps(msg, separators=(',', ':'))
    #util.debug(f'- data: {data}')
    sig = util.sign(data, sk)

    obj = {
        'data': msg,
        'sig': sig
    }

    #util.debug(f'- obj: {json.dumps(obj)}')

    data = json.dumps(obj, separators=(',', ':')).encode('utf-8')
    url = 'https://lat-long-prototype.wl.r.appspot.com/new-pos-sig'
    headers = {'Content-Type': 'application/json'}
    resp = None

    try:
        util.debug(f'+ requests.post() >')
        resp = requests.post(url, headers = headers, timeout = 5)
        resp_code = resp.status_code
        util.debug(f'+ requests.post() <')
        #util.debug(f'- resp_code: {resp_code}')
    except:
        resp_code = 999
        util.debug(util.bcolors.FAIL + '* network exception' + util.bcolors.STANDARD)

    server_response = util.bcolors.FAIL + str(resp_code) + util.bcolors.STANDARD
    if resp_code == 200:
        server_response = util.bcolors.OKGREEN + 'ok' + util.bcolors.STANDARD
    util.debug(f'- server_response: {server_response}')

    if resp is None:
        return None
    else:
        return resp.json()

def send_at(ser, command, back, timeout):
    rec_buff = ''
    ser.write((command+'\r\n').encode())
    time.sleep(timeout)
    if ser.inWaiting():
        time.sleep(0.01 )
        rec_buff = ser.read(ser.inWaiting())
    if rec_buff != '':
        if back not in rec_buff.decode():
            util.debug(command + ' ERROR')
            util.debug(command + ' back:\t' + rec_buff.decode())
            return None
        else:
            return rec_buff.decode()
    else:
        util.debug('GPS is not ready')
        return 0

def read_gps_data_from_network():
    #util.debug('read_gps_data_from_network()')

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock:
        #util.debug(f'- client_sock: {client_sock}')
        client_sock.settimeout(5)

        try:
         client_sock.connect(('192.168.50.1', 60660))
        except:
         util.debug('* cannot connect to network GPS soure')
         return None

        for i in range(10):
         data = client_sock.recv(1024)
         #util.debug(f'- len(data): {len(data)}')
         if len(data) > 0:
             decoded=data.decode('ascii')
             lines = decoded.splitlines(1)

             for line in lines:
                 #util.debug(f'- line: {line}')
                 tok = line.split(',')
                 if tok[0] == '$GPRMC' and len(tok)>6:
                     if tok[3]:
                        lat = util.to_decimal(tok[3], tok[4])
                        lon = util.to_decimal(tok[5], tok[6])
                        util.debug(f'network GPS: ({lat}, {lon})')

                        return {
                            'lat': lat,
                            'lon': lon,
                            'speed': -1,
                            'heading': -1,
                            'timestamp': -1,
                            'accuracy': -1
                        }
         else:
             break

        #client_sock.close()
        return None

# +CGPSINFO:[<lat>],[<N/S>],[<log>],[<E/W>],[<date>],[<UTC time>],[<alt>],[<speed>],[<course>]
# 3832.682076,N,12142.488254,W,280521,203223.0,6.2,0.0,303.7
def read_gps_data(ser):
    answer = send_at(ser, 'AT+CGPSINFO','+CGPSINFO: ',1)
    lines = answer.splitlines()
    #util.debug(f'- lines: {lines}')
    #util.debug(f'- len(lines): {len(lines)}')
    #util.debug(f'- lines[2]: {lines[2]}')
    if len(lines) < 2 or not lines[2].startswith('+CGPSINFO: '):
        return None

    nmea = lines[2][11:]
    #util.debug(f'- nmea: {nmea}')

    if nmea == ',,,,,,,,':
        return None

    tok = nmea.split(',')
    #util.debug(f'- len(tok): {len(tok)}')
    #util.debug(f'- tok: {tok}')

    try:
        ts = tok[4] + ' ' + tok[5][0:6] + ' PDT'
        #util.debug(f'- ts: {ts}')
        dt = datetime.strptime(ts, '%d%m%y %H%M%S %Z')
        #util.debug(f'- dt: {dt}')
    except:
        util.debug(f'* failed to parse date time: {ts}')
        return None

    try:
        gps = {
            'lat': util.to_decimal(tok[0], tok[1]),
            'lon': util.to_decimal(tok[2], tok[3]),
            'speed': tok[7],
            'heading': tok[8],
            'timestamp': int(dt.timestamp()) - 7 * 60 * 60,
            'accuracy': -1
        }
    except:
        util.debug(f'* failed to parse nmea: {nmea}')
        traceback.print_exc(file=sys.stdout)
        return None

    return gps


def excepthook(exctype, value, tb):
    util.debug('*** excepthook:')
    #util.debug('Type:', exctype)
    #util.debug('Value:', value)
    #util.debug('Traceback:', tb)
    tb.print_exc(file=sys.stdout)
    set_led_pattern([0.25, 0.25])

def main(config_file, network_gps):
    #sys.excepthook = excepthook

    socket.setdefaulttimeout(10)

    initialize_gpio()
    start_waveshare()
    start_led()
    set_led_pattern([0.3, 2.7])

    global config
    config = Config(config_file)

    util.debug('done')
    global hostname
    hostname = socket.gethostname()
    util.debug(f'- hostname: {hostname}')

    set_led_pattern([0.3, 0.3, 0.3, 2.1])
    os.system('sudo bluetoothctl power on')
    time.sleep(1)
    os.system('sudo bluetoothctl discoverable on')
    time.sleep(1)
    os.system('sudo bluetoothctl pairable on')
    time.sleep(1)
    os.system('sudo hciconfig hci0 piscan')

    util.debug('waiting for network...')

    network_sleep = os.getenv('NETWORK_SLEEP')
    if network_sleep is None:
        network_sleep = 120
    else:
        network_sleep = int(network_sleep)

    try:
        for i in range(network_sleep):
            util.debug(f'{network_sleep - i}')
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    set_led_pattern([0.3, 0.3, 0.3, 0.3, 0.3, 1.5])
    while True:
        code = 0
        try:
            util.debug(f'checking connectivity...')
            resp = requests.get('http://www.google.com', timeout=5)
            code = resp.status_code
        except:
            code = 999
            util.debug(f'* network exception')

        util.debug(f'- code: {code}')
        if code == 200:
            util.debug(f'done')
            break
        else:
            time.sleep(1)

    ser = serial.Serial('/dev/ttyS0', 115200)
    ser.flushInput()

    util.debug('enabling GPS...')
    send_at(ser, 'AT+CGPS=1,1','OK',1)

    inf = TripInference(
        '/home/pi/tmp/gtfs-cache/',
        config.get_property('static_gtfs_url'),
        config.get_property('agency_name'),
        config.get_property('vehicle_id'),
        15
    )

    set_led_pattern([0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.9])

    while True:
        util.debug(f'checking gps...')
        gps = None
        if network_gps:
            gps = read_gps_data_from_network()
        else:
            gps = read_gps_data(ser)
        #util.debug(f'- gps: {gps}')
        if not gps is None:
            util.debug(f'done')
            break
        else:
            time.sleep(1)

    set_led_pattern([3, 0])

    #util.debug(f'- pem:\n{pem}')
    sk = ecdsa.SigningKey.from_pem('-----BEGIN PRIVATE KEY-----\n' + config.get_property('agency_key') + '\n-----END PRIVATE KEY-----\n')
    assigned_trip_id = None

    while True:
        try:
            data = None
            if network_gps:
                data = read_gps_data_from_network()
            else:
                data = read_gps_data(ser)
            if data == None:
                util.error('gps not ready...')

                data = {
                    'lat': INVALID_GPS,
                    'lon': INVALID_GPS,
                    'speed': -1,
                    'heading': -1,
                    'accuracy': -1,
                    'timestamp': 0
                }

            if data['lat'] != INVALID_GPS:
                seconds = util.get_seconds_since_midnight()
                lat = data['lat']
                lon = data['lon']
                grid_index = inf.grid.get_index(lat, lon)
                util.debug(f'({data["lat"]}, {data["lon"]})')
                util.debug(f'current location: lat={lat} long={lon} seconds={seconds} grid_index={grid_index}')
                trip_id = str(inf.get_trip_id(lat, lon, seconds, assigned_trip_id))
                util.debug(f'- trip_id: {trip_id}')

            r = send_gps_data(data, trip_id, sk)
            assigned_trip_id = r.get('assigned_trip_id', None)
        except KeyboardInterrupt:
            send_at(ser, 'AT+CGPS=0','OK',1)
            if ser != None:
                ser.close()
        except:
            util.debug(f'* exception: {sys.exc_info()[0]}')
            traceback.print_exc()

        time.sleep(2)

if __name__ == '__main__':
    # -c <config file>: config file location
    # -n: acquire lat/long over network
    config_file = None
    network_gps = False

    for i in range(1, len(sys.argv)):
        if sys.argv[i] == '-n':
            network_gps = True

        if sys.argv[i] == '-c' and i < len(sys.argv) - 1:
            i += 1
            config_file = sys.argv[i]

    if config_file is None:
        util.debug(f'* usage: {sys.argv[0]} [-n] -c <config_file>')
        util.debug(f'    -n: acquire lat/long over network (currently hardwired to 192.168.50.1')
        util.debug(f'    -c <config_file>: give path to config file')

        exit(1)

    main(config_file, network_gps)
