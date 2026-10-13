"""Loft symmetric CST sections into a closed, triangulated full-wing mesh.

Coordinates in metres: x aft, y spanwise, z up. Span is the horizontal
tip-to-tip y distance. Sweep is measured along the leading-edge datum;
twist rotates around each section's quarter chord, positive nose-up.
"""
import struct
from collections import Counter
import numpy as np
from geometry import surfaces, geometry_checks, chord_grid

def validate_wing(c):
    limits = {"span_m": (0.2, 20), "root_chord_m": (0.03, 3), "tip_chord_m": (0.03, 3),
        "leading_edge_sweep_deg": (-30, 45), "dihedral_deg": (-15, 15),
        "root_twist_deg": (-15, 15), "tip_twist_deg": (-15, 15)}
    for key, (lo, hi) in limits.items():
        v = c.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or not lo <= v <= hi:
            raise ValueError(f"{key} must be between {lo} and {hi}.")
    if c["tip_chord_m"] > c["root_chord_m"]:
        raise ValueError("Tip chord must not exceed root chord in this tapered-wing prototype.")
    if abs(c["tip_twist_deg"] - c["root_twist_deg"]) > 20:
        raise ValueError("Root-to-tip twist change must not exceed 20 degrees.")
    for key, lo, hi in [("chord_points", 21, 301), ("span_stations", 5, 101)]:
        v = c.get(key)
        if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
            raise ValueError(f"{key} must be an integer between {lo} and {hi}.")
    if c["span_stations"] % 2 != 1:
        raise ValueError("span_stations must be odd so there is one shared centre section.")

def build_mesh(c, root_weights, tip_weights):
    validate_wing(c)
    n, ns = c["chord_points"], c["span_stations"]
    x = chord_grid(n)
    ys = np.linspace(-c["span_m"]/2, c["span_m"]/2, ns)
    vertices, stations = [], []
    for y in ys:
        eta = abs(y)/(c["span_m"]/2)
        chord = (1-eta)*c["root_chord_m"] + eta*c["tip_chord_m"]
        w = (1-eta)*np.asarray(root_weights) + eta*np.asarray(tip_weights)
        valid, thickness, _ = geometry_checks(w[None, :], 0.01, 0.4)
        if not valid[0]:
            raise ValueError("An interpolated airfoil is intersecting or outside thickness/camber limits.")
        _, lower, upper = surfaces(w, x)
        # One unique LE and one unique TE per ring; no duplicate seam vertices.
        ring_x = np.r_[x[::-1], x[1:-1]]
        ring_z = np.r_[upper[::-1], lower[1:-1]]
        twist = np.deg2rad((1-eta)*c["root_twist_deg"] + eta*c["tip_twist_deg"])
        dx, z = (ring_x-0.25)*chord, ring_z*chord
        datum_x = abs(y)*np.tan(np.deg2rad(c["leading_edge_sweep_deg"]))
        datum_z = abs(y)*np.tan(np.deg2rad(c["dihedral_deg"]))
        xyz = np.column_stack([datum_x + chord*0.25 + np.cos(twist)*dx + np.sin(twist)*z,
            np.full(len(ring_x), y), datum_z - np.sin(twist)*dx + np.cos(twist)*z])
        vertices.extend(xyz)
        stations.append({"y_m": float(y), "chord_m": float(chord), "twist_deg": float(np.rad2deg(twist)),
            "leading_edge_datum_x_m": float(datum_x), "dihedral_datum_z_m": float(datum_z),
            "maximum_thickness_ratio": float(thickness[0])})
    ring_count = 2*n-2
    faces = []
    for j in range(ns-1):
        for k in range(ring_count):
            next_k = (k+1) % ring_count
            a, b = j*ring_count+k, j*ring_count+next_k
            cc, d = (j+1)*ring_count+k, (j+1)*ring_count+next_k
            faces.extend([(a, cc, d), (a, d, b)])
    def upper_index(j):
        return n-1-j
    def lower_index(j):
        return n-1 if j == 0 else (0 if j == n-1 else n+j-1)
    # Cap using cross-chord strips, valid for cambered/concave sections too.
    for station in [0, ns-1]:
        offset = station*ring_count
        for j in range(n-1):
            quad = [upper_index(j), upper_index(j+1), lower_index(j+1), lower_index(j)]
            polygon = list(dict.fromkeys(quad))
            for k in range(1, len(polygon)-1):
                face = [offset+polygon[0], offset+polygon[k], offset+polygon[k+1]]
                faces.append(tuple(face[::-1] if station == 0 else face))
    v, f = np.asarray(vertices), np.asarray(faces, dtype=np.int32)
    checks = check_mesh(v, f)
    if not checks["closed_manifold"] or not checks["consistent_orientation"] or checks["degenerate_faces"] or checks["signed_volume_m3"] <= 0:
        raise ValueError(f"Mesh quality check failed: {checks}")
    taper = c["tip_chord_m"]/c["root_chord_m"]
    area = c["span_m"]*(c["root_chord_m"]+c["tip_chord_m"])/2
    dimensions = {"span_m": c["span_m"], "reference_planform_area_m2": area,
        "reference_aspect_ratio": c["span_m"]**2/area, "taper_ratio": taper,
        "reference_mean_aerodynamic_chord_m": (2/3)*c["root_chord_m"]*(1+taper+taper*taper)/(1+taper),
        "area_definition": "Untwisted trapezoidal reference planform; not actual curved skin surface area"}
    return v, f, stations, dimensions, checks

def check_mesh(v, f):
    triangles = v[f]
    double_area = np.linalg.norm(np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]), axis=1)
    directed = Counter((int(a), int(b)) for face in f for a, b in zip(face, np.roll(face, -1)))
    undirected = Counter(tuple(sorted(e)) for e in directed.elements())
    volume = np.einsum("ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum()/6
    return {"vertices": len(v), "triangles": len(f), "closed_manifold": all(n == 2 for n in undirected.values()),
        "consistent_orientation": all(n == 1 and directed[(b, a)] == 1 for (a, b), n in directed.items()),
        "degenerate_faces": int((double_area <= 1e-14).sum()), "signed_volume_m3": float(volume),
        "finite_vertices": bool(np.isfinite(v).all()), "minimum_xyz_m": v.min(axis=0).tolist(), "maximum_xyz_m": v.max(axis=0).tolist()}

def write_stl(path, v, f):
    """Binary STL is unitless; export numerical coordinates in millimetres."""
    with path.open("wb") as stream:
        stream.write(b"BTP 3D wing geometry; coordinate units mm; performance unverified".ljust(80, b" "))
        stream.write(struct.pack("<I", len(f)))
        for face in f:
            p = v[face]*1000
            normal = np.cross(p[1]-p[0], p[2]-p[0])
            normal /= np.linalg.norm(normal)
            stream.write(struct.pack("<12fH", *normal, *p.flatten(), 0))

def write_obj(path, v, f):
    with path.open("w", encoding="utf-8") as stream:
        stream.write("# BTP full wing; coordinate values in metres; physical performance unverified\n")
        for vertex in v:
            stream.write("v " + " ".join(f"{x:.10f}" for x in vertex) + "\n")
        for face in f:
            stream.write("f " + " ".join(str(int(i)+1) for i in face) + "\n")
