# UR10 Bin Stacking

This folder contains a runnable wrapper around Isaac Sim's official Cortex UR10 conveyor/bin-stacking example.

Files:

- `run_ur10_bin_stacking.py`: headless wrapper adapted from `demo_ur10_conveyor_main.py`
- `run_ur10_bin_stacking_in_container.sh`: helper to execute the wrapper inside the `wheel-isaac-sim` container
- `last_run.log`: latest captured console log after a run

The wrapper keeps the official task logic, but changes execution to:

- headless mode
- auto-play on entry
- fixed-duration run with `is_done_cb`

Run from this repository root:

```bash
bash ur10/run_ur10_bin_stacking_in_container.sh
```
