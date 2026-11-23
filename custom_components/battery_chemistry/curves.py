"""Discharge-curve model for the Battery Chemistry Correction integration.

Pure Python, no Home Assistant imports, so the math can be unit tested
offline (see tests/test_curves.py).

Model
-----
A battery-powered device reports a percentage that its firmware derives
from pack voltage using a discharge curve for the cell chemistry the
device was designed for (almost always alkaline). When different cells
are installed (for example NiMH in an alkaline device), the reported
percentage is wrong because the chemistries have different voltage
curves.

Correction, per cell:

1. Invert the *source* chemistry's curve at the reported percentage to
   estimate the per-cell voltage the device must have measured.
2. Read the *actual* chemistry's curve at that voltage to get the true
   remaining percentage.

Curves are piecewise-linear tables of (remaining %, per-cell volts),
sorted by descending percentage. Percentages are clamped to 0-100 and
voltages outside a curve's range clamp to the curve's endpoints.

The alkaline table represents a typical low-drain device gauge
calibration, not a laboratory constant-current discharge: device gauges
are deliberately pessimistic in the lower half of the scale (the device
must still be running when it displays 0%, under load pulses and cold
temperatures), which is why a fresh NiMH pack at ~1.28 V/cell reads
only ~20% on an alkaline gauge. The NiMH table follows the published
discharge shape of low-self-discharge NiMH cells (flat ~1.25-1.2 V
plateau, knee below ~10%). The remaining chemistries are documented
approximations (resting-voltage tables for lead-acid, standard Li-ion
discharge shape, and the flat regulated output of 1.5 V lithium cells).

The result is an estimate derived from a reported percentage, not a
measurement.
"""

from __future__ import annotations

# (remaining percent, per-cell volts), descending percent.
ALKALINE: tuple[tuple[float, float], ...] = (
    (100.0, 1.60),
    (90.0, 1.52),
    (80.0, 1.47),
    (70.0, 1.43),
    (60.0, 1.40),
    (50.0, 1.37),
    (40.0, 1.34),
    (30.0, 1.315),
    (20.0, 1.285),
    (10.0, 1.245),
    (5.0, 1.21),
    (0.0, 1.00),
)

NIMH: tuple[tuple[float, float], ...] = (
    (100.0, 1.40),
    (90.0, 1.33),
    (80.0, 1.30),
    (70.0, 1.28),
    (60.0, 1.265),
    (50.0, 1.25),
    (40.0, 1.24),
    (30.0, 1.23),
    (20.0, 1.215),
    (10.0, 1.17),
    (5.0, 1.10),
    (0.0, 0.95),
)

# 1.5 V regulated lithium (e.g. USB-rechargeable AA with a buck regulator):
# output is held at ~1.5 V until the cell is nearly empty, then falls off.
LITHIUM_15V: tuple[tuple[float, float], ...] = (
    (100.0, 1.52),
    (50.0, 1.51),
    (20.0, 1.50),
    (10.0, 1.48),
    (5.0, 1.42),
    (0.0, 1.05),
)

# Li-ion, 3.7 V nominal, per cell.
LI_ION: tuple[tuple[float, float], ...] = (
    (100.0, 4.20),
    (90.0, 4.05),
    (80.0, 3.95),
    (70.0, 3.88),
    (60.0, 3.82),
    (50.0, 3.78),
    (40.0, 3.74),
    (30.0, 3.70),
    (20.0, 3.65),
    (10.0, 3.55),
    (5.0, 3.40),
    (0.0, 3.00),
)

# Lead-acid, per 2 V cell (multiply by 6 for a 12 V battery). Resting
# voltage approximation.
LEAD_ACID: tuple[tuple[float, float], ...] = (
    (100.0, 2.12),
    (90.0, 2.08),
    (80.0, 2.05),
    (70.0, 2.02),
    (60.0, 2.00),
    (50.0, 1.97),
    (40.0, 1.94),
    (30.0, 1.91),
    (20.0, 1.88),
    (10.0, 1.84),
    (0.0, 1.75),
)

CURVES: dict[str, tuple[tuple[float, float], ...]] = {
    "alkaline": ALKALINE,
    "nimh": NIMH,
    "lithium_15v": LITHIUM_15V,
    "li_ion": LI_ION,
    "lead_acid": LEAD_ACID,
}

CHEMISTRY_LABELS: dict[str, str] = {
    "alkaline": "Alkaline",
    "nimh": "NiMH / LSD NiMH",
    "lithium_15v": "Lithium 1.5V regulated",
    "li_ion": "Li-ion (3.7V)",
    "lead_acid": "Lead-acid 12V",
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def voltage_for_percent(curve: tuple[tuple[float, float], ...], percent: float) -> float:
    """Per-cell voltage at a remaining percentage, piecewise linear."""
    pct = _clamp(float(percent), 0.0, 100.0)
    for (p_hi, v_hi), (p_lo, v_lo) in zip(curve, curve[1:]):
        if p_lo <= pct <= p_hi:
            if p_hi == p_lo:
                return v_hi
            frac = (pct - p_lo) / (p_hi - p_lo)
            return v_lo + frac * (v_hi - v_lo)
    # pct is within [0, 100] and the curve spans it, so this is unreachable
    # for well-formed curves; fall back to the nearest endpoint.
    return curve[0][1] if pct > curve[0][0] else curve[-1][1]


def percent_for_voltage(curve: tuple[tuple[float, float], ...], volts: float) -> float:
    """Remaining percentage at a per-cell voltage, piecewise linear."""
    v = float(volts)
    if v >= curve[0][1]:
        return 100.0
    if v <= curve[-1][1]:
        return 0.0
    for (p_hi, v_hi), (p_lo, v_lo) in zip(curve, curve[1:]):
        if v_lo <= v <= v_hi:
            if v_hi == v_lo:
                return p_hi
            frac = (v - v_lo) / (v_hi - v_lo)
            return p_lo + frac * (p_hi - p_lo)
    return 0.0


def estimate_cell_voltage(reported_percent: float, source_chemistry: str) -> float:
    """Estimate per-cell voltage from a percentage reported on the
    source chemistry's scale."""
    return voltage_for_percent(CURVES[source_chemistry], reported_percent)


def correct_percent(
    reported_percent: float,
    source_chemistry: str,
    actual_chemistry: str,
) -> float:
    """Correct a reported percentage to the actual chemistry's scale."""
    volts = estimate_cell_voltage(reported_percent, source_chemistry)
    return _clamp(percent_for_voltage(CURVES[actual_chemistry], volts), 0.0, 100.0)
