"""Local desktop form for generating a conditional 2D airfoil proposal."""
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from common import ROOT, save_json
from generate_airfoil import generate

class DesignApp:
    def __init__(self, root):
        self.root = root
        root.title("BTP | Airfoil design prototype")
        root.geometry("1150x750")
        root.minsize(1000, 650)
        self.events = queue.Queue()
        self.output = None
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f8fafc")
        style.configure("TLabel", background="#f8fafc", foreground="#0f172a", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("TButton", font=("Segoe UI", 11), padding=10)
        shell = ttk.Frame(root, padding=24)
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="Generate an airfoil", style="Title.TLabel").pack(anchor="w")
        ttk.Label(shell, text="Enter section targets. Preview a proposed shape and export its image and coordinates.").pack(anchor="w", pady=(5, 10))
        ttk.Label(shell, text="Exploratory prototype: predicted matches are not verified flight performance. Drag predictions remain weak.", wraplength=1050, foreground="#9a3412").pack(anchor="w", pady=(0, 20))
        body = ttk.Frame(shell)
        body.pack(fill="both", expand=True)
        form = ttk.Frame(body, padding=(0, 0, 24, 0))
        form.pack(side="left", fill="y")
        self.config = json.loads((ROOT / "config/design_conditions.json").read_text())
        self.fields = {}
        definitions = [("angle_of_attack_deg", "Angle of attack (degrees)", 1),
            ("target_cl", "Desired lift coefficient (Cl)", 1),
            ("cl_tolerance", "Allowed lift difference (+/-)", 1),
            ("maximum_cd", "Maximum drag coefficient (Cd)", 1),
            ("minimum_thickness_ratio", "Minimum thickness (% chord)", 100),
            ("maximum_thickness_ratio", "Maximum thickness (% chord)", 100)]
        for key, label, scale in definitions:
            ttk.Label(form, text=label).pack(anchor="w", pady=(8, 3))
            value = tk.StringVar(value=f"{self.config[key]*scale:g}")
            ttk.Entry(form, textvariable=value, width=29).pack(fill="x")
            self.fields[key] = (value, scale)
        ttk.Label(form, text="Supported range: -4 to +8 degrees\nReynolds number: 100,000 (fixed)\nDefault values are an example.", foreground="#475569").pack(anchor="w", pady=16)
        self.button = ttk.Button(form, text="Generate shape", command=self.start)
        self.button.pack(fill="x", pady=(0, 8))
        self.open_button = ttk.Button(form, text="Open saved results", command=self.open_results, state="disabled")
        self.open_button.pack(fill="x")
        preview = ttk.Frame(body)
        preview.pack(side="left", fill="both", expand=True)
        self.status = tk.StringVar(value="Set your targets and click Generate shape.")
        ttk.Label(preview, textvariable=self.status, wraplength=730, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(8, 12))
        self.image_label = ttk.Label(preview, text="Your generated cross-section will appear here.", anchor="center")
        self.image_label.pack(fill="both", expand=True)
        self.detail = tk.StringVar(value="Outputs: airfoil.png, airfoil.dat, coordinates.csv and a traceable design.json.\nA missing match is reported clearly; the tool will not claim the closest candidate meets your targets.")
        ttk.Label(preview, textvariable=self.detail, wraplength=730, foreground="#475569").pack(anchor="w", pady=(12, 0))
        root.after(150, self.poll)

    def start(self):
        try:
            conditions = dict(self.config)
            for key, (value, scale) in self.fields.items():
                conditions[key] = float(value.get()) / scale
            conditions["description"] = "Conditions entered in the local airfoil design app."
            from generate_airfoil import validate
            validate(conditions)
        except ValueError as error:
            messagebox.showerror("Check the conditions", str(error))
            return
        save_json(ROOT / "config/design_conditions.json", conditions)
        self.button.configure(state="disabled")
        self.status.set("Generating and checking candidate geometries...")
        def worker():
            try:
                self.events.put((True, generate(conditions)))
            except Exception as error:
                self.events.put((False, str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            success, value = self.events.get_nowait()
            self.button.configure(state="normal")
            if not success:
                self.status.set("Generation stopped. Adjust the conditions or inspect the error.")
                messagebox.showerror("Could not generate a candidate", value)
            else:
                self.output = Path(value["output_folder"])
                img = Image.open(self.output / "airfoil.png")
                img.thumbnail((740, 400))
                self.photo = ImageTk.PhotoImage(img)
                self.image_label.configure(image=self.photo, text="")
                matched = value["status"] == "predicted_match"
                self.status.set("Candidate meets the predictor targets (unverified)." if matched else "No predicted match found. Closest candidate shown.")
                p = value["predictions"]
                self.detail.set(f"Predicted Cl: {p['Cl']:.4f}   |   Predicted Cd: {p['Cd']:.5f}\n"
                    f"Maximum thickness: {100*value['maximum_thickness_ratio']:.1f}% chord\n"
                    f"{value['predicted_matching_candidates']} candidates matched the predictor targets.\n"
                    f"Saved in: {self.output}\nPhysical performance remains unverified.")
                self.open_button.configure(state="normal")
        except queue.Empty:
            pass
        self.root.after(150, self.poll)

    def open_results(self):
        if self.output:
            import os
            os.startfile(self.output)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    root = tk.Tk()
    if args.smoke_test:
        root.withdraw()
    app = DesignApp(root)
    if args.smoke_test:
        root.update_idletasks()
        assert len(app.fields) == 6
        root.destroy()
        print("Desktop form initialized successfully.")
        return
    root.mainloop()

if __name__ == "__main__":
    main()
