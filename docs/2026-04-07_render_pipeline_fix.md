# RJ2506 渲染链路修复记录

**日期:** 2026-04-07

## 问题描述

录制脚本 `record_rj2506_control_video.py` 生成的视频画面接近静态，文件大小仅 3.2KB（正常应为 400KB+）。

## 根因分析

通过对比工作的渲染脚本 `render_supre_scene_preview.py` 和问题脚本，发现以下关键差异：

| 方面 | 工作脚本 | 问题脚本 |
|------|---------|---------|
| 渲染器 | `RayTracedLighting` | 默认 |
| 相机 API | `rep.create.camera()` | `isaacsim.sensors.camera.Camera` |
| 渲染触发 | `rep.orchestrator.step()` | `world.step(render=True)` |
| 光照 | DomeLight + DistantLight | 无 |
| Warmup | 90步 `world.step(render=False)` | 无 |
| 帧保存 | `BasicWriter` | `camera.get_rgba()` |

**根本原因:** 原录制脚本使用 IsaacSim 原生 Camera API，未正确绑定渲染管线，导致帧数据为空/黑色。

## 修复内容

### 1. 修复 Bug (record_rj2506_control_video.py)

```python
# 第78-83行: 修复 render_product 未定义问题
render_product_path = ""
try:
    camera.add_rgba_to_frame()
    render_product_path = getattr(camera, "render_product_path", "") or \
                         getattr(camera, "get_render_product_path", lambda: "")()
except Exception as e:
    print(f"[record] warning: add_rgba_to_frame failed: {e}", flush=True)
```

### 2. 添加光照

```python
from pxr import UsdLux
dome = UsdLux.DomeLight.Define(stage, "/World/PreviewDome")
dome.CreateIntensityAttr(2500)
key = UsdLux.DistantLight.Define(stage, "/World/PreviewKey")
key.CreateIntensityAttr(1800)
```

### 3. 创建新脚本 (record_rj2506_control_video_replicator.py)

采用与工作脚本完全相同的 Replicator 管线：

- 使用 `RayTracedLighting` 渲染器
- 使用 `rep.create.camera()` 和 `rep.create.render_product()`
- 使用 `rep.orchestrator.step()` 触发渲染
- 使用 `BasicWriter` 保存帧
- 添加 90 步 warmup
- 添加 DomeLight + DistantLight 光照

## 验证结果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 帧文件大小 | ~3KB | ~111KB |
| 视频大小 | 3.2KB | 23KB |
| 帧数 | 30帧（空白） | 22帧（正常） |

**输出文件:**
- 视频: `videos/rj2506_replicator_full.mp4` (1280x720, 22帧)
- 帧: `videos/rj2506_replicator_frames/`
- Manifest: `videos/rj2506_replicator_manifest.json`

## 其他工作

### .gitignore 创建

创建了 `.gitignore` 文件，忽略以下内容：

- `renders/` - 渲染输出目录
- `videos/` - 视频和帧序列目录
- `**/capture/` - capture 子目录
- `**/frames/` - frames 子目录
- `**/*_frames/` - 各类 frames 目录
- `**/*.mp4`, `**/*.avi`, `**/*.mov` - 视频文件

## 待办事项

- [ ] 将 `record_rj2506_control_video_replicator.py` 的改进合并回原脚本
- [ ] 添加渲染管线选择的命令行参数
- [ ] 调查材质纹理缺失警告（ConveyorBelt_A08 相关）
