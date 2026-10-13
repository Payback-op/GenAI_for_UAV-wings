# Saved 2D model and generator

Frozen version captured on 8 October 2026. Original working files remain in C:\BTP.

Run the saved generator from C:\BTP:

```powershell
.\.venv\Scripts\python.exe models\2d\src\design_app.py
```

This snapshot has its own code, model, inputs, data and results. Running it writes new outputs inside the snapshot; the manifest records the initially preserved files. The trained model and source are not changed by generating designs. The project Python environment is shared.

Predictor-target matches are provisional. Source-label conflicts and weak drag performance remain unresolved.
