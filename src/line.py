import math
import sys
from .point2d import Point2D

def line_between_points(p1, p2):
    x_diff = p2.x - p1.x
    if x_diff == 0:
        a = sys.float_info.max/2
    else:
        a = (p2.y - p1.y) / x_diff
    b = p1.y - a * p1.x
    return a, b

def at_angle(p, angle):
    a = math.tan(angle)
    b = p.y - a * p.x
    return a, b

def point_at_angle(p, angle, length):
    x = p.x + math.cos(angle) * length
    y = p.y + math.sin(angle) * length
    return Point2D(x, y)

def angle_between_lines(a1, a2):
    return math.atan2(a1 - a2, 1 + a1*a2)

def angle_around_point(p, focal_spot):
    fx, fy = focal_spot[0], focal_spot[1]
    x, y = p[0], p[1]
    dx, dy = x - fx, y - fy
    angle = math.atan2(dy, dx)
    angle = (math.pi - angle) % (2 * math.pi)
    return angle

def other_end(a, b, p, l, choose_point):
    try:
        root_base = -p.y**2 + (2*a*p.x + 2*b)*p.y - a**2*p.x**2 - 2*a*b*p.x + (a**2 + 1) * l**2 - b**2
        root = math.sqrt(root_base)

        x1 = -(root - a * p.y - p.x + a * b) / (a**2 + 1)
        x2 =  (root + a * p.y + p.x - a * b) / (a**2 + 1)
    except:
        x1 = p.x + l
        x2 = p.x - l

    p1 = Point2D(x1, a * x1 + b)
    p2 = Point2D(x2, a * x2 + b)
    return p1 if choose_point(p1, p2) else p2

def perpendicular(a, b, p):
    ap = -1/a
    bp = p.y - ap * p.x
    return ap, bp

def other_end_along_perpendicular(a, b, p, l, choose_point):
    a, b = perpendicular(a, b, p)
    return other_end(a, b, p, l, choose_point)

def other_end_along_horizontal(p, l, choose_point):
    p1 = Point2D(p.x - l, p.y)
    p2 = Point2D(p.x + l, p.y)
    return p1 if choose_point(p1, p2) else p2

def other_end_along_vertical(p, x, l, choose_point):
    dx = p.x - x
    dy = math.sqrt(l**2 - dx**2)
    p1 = Point2D(x, p.y + dy)
    p2 = Point2D(x, p.y - dy)
    return p1 if choose_point(p1, p2) else p2

def other_end_perpendicular_to_horizontal_on_x(p, angle, x):
    a, b = at_angle(p, angle)
    return Point2D(x, a * x + b)

def other_end_perpendicular_to_horizontal(p, angle , l, choose_point):
    dx = 1 / math.tan(angle) * l
    x = p.x + dx
    p1 = Point2D(x, p.y - l)
    p2 = Point2D(x, p.y + l)
    return p1 if choose_point(p1, p2) else p2

def other_end_perpendicular_to_vertical_on_given_y(p, angle, y):
    a, b = at_angle(p, angle)
    return Point2D((y - b) / a , y)

def other_end_perpendicular_to_vertical(p, angle , l, choose_point):
    dy = math.tan(angle) * l
    y = p.y + dy
    p1 = Point2D(p.x + l, y)
    p2 = Point2D(p.x - l, y)
    return p1 if choose_point(p1, p2) else p2