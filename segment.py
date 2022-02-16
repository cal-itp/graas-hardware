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

    def __init__(self, segment_index, trip_id, trip_name, trip_start_seconds, stop_id, bounding_box, start_time, end_time, min_file_offset, max_file_offset):
        self.id = Segment.id_base
        Segment.id_base += 1

        util.debug(f'segment: id={self.id} trip_id={trip_id} top_left={bounding_box.top_left} bottom_right={bounding_box.bottom_right} start_time={util.seconds_to_hhmmss(start_time)} end_time={util.seconds_to_hhmmss(end_time)}')

        self.segment_index = segment_index
        self.trip_id = trip_id
        self.trip_name = trip_name
        self.trip_start_seconds = trip_start_seconds
        self.stop_id = stop_id
        #print(f'- trip_start_seconds: {trip_start_seconds}')
        self.bounding_box = bounding_box
        self.start_time = start_time
        self.end_time = end_time
        self.min_file_offset = min_file_offset
        self.max_file_offset = max_file_offset
        self.waypoint_list = None

    def set_segments_per_trip(self, count):
        self.segments_per_trip = count

    def get_trip_fraction(self):
        return float(self.segment_index) / self.segments_per_trip

    def get_score(self, lat, lon, seconds, path):
        if not self.bounding_box.contains(lat, lon):
            return -1

        ### REMOVE ME: for testing only
        #if random.random() < .5:
        #    util.debug(f'segment update: id={self.id} trip-name={util.to_b64(self.trip_name)} score={0.0000001}')

        if seconds < self.trip_start_seconds or seconds < self.start_time - MAX_TIME_DISTANCE or seconds > self.end_time + MAX_TIME_DISTANCE:
            return -1

        if self.waypoint_list is None:
            self.waypoint_list = []

            with open(path + '/shapes.txt', 'r') as f:
                names = f.readline().strip()
                csvline = csv.CSVLine(names)

                f.seek(self.min_file_offset)

                while True:
                    line = f.readline().strip()
                    r = csvline.parse(line)

                    llat = float(r['shape_pt_lat'])
                    llon = float(r['shape_pt_lon'])

                    self.waypoint_list.append({'lat': llat, 'lon': llon})

                    if f.tell() > self.max_file_offset:
                        break

            delta_time = self.end_time - self.start_time

            for i in range(len(self.waypoint_list)):
                fraction = i / len(self.waypoint_list)
                time = int(self.start_time + fraction * delta_time)
                self.waypoint_list[i]['time'] = time

        min_distance = 1000000000
        min_index = -1
        closestLat = 0
        closestLon = 0

        for i in range(len(self.waypoint_list) - 1):
            sp1 = self.waypoint_list[i]
            sp2 = self.waypoint_list[i + 1]

            distance = geo_util.get_min_distance(sp1, sp2, lat, lon, seconds)

            if distance < min_distance:
                min_distance = distance
                min_index = i
                closestLat = self.waypoint_list[i]['lat']
                closestLon = self.waypoint_list[i]['lon']

        print(f'- min_distance: {min_distance}')

        if min_distance > MAX_LOCATION_DISTANCE:
            return -1

        print(f'+ update time : {util.seconds_to_hhmm(seconds)}')
        print(f'+ segment time: {util.seconds_to_hhmm(self.waypoint_list[min_index]["time"])}')
        time_distance = abs(seconds - self.waypoint_list[min_index]['time'])
        print(f'- time_distance: {time_distance}')

        if time_distance > MAX_TIME_DISTANCE:
            return -1

        location_score = .5 * (MAX_LOCATION_DISTANCE - min_distance) / MAX_LOCATION_DISTANCE
        time_score = .5 * (MAX_TIME_DISTANCE - time_distance) / MAX_TIME_DISTANCE

        util.debug(f'segment update: id={self.id} trip-name={util.to_b64(self.trip_name)} score={location_score + time_score} trip_pos=({self.segment_index}/{self.segments_per_trip}) closest-lat={closestLat} closest-lon={closestLon}')
        util.debug(f'+ trip_name: {self.trip_name}')
        return location_score + time_score

    def get_trip_id(self):
        return self.trip_id
