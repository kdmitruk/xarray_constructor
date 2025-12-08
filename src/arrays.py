from .card import Card
from typing import NamedTuple
from .line import *
from .point2d import Point2D
from matplotlib.patches import Wedge


class SlideParameters(NamedTuple):
    calc_min_start_point: object
    calc_max_start_point: object
    compare_d: object
    calc_near: object


class RotationParameters(NamedTuple):
    calc_start_point: object
    compare_d: object
    angle_range: object


class Array:
    def __init__(self, configuration):
        self.cards = []


        configuration = configuration["array"]

        self.mode = configuration["mode"]
        self.offset_x = float(configuration["offset_x"])
        self.offset_z = float(configuration["offset_z"])
        self.length = float(configuration["length"])
        self.height = float(configuration["height"])
        self.bottom_thickness = float(configuration["bottom_thickness"])

        self.initial_offset = float(configuration["initial_card_offset"])


        self.right_side_enabled = "right_side" in configuration and configuration["right_side"]["enabled"]
        if self.right_side_enabled:
            self.right_side_length = float(configuration["right_side"]["length"])
            self.right_side_height = float(configuration["right_side"]["height"])

        self.left_side_enabled = "left_side" in configuration and configuration["left_side"]["enabled"]
        if self.left_side_enabled:
            self.left_side_length = float(configuration["left_side"]["length"])
            self.left_side_height = float(configuration["left_side"]["height"])

    def plot(self, ax, focal_spot, ray_length):
        border_params = {
            "linewidth": 0,
            "fill": True,
            "color": "black",
            "alpha": 0.4
        }

        l = self.offset_x
        r = self.offset_x + self.length
        t = self.offset_z + self.height
        b = self.offset_z

        x = [l, r]
        y = [b, b]

        horizontal_result = (l, r, t, b)
        right_result = (0, 0, 0, 0)

        if self.right_side_enabled and self.mode == "compact":
            rs_l = r
            rs_r = r + self.right_side_length #- self.bottom_thickness
            rs_t = t
            rs_b = b - self.right_side_height
            x.extend([rs_l, rs_r, rs_r])
            y.extend([rs_b, rs_b, rs_t])

            right_result = [rs_l, rs_r, rs_t, rs_b]

        x.extend([r, l])
        y.extend([t, t])

        if self.left_side_enabled and self.mode == "compact":
            ls_l = l - self.left_side_length
            ls_r = l
            ls_t = t
            ls_b = b - self.left_side_height
            x.extend([ls_l, ls_l, ls_r])
            y.extend([ls_t, ls_b, ls_b])

        x.extend([l])
        y.extend([b])

        ax.plot(x, y, color='black')
        for card in self.cards:
            card.plot(ax, focal_spot)

        ax.add_patch(Wedge((focal_spot.x, focal_spot.y), ray_length, math.degrees(self.end_angle), math.degrees(self.start_angle), color='c', alpha=0.1))

        return horizontal_result, right_result


    def choose_side(focal_spot, angle, forward_angle, width, calc_start_point, compared_coordinate):
        a, b = at_angle(focal_spot, angle)
        start_point = calc_start_point(a, b)
        end_point = point_at_angle(start_point, forward_angle, width)
        center = Point2D.avg(start_point, end_point)

        return compared_coordinate(center) - compared_coordinate(focal_spot);

    def calculate_arch(self, focal_spot):
        self.cards = []

        left_corner = Point2D(
            self.offset_x - (self.bottom_thickness if self.left_side_enabled else 0) - Card.bottom_margin,
            self.offset_z + self.bottom_thickness + Card.bottom_margin
        )

        right_corner = Point2D(
            self.offset_x + self.length + (
                self.bottom_thickness if self.right_side_enabled else 0) + Card.bottom_margin,
            self.offset_z + self.bottom_thickness + Card.bottom_margin)


        start_point = Point2D (
            self.offset_x + self.initial_offset,
            left_corner.y
        )

        start_angle = start_point.polar_angle(focal_spot)
        self.start_angle = start_angle

        angle = start_angle
        end_angle = right_corner.polar_angle(focal_spot)

        d1 = Point2D.dist(left_corner, focal_spot)
        d2 = Point2D.dist(right_corner, focal_spot)

        d = max(d1, d2)

        while angle > end_angle:
            previous_angle = angle
            card, angle = Card.fit_along_arch(focal_spot, angle, Card.photodiode_size_x, d)
            card.position_type = Card.PositionType.HORIZONTAL
            if angle > end_angle:
                self.cards.append(card)


        self.end_angle = previous_angle

        return angle

    def calculate(self, focal_spot):
        self.cards = []

        eps = 1e-2

        left_corner = Point2D(
            self.offset_x - (self.bottom_thickness if self.left_side_enabled else 0) - Card.bottom_margin,
            self.offset_z + self.bottom_thickness + Card.bottom_margin
        )

        left_end = Point2D(
            left_corner.x,
            left_corner.y - self.left_side_height
        ) if self.left_side_enabled else Point2D(
            self.offset_x,
            left_corner.y
        )

        left_corner_angle = left_corner.polar_angle(focal_spot)
        left_end_angle = left_end.polar_angle(focal_spot)



        right_corner = Point2D(
            self.offset_x + self.length + (
                self.bottom_thickness if self.right_side_enabled else 0) + Card.bottom_margin,
            self.offset_z + self.bottom_thickness + Card.bottom_margin)

        right_end = Point2D(
            right_corner.x,
            right_corner.y - self.right_side_height
        ) if self.right_side_enabled else Point2D(
            self.offset_x + self.length,
            right_corner.y
        )

        right_corner_angle = right_corner.polar_angle(focal_spot)
        right_end_angle = right_end.polar_angle(focal_spot)

        start_point = Point2D (
            self.offset_x + self.initial_offset,
            left_corner.y
        )
        start_angle = start_point.polar_angle(focal_spot)

        top_choose_max_far = lambda p1, p2: p1.y > p2.y
        top_calc_min_start_point = lambda a, b: Point2D((left_corner.y - b) / a, left_corner.y)
        top_calc_max_start_point = lambda p, angle: other_end_perpendicular_to_horizontal(p, angle,
                                                                                               Card.photodiode_size_x,
                                                                                               top_choose_max_far)
        cw_calc_max_start_point_at_corner = lambda p, angle: other_end_perpendicular_to_horizontal_on_x(p,
                                                                                                             angle,
                                                                                                             right_corner.x)

        ccw_calc_max_start_point_at_corner = lambda p, angle: other_end_perpendicular_to_horizontal_on_x(p,
                                                                                                              angle,
                                                                                                              left_corner.x)
        cc_forward_angle = 0
        ccw_forward_angle = math.radians(270)
        top_compared_coordinate = lambda p: p.x

        right_x = right_corner.x - Card.bottom_margin
        right_calc_start_point = lambda a, b: Point2D(right_x, right_x * a + b)
        right_forward_angle = math.radians(-90)

        left_x = left_corner.x
        left_calc_start_point = lambda a, b: Point2D(left_x, left_x * a + b)
        left_forward_angle = math.radians(-90)


        sliding_left_to_right = SlideParameters(
            calc_min_start_point=top_calc_min_start_point,
            calc_max_start_point=top_calc_max_start_point,
            compare_d=lambda d: d < 0,
            calc_near=lambda far: other_end(0, left_corner.y, far, Card.photodiode_size_x,
                                                 lambda p1, p2: p1.x > p2.x
                                                 )
        )

        sliding_right_to_left = SlideParameters(
            calc_min_start_point=top_calc_min_start_point,
            calc_max_start_point=top_calc_max_start_point,
            compare_d=lambda d: d > 0,
            calc_near=lambda far: other_end(0, left_corner.y, far, Card.photodiode_size_x,
                                                 lambda p1, p2: p1.x < p2.x
                                                 )
        )

        sliding_left_to_right_corner = SlideParameters(
            calc_min_start_point=top_calc_min_start_point,
            calc_max_start_point=cw_calc_max_start_point_at_corner,
            compare_d=lambda d: d < 0,
            calc_near=lambda far: Card.calc_near_over_a_corner(far, right_corner,
                                                               lambda a, b, far: other_end(a, b, far,
                                                                                                Card.photodiode_size_x,
                                                                                                lambda p1,
                                                                                                       p2: p1.x > p2.x
                                                                                                )
                                                               )
        )

        sliding_right_to_left_corner = SlideParameters(
            calc_min_start_point=top_calc_min_start_point,
            calc_max_start_point=ccw_calc_max_start_point_at_corner,
            compare_d=lambda d: d > 0,
            calc_near=lambda far: Card.calc_near_over_a_corner(far, left_corner,
                                                               lambda a, b, far: other_end(a, b, far,
                                                                                                Card.photodiode_size_x,
                                                                                                lambda p1,
                                                                                                       p2: p1.x < p2.x
                                                                                                )
                                                               )
        )

        rotating_left_to_right = RotationParameters(
            calc_start_point=top_calc_min_start_point,
            compare_d=lambda d: d > 0,
            angle_range=(cc_forward_angle, cc_forward_angle + math.radians(90))
        )

        rotating_right_to_left = RotationParameters(
            calc_start_point=top_calc_min_start_point,
            compare_d=lambda d: d > 0,
            angle_range=(ccw_forward_angle, ccw_forward_angle - math.radians(90))
        )

        cw_rotating_top_to_bottom = RotationParameters(
            calc_start_point=right_calc_start_point,
            compare_d=lambda d: d < 0,
            angle_range=(right_forward_angle, right_forward_angle + math.radians(90))
        )
        ccw_rotating_top_to_bottom = RotationParameters(
            calc_start_point=left_calc_start_point,
            compare_d=lambda d: d < 0,
            angle_range=(left_forward_angle, left_forward_angle - math.radians(90))
        )

        angle = start_angle
        previous_angle = 0

        #clockwise
        while angle > right_end_angle:
            previous_angle = angle
            if angle > right_corner_angle:
                side = Array.choose_side(focal_spot, angle, cc_forward_angle, Card.photodiode_size_x,
                                         top_calc_min_start_point, top_compared_coordinate)
                if side > 0:
                    card, angle = Card.fit_sliding(focal_spot, angle, Card.photodiode_size_x, sliding_left_to_right,
                                                   eps)
                    card.position_type = Card.PositionType.HORIZONTAL
                    if card.near.x > right_corner.x:
                        card, angle = Card.fit_sliding(focal_spot, previous_angle, Card.photodiode_size_x,
                                                       sliding_left_to_right_corner, eps)
                        card.position_type = Card.PositionType.RIGHT
                else:
                    card, angle = Card.fit_rotating(focal_spot, angle, Card.photodiode_size_x, rotating_left_to_right,
                                                    eps)
                    card.position_type = Card.PositionType.HORIZONTAL
            elif self.right_side_enabled:
                card, angle = Card.fit_rotating(focal_spot, angle, Card.photodiode_size_x, cw_rotating_top_to_bottom, eps)
                card.position_type = Card.PositionType.RIGHT

            if angle > right_end_angle:
                self.cards.append(card)
        self.end_angle = previous_angle

        #counterclockwise
        angle = start_angle


        if angle >= left_end_angle:
            self.start_angle = start_angle
        else:
            while angle < left_end_angle:
                previous_angle = angle
                if angle < left_corner_angle:
                    side = Array.choose_side(focal_spot, angle, ccw_forward_angle, Card.photodiode_size_x,
                                             top_calc_min_start_point, top_compared_coordinate)
                    if side < 0:
                        card, angle = Card.fit_sliding(focal_spot, angle, Card.photodiode_size_x, sliding_right_to_left,
                                                       eps)
                        if card.near.x < left_corner.x:
                            card, angle = Card.fit_sliding(focal_spot, previous_angle, Card.photodiode_size_x,
                                                           sliding_right_to_left_corner, eps)
                            card.position_type = Card.PositionType.LEFT
                    else:
                        card, angle = Card.fit_rotating(focal_spot, angle, Card.photodiode_size_x, rotating_right_to_left,
                                                        eps)
                    card.position_type = Card.PositionType.HORIZONTAL
                elif self.left_side_enabled:
                    card, angle = Card.fit_rotating(focal_spot, angle, Card.photodiode_size_x, ccw_rotating_top_to_bottom, eps)
                    card.position_type = Card.PositionType.LEFT

                if angle < left_end_angle:
                    self.cards.append(card)
            self.start_angle = previous_angle

        return angle

    def export(self, focal_spot):
        platforms = []
        detectors = []

        for card in self.cards:
            local_platforms = []
            for i in range(len(Card.platforms)):
                plate = card.plates[i]
                p1 = (plate[0][0], Card.platforms[i].y, plate[0][1])
                p2 = (plate[1][0], Card.platforms[i].y, plate[1][1])
                local_platforms.append((p1, p2))

            near = (card.near[0], Card.photodiode_offset_y, card.near[1])
            far = (card.far[0], Card.photodiode_offset_y, card.far[1])

            angle_near = angle_around_point(near, focal_spot)
            angle_far = angle_around_point(far, focal_spot)

            if angle_near < angle_far:
                near, far = far, near
                local_platforms = [(p2, p1) for (p1, p2) in local_platforms]

            platforms.extend(local_platforms)

            detectors.append((near, far))

        return {"platforms": platforms, "detectors": detectors}

    def plot3d(self, focal_spot):
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        data = self.export(focal_spot)
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')

        def draw_pairs(pairs, color):
            for p1, p2 in pairs:
                x_vals = [p1[0], p2[0]]
                y_vals = [p1[1], p2[1]]
                z_vals = [p1[2], p2[2]]
                ax.plot(x_vals, y_vals, z_vals, color=color, linewidth=1)

        platforms = data['platforms']
        all_platform_points = [p for pair in platforms for p in pair]
        px, py, pz = zip(*all_platform_points)
        ax.scatter(px, py, pz, c='black', marker='o', s=30, label='Platforms')

        draw_pairs(platforms, 'black')

        for i in range(0, len(platforms), 2):
            if i + 1 < len(platforms):
                p1a, p1b = platforms[i]
                p2a, p2b = platforms[i + 1]
                quad = [p1a, p1b, p2b, p2a]
                face = Poly3DCollection([quad], alpha=0.2, facecolor='black', edgecolor='black')
                ax.add_collection3d(face)

        detectors = data['detectors']
        all_detector_points = [p for pair in detectors for p in pair]
        dx, dy, dz = zip(*all_detector_points)
        ax.scatter(dx, dy, dz, c='blue', marker='^', s=40, label='Detectors')

        draw_pairs(detectors, 'blue')

        # ===  ZAKRESÓW ===
        all_x = list(px) + list(dx)
        all_y = list(py) + list(dy)
        all_z = list(pz) + list(dz)

        max_range = max(
            max(all_x) - min(all_x),
            max(all_y) - min(all_y),
            max(all_z) - min(all_z)
        ) / 2.0

        mid_x = (max(all_x) + min(all_x)) / 2.0
        mid_y = (max(all_y) + min(all_y)) / 2.0
        mid_z = (max(all_z) + min(all_z)) / 2.0

        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)

        ax.set_xlabel('X (scanner width)')
        ax.set_ylabel('Y (scanner length)')
        ax.set_zlabel('Z (scanner height)')
        ax.legend()
        ax.grid(True)

        plt.show()

