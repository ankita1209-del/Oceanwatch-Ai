from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path(r"c:\OceanWatch AI")
output = root / "data" / "images" / "habsos_dataset_report.png"

csvs = list((root / "data" / "raw" / "habsos").rglob("*.csv"))
frames = []
for csv_file in csvs:
    try:
        df = pd.read_csv(csv_file, low_memory=False)
    except Exception:
        continue
    required = {"STATE_ID", "LATITUDE", "LONGITUDE", "CELLCOUNT"}
    if required.issubset(df.columns):
        frames.append(df[["STATE_ID", "LATITUDE", "LONGITUDE", "CELLCOUNT"]].copy())

if not frames:
    raise FileNotFoundError("No usable HAB CSV files were found in data/raw/habsos")

df = pd.concat(frames, ignore_index=True)
df["CELLCOUNT"] = pd.to_numeric(df["CELLCOUNT"], errors="coerce")
df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")

df = df.dropna(subset=["LATITUDE", "LONGITUDE", "CELLCOUNT"]).copy()
df = df[df["LATITUDE"].between(18, 35) & df["LONGITUDE"].between(-98, -70)]

fig, axes = plt.subplots(1, 2, figsize=(16, 8))
for state, group in df.groupby("STATE_ID", sort=False):
    axes[0].scatter(group["LONGITUDE"], group["LATITUDE"], s=18, alpha=0.7, label=state)

axes[0].set_title("HABSOS Karenia brevis sampling locations", fontsize=14)
axes[0].set_xlabel("Longitude (°)")
axes[0].set_ylabel("Latitude (°)")
axes[0].grid(True, alpha=0.25)
axes[0].legend(title="State", loc="best", fontsize=8)

state_counts = df["STATE_ID"].value_counts().sort_values(ascending=False)
state_counts.plot(kind="bar", ax=axes[1], color="steelblue")
axes[1].set_title("Number of sample points by state", fontsize=14)
axes[1].set_xlabel("State")
axes[1].set_ylabel("Samples")
axes[1].tick_params(axis="x", rotation=0)

fig.suptitle("OceanWatch AI dataset used for HAB analysis", fontsize=18, y=1.02)
fig.tight_layout()
output.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(output, dpi=220, bbox_inches="tight")
print(f"Created: {output}")
print(f"Exists: {output.exists()}")
print(f"Size bytes: {output.stat().st_size}")
