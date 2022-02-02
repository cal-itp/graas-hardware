import math
import util

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
def get_min_distance(lat0, lon0, lat1, lon1, lat2, lon2):
    """
    Get the minimal distance of a GPS update U from a trip segment S
    defined by endpoints SP1 and SP2.

    Args:
        lat0 (float): fractional lat value of SP1
        lon0 (float): fractional long value of SP1
        lat1 (float): fractional lat value of SP2
        lon1 (float): fractional long value of SP2
        lat2 (float): fractional lat value of U
        lon2 (float): fractional long value of U
    """

    # find center lat
    lmin = min(lat0, lat1, lat2)
    lmax = max(lat0, lat1, lat2)
    latc = (lmax - lmin) / 2

    # convert lat/long to cartesian
    cl = math.cos(math.radians(latc))
    x0 = util.EARTH_RADIUS_IN_FEET * lon0 * cl
    y0 = util.EARTH_RADIUS_IN_FEET * lat0
    x1 = util.EARTH_RADIUS_IN_FEET * lon1 * cl
    y1 = util.EARTH_RADIUS_IN_FEET * lat1
    x2 = util.EARTH_RADIUS_IN_FEET * lon2 * cl
    y2 = util.EARTH_RADIUS_IN_FEET * lat2

    # check proximity to segment end points
    d1 = util.distance(x0, y0, x2, y2)
    d2 = util.distance(x1, y1, x2, y2)

    # find segment slope and intersect
    if x0 == x1:
        # vertical segment edge case
        m = util.signum(y1 - y0) * float('inf')
    else:
        m = float(y1 - y0) / (x1 - x0)
    b = y0 - m * x0

    # find orthogonal slope and intersect
    if m == 0:
        m_ = 0
    else:
        m_ = -(1.0 / m)
    b_ = y2 - m_ * x2

    # find INTERSECTION_POINT of segment and orthogonal
    if m == 0:
        x = float('inf')
    else:
        x = (b_ - b) / (m - m_)
    y = m * x + b

    d3 = util.distance(x0, y0, x1, y1) # length of vector(SP1, SP2)
    d4 = util.distance(x0, y0, x, y)   # length of vector(SP1, INTERSECTION_POINT)
    d5 = util.distance(x, y, x2, y2)   # distance of U from INTERSECTION_POINT

    # if intersection of orthogonal through U lies on S
    if d4 <= d3:
        return min(d1, d2, d5)
    else:
        return min(d1, d2)
