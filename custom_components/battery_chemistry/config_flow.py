"""Config flow for the Battery Chemistry Correction integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_CELL_COUNT,
    CONF_CHEMISTRY,
    CONF_NAME,
    CONF_SOURCE_CALIBRATION,
    CONF_SOURCE_SENSOR,
    DEFAULT_CELL_COUNT,
    DEFAULT_SOURCE_CALIBRATION,
    DOMAIN,
)
from .curves import CHEMISTRY_LABELS


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    chemistry_options = [
        {"value": key, "label": label} for key, label in CHEMISTRY_LABELS.items()
    ]
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): TextSelector(
                TextSelectorConfig()
            ),
            vol.Required(
                CONF_SOURCE_SENSOR, default=defaults.get(CONF_SOURCE_SENSOR)
            ): EntitySelector(
                EntitySelectorConfig(domain="sensor", device_class="battery")
            ),
            vol.Required(
                CONF_CHEMISTRY, default=defaults.get(CONF_CHEMISTRY, "nimh")
            ): SelectSelector(
                SelectSelectorConfig(
                    options=chemistry_options, mode=SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Required(
                CONF_SOURCE_CALIBRATION,
                default=defaults.get(
                    CONF_SOURCE_CALIBRATION, DEFAULT_SOURCE_CALIBRATION
                ),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=chemistry_options, mode=SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Required(
                CONF_CELL_COUNT,
                default=defaults.get(CONF_CELL_COUNT, DEFAULT_CELL_COUNT),
            ): NumberSelector(
                NumberSelectorConfig(min=1, max=24, step=1, mode=NumberSelectorMode.BOX)
            ),
        }
    )


class BatteryChemistryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Battery Chemistry Correction."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        if user_input is not None:
            user_input = dict(user_input)
            user_input[CONF_CELL_COUNT] = int(user_input[CONF_CELL_COUNT])
            await self.async_set_unique_id(
                f"{user_input[CONF_SOURCE_SENSOR]}|{user_input[CONF_CHEMISTRY]}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME], data=user_input
            )

        return self.async_show_form(step_id="user", data_schema=_schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return BatteryChemistryOptionsFlow(config_entry)


class BatteryChemistryOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Battery Chemistry Correction."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        if user_input is not None:
            user_input = dict(user_input)
            user_input[CONF_CELL_COUNT] = int(user_input[CONF_CELL_COUNT])
            # Options override data in the sensor; name and source stay
            # editable here too so an entry can be retargeted in place.
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(defaults))
