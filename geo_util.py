import math
import util

FLOAT_INF = float('inf')

"""
    If the part of the surface of the earth which you want to draw is relatively small, then you can use a very simple approximation. You can simply use the horizontal axis x to denote longitude λ, the vertical axis y to denote latitude φ. The ratio between these should not be 1:1, though. Instead you should use cos(φ0) as the aspect ratio, where φ0 denotes a latitude close to the center of your map. Furthermore, to convert from angles (measured in radians) to lengths, you multiply by the radius of the earth (which in this model is assumed to be a sphere).

    x = r λ cos(φ0)
    y = r φ


  - line equation from two points:
    m = (y1 - y0) / (x1 - x0)
    b = y0 - m * x0
    edge cases line horizontal or vertical: can probably set m to (-)Double.MAX_VALUE or 1 / (-)Double.MAX_VALUE

  - check if intersection between vector s (SP1 to SP2) and u is on s
    + invert slope of s: m' = -(1/m)
    + find equation for u:
      f(x) = m'x + b'
      uy = m' * ux + b'
      b' = uy - (m' * ux)

    + derive x of intersection by setting m * x + b = m' * x + b'
        m * x + b - m' * x = b'
        m * x - m' * x = b' - b
        x (m - m') = b' - b
        x = (b' - b) / (m - m')
    + use x in either equation to get y
        y = m * x + b
    + check if (x, y) is on s:
      create vector s' from SP1 to (x, y)
      check that len(s') >= 0 && len(s') < len(s)
"""
def get_min_distance(sp1, sp2, latu, lonu, seconds):
    """
    Get the minimal distance of a GPS update U from a trip segment S
    defined by endpoints SP1 and SP2.

    Args:
        sp1 (obj): object with 'lat', 'lon' and 'time' attributes
        sp2 (obj): object with 'lat', 'lon' and 'time' attributes
        latu (float): fractional lat value of U
        lonu (float): fractional long value of U
        seconds (int): seconds since midnight
    """

    #print(f'++++++++')
    #print(f'- sp1 : {sp1}')
    #print(f'- sp2 : {sp2}')
    #print(f'-   u : ({latu}, {lonu})')
    #print(f'+ secs: {seconds}')

    lat0 = sp1['lat']
    lon0 = sp1['lon']

    lat1 = sp2['lat']
    lon1 = sp2['lon']

    # find center lat
    """
    lmin = min(lat0, lat1, latu)
    lmax = max(lat0, lat1, latu)
    latc = (lmax + lmin) / 2

    #print(f'--------')
    #print(f'- lmin: {lmin}')
    #print(f'- lmax: {lmax}')
    #print(f'- latc: {latc}')

    # convert lat/long to cartesian
    cl = math.cos(math.radians(latc))
    x0 = util.EARTH_RADIUS_IN_FEET * lon0 * cl
    y0 = util.EARTH_RADIUS_IN_FEET * lat0
    x1 = util.EARTH_RADIUS_IN_FEET * lon1 * cl
    y1 = util.EARTH_RADIUS_IN_FEET * lat1
    x2 = util.EARTH_RADIUS_IN_FEET * lonu * cl
    y2 = util.EARTH_RADIUS_IN_FEET * latu
    """

    #print(f'--------')
    #print(f'-  cl: {cl}')
    #print(f'- sp1: ({x0}, {y0})')
    #print(f'- sp1: ({x1}, {y1})')
    #print(f'-   u: ({x2}, {y2})')

    h1 = int(util.haversine_distance(lat0, lon0, latu, lonu))
    h2 = int(util.haversine_distance(lat1, lon1, latu, lonu))

    #print(f'--------')
    #print(f'- h1: {h1}')
    #print(f'- h2: {h2}')

    # check proximity to segment end points
    #d1 = util.distance(x0, y0, x2, y2)
    #d2 = util.distance(x1, y1, x2, y2)

    #t1 = abs(sp1['time'] - seconds)
    #t2 = abs(sp2['time'] - seconds)

    #print(f'--------')
    #print(f'- d1: {d1}')
    #print(f'- d2: {d2}')

    # find segment slope and intersect
    if lon0 == lon1:
        # vertical segment edge case
        m = util.signum(lat1 - lat0) * FLOAT_INF
    else:
        m = float(lat1 - lat0) / (lon1 - lon0)
    b = lat0 - m * lon0

    # find orthogonal slope and intersect
    if m == 0:
        m_ = 0
    else:
        m_ = -(1.0 / m)
    b_ = latu - m_ * lonu

    # find INTERSECTION_POINT of segment and orthogonal
    if m == 0:
        lon = FLOAT_INF
    else:
        lon = (b_ - b) / (m - m_)
    lat = m * lon + b

    #d3 = util.distance(x0, y0, x1, y1) # length of vector(SP1, SP2)
    #d4 = util.distance(x0, y0, x, y)   # length of vector(SP1, INTERSECTION_POINT)
    #d5 = util.distance(x, y, x2, y2)   # distance of U from INTERSECTION_POINT

    h3 = util.haversine_distance(lat0, lon0, lat1, lon1) # length of vector(SP1, SP2)

    h4 = FLOAT_INF
    if lon != FLOAT_INF:
        h4 = util.haversine_distance(lat0, lon0, lat, lon)   # length of vector(SP1, INTERSECTION_POINT)

    h5 = FLOAT_INF
    if lon != FLOAT_INF:
         h5 = util.haversine_distance(lon, lat, latu, lonu)   # distance of U from INTERSECTION_POINT

    #print(f'- d3: {d3}')
    #print(f'- d4: {d4}')
    #print(f'- d5: {d5}')

    # if intersection of orthogonal through U lies on S
    if h4 <= h3:
        return min(h1, h2, h5)
    else:
        return min(h1, h2)
