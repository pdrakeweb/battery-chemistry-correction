# Battery Chemistry Correction

Creates a battery percentage sensor corrected for the cells actually installed in a device, for devices whose firmware reports battery percentage on a different chemistry's discharge curve (for example NiMH cells in a device calibrated for alkaline, which reads permanently low).

Install via HACS, restart, then Settings → Devices & Services → Add Integration → **Battery Chemistry Correction**. One entry per device: pick the source battery sensor, the installed chemistry, the source device's calibration chemistry (alkaline by default), and the series cell count.
