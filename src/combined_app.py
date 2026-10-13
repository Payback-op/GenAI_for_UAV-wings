"""2&3 desktop app: one generation run, synchronized section/wing views."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from common import ROOT, save_json
from generate_combined import generate_combined, validate_combined, draw_section, draw_planform
from generate_wing import draw_wing


class CombinedApp:
    def __init__(self, root):
        self.root = root
        self.config = json.loads((ROOT / "config/combined_conditions.json").read_text())
        self.events = queue.Queue()
        self.output = None
        self.generated_conditions = None
        self.busy = False
        self.fields = {}
        self.entries = []
        root.title("BTP | 2&3 — combined wing generator")
        root.geometry("1500x900")
        root.minsize(1200, 760)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f8fafc")
        style.configure("TLabel", background="#f8fafc", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Group.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        shell = ttk.Frame(root, padding=18)
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="2&3 — one wing, both views", style="Title.TLabel").pack(anchor="w")
        ttk.Label(shell, text="Enter airfoil targets and wing dimensions. Generate once to update all views together.").pack(anchor="w", pady=(4, 5))
        ttk.Label(shell, text="Cl and Cd describe the airfoil section. Whole-wing performance is unverified.", foreground="#9a3412").pack(anchor="w", pady=(0, 10))
        self.status = tk.StringVar(value="Ready. These starting values are editable examples.")
        ttk.Label(shell, textvariable=self.status, font=("Segoe UI", 11, "bold"), wraplength=1100).pack(anchor="w", pady=(0, 8))
        body = ttk.Frame(shell)
        body.pack(fill="both", expand=True)
        controls = ttk.Frame(body, padding=(0, 0, 14, 0))
        controls.pack(side="left", fill="y")
        viewport = ttk.Frame(controls)
        viewport.pack(fill="both", expand=True)
        self.form_canvas = tk.Canvas(viewport, width=300, background="#f8fafc", highlightthickness=0)
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=self.form_canvas.yview)
        self.form_canvas.configure(yscrollcommand=scrollbar.set)
        self.form_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        form = ttk.Frame(self.form_canvas)
        form_window = self.form_canvas.create_window((0, 0), window=form, anchor="nw")
        form.bind("<Configure>", lambda event: self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all")))
        self.form_canvas.bind("<Configure>", lambda event: self.form_canvas.itemconfigure(form_window, width=event.width))
        self.form_canvas.bind("<MouseWheel>", lambda event: self.form_canvas.yview_scroll(int(-event.delta/120), "units"))
        row = 0
        groups = [
            ("airfoil", "Airfoil requirements", [
                ("angle_of_attack_deg", "Angle of attack (°)"),
                ("target_cl", "Desired lift coefficient (Cl)"),
                ("cl_tolerance", "Allowed lift difference (±)"),
                ("maximum_cd", "Maximum drag (Cd)"),
                ("minimum_thickness_ratio", "Minimum thickness (%)"),
                ("maximum_thickness_ratio", "Maximum thickness (%)")]),
            ("wing", "Wing dimensions", [
                ("span_m", "Full wing span (m)"),
                ("root_chord_m", "Root chord (m)"),
                ("tip_chord_m", "Tip chord (m)"),
                ("leading_edge_sweep_deg", "Leading-edge sweep (°)"),
                ("dihedral_deg", "Dihedral (°)"),
                ("root_twist_deg", "Root twist (°)"),
                ("tip_twist_deg", "Tip twist (°)")])]
        for section, heading, labels in groups:
            ttk.Label(form, text=heading, style="Group.TLabel").grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 6))
            row += 1
            for key, label in labels:
                value = self.config[section][key]
                if "thickness_ratio" in key:
                    value *= 100
                variable = tk.StringVar(value=f"{value:g}")
                ttk.Label(form, text=label, wraplength=190).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=6)
                entry = ttk.Entry(form, textvariable=variable, width=10)
                entry.grid(row=row, column=1, sticky="ew", pady=6)
                self.fields[(section, key)] = variable
                self.entries.append(entry)
                row += 1
            note = "AoA: −4 to +8°. Re: 100,000 (fixed)." if section == "airfoil" else "The same airfoil is scaled and twisted across the full span."
            ttk.Label(form, text=note, wraplength=285, foreground="#475569").grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 8))
            row += 1
        form.columnconfigure(0, weight=1)
        self.button = ttk.Button(controls, text="Generate 2D + 3D", command=self.start)
        self.button.pack(fill="x", pady=(10, 5))
        self.open_button = ttk.Button(controls, text="Open saved images / 3D files", command=self.open_results, state="disabled")
        self.open_button.pack(fill="x")
        panels = ttk.Panedwindow(body, orient="horizontal")
        panels.pack(side="left", fill="both", expand=True)
        left, right = ttk.Frame(panels), ttk.Frame(panels)
        panels.add(left, weight=1)
        panels.add(right, weight=1)
        ttk.Label(left, text="2D — airfoil and wing shape", style="Group.TLabel").pack(anchor="w", padx=8, pady=6)
        ttk.Label(right, text="3D — drag the wing to rotate", style="Group.TLabel").pack(anchor="w", padx=8, pady=6)
        self.figure_2d = Figure(figsize=(5, 6), facecolor="#f8fafc")
        self.section_ax = self.figure_2d.add_subplot(211)
        self.planform_ax = self.figure_2d.add_subplot(212)
        self.figure_2d.subplots_adjust(left=0.16, right=0.97, bottom=0.1, top=0.91, hspace=0.45)
        self.figure_3d = Figure(figsize=(6, 6), facecolor="#f8fafc")
        self.wing_ax = self.figure_3d.add_subplot(111, projection="3d")
        self.figure_3d.subplots_adjust(left=0, right=1, bottom=0, top=0.9)
        for ax in [self.section_ax, self.planform_ax, self.wing_ax]:
            ax.set_axis_off()
        self.canvas_2d = FigureCanvasTkAgg(self.figure_2d, master=left)
        self.canvas_3d = FigureCanvasTkAgg(self.figure_3d, master=right)
        self.canvas_2d.get_tk_widget().pack(fill="both", expand=True)
        self.canvas_3d.get_tk_widget().pack(fill="both", expand=True)
        NavigationToolbar2Tk(self.canvas_3d, right).update()
        self.detail = tk.StringVar(value="Each run saves a combined image, 2D coordinates, and STL / OBJ models in one results folder.")
        self.detail_label = ttk.Label(shell, textvariable=self.detail, wraplength=1400)
        self.detail_label.pack(anchor="w", pady=(10, 0))
        shell.bind("<Configure>", lambda event: self.detail_label.configure(wraplength=max(600, event.width-40)))
        latest = ROOT / "results/2&3/latest.json"
        if latest.exists():
            try:
                self.show(json.loads(latest.read_text()))
            except (OSError, KeyError, ValueError):
                self.status.set("Previous files are unavailable. Click Generate to make both views.")
        for variable in self.fields.values():
            variable.trace_add("write", self.inputs_changed)
        root.after(150, self.poll)

    def conditions(self):
        c = deepcopy(self.config)
        for (section, key), variable in self.fields.items():
            value = float(variable.get())
            c[section][key] = value/100 if "thickness_ratio" in key else value
        c["name"] = "2&3"
        validate_combined(c)
        return c

    def inputs_changed(self, *args):
        if self.generated_conditions is not None and not self.busy:
            try:
                current = self.conditions()
            except ValueError:
                current = None
            if current != self.generated_conditions:
                self.status.set("Inputs changed. Click Generate 2D + 3D to update both views.")
            else:
                self.status.set(self.result_status)

    def start(self):
        try:
            c = self.conditions()
        except (ValueError, KeyError) as error:
            messagebox.showerror("Check your inputs", str(error))
            return
        save_json(ROOT / "config/combined_conditions.json", c)
        self.config = c
        self.busy = True
        self.button.configure(state="disabled")
        for entry in self.entries:
            entry.configure(state="disabled")
        self.status.set("Generating the airfoil and 3D wing together...")

        def worker():
            try:
                summary = generate_combined(c, progress=lambda message: self.events.put(("progress", message)))
                self.events.put(("result", summary))
            except Exception as error:
                self.events.put(("error", str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def show(self, summary):
        folder = Path(summary["output_folder"])
        with np.load(folder / "3d/wing_mesh.npz") as mesh:
            vertices, faces = mesh["vertices_m"], mesh["faces"]
        self.section_ax.set_axis_on()
        self.planform_ax.set_axis_on()
        draw_section(self.section_ax, summary["airfoil"])
        draw_planform(self.planform_ax, vertices)
        self.section_ax.set_title("Airfoil cross-section (before twist)", fontsize=10)
        self.planform_ax.set_title("Wing top view (mesh edges)", fontsize=10)
        draw_wing(self.wing_ax, vertices, faces)
        self.wing_ax.set_title("Same airfoil → full wing", fontsize=11)
        self.canvas_2d.draw_idle()
        self.canvas_3d.draw_idle()
        self.output = folder
        self.generated_conditions = deepcopy(summary["conditions"])
        self.open_button.configure(state="normal")
        matched = summary["status"] == "predicted_match"
        self.result_status = "Both views ready. Airfoil predictor targets matched (unverified)." if matched else "No predicted target match. Both views show the same closest candidate."
        self.status.set(self.result_status)
        p, d = summary["airfoil"]["predictions"], summary["wing"]["dimensions"]
        self.detail.set(f"Section predicted Cl: {p['Cl']:.4f}   |   Cd: {p['Cd']:.5f}   |   Thickness: {100*summary['airfoil']['maximum_thickness_ratio']:.1f}% chord\n"
            f"Wing span: {d['span_m']:g} m   |   Reference area: {d['reference_planform_area_m2']:.3f} m²   |   Aspect ratio: {d['reference_aspect_ratio']:.2f}   |   STL: millimetres; OBJ: metres\n"
            f"Saved together: {folder}")
        self.inputs_changed()

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    self.status.set(value)
                    continue
                self.busy = False
                self.button.configure(state="normal")
                for entry in self.entries:
                    entry.configure(state="normal")
                if kind == "result":
                    self.show(value)
                else:
                    self.status.set("Generation stopped. The displayed views are from the previous run.")
                    messagebox.showerror("Could not generate both views", value)
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
    app = CombinedApp(root)
    if args.smoke_test:
        root.update_idletasks()
        app.canvas_2d.draw()
        app.canvas_3d.draw()
        assert len(app.fields) == 13 and app.output is not None
        original = app.fields[("wing", "span_m")].get()
        app.fields[("wing", "span_m")].set("2.1")
        assert "Inputs changed" in app.status.get()
        app.fields[("wing", "span_m")].set(original)
        root.destroy()
        print("2&3 controls, synchronized 2D/3D canvases, and changed-input status initialized successfully.")
    else:
        root.mainloop()


if __name__ == "__main__":
    main()
