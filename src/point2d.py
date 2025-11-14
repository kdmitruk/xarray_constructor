import math

class Point2D():
    @staticmethod
    def avg(a, b):
        return Point2D((a.x + b.x)/2, (a.y + b.y)/2)

    @staticmethod
    def dist(p1, p2):
        return math.hypot(p1.x - p2.x, p1.y - p2.y)

    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __str__(self):
        return f"(x: {self.x}, y: {self.y})"

    def __getitem__(self, index):
        match index:
            case 0:
                return self.x
            case 1:
                return self.y
            case _:
                raise Exception("Bad index")

    def __str__(self):
        return f"Point2D({self.x}, {self.y})"
    __repr__ = __str__

    def rotated(self, origin, angle):
        x = origin.x + math.cos(angle) * (self.x - origin.x) - math.sin(angle) * (self.y - origin.y)
        y = origin.y + math.sin(angle) * (self.x - origin.x) + math.cos(angle) * (self.y - origin.y)
        return Point2D(x, y)

    def translated(self, vector):
        x = self.x + vector.x
        y = self.y + vector.y
        return Point2D(x, y)

    def polar_angle(self, center):
        angle = math.atan2(self.y - center.y, self.x - center.x)
        if angle > math.pi:
            angle -= 2 * math.pi
        elif angle <= -math.pi:
            angle += 2 * math.pi

        return angle

    def points_on_circle(self, center, radius, width):
        dx = self.x - center.x
        dy = self.y - center.y
        d = math.hypot(dx, dy)

        if not math.isclose(d, radius, rel_tol=1e-9):
            raise ValueError("The point is not on the circle.")

        if width > 2 * radius:
            return []

        a = (radius ** 2 - width ** 2 + d ** 2) / (2 * d)
        h = math.sqrt(max(0.0, radius ** 2 - a ** 2))

        x2 = center.x + a * dx / d
        y2 = center.y + a * dy / d

        rx = -dy * (h / d)
        ry = dx * (h / d)

        p1 = Point2D(x2 + rx, y2 + ry)
        p2 = Point2D(x2 - rx, y2 - ry)

        return [p1, p2]
