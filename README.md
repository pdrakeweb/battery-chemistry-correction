# Battery Chemistry Correction

Home Assistant custom integration. Creates a battery percentage sensor corrected for the cells actually installed in a device, for devices whose firmware reports battery percentage on a different chemistry's discharge curve.

A device that was designed for alkaline cells reports its battery percentage from pack voltage using an alkaline discharge curve. NiMH cells run at a lower voltage (1.2 V nominal per cell against 1.5 V), so a healthy NiMH pack in an alkaline device reads permanently low. Example: an Airthings View Plus on freshly charged low-self-discharge NiMH cells reports 16-18%, where the pack is in fact most of the way charged.

## How the correction works

Per cell:

1. The reported percentage is inverted through the source chemistry's discharge curve to estimate the per-cell voltage the device measured.
2. That voltage is read against the installed chemistry's discharge curve to get the corrected remaining percentage.

Curves are piecewise-linear tables of per-cell voltage against remaining percentage, in `custom_components/battery_chemistry/curves.py`. The corrected value is an estimate derived from a reported percentage, not a measurement. It is only as good as the two curves and the device's own gauge.

Curve basis:

- **Alkaline** — a typical low-drain device gauge calibration. Device gauges are pessimistic in the lower half of the scale (the device must still run at a displayed 0%, under load pulses and at low temperature), so the table's lower half sits higher in voltage than a laboratory constant-current discharge curve. This is the table that reproduces the observed behaviour of real gauges: a fresh NiMH pack at ~1.28 V/cell reads ~20%.
- **NiMH / LSD NiMH** — the standard NiMH discharge shape: a short fall from ~1.4 V to a flat 1.25-1.2 V plateau that holds most of the capacity, then a knee below ~10%. Low-self-discharge cells share this shape; they differ in storage loss, not discharge curve.
- **Lithium 1.5 V regulated** — approximation. These cells hold a regulated ~1.5 V output until nearly empty, then fall quickly, so most of the scale maps to a narrow voltage band and the correction is coarse.
- **Li-ion (3.7 V)** — standard single-cell Li-ion discharge shape, 4.2 V full to ~3.0 V empty.
- **Lead-acid 12 V** — resting-voltage approximation, per 2 V cell (a 12 V battery is six in series). Resting voltage is load-dependent; treat values as approximate.

Cell count (series cells) does not change the percentage math, which is per-cell. It is used for the estimated pack voltage attribute.

## Install (HACS)

1. HACS → Integrations → ⋮ → Custom repositories → add `https://github.com/pdrakeweb/battery-chemistry-correction`, category Integration.
2. Install **Battery Chemistry Correction**, restart Home Assistant.
3. Settings → Devices & Services → Add Integration → **Battery Chemistry Correction**.

## Configuration

Each config entry creates one corrected sensor.

| Field | Meaning |
|---|---|
| Name | Name for the corrected sensor. |
| Source battery sensor | The device's own battery percentage sensor. |
| Installed chemistry | The cells actually in the device: Alkaline, NiMH / LSD NiMH, Lithium 1.5 V regulated, Li-ion (3.7 V), Lead-acid 12 V. |
| Source device calibration | The chemistry the source device's gauge assumes. Alkaline unless the device was designed for something else. |
| Cells in series | Cell count of the pack; used for the pack voltage attribute. |

Chemistry, calibration, source sensor, and cell count can be changed afterwards under the entry's Configure (options) dialog.

## Sensor

State: corrected percentage (device class `battery`, unit `%`), updated whenever the source sensor changes, unavailable when the source is unavailable.

Attributes: `source_sensor`, `source_percent`, `chemistry`, `source_calibration`, `cell_count`, `estimated_cell_voltage`, `estimated_pack_voltage`.

## Tests

The curve math is pure Python (`curves.py`, no Home Assistant imports):

```
python3 -m unittest discover tests
```

Tests cover same-chemistry identity, a fresh NiMH pack (16-25% on the alkaline scale) correcting to a high value, a near-empty NiMH pack correcting near 0, monotonicity of every correction, and voltage round-trips for every curve.

## Requirements

Home Assistant 2024.1.0 or newer.
