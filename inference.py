import copy
import csv
import datetime
import json
import math
import os
import time
import util
import platform
from shapepoint import ShapePoint
from area import Area
from grid import Grid
from segment import Segment
from timer import Timer

STOP_PROXIMITY = 150
SCORE_THRESHOLD = 7
MIN_FLUSH_TIME_DELTA = 30 * 60
STOP_CAP = 10

class TripInference:
    VERSION = '0.2 (12/07/21)'

    def __init__(self, path, url, agency_id, vehicle_id, subdivisions, dow = -1, epoch_seconds = -1):
        if path[-1] != '/':
            path += '/'

        util.update_cache_if_needed(path, url)

        self.trip_candidates = {}
        self.last_candidate_flush = time.time()
        self.agency_id = agency_id
        self.vehicle_id = vehicle_id

        self.path = path
        calendar_map = self.get_calendar_map()
        util.debug(f'- calendar_map: {json.dumps(calendar_map, indent = 4)}')

        route_map = self.get_route_map()
        util.debug(f'- route_map: {json.dumps(route_map, indent = 4)}')

        self.area = Area()
        self.populateBoundingBox(self.area)
        util.debug(f'- self.area: {self.area}')
        self.grid = Grid(self.area, subdivisions)

        if dow < 0:
            dow = datetime.datetime.today().weekday()
        util.debug(f'- dow: {dow}')

        if epoch_seconds < 0:
            epoch_seconds = util.get_epoch_seconds()
        util.debug(f'+ epoch_seconds: {datetime.datetime.fromtimestamp(epoch_seconds)}')

        self.stops = self.get_stops()
        #util.debug(f'-- stops: {stops}')

        self.preload_stop_times()
        self.preload_shapes()

        self.compute_shape_lengths()
        self.block_map = {}

        trip_set = set()

        with platform.get_text_file_contents(path + '/trips.txt') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            count = 1

            load_timer = Timer('load')

            for r in rows:
                loop_timer = Timer('loop')
                trip_id = r['trip_id']
                service_id = r['service_id']
                shape_id = r['shape_id']

                trip_set.add(trip_id)

                if not service_id in calendar_map:
                    util.debug(f'* service id \'{service_id}\' not found in calendar map, skipping trip \'{trip_id}\'')
                    continue

                cal = calendar_map[service_id].get('cal', None)
                if cal is not None and cal[dow] != 1:
                    util.debug(f'* dow \'{dow}\' not set, skipping trip \'{trip_id}\'')
                    continue

                start_date = calendar_map[service_id].get('start_date', None)
                end_date = calendar_map[service_id].get('end_date', None)

                if start_date is not None and end_date is not None:
                    start_seconds = util.get_epoch_seconds(start_date)
                    end_seconds = util.get_epoch_seconds(end_date)
                    if epoch_seconds < start_seconds or epoch_seconds > end_seconds:
                        util.debug(f'* trip date outside service period (start: {start_date}, end: {end_date}), skipping trip \'{trip_id}\'')
                        continue

                util.debug(f'')
                util.debug(f'-- trip_id: {trip_id} ({count}/{len(rows)})')
                count += 1

                route_id = r['route_id']
                shape_id = r['shape_id']
                #util.debug(f'-- shape_id: {shape_id}')
                timer = Timer('way points')
                way_points = self.get_shape_points(shape_id)
                #util.debug(timer)
                #util.debug(f'-- way_points: {way_points}')
                util.debug(f'-- len(way_points): {len(way_points)}')

                if len(way_points) == 0:
                    util.debug(f'* no way points for trip_id \'{trip_id}\', shape_id \'{shape_id}\'')
                    continue

                timer = Timer('stop times')
                stop_times = self.get_stop_times(trip_id)

                block_id = r.get('block_id', None)
                #util.debug(f'-- block_id: {block_id}')

                if block_id is not None and len(block_id) > 0 and stop_times is not None and len(stop_times) > 0:
                    trip_list = self.block_map.get(block_id, None)

                    if trip_list is None:
                        trip_list = []
                        self.block_map[block_id] = trip_list

                    start_time = stop_times[0].get('arrival_time', None)
                    end_time = stop_times[-1].get('arrival_time', None)

                    if start_time is not None and end_time is not None:
                        trip_list.append({
                            'trip_id': trip_id,
                            'start_time': start_time,
                            'end_time': end_time
                        })

                #util.debug(timer)
                #util.debug(f'-- stop_times: {stop_times}')
                util.debug(f'-- len(stop_times): {len(stop_times)}')
                timer = Timer('interpolate')
                self.interpolate_way_point_times(way_points, stop_times, self.stops)
                #util.debug(timer)

                #trip_name = route_map[route_id]['name'] + ' @ ' + util.seconds_to_ampm_hhmm(stop_times[0]['arrival_time'])
                trip_name = trip_id + ' @ ' + util.seconds_to_ampm_hhmm(stop_times[0]['arrival_time'])
                util.debug(f'-- trip_name: {trip_name}')
                shape_length = self.shape_length_map[shape_id]

                if shape_length is None:
                    segment_length = 2 * util.FEET_PER_MILE
                else:
                    segment_length = int(shape_length / 30)

                #util.debug(f'-- segment_length: {segment_length}')
                timer = Timer('segments')
                self.make_trip_segments(trip_id, trip_name, stop_times[0], way_points, segment_length)
                #util.debug(timer)
                #util.debug(loop_timer)

        util.debug(f'-- self.block_map: {json.dumps(self.block_map, indent = 4)}')

        util.debug(load_timer)
        util.debug(f'-- self.grid: {self.grid}')

        for tid in self.stop_time_map:
            if not tid in trip_set:
                self.stop_time_map.pop(tid)

        self.shape_map = {}

    def populateBoundingBox(self, area):
        with platform.get_text_file_contents(self.path + '/shapes.txt') as f:
            names = f.readline().strip()
            #util.debug(f'-- names: {names}')
            csvline = csv.CSVLine(names)

            while True:
                line = f.readline()

                if not line:
                    break

                line = line.strip()
                r = csvline.parse(line)

                lat = float(r['shape_pt_lat'])
                lon = float(r['shape_pt_lon'])
                area.update(lat, lon)

    def compute_shape_lengths(self):
        self.shape_length_map = {}

        for shape_id in self.shape_map:
            #util.debug(f'-- shape_id: {shape_id}')
            point_list = self.shape_map[shape_id]
            #util.debug(f'-- point_list: {point_list}')
            length = 0

            for i in range(len(point_list) - 1):
                p1 = point_list[i];
                #util.debug(f'--- p1: {p1}')
                p2 = point_list[i + 1]
                #util.debug(f'--- p2: {p2}')

                length += util.haversine_distance(p1['lat'], p1['long'], p2['lat'], p2['long'])

            self.shape_length_map[shape_id] = length
            util.debug(f'++ length for shape {shape_id}: {util.get_display_distance(length)}')

    def preload_shapes(self):
        self.shape_map = {}

        with platform.get_text_file_contents(self.path + '/shapes.txt') as f:
            names = f.readline().strip()
            #util.debug(f'-- names: {names}')
            csvline = csv.CSVLine(names)

            while True:
                file_offset = f.tell()
                #util.debug(f'-- file_offset: {file_offset}')
                line = f.readline()

                if not line:
                    break

                line = line.strip()
                r = csvline.parse(line)
                shape_id = r['shape_id']
                #debug.log(f'-- sid: {sid}')

                lat = float(r['shape_pt_lat'])
                lon = float(r['shape_pt_lon'])

                plist = self.shape_map.get(shape_id, None)

                if plist is None:
                    plist = []
                    self.shape_map[shape_id] = plist

                entry = {'lat': lat, 'long': lon, 'file_offset': file_offset}
                sdt = r.get('shape_dist_traveled', None)

                if sdt is not None and len(sdt) > 0:
                    entry['traveled'] = float(sdt)

                plist.append(entry)

    def get_shape_points(self, shape_id):
        return self.shape_map.get(shape_id, None)

    def get_stops(self):
        slist = {}

        with platform.get_text_file_contents(self.path + '/stops.txt') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            for r in rows:
                # util.debug(f'-- r: {r}')
                id = r['stop_id']
                lat = float(r['stop_lat'])
                lon = float(r['stop_lon'])

                slist[id] = {'lat': lat, 'long': lon}

        return slist

    def get_route_map(self):
        #util.debug(f'get_route_map()')
        route_map = {}

        with platform.get_text_file_contents(self.path + '/routes.txt') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            for r in rows:
                route_id = r['route_id']
                #debug.log(f'-- route_id id: {route_id}')
                short_name = r['route_short_name'] ### TODO short_name is optional
                long_name = r['route_long_name']
                name = short_name if len(short_name) > 0 else long_name

                route_map[route_id] = {'name': name}

        return route_map

    def get_calendar_map(self):
        #util.debug(f'get_calendar_map()')
        calendar_map = {}

        with platform.get_text_file_contents(self.path + '/calendar.txt') as f:
            dow = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            reader = csv.DictReader(f)
            rows = list(reader)

            for r in rows:
                service_id = r['service_id']
                util.debug(f'-- service id: {service_id}')
                cal = []

                for d in dow:
                    cal.append(int(r[d]))
                #util.debug(f'-- cal: {cal}')

                calendar_map[service_id] = {'cal': cal, 'start_date': r.get('start_date', None), 'end_date': r.get('end_date', None)}

        return calendar_map

    def preload_stop_times(self):
        self.stop_time_map = {}

        with platform.get_text_file_contents(self.path + '/stop_times.txt') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            for r in rows:
                trip_id = r['trip_id']

                arrival_time = r['arrival_time']
                if len(arrival_time) == 0:
                    continue

                stop_id = r['stop_id']
                stop_sequence = r['stop_sequence']

                slist = self.stop_time_map.get(trip_id, None)

                if slist is None:
                    slist = []
                    self.stop_time_map[trip_id] = slist

                entry = {'arrival_time': util.hhmmss_to_seconds(arrival_time), 'stop_id': stop_id, 'stop_sequence': stop_sequence}
                sdt = r.get('shape_dist_traveled', None)

                if sdt is not None and len(sdt) > 0:
                    entry['traveled'] = float(sdt)

                #print(f'- entry: {entry}')

                slist.append(entry)

    def get_stop_times(self, trip_id):
        return self.stop_time_map.get(trip_id, None)

    def get_distance(self, way_points, wi, stop_times, stops, si):
            wp = way_points[wi]
            sp = stops[stop_times[si]['stop_id']]
            return util.haversine_distance(wp['lat'], wp['long'], sp['lat'], sp['long'])


    """
    For simpler trips `shape_dist_traveled` is optional. If the attribute is missing, we can take the following approach:
    - for each stop, assign a fraction of arrival time at that stop to total trip time -> fractions list
    - for i in len(fractions)
    -   compute index into shape list as int(fractions[i] * len(way_points) -> anchor_list
    - explore neighboring points in way_points for each match_list entry, going up to half the points until previous or next anchor point
    - adjust anchor points if closer match found
    - repeat until stable (current anchor list equals pevious anchor list) of max tries reached
    """
    def create_anchor_list_iteratively(self, way_points, stop_times, stops):
        start_seconds = stop_times[0]['arrival_time']
        stop_seconds = stop_times[-1]['arrival_time']
        total_seconds = float(stop_seconds - start_seconds)
        #print(f'- total_seconds: {total_seconds}')
        anchor_list = []

        for i in range(len(stop_times)):
            #print(f'-- i: {i}')
            seconds = stop_times[i]['arrival_time'] - start_seconds
            #print(f'-- seconds: {seconds}')
            frac = seconds / total_seconds
            #print(f'-- frac: {frac}')
            j = int(frac * (len(way_points) - 1))
            #print(f'-- j: {j}')
            anchor_list.append({'index': j, 'time': stop_times[i]['arrival_time']})

        for i in range(20):
            last_anchor_list = copy.deepcopy(anchor_list)
            #print(f'-- last_anchor_list: {last_anchor_list}')

            # explore neighbors in anchor_list, potentially changing index fields
            for j in range(len(last_anchor_list)):
                #print(f'-- j: {j}')
                c = last_anchor_list[j]
                #print(f'-- c: {c}')

                p = c
                if j > 0:
                    p = last_anchor_list[j - 1]

                n = c
                if j < len(last_anchor_list) - 1:
                    n = last_anchor_list[j + 1]

                p1 = stops[stop_times[j]['stop_id']]
                p2 = way_points[c['index']]
                min_diff = util.haversine_distance(p1['lat'], p1['long'], p2['lat'], p2['long'])
                min_index = c['index']
                #print(f'-- min_index: {min_index}')

                #print(f'-- c["index"]: {c["index"]}')
                #print(f'-- p["index"]: {p["index"]}')
                #print(f'-- n["index"]: {n["index"]}')

                kf = int(p['index'] + math.ceil((c['index'] - p['index']) / 2))
                kt = int(c['index'] + (n['index'] - c['index']) / 2)

                #print(f'-- kf: {kf}, kt: {kt}')

                for k in range(kf, kt):
                    p2 = way_points[k]
                    diff = util.haversine_distance(p1['lat'], p1['long'], p2['lat'], p2['long'])

                    if diff < min_diff:
                        min_diff = diff
                        min_index = k

                #print(f'++ min_index: {min_index}')
                anchor_list[j]['index'] = min_index

            #print(f'-- anchor_list     : {anchor_list}')

            stable = True

            for j in range(len(anchor_list)):
                i1 = anchor_list[j]['index']
                i2 = last_anchor_list[j]['index']

                if i1 != i2:
                    #print(f'* {i1} != {i2}')
                    stable = False
                    break

            if stable:
                break

        #print(f'++ anchor_list     : {anchor_list}')

        return anchor_list

    """
    anchor_list establishes a relationship between the list of stops for a trip and that trip's way points as described in shapes.txt.
    The list has one entry per stop. Each entry has an index into way_points to map to the closest shape point and the time when
    a vehicle is scheduled to arrive at that point (as given in stop_times.txt). anchor_list is an intermediate point in assigning
    timestamps to each point of the trip shape

    Complex trips with self-intersecting or self-overlapping segments are supposed to have `shape_dist_traveled` attributes for their
    shape.txt and stop_times.txt entries. This allows for straight-forward finding of shape points close to stops.
    """
    def create_anchor_list(self, way_points, stop_times, stops):
        #print(f' - len(way_points): {len(way_points)}')
        #print(f' - len(stop_times): {len(stop_times)}')
        #print(f' - len(stops): {len(stops)}')

        annotated = True

        for i in range(len(stop_times)):
            if not stop_times[i].get('traveled', False):
                annotated = False
                break;

        if annotated:
            for i in range(len(way_points)):
                if not way_points[i].get('traveled', False):
                    annotated = False
                    break;

        if not annotated:
            return self.create_anchor_list_iteratively(way_points, stop_times, stops)

        anchor_list = []

        for i in range(len(stop_times)):
            traveled = stop_times[i]['traveled']
            time = stop_times[i]['arrival_time']

            min_difference = float('inf')
            min_index = -1

            for j in range(len(way_points)):
                t = way_points[j]['traveled']
                diff = math.abs(traveled - t)

                if diff < min_difference:
                    min_difference = diff
                    min_index = j

            anchor_list.append({'index': min_index, 'time': time})

        return anchor_list

    """
    This is a naive, brute force approach that may well fail for self-intersecting or
    self-overlapping routes, or just very twisty routes. A better approach may be:
    - assign fraction to stops based on where their arrival time falls for overall trip duration.
      distance along route or a combination of both
    - set closest-stop attr for way points with corresponding fractions
    - search n neighbors on either side of points with attr and move attr to neighbor if closer
    - repeat until stable
    """
    def interpolate_way_point_times(self, way_points, stop_times, stops):
        anchor_list = self.create_anchor_list(way_points, stop_times, stops)
        firstStop = True

        #print(f'interpolate_way_point_times()')
        #util.debug(f'- len(way_points): {len(way_points)}')
        #util.debug(f'- len(stop_times): {len(stop_times)}')

        for st in stop_times:
            sp = stops[st['stop_id']]

            if firstStop:
                sp['first_stop'] = True
                firstStop = False

        util.debug(f'- anchor_list: {anchor_list}')
        #util.debug(f'- len(anchor_list): {len(anchor_list)}')

        for i in range(len(anchor_list) - 1):
            start = anchor_list[i]
            end = anchor_list[i + 1]
            tdelta = end['time'] - start['time']
            idelta = end['index'] - start['index']

            #util.debug('--------------------------')

            for j in range(idelta):
                fraction = j / idelta
                time = start['time'] + int(fraction * tdelta)
                way_points[start['index'] + j]['time'] = time
                hhmmss = util.seconds_to_hhmmss(time)
                #util.debug(f'--- {hhmmss}')

        #util.debug('--------------------------')

        index = anchor_list[0]['index']
        time = anchor_list[0]['time']

        while index >= 0:
            index -= 1
            way_points[index]['time'] = time

        index = anchor_list[-1]['index']
        time = anchor_list[-1]['time']

        while index < len(way_points):
            way_points[index]['time'] = time
            index += 1

        ### REMOVE ME: for testing only
        for i in range(len(way_points)):
            if not 'time' in way_points[i]:
                util.debug(f'.. {i}')

    def make_trip_segments(self, trip_id, trip_name, first_stop, way_points, max_segment_length):
        #print(f'- make_trip_segments()')
        #print(f'- max_segment_length: {max_segment_length}')
        #print(f'- way_points: {way_points}')

        segment_start = 0
        index = segment_start
        last_index = index
        segment_length = 0
        first_segment = True
        segment_count = 1

        area = Area()
        index_list = []
        segment_list = []

        skirt_size = max(int(max_segment_length / 10), 500)
        #print(f'- skirt_size: {skirt_size}')

        while index < len(way_points):
            lp = way_points[last_index]
            p = way_points[index]

            area.update(p['lat'], p['long'])

            grid_index = self.grid.get_index(p['lat'], p['long'])
            if not grid_index in index_list:
                index_list.append(grid_index)

            distance = util.haversine_distance(lp['lat'], lp['long'], p['lat'], p['long'])
            segment_length += distance

            if segment_length >= max_segment_length or index == len(way_points) - 1:
                area.extend(skirt_size)

                if segment_start == 0 and way_points[segment_start]['time'] == way_points[index]['time']:
                    util.error(f'0 duration first segment for trip {trip_id}')

                stop_id = None
                if first_segment:
                    first_segment = False
                    stop_id = first_stop['stop_id']

                segment = Segment(
                    segment_count,
                    trip_id,
                    trip_name,
                    first_stop['arrival_time'],
                    stop_id,
                    area,
                    way_points[segment_start]['time'],
                    way_points[index]['time'],
                    way_points[segment_start]['file_offset'],
                    way_points[index]['file_offset']
                )

                segment_list.append(segment)
                segment_count += 1

                for i in index_list:
                    self.grid.add_segment(segment, i)

                segment_length = 0
                area = Area()
                index_list = []

                index += 1
                last_index = index
                segment_start = index

                p = way_points[max(segment_start - 1, 0)]
                area.update(p['lat'], p['long'])

                continue

            last_index = index
            index += 1

        for s in segment_list:
            s.set_segments_per_trip(segment_count - 1)

    # NOTE: brute force approach that returns the *first*
    # stop within max_distance feet from lat/lon
    def get_stop_for_position(self, lat, lon, max_distance):
        stop_id = None

        for id in self.stops:
            stop = self.stops[id]
            if util.haversine_distance(lat, lon, stop['lat'], stop['long']) < max_distance:
                stop_id = id
                break

        return stop_id

    def reset_scoring(self):
        util.debug('+++ reset scoring! +++')
        self.trip_candidates = {}
        self.last_candidate_flush = time.time()


    def check_for_trip_start(self, stop_id):
        if not stop_id in self.stops:
            return

        stop = self.stops[stop_id]
        delta = time.time() - self.last_candidate_flush

        if 'first_stop' in stop and delta >= MIN_FLUSH_TIME_DELTA:
            self.reset_scoring()

    # returns None for trips filtered out for unmatched day or week,
    # calendar validity period, etc.
    def get_block_id_for_trip(self, trip_id):
        for b in self.block_map:
            trip_list = self.block_map[b]
            for t in trip_list:
                if t['trip_id'] == trip_id:
                    return b
        return None

    def get_stop_time_entities(self, trip_id, day_seconds, offset):
        util.debug(f'get_stop_time_entities()')
        util.debug(f'- trip_id: {trip_id}')
        util.debug(f'- day_seconds: {day_seconds}')
        util.debug(f'- offset: {offset}')

        index = self.get_remaining_stops_index(trip_id, day_seconds + offset)
        util.debug(f'- index: {index}')
        stop_list = self.stop_time_map.get(trip_id, [])
        util.debug(f'- stop_list: {stop_list}')
        entities = []
        timestamp = int(time.time())

        for i in range(index, len(stop_list)):
            s = stop_list[i]
            util.debug(f'-- s: {s}')

            e = {
                'agency_id': self.agency_id,
                'trip_id': trip_id,
                'stop_sequence': s['stop_sequence'],
                'delay': offset,
                'vehicle_id': self.vehicle_id,
                'timestamp': timestamp
            }

            entities.append(e)

        util.debug(f'- entities: {entities}')
        return entities

    # assumes that stop_list entries are sorted by 'arrival_time'
    def get_remaining_stops_index(self, trip_id, day_seconds):
        util.debug(f'get_remaining_stops_index()')
        util.debug(f'- trip_id: {trip_id}')
        util.debug(f'- day_seconds: {day_seconds}')

        stop_list = self.stop_time_map.get(trip_id, None)
        util.debug(f'- stop_list: {stop_list}')
        result = []

        if stop_list is None:
            return None

        for i in range(len(stop_list)):
            if stop_list[i]['arrival_time'] >= day_seconds:
                return i

        return len(stop_list)

    def get_trip_id(self, lat, lon, seconds, trip_id_from_block = None):
        segment_list = self.grid.get_segment_list(lat, lon)
        ret = {
            'trip_id': None,
            'stop_time_entities': None
        }

        if segment_list is None:
            return ret

        util.debug(f'- len(segment_list): {len(segment_list)}')
        #util.debug(f'- trip_id_from_block: {trip_id_from_block}')

        stop_id = self.get_stop_for_position(lat, lon, STOP_PROXIMITY)

        multiplier = 1
        ### removing stop multiplier actually gives better results with training data set
        #if stop_id is not None:
        #    multiplier = 10

        max_segment_score = 0
        time_offset = 0

        for segment in segment_list:
            if trip_id_from_block is not None and segment.trip_id != trip_id_from_block:
                continue

            result = segment.get_score(lat, lon, seconds, self.path)
            score = multiplier * result['score']
            time_offset = result['time_offset']
            #util.debug(f'-- time_offset: {time_offset}')

            if score <= 0:
                continue

            if score > max_segment_score:
                max_segment_score = score

            trip_id = segment.get_trip_id()

            if trip_id in self.trip_candidates:
                candidate = self.trip_candidates[trip_id]
            else:
                candidate = {'score': 0, 'name': segment.trip_name}
                self.trip_candidates[trip_id] = candidate

            candidate['score'] += score
            candidate['time_offset'] = time_offset
            #util.debug(f'-- candidate["time_offset"]: {candidate["time_offset"]}')

        if max_segment_score > 0 and stop_id is not None:
            self.check_for_trip_start(stop_id)

        max_score = 0
        max_trip_id = None
        cand_time_offset = None

        for trip_id in self.trip_candidates:
            cand = self.trip_candidates[trip_id]
            score = cand['score']
            name = cand['name']
            util.debug(f'candidate update: id={trip_id} trip-name={util.to_b64(name)} score={score}')

            if score > max_score:
                max_score = score
                max_trip_id = trip_id
                cand_time_offset = cand['time_offset']
                #util.debug(f'-- cand_time_offset: {cand_time_offset}')

        util.debug(f'- max_score: {max_score}')

        if max_score >= SCORE_THRESHOLD:
            ret['trip_id']: max_trip_id
            ret['stop_time_entities']: self.get_stop_time_entities(max_trip_id, seconds, cand_time_offset)
        return ret
