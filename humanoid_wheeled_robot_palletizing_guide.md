# 人形轮式机器人搬箱子码垛仿真指南

> **创建日期**: 2026-03-26
> **作者**: Claude Code
> **目的**: 在 Isaac Sim 中搭建能同时控制底盘和机械臂的移动操作机器人，实现搬箱子码垛任务

---

## 🎯 核心问题与解决方案

### 问题描述

在 Isaac Sim 中实现移动机械臂（mobile manipulation）时，常遇到：
- ❌ 底盘能动，机械臂不能动
- ❌ 机械臂能动，底盘不能动
- ❌ 两者无法同时控制

### 根本原因

**配置方式不正确**。Isaac Sim/IsaacLab 需要使用 `MobileManipulatorCfg` 并**分别配置底盘和机械臂的执行器组（ActuatorGroupCfg）**。

### ✅ 正确的配置方法

来自 [IsaacLab Discussion #1090](https://github.com/isaac-sim/IsaacLab/discussions/1090)：

```python
from omni.isaac.orbit.robots.mobile_manipulator import MobileManipulatorCfg
from omni.isaac.orbit.actuators.group import ActuatorControlCfg, ActuatorGroupCfg
from omni.isaac.orbit.actuators.model import ImplicitActuatorCfg

ROBOT_CFG = MobileManipulatorCfg(
    meta_info=MobileManipulatorCfg.MetaInfoCfg(
        usd_path=ROBOT_USD,
        base_num_dof=2,      # 底盘自由度（轮子数量）
        arm_num_dof=6,       # 机械臂自由度
        tool_num_dof=2,      # 夹爪自由度
    ),
    init_state=MobileManipulatorCfg.InitialStateCfg(
        dof_pos={
            'left_wheel': 0.0,
            'right_wheel': 0.0,
            'joint_1': 0.0,
            # ... 其他关节
        },
    ),
    actuator_groups={
        # 底盘控制器 - 独立配置
        "base": ActuatorGroupCfg(
            dof_names=["left_wheel", "right_wheel"],
            model_cfg=ImplicitActuatorCfg(
                velocity_limit=100.0,
                torque_limit=1000.0
            ),
            control_cfg=ActuatorControlCfg(
                command_types=["v_abs"],  # 速度控制
                stiffness={".*": 0.0},
                damping={".*": 1e5}
            ),
        ),
        # 机械臂控制器 - 独立配置
        "arm": ActuatorGroupCfg(
            dof_names=["joint_1", "joint_2", "joint_3",
                       "joint_4", "joint_5", "joint_6"],
            model_cfg=ImplicitActuatorCfg(
                stiffness=800.0,
                damping=40.0
            ),
            control_cfg=ActuatorControlCfg(
                command_types=["p_abs"],  # 位置控制
                stiffness={".*": 800.0},
                damping={".*": 40.0}
            ),
        ),
        # 夹爪控制器 - 独立配置
        "tool": ActuatorGroupCfg(
            dof_names=["gripper_left", "gripper_right"],
            model_cfg=ImplicitActuatorCfg(
                stiffness=100.0,
                damping=10.0
            ),
            control_cfg=ActuatorControlCfg(
                command_types=["p_abs"],
                stiffness={".*": 100.0},
                damping={".*": 10.0}
            ),
        ),
    },
)
```

**关键点：**
1. ✅ 使用 `MobileManipulatorCfg` 而非普通的 `ArticulationCfg`
2. ✅ 在 `actuator_groups` 中分别定义 `base`、`arm`、`tool`
3. ✅ 底盘使用**速度控制**（`v_abs`），机械臂使用**位置控制**（`p_abs`）
4. ✅ 不同执行器组使用不同的 `stiffness` 和 `damping` 参数

---

## 📦 现成的码垛场景推荐

### 方案 1: UR10 Bin Stacking（官方推荐）⭐⭐⭐⭐⭐

**最成熟的码垛方案**，有完整文档和教程。

#### 基本信息

- **官方文档**: [UR10 Bin Stacking Tutorial](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/cortex_tutorials/tutorial_cortex_5_ur10_bin_stacking.html)
- **场景描述**: 传送带 → 机械臂抓取 → 箱子翻转（如需要）→ 码垛到托盘
- **箱子规格**: 可配置大小和重量
- **控制框架**: Cortex（决策网络 + 状态机）

#### 运行示例

```bash
# Isaac Sim 5.1.0+
cd <isaac_sim_root>
./python.sh standalone_examples/api/isaacsim.cortex.framework/ur10_bin_stacking.py
```

#### 场景特点

✅ **优点：**
- 完整的码垛逻辑（包含翻转、堆叠、排序）
- 传送带自动生成箱子系统
- 现成的场景 USD 文件
- 基于 Cortex 框架，易于扩展

⚠️ **缺点：**
- 是固定底座机械臂，需要改造成移动平台

#### 场景组成

```
UR10 Bin Stacking 场景
├── 传送带 (Conveyor Belt)
│   └── 自动生成箱子
├── UR10 机械臂 + 吸盘夹爪
│   ├── 抓取箱子
│   └── 翻转箱子（如果是反向）
├── 翻转站 (Flip Station)
│   └── 用于翻转错误朝向的箱子
└── 托盘 (Pallet)
    └── 堆叠目标位置（2x2x2 = 8层）
```

#### Cortex 决策网络架构

```python
# 顶层决策逻辑（伪代码）
if stack_is_complete or no_active_bin:
    go_home()
elif bin_in_gripper:
    if bin_needs_flip:
        flip_bin()
    else:
        place_on_stack()
else:
    pick_bin_from_conveyor()
```

---

### 方案 2: SO-100 机器人码垛演示 ⭐⭐⭐⭐

**针对小型机械臂的轻量级方案**。

#### 基本信息

- **演示文档**: [SO-100 Demo Specs](https://studylib.net/doc/28151059/isaac-sim-demo-specifications.md)
- **URDF 来源**: [LeRobot SO-100](https://wiki.seeedstudio.com/lerobot_so100m_isaacsim/)
- **场景**: Box Palletizing + Depalletizing

#### 箱子规格

| 参数 | 值 |
|------|-----|
| 尺寸 | 8cm × 6cm × 4cm |
| 重量 | 0.2 kg |
| 堆叠模式 | 2×2×2 = 8 个箱子 |
| 颜色 | 可配置（用于分类码垛） |

#### 演示任务

1. **Demo 8: Box Palletizing**
   - 从传送带抓取箱子
   - 按 2×2 模式堆叠到托盘
   - 实现时间：4-5天

2. **Demo 9: Box Depalletizing**
   - 托盘上预先堆叠 2×2×2 = 8 个箱子
   - 机器人逐个移除箱子
   - 放置到指定位置

#### URDF 路径

```bash
/lerobot/SO-ARM100/URDF/SO_5DOF_ARM100_8j_URDF.SLDASM/urdf/SO_5DOF_ARM100_8j_URDF.SLDASM.urdf
```

#### 导入到 Isaac Sim

```python
# 使用 URDF Importer
import omni.isaac.core.utils.nucleus as nucleus

urdf_path = "/path/to/SO_5DOF_ARM100_8j_URDF.SLDASM.urdf"
robot = nucleus.get_assets_root_path() + "/Robots/SO-100/so100.usd"

# 导入并转换
from omni.isaac.urdf import _urdf
urdf_interface = _urdf.acquire_urdf_interface()
urdf_interface.parse_urdf(urdf_path, robot)
```

---

### 方案 3: Trossen Mobile AI（移动操作平台）⭐⭐⭐⭐⭐

**完整的移动操作解决方案**，已解决底盘+机械臂控制问题。

#### 基本信息

- **GitHub 仓库**: [TrossenRobotics/trossen_ai_isaac](https://github.com/TrossenRobotics/trossen_ai_isaac)
- **机器人型号**: Mobile AI（差分驱动底盘 + 机械臂）
- **框架支持**: Isaac Sim + Isaac Lab

#### 包含内容

```
trossen_ai_isaac/
├── assets/robots/
│   ├── mobile_ai/mobile_ai.usd        # 移动机械臂完整模型
│   ├── stationary_ai/                 # 固定机械臂
│   └── wxai/                          # 双臂系统
├── examples/
│   ├── pick_and_place.py              # 抓取放置示例
│   └── target_following.py            # 目标跟踪
├── tasks/
│   ├── reach/                         # 到达任务
│   ├── lift/                          # 提升任务
│   └── cabinet/                       # 开柜任务
└── teleoperation/
    └── leader_arm_teleop.py           # 遥操作数据收集
```

#### 特点

✅ **优点：**
- 已解决底盘+机械臂控制问题（开箱即用）
- 完整的 RL 训练环境（Isaac Lab）
- Teleoperation 数据收集功能
- 支持模仿学习（Imitation Learning）

#### 运行示例

```bash
# 1. 安装依赖
cd trossen_ai_isaac
./isaaclab.sh --install

# 2. 启动机器人可视化
./isaaclab.sh -p scripts/bringup_robot.py --robot mobile_ai

# 3. 运行 Pick-and-Place 任务
./isaaclab.sh -p examples/pick_and_place.py

# 4. RL 训练
./isaaclab.sh -p scripts/rsl_rl/train.py --task Isaac-Reach-MobileAI-v0
```

#### Mobile AI 配置示例

```python
# 来自 trossen_ai_isaac 的配置
from trossen_ai_isaac.robots import MobileAICfg

robot = MobileAICfg(
    # 底盘配置
    base_controller="differential_drive",
    wheel_radius=0.05,
    wheel_separation=0.3,

    # 机械臂配置
    arm_dof_indices=[0, 1, 2, 3, 4, 5],
    gripper_dof_index=6,

    # 末端执行器
    ee_link="end_effector_link",
)
```

---

### 方案 4: TidyBot++ 移动操作平台 ⭐⭐⭐⭐

**学术研究级别的移动操作机器人**。

#### 基本信息

- **GitHub**: [roahmlab/tidybot_ros](https://github.com/roahmlab/tidybot_ros)
- **组成**: 移动底盘 + Kinova Gen3 机械臂
- **支持**: Gazebo + Isaac Sim 双仿真环境

#### 机器人组成

| 组件 | 型号/配置 |
|------|----------|
| 底盘 | 差分驱动或全向轮 |
| 机械臂 | Kinova Gen3 (7-DoF) |
| 夹爪 | Robotiq 2F-140 |
| 相机 | Orbbec 深度相机 |
| 控制 | ROS2 + MoveIt |

#### 支持的任务

1. **Diffusion Policy 训练与部署**
   - 在 Gazebo/Isaac Sim 中训练
   - 部署到真实硬件

2. **VLA 模型微调**
   - Vision-Language-Action 模型
   - 多模态控制

#### 运行 Isaac Sim 仿真

```bash
# 1. 启动 Isaac Sim（容器1）
docker run --gpus all -it isaac-sim-container
./isaac-sim.sh

# 2. 启动 ROS2 控制节点（容器2）
docker run --network host -it tidybot-ros-container
ros2 launch tidybot_bringup sim_isaac.launch.py

# 3. 运行策略
ros2 run tidybot_policy deploy_policy --model diffusion
```

---

## 🚀 推荐实施路径

根据你的需求（轮式底盘 + 机械臂码垛），我推荐以下实施步骤：

### 阶段 1: 学习移动操作配置（1-2天）

**目标**: 理解如何正确配置底盘+机械臂

**资源**:
- 克隆 Trossen Mobile AI 仓库
- 研究 `mobile_ai.usd` 的配置
- 运行官方示例，理解执行器组配置

```bash
git clone https://github.com/TrossenRobotics/trossen_ai_isaac.git
cd trossen_ai_isaac
./isaaclab.sh -p scripts/bringup_robot.py --robot mobile_ai
```

**学习重点**:
```python
# 注意这部分配置
actuator_groups={
    "base": ActuatorGroupCfg(...),    # 底盘配置
    "arm": ActuatorGroupCfg(...),     # 机械臂配置
    "tool": ActuatorGroupCfg(...),    # 夹爪配置
}
```

---

### 阶段 2: 移植 UR10 码垛场景（3-4天）

**目标**: 将 UR10 的码垛逻辑迁移到移动机械臂

#### 步骤 2.1: 准备 UR10 场景

```bash
# 运行原始 UR10 Bin Stacking
cd <isaac_sim_root>
./python.sh standalone_examples/api/isaacsim.cortex.framework/ur10_bin_stacking.py
```

**观察重点**:
- 传送带如何生成箱子
- 机械臂如何抓取和放置
- Cortex 决策网络的逻辑

#### 步骤 2.2: 替换机器人模型

```python
# ur10_bin_stacking.py 修改
from omni.isaac.orbit.robots.mobile_manipulator import MobileManipulatorCfg

# 原来：固定底座 UR10
# robot = UR10Cfg(...)

# 修改为：移动机械臂
robot = MobileManipulatorCfg(
    usd_path="/path/to/mobile_robot.usd",
    meta_info=MobileManipulatorCfg.MetaInfoCfg(
        base_num_dof=2,
        arm_num_dof=6,
        tool_num_dof=2,
    ),
    actuator_groups={
        "base": ...,
        "arm": ...,
        "tool": ...,
    }
)
```

#### 步骤 2.3: 调整码垛逻辑

**保持不变**:
- ✅ 传送带生成箱子的逻辑
- ✅ 抓取和放置的决策网络
- ✅ 托盘的堆叠位置计算

**需要修改**:
- 🔧 机械臂末端执行器的坐标（因为底盘可能移动）
- 🔧 添加底盘导航逻辑（如果需要移动）

---

### 阶段 3: 添加移动能力（可选，2-3天）

**目标**: 让机器人可以在不同位置之间移动

#### 选项 A: 静态底盘（简单）

底盘不移动，只用机械臂码垛：

```python
# 底盘速度始终为 0
base_velocity = torch.zeros(2)  # [left_wheel, right_wheel] = [0, 0]
```

#### 选项 B: 导航到固定位置（中等）

底盘在几个固定位置之间切换：

```python
# 位置1: 传送带旁（抓取位置）
# 位置2: 托盘旁（放置位置）

if task == "pick":
    navigate_to(conveyor_position)
elif task == "place":
    navigate_to(pallet_position)
```

#### 选项 C: 完全自主导航（复杂）

集成 Isaac ROS Navigation：

```python
# 使用 Nav2 + Isaac ROS
from isaac_ros_navigation import NavigationStack

nav = NavigationStack()
nav.navigate_to_pose(goal_pose)
```

---

### 阶段 4: 测试与优化（1-2天）

#### 4.1 功能测试

- [ ] 底盘能独立移动
- [ ] 机械臂能独立移动
- [ ] 底盘和机械臂能同时控制
- [ ] 传送带正常生成箱子
- [ ] 机械臂能抓取箱子
- [ ] 机械臂能准确码垛

#### 4.2 性能优化

```python
# 调整物理参数
sim.set_solver_iterations(8)           # 默认4，增加稳定性
sim.set_contact_offset(0.002)          # 接触偏移
sim.set_rest_offset(0.001)             # 静止偏移

# 调整抓取力
gripper_force = 100.0  # 增加抓取力，避免箱子掉落

# 调整码垛速度
arm_velocity_limit = 1.0  # m/s，避免过快导致不稳定
```

---

## 📚 关键技术文档

### Isaac Sim 官方文档

| 主题 | 链接 |
|------|------|
| UR10 Bin Stacking 教程 | [docs.isaacsim.omniverse.nvidia.com](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/cortex_tutorials/tutorial_cortex_5_ur10_bin_stacking.html) |
| 导入机械臂教程 | [Tutorial 6: Setup a Manipulator](https://docs.isaacsim.omniverse.nvidia.com/6.0.0/robot_setup_tutorials/tutorial_import_assemble_manipulator.html) |
| 移动机器人教程 | [Tutorial 5: Rig a Mobile Robot](https://docs.isaacsim.omniverse.nvidia.com/6.0.0/robot_setup_tutorials/tutorial_import_assemble_mobile_robot.html) |
| Cortex 框架文档 | [Building Cortex Extensions](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/cortex_tutorials/tutorial_cortex_7_cortex_extension.html) |

### IsaacLab 文档

| 主题 | 链接 |
|------|------|
| 添加新机器人 | [Adding a New Robot](https://isaac-sim.github.io/IsaacLab/main/source/tutorials/01_assets/add_new_robot.html) |
| 执行器配置 | [isaaclab.actuators API](https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.actuators.html) |
| 移动操作讨论 | [Discussion #1090](https://github.com/isaac-sim/IsaacLab/discussions/1090) |

### GitHub 仓库

| 项目 | 链接 | 说明 |
|------|------|------|
| Trossen AI Isaac | [TrossenRobotics/trossen_ai_isaac](https://github.com/TrossenRobotics/trossen_ai_isaac) | 移动操作平台 |
| TidyBot++ ROS2 | [roahmlab/tidybot_ros](https://github.com/roahmlab/tidybot_ros) | 学术级移动机器人 |
| IsaacLab | [isaac-sim/IsaacLab](https://github.com/isaac-sim/IsaacLab) | Isaac Lab 框架 |

---

## 🐛 常见问题与解决方案

### 问题 1: 底盘和机械臂控制冲突

**症状**: 控制底盘时，机械臂停止；控制机械臂时，底盘停止。

**原因**: 使用了单一的 `ArticulationCfg` 而非 `MobileManipulatorCfg`。

**解决方案**:

```python
# ❌ 错误做法
robot = ArticulationCfg(
    prim_path="/World/Robot",
    spawn=UsdFileCfg(usd_path="mobile_robot.usd"),
)

# ✅ 正确做法
robot = MobileManipulatorCfg(
    meta_info=MobileManipulatorCfg.MetaInfoCfg(
        usd_path="mobile_robot.usd",
        base_num_dof=2,
        arm_num_dof=6,
    ),
    actuator_groups={
        "base": ActuatorGroupCfg(...),
        "arm": ActuatorGroupCfg(...),
    }
)
```

---

### 问题 2: 重力补偿不足，机械臂下垂

**症状**: 机械臂在静止时会慢慢下垂。

**原因**: PD 控制器的 stiffness 太低，无法对抗重力。

**解决方案**:

```python
# 方法 1: 增加 stiffness
"arm": ActuatorGroupCfg(
    control_cfg=ActuatorControlCfg(
        stiffness={".*": 2500.0},  # 从 800 增加到 2500
        damping={".*": 100.0},
    ),
)

# 方法 2: 使用重力补偿（推荐）
from isaaclab.controllers import GravityCompensationController

gravity_comp = GravityCompensationController(robot)
torque = gravity_comp.compute()
robot.set_joint_effort_target(torque)
```

**参考**: [IsaacLab Issue #2886](https://github.com/isaac-sim/IsaacLab/issues/2886)

---

### 问题 3: URDF 导入后关节不正确

**症状**: 从 URDF 转换到 USD 后，某些关节缺失或行为异常。

**原因**: URDF 转换过程中可能丢失信息。

**解决方案**:

```bash
# 1. 使用最新的 URDF Importer
# Isaac Sim > Isaac Utils > URDF Importer

# 2. 检查转换后的 USD 文件
# 打开 Stage 窗口，检查关节层级结构

# 3. 手动修复缺失的关节
# 在 Property 面板中添加 Physics > Articulation
```

**详细教程**: [Tutorial 6: Setup a Manipulator](https://docs.isaacsim.omniverse.nvidia.com/6.0.0/robot_setup_tutorials/tutorial_import_assemble_manipulator.html)

---

### 问题 4: 箱子抓取不稳定，容易掉落

**症状**: 夹爪抓住箱子后，移动时箱子会掉落。

**原因**:
1. 夹爪力不足
2. 摩擦系数太低
3. 接触点太少

**解决方案**:

```python
# 方法 1: 增加夹爪力
gripper_cfg = ActuatorGroupCfg(
    model_cfg=ImplicitActuatorCfg(
        stiffness=200.0,  # 增加刚度
        damping=20.0,
    ),
)

# 方法 2: 调整物理材质
from omni.isaac.core.materials import PhysicsMaterial

# 夹爪材质
gripper_material = PhysicsMaterial(
    prim_path="/World/Materials/Gripper",
    static_friction=1.0,     # 静摩擦系数
    dynamic_friction=0.8,    # 动摩擦系数
    restitution=0.0,         # 弹性系数（0 = 不反弹）
)

# 箱子材质
box_material = PhysicsMaterial(
    prim_path="/World/Materials/Box",
    static_friction=1.0,
    dynamic_friction=0.8,
    restitution=0.1,
)

# 方法 3: 使用吸盘夹爪（最稳定）
# UR10 Bin Stacking 示例中使用的是吸盘夹爪
# 参考: ur10_bin_stacking.py
```

---

### 问题 5: 码垛位置不准确

**症状**: 箱子放置位置偏移，堆叠不整齐。

**原因**:
1. 运动学计算误差
2. 末端执行器偏移
3. 托盘位置不准确

**解决方案**:

```python
# 1. 精确标定末端执行器
robot_cfg = MobileManipulatorCfg(
    ee_info=MobileManipulatorCfg.EndEffectorFrameCfg(
        body_name="ee_link",
        pos_offset=(0.0, 0.0, 0.15),  # 精确测量偏移
        rot_offset=(1.0, 0.0, 0.0, 0.0),
    ),
)

# 2. 使用视觉反馈（推荐）
from isaac_ros_vision import ObjectDetector

detector = ObjectDetector()
box_pose = detector.detect_box()  # 实时检测箱子位置
place_pose = compute_stack_position(box_pose)

# 3. 添加放置后的验证
def verify_placement(expected_pose, tolerance=0.01):
    actual_pose = get_box_pose()
    error = np.linalg.norm(actual_pose - expected_pose)
    if error > tolerance:
        retry_placement()
```

---

## 🎯 快速启动指南

### 最小可行方案（1天内可运行）

**目标**: 在 Isaac Sim 中看到一个能同时控制底盘和机械臂的移动机器人。

```bash
# 1. 克隆 Trossen AI Isaac 仓库
git clone https://github.com/TrossenRobotics/trossen_ai_isaac.git
cd trossen_ai_isaac

# 2. 安装依赖
./isaaclab.sh --install

# 3. 启动机器人可视化
./isaaclab.sh -p scripts/bringup_robot.py --robot mobile_ai

# 4. 测试底盘控制
# 在 Isaac Sim 中，打开 Python Script Editor
# 执行以下代码：
```

```python
# 测试脚本
import torch
from omni.isaac.lab.app import AppLauncher

# 获取机器人
robot = world.scene["robot"]

# 控制底盘移动（差分驱动）
base_velocity = torch.tensor([[0.5, 0.5]])  # [left, right] 前进
robot.set_joint_velocity_target(base_velocity, joint_ids=[0, 1])

# 控制机械臂（位置控制）
arm_position = torch.tensor([[0.0, -0.5, 0.5, 0.0, 0.5, 0.0]])
robot.set_joint_position_target(arm_position, joint_ids=[2, 3, 4, 5, 6, 7])

# 同时控制（验证两者可以同时动）
world.step()
```

---

### 完整码垛方案（1周内可运行）

#### Day 1-2: 环境搭建

```bash
# 1. 安装 Isaac Sim 5.1.0+
# 下载: https://developer.nvidia.com/isaac-sim

# 2. 安装 Isaac Lab
git clone https://github.com/isaac-sim/IsaacLab.git
cd IsaacLab
./isaaclab.sh --install

# 3. 克隆参考仓库
git clone https://github.com/TrossenRobotics/trossen_ai_isaac.git
```

#### Day 3-4: 运行 UR10 码垛

```bash
cd <isaac_sim_root>
./python.sh standalone_examples/api/isaacsim.cortex.framework/ur10_bin_stacking.py
```

**学习重点**:
- 观察传送带如何生成箱子
- 理解 Cortex 决策网络
- 记录托盘堆叠位置算法

#### Day 5-6: 替换为移动机器人

```python
# 修改 ur10_bin_stacking.py

# 1. 替换机器人配置
from trossen_ai_isaac.robots import MobileAICfg
robot = MobileAICfg()

# 2. 调整末端执行器偏移
ee_offset = (0.0, 0.0, 0.15)  # 根据实际测量

# 3. 保持码垛逻辑不变
# ... Cortex 决策网络代码保持不变 ...
```

#### Day 7: 测试与调优

```python
# 测试清单
tests = [
    "底盘独立移动",
    "机械臂独立移动",
    "同时控制底盘和机械臂",
    "抓取箱子",
    "码垛到托盘",
    "处理翻转箱子",
]

for test in tests:
    run_test(test)
    verify_result(test)
```

---

## 📊 性能优化建议

### 1. 仿真速度优化

```python
# 减少渲染负担
sim.set_rendering_dt(1/30)  # 30 FPS 足够

# 使用 GPU 加速
sim.set_gpu_found(0)
sim.set_gpu_physics_enabled(True)

# 减少子步数（如果稳定性足够）
sim.set_physics_dt(1/200)  # 从 1/1000 降低到 1/200
```

### 2. 训练加速

```python
# 使用多环境并行
num_envs = 4096  # 增加并行环境数量

# 使用 Warp 后端（更快的张量操作）
import warp as wp
wp.init()
```

### 3. 内存优化

```python
# 限制场景物体数量
max_boxes = 50  # 传送带上最多 50 个箱子

# 定期清理已完成的箱子
if len(boxes) > max_boxes:
    remove_oldest_box()
```

---

## 🔗 参考资源汇总

### 文档

1. [Isaac Sim UR10 Bin Stacking Tutorial](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/cortex_tutorials/tutorial_cortex_5_ur10_bin_stacking.html)
2. [Isaac Lab Mobile Manipulator Discussion](https://github.com/isaac-sim/IsaacLab/discussions/1090)
3. [SO-100 Demo Specifications](https://studylib.net/doc/28151059/isaac-sim-demo-specifications.md)
4. [Isaac Sim Robot Setup Tutorials](https://docs.isaacsim.omniverse.nvidia.com/6.0.0/robot_setup_tutorials/index.html)

### 代码仓库

1. [TrossenRobotics/trossen_ai_isaac](https://github.com/TrossenRobotics/trossen_ai_isaac) - 移动操作平台
2. [roahmlab/tidybot_ros](https://github.com/roahmlab/tidybot_ros) - 学术级移动机器人
3. [isaac-sim/IsaacLab](https://github.com/isaac-sim/IsaacLab) - Isaac Lab 框架
4. [isaac-sim/OmniIsaacGymEnvs](https://github.com/isaac-sim/OmniIsaacGymEnvs) - RL 训练环境

### 视频教程

1. [NVIDIA Isaac Sim Tutorials](https://www.youtube.com/playlist?list=PL3xUNnH4TdbsfndCMkJaEQMLCUgpj0H2g)
2. [Cortex Framework Overview](https://developer.nvidia.com/blog/cortex-framework/)

### 论文

1. **WholeBodyVLA**: Towards Unified Latent VLA for Whole-body Loco-manipulation Control (ICLR 2026)
2. **VIRAL**: Visual Sim-to-Real at Scale for Humanoid Loco-Manipulation (2025.11)
3. **FALCON**: Learning Force-Adaptive Humanoid Loco-Manipulation (2026)

---

## 📝 总结

### 核心要点

1. ✅ **正确配置是关键**: 使用 `MobileManipulatorCfg`，分离底盘和机械臂控制
2. ✅ **从成熟方案开始**: UR10 Bin Stacking 提供完整的码垛逻辑
3. ✅ **参考现有项目**: Trossen Mobile AI 已解决移动操作难题
4. ✅ **循序渐进**: 先静态码垛，再添加移动能力

### 下一步行动

1. **今天**: 克隆 Trossen AI Isaac，运行 Mobile AI 示例
2. **本周**: 运行 UR10 Bin Stacking，理解码垛逻辑
3. **下周**: 结合两者，实现移动机器人码垛

### 成功标准

- [ ] 底盘和机械臂可以同时控制
- [ ] 机械臂能稳定抓取箱子
- [ ] 能准确码垛到托盘（2×2×2 模式）
- [ ] 处理箱子翻转逻辑
- [ ] 传送带持续生成箱子

---

**祝你搭建成功！如有问题，欢迎随时咨询。** 🚀
