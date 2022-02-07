from area import Area
import csv
import random
import geo_util
import util

MAX_LOCATION_DISTANCE = 30000 # feet
MAX_TIME_DISTANCE = 900 # seconds

"""
### TODO add cache for way points with predicted arrival times:
    - key: hash of min_file_offset, max_file_offset, start_time and end_time
    - value: grid index, list of way points with predicted arrival times
    - add class method set_current_grid_index(), which will flush all
      cache entries with non-matching grid index
    - in get_score(), either get way points from cache or create and
      put into cache
"""
class Segment:
    id_base = 0

    def __init__(self, trip_id, trip_name, trip_start_seconds, bounding_box, start_time, end_time, min_file_offset, max_file_offset):
        self.id = Segment.id_base
        Segment.id_base += 1

        util.debug(f'segment: id={self.id} trip_id={trip_id} top_left={bounding_box.top_left} bottom_right={bounding_box.bottom_right} start_time={util.seconds_to_hhmmss(start_time)} end_time={util.seconds_to_hhmmss(end_time)}')

        self.trip_id = trip_id
        self.trip_name = trip_name
        self.trip_start_seconds = trip_start_seconds
        #print(f'- trip_start_seconds: {trip_start_seconds}')
        self.bounding_box = bounding_box
        self.start_time = start_time
        self.end_time = end_time
        self.min_file_offset = min_file_offset
        self.max_file_offset = max_file_offset

    def get_score(self, lat, lon, seconds, path):
        if not self.bounding_box.contains(lat, lon):
            return -1

        ### REMOVE ME: for testing only
        #if random.random() < .5:
        #    util.debug(f'segment update: id={self.id} trip-name={util.to_b64(self.trip_name)} score={0.0000001}')

        if seconds < self.trip_start_seconds or seconds < self.start_time - MAX_TIME_DISTANCE or seconds > self.end_time + MAX_TIME_DISTANCE:
            return -1

        list = []

        with open(path + '/shapes.txt', 'r') as f:
            names = f.readline().strip()
            csvline = csv.CSVLine(names)

            f.seek(self.min_file_offset)

            while True:
                line = f.readline().strip()
                r = csvline.parse(line)

                llat = float(r['shape_pt_lat'])
                llon = float(r['shape_pt_lon'])

                list.append({'lat': llat, 'lon': llon})

                if f.tell() > self.max_file_offset:
                    break

        delta_time = self.end_time - self.start_time
        min_distance = 1000000000
        min_index = -1
        closestLat = 0
        closestLon = 0

        """
        ### TODO the approach below only works reliably if shape points are spaced close
        together, i.e. a few hundred feet apart. If points are far apart, for example on
        a long straight road segment where there is one point for the beginning of the
        segment and one for the end, then lat/long vehicle updates can be far apart from
        either point, but can still be matching the route closely.

        A better approach for widely spaced points is to create a vector between those
        points (A) and then take the length of the orthogonal vector (B) between A
        and the update location.

        Iterate over shape point pairs and choose length of shortest orthogonal vector as
        min distance. If no such orthogonal vector exists, fall back on naive approach
        """
        for i in range(len(list) - 1):
            sp1 = list[i]
            sp2 = list[i + 1]

            distance = geo_util.get_min_distance(sp1['lat'], sp1['lon'], sp2['lat'], sp2['lon'], lat, lon)

            if distance < min_distance:
                min_distance = distance
                min_index = i
                closestLat = list[i]['lat']
                closestLon = list[i]['lon']

            fraction = i / len(list)
            time = int(self.start_time + fraction * delta_time)
            list[i]['time'] = time

        print(f'- min_distance: {min_distance}')

        if min_distance > MAX_LOCATION_DISTANCE:
            return -1

        time_distance = abs(seconds - list[min_index]['time'])

        if time_distance > MAX_TIME_DISTANCE:
            return -1

        location_score = .5 * (MAX_LOCATION_DISTANCE - min_distance) / MAX_LOCATION_DISTANCE
        time_score = .5 * (MAX_TIME_DISTANCE - time_distance) / MAX_TIME_DISTANCE

        util.debug(f'segment update: id={self.id} trip-name={util.to_b64(self.trip_name)} score={location_score + time_score} closest-lat={closestLat} closest-lon={closestLon}')
        return location_score + time_score

    def get_trip_id(self):
        return self.trip_id
