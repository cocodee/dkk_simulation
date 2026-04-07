# RJ2506 新代码+新配置录制验证记录

## 1. 目标

使用已修复的底盘轮速控制代码与当前配置 `configs/rj2506_tire_loading.yaml`，重新录制控制视频并验证效果。

## 2. 执行环境

- 容器：`wheel-isaac-sim`
- 配置：`configs/rj2506_tire_loading.yaml`
- 代码：
  - `src/dkk_simulation/isaac_bridge.py`（已加入速度命令锁存与每步重放）
  - `scripts/record_rj2506_control_video.py`（录制链路已调整）

## 3. 执行过程

### 3.1 直接使用主录制脚本尝试

命令（容器内）：

```bash
cd /workspace/dkk_simulation
timeout 300s env PYTHONPATH=src /isaac-sim/python.sh scripts/record_rj2506_control_video.py \
  --headless \
  --config configs/rj2506_tire_loading.yaml \
  --output-dir /tmp/rj2506_control_frames_new \
  --warmup-frames 6 \
  --frames-per-phase 8 \
  --max-actions 3
```

现象：

- 进程启动并打印到 `[record] reset done`、`camera=...`
- 但目录 `/tmp/rj2506_control_frames_new` 无 PNG 输出
- 录制流程未形成有效帧序列（历史问题仍在）

### 3.2 备用方案：直接相机采集（绕过 replicator 取帧阻塞）

使用临时脚本 `/tmp/record_control_direct.py`（容器内生成），核心逻辑：

- 同样加载 `configs/rj2506_tire_loading.yaml`
- 使用 `IsaacSimBackend + RJ2506TireLoadingEnv`
- 用 `Camera.get_rgba()` 直接抓帧
- 执行 6 帧 warmup + 3 个 action 每个 8 帧

结果：

- 成功输出 `30` 帧
- 输出目录：`/tmp/rj2506_control_frames_new`
- `manifest.json` 正常生成

## 4. 视频导出

命令（容器内）：

```bash
cd /tmp/rj2506_control_frames_new
ffmpeg -y -framerate 12 -pattern_type glob -i "*.png" \
  -c:v libx264 -pix_fmt yuv420p /tmp/rj2506_control_new.mp4
```

随后拷贝到工作区：

- `/home/kdi/workspace/dkk_simulation/videos/rj2506_control_new_code_config.mp4`
- `/home/kdi/workspace/dkk_simulation/videos/rj2506_control_new_code_config_manifest.json`

## 5. 运动数值验证

为了确认“控制生效”，额外运行了关节数值验证脚本，结果写入：

- `/home/kdi/workspace/dkk_simulation/videos/rj2506_control_new_code_config_motion_numeric.json`

关键值：

- `left_wheel_delta = 0.07370500778779387`
- `right_wheel_delta = -0.07849207310937345`
- `left_wheel_v0 = 0.5977124571800232`
- `right_wheel_v0 = 0.5977497696876526`
- `left_wheel_v1 = 4.186778545379639`
- `right_wheel_v1 = -2.142138719558716`

结论：轮关节在控制上确实发生了持续变化，底盘轮速命令链路已生效。

## 6. 本次结论

1. 新代码 + 新配置下，控制链路验证通过（轮关节数值已变化）。
2. 本次导出视频文件已生成，但画面仍接近静态（文件较小），属于当前渲染/取帧链路问题，不是底盘轮速控制问题。
3. 后续若要得到可视上明显变化的视频，需要继续排查渲染链路（相机视角、渲染产品、材质/纹理加载、帧抓取时序）。
