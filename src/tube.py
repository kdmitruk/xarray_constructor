import json
import math
from matplotlib.patches import Rectangle, Wedge
from .point2d import Point2D
import os

class Tube:
    @staticmethod
    def get_tubes_list():
        files = os.listdir("tubes")
        return [os.path.splitext(file)[0] for file in files if file.endswith('.json')]

    @staticmethod
    def set_tube_configuration(tube_file_path):
        tube_file = open(tube_file_path, 'r')
        tube_data = json.load(tube_file)
        Tube.configure(tube_data)

    @staticmethod
    def configure(configuration):
        Tube.size_x = float(configuration["size_x"])
        Tube.size_z = float(configuration["size_z"])
        Tube.focal_spot_x = float(configuration["focal_spot_x"])
        Tube.focal_spot_z = float(configuration["focal_spot_z"])
        Tube.start_angle = math.radians(float(configuration["start_angle"]) - 90)
        Tube.angle = math.radians(-float(configuration["angle"]))

    def place(self, offset_x, offset_z, bottom):
        self.offset_x = offset_x
        self.offset_z = offset_z
        self.bottom = bottom + offset_z

        self.angle = -math.asin((self.offset_z - self.bottom) / Tube.size_x)
        self.focal_spot = Point2D(Tube.focal_spot_x, Tube.focal_spot_z).translated(Point2D(self.offset_x, self.offset_z)).rotated(Point2D(self.offset_x, self.offset_z), self.angle)

        self.start_angle = -Tube.start_angle + self.angle
        self.end_angle = -Tube.start_angle + Tube.angle + self.angle

    def plot(self, ax, ray_length):
        ax.add_patch(Wedge((self.focal_spot.x, self.focal_spot.y), ray_length, math.degrees(self.end_angle), math.degrees(self.start_angle), color='y', alpha=0.2))
        ax.add_patch(Rectangle((self.offset_x, self.offset_z), Tube.size_x, Tube.size_z, angle=math.degrees(self.angle), rotation_point=(self.offset_x, self.offset_z), fill=False, edgecolor ="black", lw=1))
        ax.plot(self.focal_spot.x,self.focal_spot.y,'ko') 




