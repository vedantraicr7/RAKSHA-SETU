from pathlib import Path
from whitebox.whitebox_tools import WhiteboxTools

PROJECT = Path.cwd()

DEM = (
    PROJECT
    / "data"
    / "processed"
    / "terrain"
    / "raigad_dem_utm.tif"
).resolve()

OUT_DIR = (
    PROJECT
    / "data"
    / "processed"
    / "hydrology"
).resolve()

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

FILLED = (
    OUT_DIR
    / "raigad_dem_filled.tif"
)

FLOW_ACC = (
    OUT_DIR
    / "raigad_flow_accumulation.tif"
)


print("DEM:")
print(DEM)

print("\nDEM exists:")
print(DEM.exists())

if not DEM.exists():
    raise FileNotFoundError(
        f"DEM not found: {DEM}"
    )


wbt = WhiteboxTools()

# Do not rely on a relative working directory.
wbt.set_working_dir(
    str(OUT_DIR)
)


print("\nFilling depressions...")

result = wbt.fill_depressions(
    str(DEM),
    str(FILLED),
    fix_flats=True
)

if not FILLED.exists():
    raise RuntimeError(
        "FillDepressions failed. "
        "Output file was not created."
    )


print("\nFilled DEM created:")
print(FILLED)


print("\nCalculating D8 flow accumulation...")

result = wbt.d8_flow_accumulation(
    str(FILLED),
    str(FLOW_ACC),
    out_type="cells"
)

if not FLOW_ACC.exists():
    raise RuntimeError(
        "D8FlowAccumulation failed. "
        "Output file was not created."
    )


print("\nFlow accumulation created:")
print(FLOW_ACC)

print("\nDONE.")
