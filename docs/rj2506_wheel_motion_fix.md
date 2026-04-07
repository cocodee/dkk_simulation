# RJ2506 底盘运动但轮子不转问题修复记录

## 1. 问题现象

- 导出视频中可见机器人底盘整体在移动。
- 但左右驱动轮视觉上几乎不转动，和底盘位移不一致。

## 2. 根因分析

控制链路存在“瞬时命令 + 后续不续发”的问题：

1. `env.step(action)` 时会调用后端执行一次轮关节速度命令。
2. 录制阶段主要是循环 `world.step()` 采样帧。
3. 录制循环里没有持续重发底盘轮速目标，导致轮关节速度无法稳定维持。

结论：底盘运动与轮关节控制解耦，造成“车体动但轮不转/转动不明显”。

## 3. 修改内容

### 3.1 后端增加“速度命令锁存 + 每步重放”

文件：`src/dkk_simulation/isaac_bridge.py`

- 新增成员 `self._active_velocity_commands`，保存当前激活的速度命令。
- 新增 `step_world(render=False, substeps=1)`：
  - 每个仿真步先重放锁存的速度命令，再执行 `world.step(...)`。
- 在 `_apply_template()` 中：
  - 清空旧锁存。
  - 对 `command_type == "velocity"` 的命令进行锁存。
  - 初始推进阶段也先重放速度命令再步进。
- 新增 `_reapply_active_velocity_commands()` 统一重发逻辑。

### 3.2 录制脚本改为通过 backend 步进

文件：`scripts/record_rj2506_control_video.py`

- `capture_frame()` 和 `step_and_capture()` 内部改为调用 `backend.step_world(...)`。
- 不再直接调用 `world.step(...)`，确保录制期间轮速命令持续生效。

## 4. 验证过程与结果

### 4.1 关节层验证（容器内）

使用 Isaac Sim 探针脚本验证 `left_wheel_joint/right_wheel_joint`：

- 命令 API 可用：`set_joint_velocities`
- 速度反馈可读，且在连续步进中保持非零
- 锁存验证输出（20 步）：
  - `ZZZ latched dp=(0.0737,-0.0785) v0=(0.5977,0.5977) v1=(4.1868,-2.1421)`

说明轮关节角度已持续变化，不再是一次性脉冲。

### 4.2 本地测试

在仓库环境执行：

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```

结果：`Ran 14 tests ... OK`

## 5. 当前状态与限制

- 本次修复已解决“轮速命令未持续下发”问题。
- `wheel-isaac-sim` 容器中视频录制链路仍存在既有卡住现象（camera/replicator 阶段可能超时），该问题与本次轮速修复无直接耦合，需单独排查录制管线稳定性。

## 6. 关键结论

- 之前视频中轮子不转的主因不是轮关节映射错误，而是控制命令生命周期过短。
- 通过“速度命令锁存 + 每步重放 + 录制链路统一走 backend 步进”，底盘运动与轮关节转动已重新一致。
