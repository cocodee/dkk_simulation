# UR10 Bin Stacking Baseline

This document extracts the official Isaac Sim Cortex UR10 bin-stacking example into a migration baseline for a future mobile manipulation version.

## Source of Truth

- Official entry logic: `/isaac-sim/standalone_examples/api/isaacsim.cortex.framework/demo_ur10_conveyor_main.py`
- Cortex behavior: `isaacsim.cortex.behaviors.ur10.bin_stacking_behavior`
- Local runnable wrapper: [run_ur10_bin_stacking.py](/root/data1/kdi/workspace/dkk_simulation/ur10/run_ur10_bin_stacking.py)

## Scene Composition

The demo scene is assembled from three main assets:

- `Isaac/Samples/Leonardo/Stage/ur10_bin_stacking_short_suction.usd`
  Contains the fixed-base UR10 cell, conveyor, suction tool, and palletizing workspace.
- `Isaac/Props/KLT_Bin/small_KLT.usd`
  Spawned repeatedly as the conveyor bin.
- `Isaac/Environments/Simple_Warehouse/warehouse.usd`
  Used as the visual background.

The wrapper adds the stage under:

- `/World/Ur10Table`
- `/World/Background`

## Runtime Task Structure

Task logic lives in `BinStackingTask`:

- Monitors whether a conveyor bin exists in the active region.
- Spawns a new `small_KLT` bin when the previous one leaves the conveyor area.
- Assigns initial pose and linear velocity to the spawned bin.

Behavior logic lives in `BinStackingContext` and the UR10 bin-stacking decider network:

- Chooses the active bin on the conveyor.
- Computes grasp transform and grasp status.
- Decides whether the bin needs flipping.
- Places bins onto predefined stack coordinates.

## Important Fixed Assumptions

These parts are hard-coded for a stationary UR10 cell:

- Robot prim path: `/World/Ur10Table/ur10`
- Pallet stack coordinates in `BinStackingContext`
- Obstacle geometry around the flip station and navigation barrier
- Conveyor spawn region and bin flow direction

## Migration Plan To Mobile Robot

Keep:

- Conveyor bin spawn logic
- Bin state tracking
- Stack target generation
- High-level pick/flip/place decision flow

Replace:

- `CortexUr10` with a mobile manipulator robot abstraction
- Fixed robot prim path with a mobile base + arm hierarchy
- Stationary obstacle assumptions with navigation-aware collision zones
- End-effector motion policy with base-plus-arm coordinated motion

## Recommended Next Step

Use this UR10 example as the task baseline only. For the robot baseline, swap the fixed UR10 cell for a mobile manipulator while preserving:

1. conveyor bin spawning
2. bin selection and grasp state tracking
3. stack target bookkeeping
4. pick, flip, place state-machine structure
