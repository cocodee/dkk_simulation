#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/kdi/workspace/dkk_simulation"
CONTAINER="wheel-isaac-sim"
SCRIPT_SRC="${ROOT_DIR}/ur10/run_ur10_bin_stacking.py"
SCRIPT_DST="/workspace/ur10/run_ur10_bin_stacking.py"
LOG_FILE="${ROOT_DIR}/ur10/last_run.log"
CAPTURE_DIR="${ROOT_DIR}/ur10/capture"
VIDEO_FILE="${ROOT_DIR}/ur10/ur10_bin_stacking.mp4"

docker exec "${CONTAINER}" bash -lc 'mkdir -p /workspace/ur10'
rm -rf "${CAPTURE_DIR}"
mkdir -p "${CAPTURE_DIR}"
docker cp "${SCRIPT_SRC}" "${CONTAINER}:${SCRIPT_DST}"
docker exec "${CONTAINER}" bash -lc 'rm -rf /workspace/ur10/capture && mkdir -p /workspace/ur10/capture'
docker exec "${CONTAINER}" bash -lc "/isaac-sim/python.sh ${SCRIPT_DST}" | tee "${LOG_FILE}"
docker cp "${CONTAINER}:/workspace/ur10/capture/." "${CAPTURE_DIR}/"
ffmpeg -y -framerate 15 -pattern_type glob -i "${CAPTURE_DIR}/rgb_*.png" -c:v libx264 -pix_fmt yuv420p "${VIDEO_FILE}" >/dev/null 2>&1 || true
