# RJ2506 轮式双臂机器人轮胎上流水线仿真实施计划

## Summary

本计划基于当前仓库 `INVENTORY.md` 和相邻资产目录 `../supre_robot_assets` 的实际可用资源更新，不再按“从零搭建场景”处理，而是按“复用现有 Isaac Sim 资产并做任务化封装”推进。

目标是构建一个 **RJ2506 轮式双臂机器人将轮胎搬运到真实运动流水线的仿真场景**，并为后续训练环境或任务接口做好结构化准备。第一版优先保证场景稳定加载、机器人可控、轮胎可搬运、放上传送带后可继续输送。

## Available Resources

### 仿真器与运行基础

- Isaac Sim 5.1.0 Docker 运行基线已经在资源说明中出现，可作为当前主仿真器。
- Isaac Lab 2.3.0 + IsaacLab Arena 0.1.1 在 `INVENTORY.md` 中有外部参考信息，但本项目内现有资产和脚本明显更偏向 **Isaac Sim 原生 USD 场景拼装与脚本驱动**。
- 当前仓库已有可参考的 Isaac Sim 场景渲染脚本：
  - `render_supre_scene_preview.py`
  - `render_supre_scene_thumbnails.py`
- 当前仓库已有一个可运行范式参考：
  - `ur10/run_ur10_bin_stacking.py`
  - 该脚本可作为“任务脚本、对象生成、场景加载、相机采集”的代码风格基线。

### 可直接复用的 RJ2506 / 工厂 / 轮胎 / 传送带资产

来自 `../supre_robot_assets` 的关键资产如下：

- 机器人
  - `../supre_robot_assets/assets/robots/RJ2506/RJ2506.usd`
  - `../supre_robot_assets/assets/robots/RJ2506/urdf/RJ2506_fixed.urdf`
  - `../supre_robot_assets/assets/robots/RJ2506/config/joint_names_RJ2506.yaml`
- 主场景
  - `../supre_robot_assets/scenes/factory_with_rj2506_fixed.usd`
  - `../supre_robot_assets/scenes/factory_with_rj2506_physics_ready.usd`
  - `../supre_robot_assets/scenes/factory_with_rj2506_articulation.usd`
  - `../supre_robot_assets/scenes/factory_with_rj2506_complete.usd`
- 工业部件
  - `../supre_robot_assets/assets/nvidia_official/Conveyors/ConveyorBelt_A08.usd`
  - `../supre_robot_assets/assets/nvidia_official/Pallet/pallet.usd`
- 轮胎资产
  - `../supre_robot_assets/assets/realistic_wheel/final_car_wheel.usd`

### 资源选择结论

- **默认起点场景**：`factory_with_rj2506_fixed.usd`
  - 原因：在资产说明中被标注为“推荐优先使用的稳定主场景”。
- **物理排查场景**：`factory_with_rj2506_physics_ready.usd`
  - 用于轮胎接触、放带稳定性、底盘与机械臂联动物理测试。
- **控制排查场景**：`factory_with_rj2506_articulation.usd`
  - 用于确认关节句柄、drive、articulation root 与控制 API。
- **展示场景**：`factory_with_rj2506_complete.usd`
  - 用于最终渲染或演示版本，而不是第一阶段开发基线。

## Implementation Changes

### 1. 场景策略

- 以 `factory_with_rj2506_fixed.usd` 为主入口，不重建整套工厂。
- 在主场景中补入或重定位以下任务元素：
  - 取料位
  - 轮胎初始生成区
  - 传送带放置区
  - 机器人安全停靠位
  - 可选托盘或缓存位
- 第一版不强制修改已有大场景结构；优先使用增量式 USD 引用和 prim 定位。
- 若主场景中已存在传送带布局不适配，则直接引用 `ConveyorBelt_A08.usd` 新增一条任务专用流水线，不在第一阶段大改原场景。

### 2. 机器人资产与控制基线

- 机器人优先直接引用 `RJ2506.usd`，避免每次从 URDF 重新导入。
- 若 Isaac Sim 中发现关节、drive 或 articulation 行为异常，则回退到以下验证链：
  1. `factory_with_rj2506_articulation.usd` 验证关节可发现性
  2. `factory_with_rj2506_physics_ready.usd` 验证物理稳定性
  3. 必要时基于 `RJ2506_fixed.urdf` 重新导入生成修正版 USD
- 控制上将 RJ2506 拆分为四组接口：
  - 底盘
  - 左臂
  - 右臂
  - 双手/夹持执行
- 第一版不做端到端连续控制训练，先做任务级状态机和子动作接口：
  - `navigate_to_pick`
  - `pre_grasp_align`
  - `dual_arm_grasp`
  - `lift`
  - `transport_to_conveyor`
  - `place_on_conveyor`
  - `release_and_retreat`

### 3. 轮胎建模策略

- 视觉模型直接使用 `final_car_wheel.usd`。
- 第一版不要直接假设该 USD 已具备训练稳定所需的碰撞体和惯量。
- 实施时分为两层：
  - 视觉层：保留 `final_car_wheel.usd`
  - 物理层：视验证结果决定是否增加简化碰撞代理或包围体
