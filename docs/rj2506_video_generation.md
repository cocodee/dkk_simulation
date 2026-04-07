# RJ2506 控制视频生成说明

本文整理当前已验证可用的 RJ2506 控制视频生成方法。

## 1. 已验证可用：从已有帧序列合成 MP4

当前仓库已有可用帧目录：

- `/home/kdi/workspace/dkk_simulation/videos/rj2506_control_frames`

在宿主机执行以下命令可稳定生成可播放视频：

```bash
cd /home/kdi/workspace/dkk_simulation

python - <<'PY'
from pathlib import Path
frames = sorted(Path('videos/rj2506_control_frames').glob('frame_*.png'))
list_path = Path('videos/rj2506_control_frames/ffmpeg_list.txt')
with list_path.open('w', encoding='utf-8') as f:
    for p in frames:
        f.write(f"file '{p.resolve().as_posix()}'\n")
print(f"frames={len(frames)} list={list_path}")
PY

ffmpeg -y -r 12 -f concat -safe 0 \
  -i /home/kdi/workspace/dkk_simulation/videos/rj2506_control_frames/ffmpeg_list.txt \
  -vf format=yuv420p -c:v libx264 -crf 20 \
  /home/kdi/workspace/dkk_simulation/videos/rj2506_control_preview_latest.mp4
```

生成结果：

- `/home/kdi/workspace/dkk_simulation/videos/rj2506_control_preview_latest.mp4`

## 2. 重新录制（Isaac Sim 容器）

录制脚本：

- `/home/kdi/workspace/dkk_simulation/scripts/record_rj2506_control_video.py`

容器内运行模板：

```bash
docker exec wheel-isaac-sim bash -lc '
cd /workspace/dkk_simulation
/isaac-sim/python.sh scripts/record_rj2506_control_video.py \
  --headless \
  --output-dir /tmp/rj2506_control_frames \
  --warmup-frames 12 \
  --frames-per-phase 12 \
  --max-actions 12
'
```

说明：

- H100 环境下不建议依赖旧的 viewport/swapchain 捕获路径（窗口渲染链路不稳定）。
- 优先使用 headless + 帧序列导出，再用 `ffmpeg` 合成 MP4。

## 3. 快速检查

```bash
ls -lh /home/kdi/workspace/dkk_simulation/videos/rj2506_control_preview_latest.mp4
ffprobe -v error -show_entries format=duration,size \
  -of default=noprint_wrappers=1 \
  /home/kdi/workspace/dkk_simulation/videos/rj2506_control_preview_latest.mp4
```

