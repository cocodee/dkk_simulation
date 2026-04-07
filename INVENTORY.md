# wheel/assets 资源清单

> 整理时间: 2026-03-26

## 目录大小概览

| 目录/文件 | 大小 | 说明 |
|-----------|------|------|
| `nvidia_official/` | **4.1G** | NVIDIA 官方资产 |
| `robots/` | **209M** | 机器人模型 |
| `opensource_wheels/` | **56M** | 开源轮子模型 (glb/gltf) |
| `wheels/` | **53M** | 轮子资产 |
| `Isaac/` | **46M** | Isaac Sim 资产 |
| `mobile_platform_phase2_0.usd` | 44M | 移动平台 USD 场景 |
| `transporter_local.usd` | 35M | 运输机器人 USD |

---

## 1. `robots/` (209M)

### 1.1 UR5e
- `robots/ur5e/ur5e.usd`

### 1.2 UR10
- `robots/ur10/ur10.urdf`
- `robots/ur10/Universal_Robots_ROS2_Description/` — ROS2 描述包（含所有 UR 型号配置）

### 1.3 RJ2506 (796M)
- `robots/RJ2506/RJ2506.usd`
- `robots/RJ2506/urdf/` — 多种 URDF 变体:
  - `RJ2506.urdf`
  - `RJ2506_ik.urdf`
  - `RJ2506_leftarm_only.urdf`
  - `RJ2506_leftarm_only_ik.urdf`
  - `RJ2506_leftarm_only_noagv.urdf`
  - `RJ2506_leftarm_only_noagv_floor.urdf`
  - `RJ2506_leftarm_only_nobody.urdf`
  - `RJ2506_leftarm_panda_hand.urdf`
  - `RJ2506_fixed.urdf`
- `robots/RJ2506/franka_description/meshes/visual/` — Franka Panda 视觉网格 (link0-7, finger, hand)
- `robots/RJ2506/realsense2_description/` — RealSense 相机描述

---

## 2. `nvidia_official/` (4.1G)

### 2.1 Conveyors (2.9G)
传送带系统 USD 资产

### 2.2 Robots/Carter (796M)
- `Robots/Carter/carter_v1.usd`
- `Robots/Carter/nova_carter.usd`
- `Robots/Carter/Props/` — Carter 组件:
  - `carter_backwheel_caster.usd`
  - `carter_main.usd`
  - `carter_v2_3_chassis.usd`
  - `carter_v2_chassis.usd`
  - `carter_v2_wheel_left.usd`
  - `carter_v2_wheel_right.usd`
  - `carter_wheel_center.usd`
  - `carter_wheel_left.usd`
  - `carter_wheel_right.usd`
  - `materials.usd`
- `Robots/Carter/nova_carter/` — Nova Carter 零部件 USD

### 2.3 Factory (162M)
工厂环境 USD 资产

### 2.4 Pallet (131M)
- `pallet.usd`
- `o3dyn_pallet.usd`
- `pallet_holder.usd`
- `pallet_holder_short.usd`
- `Materials/Textures/` — 托盘纹理 (Albedo, Normal, ORM 等)

### 2.5 Forklift (58M)
叉车 USD 资产

### 2.6 KLT_Bin (35M)
- KLT 周转箱 USD 资产
- `Materials/Textures/` — 纹理文件

---

## 3. `Isaac/Robots/` (46M)

### 3.1 Transporter
- `Isaac/Robots/Transporter/transporter.usd`
- `Isaac/Robots/Transporter/transporter_with_articulation.usd`

### 3.2 UniversalRobots
UR 系列 Isaac Sim 资产

---

## 4. `opensource_wheels/` (56M)

来自 Polyhaven 的 glTF/glb 模型:

| 文件名 | 类型 |
|--------|------|
| `ABeautifulGame.glb` | 42.9M |
| `AntiqueCamera.glb` | 298K |
| `Avocado.glb` | 298K |
| `Box.glb` | 298K |
| `Buggy.glb` | 298K |
| `CesiumMilkTruck.glb` | 298K |
| `DamagedHelmet.glb` | 298K |
| `Duck.glb` | 298K |
| `ReciprocatingSaw.glb` | 298K |
| `Sphere.gltf` | 298K |
| `Sponza.gltf` | 298K |
| `Suzanne.glb` | 298K |
| `test1.glb` | 5.7M |
| `ToyCar.glb` | 298K |
| `ToyCar_new.glb` | 5.4M |
| `WheelBarrow.glb` | 298K |
| `WheelBarrow.gltf` | 298K |

---

## 5. `wheels/` (53M)

轮子专项资产

---

## 6. 根目录文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `mobile_platform_phase2_0.usd` | 44M | Phase2 移动平台场景 |
| `transporter_local.usd` | 35M | 本地化运输机器人 |
| `mobile_robot_phase2_flat.usd` | 12K | 简化版移动机器人场景 |
| `transporter.urdf` | 8K | 运输机器人 URDF |
| `transporter_v2.urdf` | 8K | 运输机器人 URDF v2 |
| `simple_test.urdf` | 4K | 测试用 URDF |
| `render_phase2_local.py` | 4K | 本地渲染脚本 |

---

## 7. 空目录（预留未填充）

- `scenes/`
- `materials/`
- `objects/`
- `realistic_wheel/`

---

## Isaac Sim / Isaac Lab 关联资源

### Isaac Sim (Docker: nvcr.io/nvidia/isaac-sim:5.1.0)

| 类型 | 路径 |
|------|------|
| Docker 配置 | `wheel/docker/` |
| 数据目录 | `isaac_sim_data/` |
| Python 环境封装 | `wheel/src/simulation/isaac_sim_env.py` |
| USD 资产 | `wheel/assets/Isaac/` |
| 调试脚本 | `wheel/scripts/check_isaac_loading.py`, `debug_isaac_loading.py` |
| glTF→USD 转换 | `wheel/assets/wheels/polyhaven/convert_gltf_to_usd_isaac.py` |

### Isaac Lab (v2.3.0 + IsaacLab Arena 0.1.1)

| 类型 | 路径 |
|------|------|
| 环境配置 | `lerobot/src/lerobot/envs/configs.py` (IsaaclabArenaEnv) |
| 工厂函数 | `lerobot/src/lerobot/envs/factory.py` |
| 文档 | `lerobot/docs/source/envhub_isaaclab_arena.mdx`, `envhub_leisaac.mdx` |
