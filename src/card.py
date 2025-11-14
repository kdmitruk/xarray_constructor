import json

from .point2d import Point2D
from .line import *
import math
from enum import Enum
import os


class Card:
    photodiode_size_x = None

    @staticmethod
    def get_cards_list():
        files = os.listdir("cards")
        return [os.path.splitext(file)[0] for file in files if file.endswith('.json')]

    class PositionType(Enum):
        UNDEFINED = 0
        LEFT = 1
        HORIZONTAL = 2
        RIGHT = 3

    class Platform:
        def __init__(self, configuration):
            self.y = float(configuration["y"])
            self.z = float(configuration["z"])

    @staticmethod
    def set_card_configuration(card_file_path):
        card_file = open(card_file_path, 'r')
        card_data = json.load(card_file)
        Card.configure(card_data)

    @staticmethod
    def configure(configuration):
        Card.plate_size_x = configuration["plate_size_x"]

        Card.photodiode_offset_x = configuration["photodiode_offset_x"]
        Card.photodiode_offset_z = configuration["photodiode_offset_z"]
        Card.photodiode_offset_y = configuration["photodiode_offset_y"]

        Card.photodiode_size_x = configuration["photodiode_size_x"]
        Card.photodiode_size_y = configuration["photodiode_size_y"]

        Card.bottom_margin = configuration["bottom_margin"]

        Card.platforms = []
        for platform_config in configuration["platforms"]:
            hole_array = Card.Platform(platform_config)
            Card.platforms.append(hole_array)

    def __init__(self, near, far, angle, accepted):
        self.near = near
        self.far = far
        self.accepted = accepted
        self.angle = angle
        self.position_type = Card.PositionType.UNDEFINED
        self.plates = []

    def verify_perpendicularity(focal_spot, near, far):
        center = Point2D.avg(far, near)
        card_a, _ = line_between_points(far, near)
        perp_a, _ = line_between_points(center, focal_spot)
        return card_a * perp_a + 1

    def verify_perpendicularity_X(focal_spot, near, far):
        center = Point2D.avg(far, near)
        card_a, _ = line_between_points(far, near)
        perp_a, _ = line_between_points(center, focal_spot)

        vec1_x = far.x - near.x
        vec1_y = far.y - near.y

        vec2_x = focal_spot.x - center.x
        vec2_y = focal_spot.y - center.y

        vec1_x, vec1_y = vec1_y, -vec1_x
        vec2_x, vec2_y = vec2_y, -vec2_x

        dot_product = vec1_x * vec2_x + vec1_y * vec2_y

        return dot_product

    def generate_card(near, far, fit, focal_spot, d, eps):
        center_angle = Point2D.avg(near, far).polar_angle(focal_spot)
        result_card = Card(near, far, center_angle, abs(d) < eps * 10)
        result_angle = fit.polar_angle(focal_spot)
        for platform in Card.platforms:
            result_card.plates += [result_card.calc_plate_position(platform.z)]
        return result_card, result_angle

    def calc_plate_position(self, plate_z):
        a, b = line_between_points(self.near, self.far)

        self.near_on_plate_projection = other_end_along_perpendicular(a, b, self.near,
                                                                           self.photodiode_offset_z - plate_z,
                                                                           lambda p1, p2: p1.y > p2.y)
        self.far_on_plate_projection = other_end_along_perpendicular(a, b, self.far,
                                                                          self.photodiode_offset_z - plate_z,
                                                                          lambda p1, p2: p1.y > p2.y)

        left = self.near_on_plate_projection if self.near_on_plate_projection.x < self.far_on_plate_projection.x else self.far_on_plate_projection

        plate_left = point_at_angle(left, self.angle + math.radians(90), Card.photodiode_offset_x)
        plate_right = point_at_angle(plate_left, self.angle - math.radians(90), Card.plate_size_x)

        return plate_left, plate_right

    def fit_sliding(focal_spot, angle, width, params, eps):
        a, b = at_angle(focal_spot, angle)
        min_far = params.calc_min_start_point(a, b)

        max_far = params.calc_max_start_point(min_far, angle)

        last_d = 1
        d = 0
        col = 0.1

        while abs(d - last_d) > eps:
            far = Point2D.avg(min_far, max_far)
            near = params.calc_near(far)

            last_d = d
            d = Card.verify_perpendicularity(focal_spot, near, far)

            if Point2D.avg(near, far).x < focal_spot.x:
                d = -d

            if params.compare_d(d):
                max_far = far
            else:
                min_far = far

            col = min(col + 0.05, 1)

        return Card.generate_card(near, far, near, focal_spot, d, eps)

    @staticmethod
    def calc_near_over_a_corner(far, corner, calc_near):
        a, b = line_between_points(far, corner)

        return calc_near(a, b, far)

    def fit_rotating(focal_spot, angle, width, params, eps):
        a, b = at_angle(focal_spot, angle)
        near = params.calc_start_point(a, b)
        min_far_angle = params.angle_range[0]
        max_far_angle = params.angle_range[1]

        last_d = 1
        d = 0
        col = 0.1

        while abs(d - last_d) > eps:
            far_angle = (min_far_angle + max_far_angle) / 2
            far = point_at_angle(near, far_angle, width)
            last_d = d
            d = Card.verify_perpendicularity(focal_spot, near, far)

            if params.compare_d(d):
                min_far_angle = far_angle
            else:
                max_far_angle = far_angle

            col = min(col + 0.05, 1)

        return Card.generate_card(near, far, far, focal_spot, d, eps)

    @staticmethod
    def fit_along_arch(focal_spot, angle, width, radius):
        left = point_at_angle(focal_spot, angle, radius)
        points = left.points_on_circle(focal_spot, radius, width)
        right = points[0] if points[0].x > points[1].x else points[1]
        return Card.generate_card(left, right, right, focal_spot, 0, 1)

    def plot(self, ax, focal_spot):
        points = [self.near, self.near_on_plate_projection, self.far_on_plate_projection, self.far]
        x = [p.x for p in points]
        y = [p.y for p in points]
        ax.plot(x, y, color='navy', lw=1, alpha=0.3)
        ax.plot([self.near.x, self.far.x], [self.near.y, self.far.y], color=('b' if self.accepted else 'r'))
        center = Point2D.avg(self.near, self.far)
        ax.plot([center.x, focal_spot.x], [center.y, focal_spot.y], color='k', lw=1, alpha=0.2)

    def y_range(self):
        return min(self.near)



