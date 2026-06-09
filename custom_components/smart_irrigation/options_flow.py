"""Options flow handler for Smart Irrigation integration."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import selector

from . import const
from .helpers import CannotConnect, InvalidAuth, validate_api_key


class SmartIrrigationOptionsFlowHandler(config_entries.OptionsFlow):
    """Smart Irrigation config flow options handler."""

    # options flow should allow change of use OWM (boolean)
    # options flow should allow update of API key (if set) and version (only if api key set)

    def __init__(self, config_entry) -> None:
        """Initialize HACS options flow."""
        # removing this as it's going be deprated in HA 2025.12
        # self.config_entry = config_entry
        self.options = dict(config_entry.options)
        self._errors = {}
        # Base values from entry.data.
        self._use_weather_service = config_entry.data.get(
            const.CONF_USE_WEATHER_SERVICE
        )
        self._weather_service = config_entry.data.get(const.CONF_WEATHER_SERVICE)
        self._weather_service_api_key = config_entry.data.get(
            const.CONF_WEATHER_SERVICE_API_KEY
        )

        # Legacy use_owm migration: fill in anything entry.data didn't provide.
        # (Previously these values were set here and then unconditionally clobbered
        # by the blocks below with data.get(...)=None, so the migration was a no-op.)
        if "use_owm" in config_entry.data:
            if self._use_weather_service is None:
                self._use_weather_service = config_entry.data.get("use_owm")
            if self._weather_service is None:
                self._weather_service = const.CONF_WEATHER_SERVICE_OWM
            if self._weather_service_api_key is None:
                self._weather_service_api_key = config_entry.data.get("owm_api_key")

        # Options override when present (and differ — preserves the prior guard).
        if const.CONF_USE_WEATHER_SERVICE in self.options and self.options.get(
            const.CONF_USE_WEATHER_SERVICE
        ) != config_entry.data.get(const.CONF_USE_WEATHER_SERVICE):
            self._use_weather_service = self.options.get(const.CONF_USE_WEATHER_SERVICE)
        if const.CONF_WEATHER_SERVICE in self.options:
            self._weather_service = self.options.get(const.CONF_WEATHER_SERVICE)
        if const.CONF_WEATHER_SERVICE_API_KEY in self.options:
            self._weather_service_api_key = self.options.get(
                const.CONF_WEATHER_SERVICE_API_KEY
            )
        if self._weather_service_api_key is not None:
            self._weather_service_api_key = self._weather_service_api_key.strip()
        if const.CONF_WEATHER_SERVICE_API_VERSION in self.options:
            self._owm_api_version = self.options.get(
                const.CONF_WEATHER_SERVICE_API_VERSION
            )
        else:
            self._owm_api_version = config_entry.data.get(
                const.CONF_WEATHER_SERVICE_API_VERSION
            )

    def _with_preserved_coords(self, data: dict) -> dict:
        """Carry over manual-coordinate options into a new options payload.

        Manual coordinates are owned by the panel now (Setup → Weather &
        Location), persisted in the entry options. The options flow only edits
        the weather service, so it must not drop the coordinate keys when it
        rewrites the options.
        """
        for key in (
            const.CONF_MANUAL_COORDINATES_ENABLED,
            const.CONF_MANUAL_LATITUDE,
            const.CONF_MANUAL_LONGITUDE,
            const.CONF_MANUAL_ELEVATION,
        ):
            if key in self.options:
                data[key] = self.options[key]
        return data

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        self._errors = {}
        # set default values based on config
        if user_input is not None:
            # validation
            try:
                # store values entered
                self._use_weather_service = user_input[const.CONF_USE_WEATHER_SERVICE]

                if not self._use_weather_service:
                    # update the entry right away and remove the API info, include days setting
                    user_input[const.CONF_WEATHER_SERVICE_API_KEY] = None
                    # forcing it to be 3.0 because of sunsetting of 2.5 API by OWM in June 2024
                    # user_input[const.CONF_WEATHER_SERVICE_API_VERSION] = "3.0"
                    return self.async_create_entry(
                        title="", data=self._with_preserved_coords(user_input)
                    )
                # show the next step where you can configure / update API key/version
                return await self._show_step_1(user_input)

            except InvalidAuth:
                self._errors["base"] = "auth"
            except CannotConnect:
                self._errors["base"] = "auth"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        const.CONF_USE_WEATHER_SERVICE,
                        default=self._use_weather_service,
                    ): bool,
                }
            ),
            errors=self._errors,
        )

    async def _show_step_1(self, user_input):
        return self.async_show_form(
            step_id="step1",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        const.CONF_WEATHER_SERVICE, default=self._weather_service
                    ): selector({"select": {"options": const.CONF_WEATHER_SERVICES}}),
                    vol.Optional(
                        const.CONF_WEATHER_SERVICE_API_KEY,
                        default=self._weather_service_api_key or "",
                    ): str,
                }
            ),
            errors=self._errors,
        )

    async def async_step_step1(self, user_input=None):
        """Handle a step 1."""

        self._errors = {}
        if user_input is not None:
            try:
                self._weather_service = user_input[const.CONF_WEATHER_SERVICE]
                raw_key = user_input.get(const.CONF_WEATHER_SERVICE_API_KEY) or ""
                self._weather_service_api_key = raw_key.strip()
                user_input[const.CONF_USE_WEATHER_SERVICE] = self._use_weather_service
                user_input[const.CONF_WEATHER_SERVICE_API_KEY] = (
                    self._weather_service_api_key
                )
                await validate_api_key(
                    self.hass, self._weather_service, self._weather_service_api_key
                )
                # Manual coordinates are configured in the panel now; preserve any
                # already-set coordinate options instead of dropping them here.
                final_data = self._with_preserved_coords(
                    {
                        const.CONF_USE_WEATHER_SERVICE: self._use_weather_service,
                        const.CONF_WEATHER_SERVICE: self._weather_service,
                        const.CONF_WEATHER_SERVICE_API_KEY: self._weather_service_api_key,
                    }
                )
                return self.async_create_entry(title="", data=final_data)

            except InvalidAuth:
                self._errors["base"] = "auth"
            except CannotConnect:
                self._errors["base"] = "auth"

            return await self._show_step_1(user_input)
        return await self._show_step_1(user_input)
