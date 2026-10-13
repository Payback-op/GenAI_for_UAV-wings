"""Local 3D wing controls and mouse-rotatable mesh preview."""
import argparse
import json
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from common import ROOT, save_json
from wing_geometry import validate_wing
from generate_wing import generate_wing, draw_wing

class WingApp:
    def __init__(self, root):
        self.root = root
        self.output = None
        self.events = queue.Queue()
        self.config = json.loads((ROOT / "config/wing_conditions.json").read_text())
        root.title("BTP | 3D wing generator")
        root.geometry("1240x820")
        root.minsize(1100, 760)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f8fafc")
        style.configure("TLabel", background="#f8fafc", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 21, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        shell = ttk.Frame(root, padding=20)
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="Generate a 3D wing", style="Title.TLabel").pack(anchor="w")
        ttk.Label(shell, text="Edit the example dimensions, generate a mesh, then drag the preview to rotate it.").pack(anchor="w", pady=(4, 7))
        ttk.Label(shell, text="Geometry prototype. Complete-wing aerodynamics, structural strength and flight performance are unverified.", foreground="#9a3412").pack(anchor="w", pady=(0, 12))
        body = ttk.Frame(shell)
        body.pack(fill="both", expand=True)
        form = ttk.Frame(body, padding=(0, 0, 22, 0))
        form.pack(side="left", fill="y")
        self.fields = {}
        labels = [("span_m", "Full wing span (m)"), ("root_chord_m", "Root chord (m)"),
            ("tip_chord_m", "Tip chord (m)"), ("leading_edge_sweep_deg", "Leading-edge sweep (degrees)"),
            ("dihedral_deg", "Dihedral (degrees)"), ("root_twist_deg", "Root twist (degrees)"), ("tip_twist_deg", "Tip twist (degrees)")]
        for key, label in labels:
            ttk.Label(form, text=label).pack(anchor="w", pady=(6, 2))
            var = tk.StringVar(value=f"{self.config[key]:g}")
            ttk.Entry(form, width=30, textvariable=var).pack(fill="x")
            self.fields[key] = var
        self.root_design = tk.StringVar(value=self.config["root_airfoil_design"])
        ttk.Label(form, text="Root airfoil design").pack(anchor="w", pady=(14, 2))
        ttk.Entry(form, textvariable=self.root_design, width=30).pack(fill="x")
        ttk.Button(form, text="Choose 2D design JSON", command=self.choose_root).pack(fill="x", pady=3)
        self.same_tip = tk.BooleanVar(value=self.config.get("tip_airfoil_design") == "same_as_root")
        ttk.Checkbutton(form, text="Use the root airfoil at the tip", variable=self.same_tip).pack(anchor="w", pady=3)
        self.tip_design = self.config.get("tip_airfoil_design", "same_as_root")
        ttk.Button(form, text="Choose different tip airfoil", command=self.choose_tip).pack(fill="x", pady=3)
        self.button = ttk.Button(form, text="Generate 3D model", command=self.start)
        self.button.pack(fill="x", pady=(12, 5))
        self.open_button = ttk.Button(form, text="Open STL / OBJ results", command=self.open_results, state="disabled")
        self.open_button.pack(fill="x")
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self.status = tk.StringVar(value="Ready. The saved 2D model will remain separate.")
        ttk.Label(right, textvariable=self.status, wraplength=800, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8, 4))
        self.figure = Figure(figsize=(8, 5), facecolor="#f8fafc")
        self.ax = self.figure.add_subplot(111, projection="3d")
        self.ax.set_axis_off()
        self.canvas = FigureCanvasTkAgg(self.figure, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        NavigationToolbar2Tk(self.canvas, right).update()
        self.detail = tk.StringVar(value="STL coordinates: millimetres. OBJ coordinates: metres.\n"
            "The output is a closed wing envelope, without internal spars, ribs or materials.")
        ttk.Label(right, textvariable=self.detail, wraplength=800).pack(anchor="w", pady=(8, 0))
        latest = ROOT / "results/3d/latest.json"
        if latest.exists():
            self.show(json.loads(latest.read_text()))
        root.after(150, self.poll)

    def choose_root(self):
        path = filedialog.askopenfilename(initialdir=ROOT / "results", title="Choose a generated 2D design.json", filetypes=[("Design JSON", "*.json")])
        if path:
            self.root_design.set(path)

    def choose_tip(self):
        path = filedialog.askopenfilename(initialdir=ROOT / "results", title="Choose a tip 2D design.json", filetypes=[("Design JSON", "*.json")])
        if path:
            self.tip_design = path
            self.same_tip.set(False)

    def start(self):
        try:
            c = dict(self.config)
            for key, value in self.fields.items():
                c[key] = float(value.get())
            c["description"] = "Wing geometry conditions entered in the local 3D generator."
            c["root_airfoil_design"] = self.root_design.get()
            c["tip_airfoil_design"] = "same_as_root" if self.same_tip.get() else self.tip_design
            validate_wing(c)
            if c["tip_airfoil_design"] == "same_as_root" and not self.same_tip.get():
                raise ValueError("Choose a tip design or enable use of the root airfoil at the tip.")
        except ValueError as error:
            messagebox.showerror("Check wing settings", str(error))
            return
        save_json(ROOT / "config/wing_conditions.json", c)
        self.button.configure(state="disabled")
        self.status.set("Building and checking the 3D mesh...")
        def worker():
            try:
                self.events.put((True, generate_wing(c)))
            except Exception as error:
                self.events.put((False, str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def show(self, summary):
        folder = Path(summary["output_folder"])
        with np.load(folder / "wing_mesh.npz") as mesh:
            draw_wing(self.ax, mesh["vertices_m"], mesh["faces"])
        self.figure.subplots_adjust(left=0, right=1, bottom=0, top=0.95)
        self.canvas.draw_idle()
        self.output = folder
        self.open_button.configure(state="normal")
        self.status.set("3D wing ready. Drag the model to rotate the view.")
        d, checks = summary["dimensions"], summary["mesh_checks"]
        self.detail.set(f"Span: {d['span_m']:g} m   |   Reference area: {d['reference_planform_area_m2']:.3f} m²   |   Aspect ratio: {d['reference_aspect_ratio']:.2f}\n"
            f"Closed mesh: {checks['triangles']:,} triangles. STL: millimetres; OBJ: metres.\n"
            f"Saved: {folder}\nGeometry generated; performance is not verified.")

    def poll(self):
        try:
            success, value = self.events.get_nowait()
            self.button.configure(state="normal")
            if success:
                self.show(value)
            else:
                self.status.set("Generation stopped. Check the settings or airfoil file.")
                messagebox.showerror("Could not build the wing", value)
        except queue.Empty:
            pass
        self.root.after(150, self.poll)

    def open_results(self):
        if self.output:
            os.startfile(self.output)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    root = tk.Tk()
    if args.smoke_test:
        root.withdraw()
    app = WingApp(root)
    if args.smoke_test:
        root.update_idletasks()
        app.canvas.draw()
        assert len(app.fields) == 7 and app.output is not None
        root.destroy()
        print("3D controls and rendered interactive canvas initialized successfully.")
    else:
        root.mainloop()

if __name__ == "__main__":
    main()
