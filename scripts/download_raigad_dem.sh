#!/usr/bin/env bash

set -e

OUT="data/raw/dem/copernicus_glo30"

mkdir -p "$OUT"

tiles=(
    "N17_00_E073_00"
    "N18_00_E072_00"
    "N18_00_E073_00"
    "N19_00_E072_00"
    "N19_00_E073_00"
)

for tile in "${tiles[@]}"
do
    prefix="Copernicus_DSM_COG_10_${tile}_DEM"
    file="${prefix}.tif"

    echo
    echo "Downloading ${tile}..."

    aws s3 cp \
        --no-sign-request \
        "s3://copernicus-dem-30m/${prefix}/${file}" \
        "${OUT}/${file}"
done

echo
echo "======================================"
echo "Raigad DEM download complete"
echo "======================================"
