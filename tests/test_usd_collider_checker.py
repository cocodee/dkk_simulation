import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_usd_colliders.py"
SPEC = importlib.util.spec_from_file_location("check_usd_colliders", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
check_usd_colliders = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = check_usd_colliders
SPEC.loader.exec_module(check_usd_colliders)


class UsdColliderCheckerTests(unittest.TestCase):
    def test_overlapping_collider_pairs_are_sorted_by_volume(self) -> None:
        colliders = [
            check_usd_colliders.ColliderBounds("/A", (0.0, 0.0, 0.0), (2.0, 2.0, 2.0)),
            check_usd_colliders.ColliderBounds("/B", (1.0, 1.0, 1.0), (3.0, 3.0, 3.0)),
            check_usd_colliders.ColliderBounds("/C", (1.5, 1.5, 1.5), (2.1, 2.1, 2.1)),
            check_usd_colliders.ColliderBounds("/D", (5.0, 5.0, 5.0), (6.0, 6.0, 6.0)),
        ]

        overlaps = check_usd_colliders.find_overlapping_colliders(colliders, tolerance=1e-6)

        self.assertEqual(
            [(overlap.first_prim_path, overlap.second_prim_path) for overlap in overlaps],
            [("/A", "/B"), ("/B", "/C"), ("/A", "/C")],
        )
        self.assertEqual(overlaps[0].overlap_size, (1.0, 1.0, 1.0))

    def test_touching_aabbs_are_not_reported_as_overlaps(self) -> None:
        colliders = [
            check_usd_colliders.ColliderBounds("/A", (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
            check_usd_colliders.ColliderBounds("/B", (1.0, 0.0, 0.0), (2.0, 1.0, 1.0)),
        ]

        overlaps = check_usd_colliders.find_overlapping_colliders(colliders, tolerance=1e-6)

        self.assertEqual(overlaps, [])


if __name__ == "__main__":
    unittest.main()
