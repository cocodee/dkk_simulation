#!/usr/bin/env python3
"""Encode an MP4 from an RJ2506 frame directory."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("frames_dir", help="Directory containing frame_*.png and optional manifest.json")
    parser.add_argument("--output", help="Output MP4 path. Defaults to <frames_dir>.mp4")
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--crf", type=int, default=20)
    parser.add_argument("--overwrite", action="store_true", default=False)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    frames_dir = Path(args.frames_dir).resolve()
    if not frames_dir.is_dir():
        raise SystemExit(f"Frame directory not found: {frames_dir}")

    output_path = Path(args.output).resolve() if args.output else frames_dir.with_suffix(".mp4")
    manifest_path = frames_dir / "manifest.json"
    list_path = frames_dir / "ffmpeg_list.txt"

    frames = load_frames(frames_dir, manifest_path)
    if not frames:
        raise SystemExit(f"No frames found in {frames_dir}")

    with list_path.open("w", encoding="utf-8") as handle:
        for frame in frames:
            handle.write(f"file '{frame.resolve().as_posix()}'\n")

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y" if args.overwrite else "-n",
        "-r",
        str(args.fps),
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-vf",
        "format=yuv420p",
        "-c:v",
        "libx264",
        "-crf",
        str(args.crf),
        str(output_path),
    ]
    subprocess.run(cmd, check=True)

    print(
        json.dumps(
            {
                "frames_dir": str(frames_dir),
                "manifest": str(manifest_path) if manifest_path.exists() else None,
                "frame_count": len(frames),
                "ffmpeg_list": str(list_path),
                "output": str(output_path),
                "fps": args.fps,
                "crf": args.crf,
            },
            indent=2,
        ),
        flush=True,
    )


def load_frames(frames_dir: Path, manifest_path: Path) -> list[Path]:
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_frames = data.get("frames", [])
        if manifest_frames:
            frames = [frames_dir / name for name in manifest_frames]
            missing = [str(path) for path in frames if not path.exists()]
            if missing:
                raise SystemExit(f"Manifest references missing frames: {missing[:5]}")
            return frames
    return sorted(frames_dir.glob("frame_*.png"))


if __name__ == "__main__":
    main()
