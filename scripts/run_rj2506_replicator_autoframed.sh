#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-all}"
shift || true

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_FRAMES_DIR="$ROOT_DIR/videos/rj2506_autoframed_frames"
DEFAULT_VIDEO_PATH="$ROOT_DIR/videos/rj2506_autoframed.mp4"

FRAMES_DIR="${FRAMES_DIR:-$DEFAULT_FRAMES_DIR}"
VIDEO_PATH="${VIDEO_PATH:-$DEFAULT_VIDEO_PATH}"
CONFIG_PATH="${CONFIG_PATH:-$ROOT_DIR/configs/rj2506_tire_loading.yaml}"
ISAAC_PYTHON="${ISAAC_PYTHON:-/isaac-sim/python.sh}"
FPS="${FPS:-12}"
CRF="${CRF:-20}"

usage() {
  cat <<EOF
Usage:
  $(basename "$0") [all|record|encode|probe] [extra recorder args...]

Environment variables:
  FRAMES_DIR    Output frame directory for recording / input frame directory for encoding
  VIDEO_PATH    Output MP4 path
  CONFIG_PATH   Config JSON/YAML path
  ISAAC_PYTHON  Isaac Sim python launcher
  FPS           Output video fps
  CRF           libx264 CRF value

Examples:
  $(basename "$0") all --headless --max-actions 4
  FRAMES_DIR=/tmp/rj2506_frames $(basename "$0") record --headless
  FRAMES_DIR=$ROOT_DIR/videos/rj2506_replicator_frames VIDEO_PATH=/tmp/out.mp4 $(basename "$0") encode
  FRAMES_DIR=/tmp/rj2506_probe $(basename "$0") probe
EOF
}

run_record() {
  if [[ ! -x "$ISAAC_PYTHON" ]]; then
    echo "Isaac Sim launcher not found or not executable: $ISAAC_PYTHON" >&2
    exit 1
  fi

  mkdir -p "$FRAMES_DIR"
  export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

  "$ISAAC_PYTHON" "$ROOT_DIR/scripts/record_rj2506_control_video_replicator_autoframed.py" \
    --headless \
    --config "$CONFIG_PATH" \
    --output-dir "$FRAMES_DIR" \
    "$@"
}

run_encode() {
  python "$ROOT_DIR/scripts/encode_rj2506_video.py" \
    "$FRAMES_DIR" \
    --output "$VIDEO_PATH" \
    --fps "$FPS" \
    --crf "$CRF" \
    --overwrite
}

run_probe() {
  if [[ ! -x "$ISAAC_PYTHON" ]]; then
    echo "Isaac Sim launcher not found or not executable: $ISAAC_PYTHON" >&2
    exit 1
  fi

  mkdir -p "$FRAMES_DIR"
  export PYTHONPATH="$ROOT_DIR/src:$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"

  "$ISAAC_PYTHON" "$ROOT_DIR/scripts/probe_rj2506_replicator_autoframe_scene.py" \
    --headless \
    --config "$CONFIG_PATH" \
    --output-dir "$FRAMES_DIR" \
    "$@"
}

case "$MODE" in
  all)
    run_record "$@"
    run_encode
    ;;
  record)
    run_record "$@"
    ;;
  encode)
    run_encode
    ;;
  probe)
    run_probe "$@"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    usage >&2
    exit 2
    ;;
esac
