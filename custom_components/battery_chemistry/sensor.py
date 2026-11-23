"""Sensor platform for the Battery Chemistry Correction integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_CELL_COUNT,
    CONF_CHEMISTRY,
    CONF_NAME,
    CONF_SOURCE_CALIBRATION,
    CONF_SOURCE_SENSOR,
    DEFAULT_CELL_COUNT,
    DEFAULT_SOURCE_CALIBRATION,
)
from .curves import CHEMISTRY_LABELS, correct_percent, estimate_cell_voltage


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the corrected battery sensor from a config entry."""
    config = {**entry.data, **entry.options}
    async_add_entities([CorrectedBatterySensor(entry, config)])


class CorrectedBatterySensor(SensorEntity):
    """A battery percentage corrected for the installed cell chemistry."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        self._source_sensor: str = config[CONF_SOURCE_SENSOR]
        self._chemistry: str = config[CONF_CHEMISTRY]
        self._source_calibration: str = config.get(
            CONF_SOURCE_CALIBRATION, DEFAULT_SOURCE_CALIBRATION
        )
        self._cell_count: int = int(config.get(CONF_CELL_COUNT, DEFAULT_CELL_COUNT))
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = entry.entry_id
        self._source_percent: float | None = None
        self._cell_voltage: float | None = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to the source sensor and take an initial reading."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._source_sensor], self._async_source_changed
            )
        )
        self._update_from_source()
        self.async_write_ha_state()

    @callback
    def _async_source_changed(self, event: Event) -> None:
        self._update_from_source()
        self.async_write_ha_state()

    @callback
    def _update_from_source(self) -> None:
        state = self.hass.states.get(self._source_sensor)
        if state is None or state.state in ("unknown", "unavailable", ""):
            self._source_percent = None
            self._cell_voltage = None
            return
        try:
            reported = float(state.state)
        except (TypeError, ValueError):
            self._source_percent = None
            self._cell_voltage = None
            return
        self._source_percent = reported
        self._cell_voltage = estimate_cell_voltage(reported, self._source_calibration)

    @property
    def available(self) -> bool:
        return self._source_percent is not None

    @property
    def native_value(self) -> float | None:
        if self._source_percent is None:
            return None
        corrected = correct_percent(
            self._source_percent, self._source_calibration, self._chemistry
        )
        return round(corrected)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "source_sensor": self._source_sensor,
            "source_percent": self._source_percent,
            "chemistry": CHEMISTRY_LABELS.get(self._chemistry, self._chemistry),
            "source_calibration": CHEMISTRY_LABELS.get(
                self._source_calibration, self._source_calibration
            ),
            "cell_count": self._cell_count,
        }
        if self._cell_voltage is not None:
            attrs["estimated_cell_voltage"] = round(self._cell_voltage, 3)
            attrs["estimated_pack_voltage"] = round(
                self._cell_voltage * self._cell_count, 2
            )
        return attrs
