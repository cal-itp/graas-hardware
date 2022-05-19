import inference
import os
import sys
import time
import util
from area import Area
from shapepoint import ShapePoint
from timer import Timer
import re
from datetime import datetime
from tee import Tee

def get_agency_id_from_path(path):
    ir = path.rfind('-', 0, len(path))
    if ir < 0:
        return None
    il = path.rfind('-', 0, ir)
    if il < 0:
        return None
    return path[il + 1:ir]

def main(data_files, cache_folder, output_folder, static_gtfs_url, simulate_block_assignment):
    util.debug(f'main()')
    util.debug(f'- data_files: {data_files}')
    util.debug(f'- cache_folder: {cache_folder}')
    util.debug(f'- output_folder: {output_folder}')
    util.debug(f'- static_gtfs_url: {static_gtfs_url}')

    util.debug(f'- inference.TripInference.VERSION: {inference.TripInference.VERSION}')

    pattern1 = '.*/([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-.*)/.*' # yyyy-mm-dd-hh-mm-<agency>
    pattern2 =  '.*([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]).*'     # yyyy-mm-dd-hh-mm

    tee = Tee()
    sys.stdout = tee
    last_dow = -1
    inf = None

    for df in data_files:
        expected_trip_id = None
        block_id = None

        if simulate_block_assignment:
            print(f'- df: {df}')
            i = df.rfind('/')

            if i > 0:
                metaf = df[0:i + 1] + 'metadata.txt'
                print(f'- metaf: {metaf}')
                expected_trip_id = util.get_property(metaf, 'trip-id')
                print(f'- expected_trip_id: >{expected_trip_id}<')

        m1 = re.search(pattern1, df)
        name = m1.group(1)

        m2 = re.search(pattern2, df)
        dow = get_dow(m2.group(1))
        epoch_seconds = util.get_epoch_seconds(m2.group(1))

        if dow != last_dow:
            tee.redirect()

            agency_id = get_agency_id_from_path(df)
            print(f'++ inferred agency ID: {agency_id}')

            inf = inference.TripInference(
                cache_folder,
                static_gtfs_url,
                agency_id,
                'test-vehicle-id',
                15,
                dow,
                epoch_seconds
            )

        last_dow = dow
        inf.reset_scoring()

        fn = output_folder + '/' + m1.group(1) + '-log.txt'
        print(f'-- fn: {fn}')
        tee.redirect(fn)

        with open(df, 'r') as f:
            for line in f:
                line = line.strip()

                #print(f'- line: {line}')
                tok = line.split(',')
                seconds = int(tok[0])
                day_seconds = util.get_seconds_since_midnight(seconds)
                lat = float(tok[1])
                lon = float(tok[2])
                grid_index = inf.grid.get_index(lat, lon)
                util.debug(f'current location: lat={lat} long={lon} seconds={day_seconds} grid_index={grid_index}')

                result = inf.get_trip_id(lat, lon, day_seconds, expected_trip_id)
                print(f'- result: {result}')

                trip_id = None

                if result is not None:
                    trip_id = result.get('trip_id', None)

                print(f'- trip_id: {trip_id}')

# assumes that filename contains a string of format yyyy-mm-dd
# returns day of week: 0-6 for Monday through Sunday if date string present, -1 otherwise
def get_dow(yyyymmdd):
    if yyyymmdd:
        date = datetime.strptime(yyyymmdd, '%Y-%m-%d')
        return date.weekday()
    else:
        return -1

def usage():
    print(f'usage: {sys.argv[0]} -o|--output-folder <output-folder> -c|--cache-foler <cache-folder> -u|--static-gtfs-url <static-gtfs-url> data-file [<data-files>]')
    exit(1)

if __name__ == '__main__':
    data_files = []
    cache_folder = None
    static_gtfs_url = None
    output_folder = os.getenv('HOME') + '/tmp'
    simulate_block_assignment = False
    i = 0

    while True:
        i += 1
        if i >= len(sys.argv):
            break

        arg = sys.argv[i]

        if arg == '-b' or arg == '--simulate-block-assignment':
            simulate_block_assignment = True
            continue

        if (arg == '-o' or arg == '--output-folder') and i < len(sys.argv) - 1:
            output_folder = sys.argv[i + 1]
            i += 1
            continue

        if (arg == '-c' or arg == '--cache-folder') and i < len(sys.argv) - 1:
            cache_folder = sys.argv[i + 1]
            i += 1
            continue

        if (arg == '-u' or arg == '--static-gtfs-url') and i < len(sys.argv) - 1:
            static_gtfs_url = sys.argv[i + 1]
            i += 1
            continue

        # assume arg is a data file
        data_files.append(sys.argv[i])

    if len(data_files) == 0 or cache_folder is None or static_gtfs_url is None:
        usage()

    main(data_files, cache_folder, output_folder, static_gtfs_url, simulate_block_assignment)