- 默认目标不是做完全真实轮胎弹性仿真，而是实现：
  - 可抓取
  - 可提升
  - 可搬运
  - 可稳定放上传送带并被继续输送
- 若高保真轮胎碰撞导致不稳定，允许在第一版里保留视觉高保真、物理中等保真。

### 4. 流水线策略

- 传送带优先使用 `ConveyorBelt_A08.usd`。
- 需要明确验证三件事：
  - 该传送带是否自带可配置运动接口
  - 轮胎放上去后的摩擦与姿态是否稳定
  - 机器人末端与传送带护栏/边缘是否冲突
- 第一版成功条件定义为：
  - 轮胎被双臂搬运到目标放置区
  - 双臂释放后轮胎保持在皮带有效工作面
  - 轮胎随后被皮带继续向下游输送若干步
- 如果直接平放落带容易侧翻或卡边，允许增加轻量导向结构，但不要改成“缓存位伪装成流水线”。

### 5. 任务流程

第一版任务闭环固定为：

1. 机器人从待机位出发。
2. 轮胎在取料区生成或复位。
3. 底盘移动到抓取准备位。
4. 双臂协同对位。
5. 双臂夹持并抬起轮胎。
6. 底盘搬运到传送带放置位。
7. 双臂将轮胎平放到运动皮带。
8. 释放轮胎并撤离。
9. 验证轮胎被成功输送。
10. 生成下一轮胎，形成连续上料循环。

### 6. 工程落地结构

项目内建议新增并固定以下目录：

- `docs/`
  - 存放本计划、验证记录、资产选型说明
- `src/dkk_simulation/`
  - `assets.py`：统一资产路径和资源选择
  - `scene_builder.py`：加载主场景并附加轮胎、传送带、相机、标记位
  - `robot_interface.py`：RJ2506 控制和关节/底盘句柄封装
  - `task_flow.py`：状态机与任务阶段切换
  - `env.py`：训练/评测接口包装
- `configs/`
  - `rj2506_tire_loading.yaml`
- `scripts/`
  - `run_rj2506_tire_loading.py`
  - `check_rj2506_scene.py`
  - `check_conveyor_tire_contact.py`
- `tests/`
  - 配置解析、任务状态机、资产路径解析、无 Isaac Sim 条件下的单元测试

## Public Interfaces

### 配置接口

配置文件至少暴露以下字段：

- 主场景路径
- 机器人 USD 路径
- 轮胎 USD 路径
- 传送带 USD 路径
- 取料位 pose
- 放置位 pose
- 待机位 pose
- 相机配置
- conveyor 速度
- episode 最大步数
- 成功/失败阈值

### 环境接口

环境包装层固定提供：

- `reset(seed=None, options=None)`
- `step(action)`
- `get_observation()`
- `get_action_mask()`
- `is_success()`
- `is_failure()`

### 任务阶段枚举

建议固定为：

- `IDLE`
- `NAVIGATE_TO_PICK`
- `PRE_GRASP_ALIGN`
- `DUAL_ARM_GRASP`
- `LIFT`
- `TRANSPORT_TO_CONVEYOR`
- `PLACE_ON_CONVEYOR`
- `RELEASE`
- `RETREAT`
- `DONE`
- `FAILED`

## Test Plan

### 场景与资产验证

- 验证 `factory_with_rj2506_fixed.usd` 能在 Isaac Sim 中正常加载。
- 验证 `RJ2506.usd` 在主场景中的 prim 路径、关节数量和 articulation 句柄可正确发现。
- 验证 `ConveyorBelt_A08.usd` 可单独加载并参与物理仿真。
- 验证 `final_car_wheel.usd` 可单独加载，并检查碰撞、重心和接触稳定性。

### 控制验证

- 底盘可独立前进、后退、转向。
- 左右臂可独立运动到预设姿态。
- 双臂可同步执行抓取对位动作。
- 机器人在持胎状态下移动时不出现明显自碰撞或姿态发散。

### 任务闭环验证

- 单轮胎抓取、抬升、搬运、落带、释放流程可完整执行。
- 轮胎放上传送带后可持续输送而非立即弹飞、穿透或卡死。
- 连续上料至少可完成多个轮胎循环。

### 回退验证

- 若主场景控制异常，使用 `factory_with_rj2506_articulation.usd` 复核控制接口。
- 若主场景物理异常，使用 `factory_with_rj2506_physics_ready.usd` 复核物理参数。
- 若 USD 资产本身存在问题，再回退到 `RJ2506_fixed.urdf` 做重导入验证。

## Assumptions

- 当前最现实的主路线是 **Isaac Sim 原生脚本驱动 + 现有 USD 场景复用**，而不是直接切到 Isaac Lab 新建全套任务。
- `factory_with_rj2506_fixed.usd` 是第一阶段最稳妥的主开发入口。
- `final_car_wheel.usd` 更适合做视觉主资产，碰撞和惯量可能仍需二次调整。
- `ConveyorBelt_A08.usd` 是第一版流水线首选，不额外自建皮带模型。
- 第一阶段的重点是把场景和任务闭环跑通，再决定是否向训练环境、策略学习或更高保真接触建模推进。

