import matplotlib.patches as patches

from .point2d import Point2D
import math
import json
from .tube import Tube
from .card import Card
from .arrays import Array

class Scanner:
    def __init__(self):
        self.tube = Tube()

    def configure_from_file(self, scanner_file_path):
        self.name = scanner_file_path
        scanner_file = open(scanner_file_path, 'r')
        self.config = json.load(scanner_file)
        self.update_configuration()

    def update_configuration(self):
        self.configure(self.config)

    def save_configuration(self, scanner_file_path):
        with open(scanner_file_path, 'w') as scanner_file:
            json.dump(self.config, scanner_file, indent=4)

    def configure(self, configuration):
        tube_configuration = configuration["tube"]
        model = tube_configuration["model"]
        offset_x = float(tube_configuration["offset_x"])
        offset_z = float(tube_configuration["offset_z"])
        shift_z = float(tube_configuration["shift_z"])
        Tube.set_tube_configuration(f"tubes/{model}.json")

        self.tube.place(offset_x, offset_z, shift_z)

        card_configuration = configuration["card"]
        model = card_configuration["model"]
        Card.set_card_configuration(f"cards/{model}.json")

        tunnel_configuration = configuration["tunnel"]
        self.tunnel_offset_x = float(tunnel_configuration["offset_x"])
        self.tunnel_offset_z = float(tunnel_configuration["offset_z"])
        self.tunnel_size_x = float(tunnel_configuration["size_x"])
        self.tunnel_size_z = float(tunnel_configuration["size_z"])

        case_configuration = configuration["case"]
        self.case_offset_x = float(case_configuration["offset_x"])
        self.case_offset_z = float(case_configuration["offset_z"])
        self.case_size_x = float(case_configuration["size_x"])
        self.case_size_z = float(case_configuration["size_z"])

        self.array = Array(configuration)
        self.begin = self.end = self.actual_end = 0

    def calculate_array(self):
        if self.array.mode == "compact":
            self.actual_end = self.array.calculate(self.tube.focal_spot)
        elif self.array.mode == "arc":
            self.actual_end = self.array.calculate_arch(self.tube.focal_spot)

        self.actual_end = math.degrees(self.actual_end)

    def export_array(self, filename):
        data = self.array.export(self.tube.focal_spot)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def export_simulation_input(self, filename):
        detectors = self.array.export(self.tube.focal_spot)["detectors"]
        focal_spot = self.tube.focal_spot

        sphere_radius = min(self.tunnel_size_x, self.tunnel_size_z) / 2
        sphere_center_x = self.tunnel_offset_x + self.tunnel_size_x / 2
        sphere_center_z = self.tunnel_offset_z + self.tunnel_size_z / 2

        sphere_center = [sphere_center_x, sphere_center_z]
        focal_spot_center = [focal_spot.x, focal_spot.y]

        transformed_panels = []
        for detector in detectors:
            left_3d = detector[0]
            right_3d = detector[1]
            left = [left_3d[0], left_3d[2]]
            right = [right_3d[0], right_3d[2]]
            transformed_panels.append([left, right])

        simulation_data = {
            "sphere": {
                "center": sphere_center,
                "radius": sphere_radius
            },
            "focal_spot": {
                "center": focal_spot_center
            },
            "detectors": transformed_panels
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(simulation_data, f, indent=4, ensure_ascii=False)



    def plot(self, ax):
        top_left = Point2D(self.array.offset_x, self.array.offset_z + self.array.height)
        top_right = Point2D(self.array.offset_x + self.array.length, self.array.offset_z + self.array.height)

        top_left_dist = math.dist([self.tube.focal_spot.x, self.tube.focal_spot.y], [top_left.x, top_left.y])
        top_right_dist = math.dist([self.tube.focal_spot.x, self.tube.focal_spot.y], [top_right.x, top_right.y])

        ray_length = max(top_left_dist, top_right_dist)

        ax.add_patch(patches.Rectangle((self.case_offset_x, self.case_offset_z), self.case_size_x, self.case_size_z, fill=False, edgecolor ="grey", lw=1))
        ax.add_patch(patches.Rectangle((self.tunnel_offset_x, self.tunnel_offset_z), self.tunnel_size_x, self.tunnel_size_z, fill=False, edgecolor ="black", lw=1))

        self.tube.plot(ax, ray_length)
        self.array.plot(ax, self.tube.focal_spot, ray_length)

