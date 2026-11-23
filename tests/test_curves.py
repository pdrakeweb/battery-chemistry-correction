"""Offline tests for the battery_chemistry curve math.

curves.py has no Home Assistant imports, so it is imported directly by
path. Run: python3 -m pytest tests/ or python3 -m unittest discover tests
"""

import importlib.util
import unittest
from pathlib import Path

CURVES_PATH = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "battery_chemistry"
    / "curves.py"
)
spec = importlib.util.spec_from_file_location("curves", CURVES_PATH)
curves = importlib.util.module_from_spec(spec)
spec.loader.exec_module(curves)

correct = curves.correct_percent


class TestIdentity(unittest.TestCase):
    def test_alkaline_to_alkaline_is_identity(self):
        for pct in (0, 5, 10, 18, 25, 40, 50, 63, 80, 95, 100):
            self.assertAlmostEqual(correct(pct, "alkaline", "alkaline"), pct, places=6)

    def test_same_chemistry_is_identity_for_all(self):
        for chem in curves.CURVES:
            for pct in (0, 12, 33, 50, 77, 100):
                self.assertAlmostEqual(correct(pct, chem, chem), pct, places=6)


class TestNiMHCorrection(unittest.TestCase):
    def test_fresh_nimh_pack_corrects_high(self):
        # A fresh LSD NiMH pack reads ~16-25% on an alkaline gauge.
        self.assertGreaterEqual(correct(25, "alkaline", "nimh"), 75)
        self.assertGreaterEqual(correct(20, "alkaline", "nimh"), 70)
        self.assertGreaterEqual(correct(16, "alkaline", "nimh"), 60)

    def test_near_empty_nimh_corrects_near_zero(self):
        self.assertLessEqual(correct(2, "alkaline", "nimh"), 10)
        self.assertLessEqual(correct(0, "alkaline", "nimh"), 5)

    def test_midrange_is_between(self):
        mid = correct(10, "alkaline", "nimh")
        self.assertGreater(mid, correct(2, "alkaline", "nimh"))
        self.assertLess(mid, correct(25, "alkaline", "nimh"))


class TestMonotonicity(unittest.TestCase):
    def test_corrected_is_monotonic_in_reported(self):
        for actual in curves.CURVES:
            values = [correct(p, "alkaline", actual) for p in range(0, 101, 5)]
            for low, high in zip(values, values[1:]):
                self.assertLessEqual(low, high + 1e-9, f"{actual}: {values}")

    def test_curves_are_strictly_ordered(self):
        for name, curve in curves.CURVES.items():
            percents = [p for p, _ in curve]
            volts = [v for _, v in curve]
            self.assertEqual(percents, sorted(percents, reverse=True), name)
            self.assertEqual(volts, sorted(volts, reverse=True), name)


class TestRoundTripAndClamps(unittest.TestCase):
    def test_voltage_round_trip(self):
        for name, curve in curves.CURVES.items():
            for pct in (0, 7, 25, 50, 82, 100):
                v = curves.voltage_for_percent(curve, pct)
                self.assertAlmostEqual(
                    curves.percent_for_voltage(curve, v), pct, places=6, msg=name
                )

    def test_output_clamped(self):
        self.assertEqual(correct(150, "alkaline", "nimh"), 100)
        self.assertEqual(correct(-10, "alkaline", "nimh"), correct(0, "alkaline", "nimh"))

    def test_voltage_estimate_anchor(self):
        # The View Plus case: 18% on the alkaline scale is ~1.28 V/cell,
        # the NiMH plateau, so the corrected value is a high percentage.
        v = curves.estimate_cell_voltage(18, "alkaline")
        self.assertAlmostEqual(v, 1.277, places=3)
        self.assertGreaterEqual(correct(18, "alkaline", "nimh"), 65)


if __name__ == "__main__":
    unittest.main()
