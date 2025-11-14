import json
import sys
import numpy as np
import pyvista as pv
import matplotlib.pyplot as plt
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

def load_config(path):
    with open(path, "r") as f:
        return json.load(f)

class SphereChecker:
    def __init__(self, center, radius):
        self.center = np.array(center)
        self.radius = radius

    def __call__(self, point):
        return np.linalg.norm(point - self.center) <= self.radius

def generate_sphere(center, radius):
    mesh = pv.Sphere(radius=radius, center=(center[0], 0, center[1]))
    return mesh, SphereChecker(np.array([center[0], 0, center[1]]), radius)

def generate_scene(config):
    center = config["center"]
    radius = config["radius"]
    model, model_check = generate_sphere(center, radius)
    return [model], [model_check]

def create_focal_spot(config_focal, length_points):
    cx, cz = config_focal["center"]
    cy = 0.0
    focal_spot = np.array([cx, cy, cz])
    focal_line = pv.Line(
        (cx, length_points[0], cz),
        (cx, length_points[-1], cz)
    )
    return focal_spot, focal_line

def calc_normal(detector):
    a0 = np.array([detector[0][0], 0, detector[0][1]])
    a1 = np.array([detector[0][0], 1, detector[0][1]])
    b1 = np.array([detector[1][0], 1, detector[1][1]])
    v = a1 - a0
    u = b1 - a0
    return np.cross(v, u)

def create_detectors(detectors, config):
    length = config["length"]
    detector_resolution = config["detector_resolution"]
    roll_axis_resolution = config["roll_axis_resolution"]

    planes = []
    detector_points = []

    for detector in detectors:
        center = ((detector[0][0] + detector[1][0]) / 2,
                  0,
                  (detector[0][1] + detector[1][1]) / 2)
        normal = calc_normal(detector)
        width = np.hypot(detector[0][0] - detector[1][0],
                         detector[0][1] - detector[1][1])

        plane = pv.Plane(
            center=center,
            direction=normal,
            i_size=width,
            j_size=length,
            i_resolution=detector_resolution,
            j_resolution=roll_axis_resolution
        )
        planes.append(plane)

        for t in np.linspace(0, 1, detector_resolution):
            x = detector[0][0] * (1 - t) + detector[1][0] * t
            z = detector[0][1] * (1 - t) + detector[1][1] * t
            detector_points.append((x, z))

    return planes, detector_points, np.linspace(-length / 2, length / 2, roll_axis_resolution)

def sample_along_line(checks, focal_spot, point_on_plane, samples_per_unit_length):
    result = 0
    length = np.linalg.norm(point_on_plane - focal_spot)
    n_samples = int(length * samples_per_unit_length)
    for t in range(n_samples):
        point = focal_spot + (point_on_plane - focal_spot) * (t / n_samples)
        if all(check(point) for check in checks):
            result += 1
    return result

def process_row(args):
    checks, i, focal_spot, plane_points_row, y, samples_per_unit_length = args
    moving_focal_spot = np.array([focal_spot[0], y, focal_spot[2]])
    results = []
    for j in range(len(plane_points_row)):
        point_on_plane = np.array([plane_points_row[j][0], y, plane_points_row[j][1]])
        result = sample_along_line(checks, moving_focal_spot, point_on_plane, samples_per_unit_length)
        results.append(result)
    return i, results

def process(checks, focal_spot, plane_points, length_points, samples_per_unit_length):
    projection_data = np.zeros((len(length_points), len(plane_points)))
    tasks = [(checks, i, focal_spot, plane_points, length_points[i], samples_per_unit_length)
             for i in range(len(length_points))]

    with Pool(processes=cpu_count()) as pool:
        with tqdm(total=len(length_points), desc="Progress", unit="row") as pbar:
            for result in pool.imap(process_row, tasks):
                projection_data[result[0]] = result[1]
                pbar.update(1)

    return projection_data

def show(meshes, planes, focal_line):
    plotter = pv.Plotter()
    for mesh in meshes:
        plotter.add_mesh(mesh, opacity=0.3, color="red")
    plotter.add_mesh(focal_line, color="red", opacity=1.0, line_width=10)
    for plane in planes:
        plotter.add_mesh(plane, color="blue", opacity=0.2, show_edges=True)
    plotter.show_grid()
    plotter.show(interactive_update=True)
    return plotter

def save_projection(projection):
    fig = plt.figure(figsize=(10, 10), frameon=False)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(projection, origin='lower', cmap='jet')
    ax.axis('off')
    plt.savefig("projection.png", dpi=300, bbox_inches='tight', pad_inches=0)
    plt.close()

def main():
    if len(sys.argv) < 3:
        print("Usage: python sim.py <scene.json> <config.json>")
        sys.exit(1)

    scene_config = load_config(sys.argv[1])
    settings_config = load_config(sys.argv[2])

    samples_per_unit_length = settings_config.get("samples_per_unit_length")

    meshes, checks = generate_scene(scene_config["sphere"])

    detectors = scene_config["detectors"]
    detector_config = {
        "detector_resolution": settings_config.get("detector_resolution"),
        "roll_axis_resolution": settings_config.get("roll_axis_resolution"),
        "length": settings_config.get("detector_length")
    }

    planes, detector_points, length_points = create_detectors(detectors, detector_config)
    focal_spot, focal_line = create_focal_spot(scene_config["focal_spot"], length_points)

    plotter = show(meshes, planes, focal_line)

    projection = process(checks, focal_spot, detector_points, length_points, samples_per_unit_length)

    save_projection(projection)
    plotter.show()

if __name__ == '__main__':
    main()
