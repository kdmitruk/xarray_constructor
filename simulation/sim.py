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

class SphereGeometry:
    def __init__(self, center, radius):
        self.center = np.array(center)
        self.radius = radius

    def intersect_length(self, S, P):
        S = np.asarray(S, dtype=float)
        P = np.asarray(P, dtype=float)

        D = P - S
        f = S - self.center

        a = np.dot(D, D)
        b = 2.0 * np.dot(D, f)
        c = np.dot(f, f) - self.radius ** 2

        delta = b * b - 4 * a * c
        if delta <= 0:
            return 0.0

        sqrt_delta = np.sqrt(delta)
        t1 = (-b - sqrt_delta) / (2 * a)
        t2 = (-b + sqrt_delta) / (2 * a)

        t_enter = max(t1, 0.0)
        t_exit  = min(t2, 1.0)

        if t_enter >= t_exit:
            return 0.0

        return np.linalg.norm(D) * (t_exit - t_enter)

def generate_sphere(center, radius):
    mesh = pv.Sphere(radius=radius, center=(center[0], 0, center[1]))
    geom = SphereGeometry(np.array([center[0], 0, center[1]]), radius)
    return mesh, geom

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

def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]

def is_occluded(focal_spot, point, occluder, eps=1e-9):
    fs = np.array([focal_spot[0], focal_spot[2]], dtype=float)
    p  = np.array(point, dtype=float)
    a  = np.array(occluder[0], dtype=float)
    b  = np.array(occluder[1], dtype=float)

    v = p - fs
    w = b - a

    denominator = cross(v, w)
    if abs(denominator) < eps:
        return False

    c = a - fs

    t = cross(c, w) / denominator
    u = cross(c, v) / denominator

    return (t > eps) and (0.0 <= u <= 1.0)

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
        current_detector_points = []

        for i in range(detector_resolution):
            t = (i + 0.5) / detector_resolution
            x = detector[0][0] * (1 - t) + detector[1][0] * t
            z = detector[0][1] * (1 - t) + detector[1][1] * t
            current_detector_points.append((x, z))


        detector_points += current_detector_points

    return planes, detector_points, np.linspace(-length / 2, length / 2, roll_axis_resolution)

def calculate_occlusion(detectors, detector_points, num_rows, detector_resolution, focal_spot):
    width = len(detector_points)
    occlusion_mask = np.zeros((int(num_rows), width), dtype=np.uint8)

    for i in range(len(detectors)):
        previous_detector = detectors[i-1] if i > 0 else None
        next_detector = detectors[i+1] if i < len(detectors) - 1 else None

        if previous_detector:
            global_index = i * detector_resolution
            while (
                global_index < width and
                is_occluded(focal_spot, detector_points[global_index], previous_detector)
            ):
                occlusion_mask[:, global_index] = 1
                global_index += 1

        if next_detector:
            global_index = (i + 1) * detector_resolution - 1
            while (
                global_index >= 0 and
                is_occluded(focal_spot, detector_points[global_index], next_detector)
            ):
                occlusion_mask[:, global_index] = 1
                global_index -= 1

    return occlusion_mask


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
    geometries, i, focal_spot, plane_points_row, y = args
    S = np.array([focal_spot[0], y, focal_spot[2]])

    results = []
    for j in range(len(plane_points_row)):
        P = np.array([plane_points_row[j][0], y, plane_points_row[j][1]])

        value = 0.0
        for geom in geometries:
            value += geom.intersect_length(S, P)
        results.append(value)

    return i, results

def process(geometries, focal_spot, plane_points, length_points):
    projection_data = np.zeros((len(length_points), len(plane_points)))

    tasks = [
        (geometries, i, focal_spot, plane_points, length_points[i])
        for i in range(len(length_points))
    ]

    with Pool(processes=cpu_count()) as pool:
        with tqdm(total=len(length_points), desc="Progress", unit="row") as pbar:
            for i, row in pool.imap(process_row, tasks):
                projection_data[i] = row
                pbar.update(1)

    return projection_data

def blend_occlusion(projection, occlusion):
    projection_max = np.max(projection)
    mask = occlusion == 1
    projection[mask] = projection_max
    return projection


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

    meshes, checks = generate_scene(scene_config["sphere"])

    detectors = scene_config["detectors"]
    detector_config = {
        "detector_resolution": settings_config.get("detector_resolution"),
        "roll_axis_resolution": settings_config.get("roll_axis_resolution"),
        "length": settings_config.get("detector_length")
    }

    planes, detector_points, length_points = create_detectors(detectors, detector_config)
    focal_spot, focal_line = create_focal_spot(scene_config["focal_spot"], length_points)
    occlusion_mask = calculate_occlusion(
        detectors,
        detector_points,
        len(length_points),
        detector_config["detector_resolution"],
        focal_spot
    )
    plotter = show(meshes, planes, focal_line)

    projection = process(checks, focal_spot, detector_points, length_points)
    projection = blend_occlusion(projection, occlusion_mask)

    save_projection(projection)
    plotter.show()

if __name__ == '__main__':
    main()
