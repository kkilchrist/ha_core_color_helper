"""Support for input_color helper."""
from __future__ import annotations

import colorsys
import logging
from typing import Self

import voluptuous as vol

from homeassistant.const import (
    ATTR_EDITABLE,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    SERVICE_RELOAD,
)
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import collection
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "input_color"

CONF_INITIAL = "initial"

ATTR_VALUE = "value"
ATTR_INITIAL = "initial"

SERVICE_SET_COLOR = "set_color"

DEFAULT_COLOR = "#FFFFFF"

HEX_SCHEMA = vol.All(
    cv.string,
    vol.Match(r"^#[0-9A-F]{6}$")  # Ensures hex format, uppercase only, must start with #
)


# Validator for RGB values (ensures all keys exist and values are within the valid range)
RGB_SCHEMA = vol.Schema({
    vol.Required('red'): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    vol.Required('green'): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    vol.Required('blue'): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
})

# Validator for HSV values (ensures valid ranges for hue, saturation, and value)
HSV_SCHEMA = vol.Schema({
    vol.Required('h'): vol.All(vol.Coerce(float), vol.Range(min=0, max=360)),
    vol.Required('s'): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
    vol.Required('v'): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
})

# Individual component validators for red, green, blue, hue, saturation, value
COMPONENT_SCHEMA = vol.Schema({
    vol.Optional('red'): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    vol.Optional('green'): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    vol.Optional('blue'): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    vol.Optional('hue'): vol.All(vol.Coerce(float), vol.Range(min=0, max=360)),
    vol.Optional('saturation'): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
    vol.Optional('value'): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
})

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: cv.schema_with_slug_keys(
            vol.Schema(
                {
                    vol.Optional(CONF_NAME): cv.string,
                    vol.Optional(CONF_INITIAL, default=DEFAULT_COLOR): vol.Any(
                        HEX_SCHEMA,   # HEX format
                        RGB_SCHEMA,     # RGB format
                        HSV_SCHEMA,     # HSV format
                        COMPONENT_SCHEMA # Individual red, green, blue, hue, saturation, value
                    ),
                    vol.Optional(CONF_ICON): cv.icon,
                }
            )
        )
    },
    extra=vol.ALLOW_EXTRA,
)

RELOAD_SERVICE_SCHEMA = vol.Schema({})

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Input Color component."""
    component = EntityComponent[InputColor](_LOGGER, DOMAIN, hass)

    id_manager = collection.IDManager()

    yaml_collection = collection.YamlCollection(
        _LOGGER, id_manager
    )

    # Synchronize entity lifecycle (register collection with Home Assistant)
    collection.sync_entity_lifecycle(
        hass, DOMAIN, DOMAIN, component, yaml_collection, InputColor
    )

    # Load YAML configuration and add entities
    await yaml_collection.async_load(
        [
            {CONF_ID: id_, **(conf or {})}
            for id_, conf in config.get(DOMAIN, {}).items()
        ]
    )

    # Now add the entities to Home Assistant using async_add_entities
    async def async_add_entities(entities):
        """Add entities to Home Assistant."""
        await component.async_add_entities(entities)

    # Add entities from YAML collection to Home Assistant
    entities = []
    for conf in config.get(DOMAIN, {}).values():
        entity = InputColor(conf)
        # Check if the entity already exists in Home Assistant
        if not any(existing_entity.unique_id == entity.unique_id for existing_entity in component.entities):
            entities.append(entity)
        else:
            # Handle duplicate entity case, e.g., log a warning
            _LOGGER.warning("Duplicate entity ID found: %s", entity.unique_id)

    if entities:
        await async_add_entities(entities)  # Register entities with async_add_entities
    # Register the service for setting colors
    component.async_register_entity_service(
        SERVICE_SET_COLOR,
        cv.make_entity_service_schema(  # This ensures proper entity targeting
            {
                vol.Optional("hex_value"): vol.All(
                    cv.string,
                    lambda v: v.upper(),  # Convert to uppercase
                    vol.Match(r"^(#?[0-9A-F]{6})$"),  # Ensures uppercase hex, # optional but only allowed in position 1
                ),
                vol.Optional("rgb_value"): vol.Schema(
                    {
                        vol.Required("red"): vol.All(
                            vol.Coerce(int), vol.Range(min=0, max=255)
                        ),
                        vol.Required("green"): vol.All(
                            vol.Coerce(int), vol.Range(min=0, max=255)
                        ),
                        vol.Required("blue"): vol.All(
                            vol.Coerce(int), vol.Range(min=0, max=255)
                        ),
                    }
                ),
                vol.Optional("hsv_value"): vol.Schema(
                    {
                        vol.Required("h"): vol.All(
                            vol.Coerce(float), vol.Range(min=0.0, max=1.0)
                        ),
                        vol.Required("s"): vol.All(
                            vol.Coerce(float), vol.Range(min=0.0, max=1.0)
                        ),
                        vol.Required("v"): vol.All(
                            vol.Coerce(float), vol.Range(min=0.0, max=1.0)
                        ),
                    }
                ),
            }
        ),
        "async_set_color",
    )

    return True


class InputColor(collection.CollectionEntity, RestoreEntity):
    """Representation of an input_color helper."""

    _attr_should_poll = False
    editable: bool

    def __init__(self, config: ConfigType) -> None:
        """Initialize an input color."""
        self._config = config
        self._state: str | None = config.get(CONF_INITIAL)
        self.editable = False  # Default to False; set to True in from_storage

        self.entity_id = f"{DOMAIN}.{config.get(CONF_ID, 'unknown')}"

    @classmethod
    def from_storage(cls, config: ConfigType) -> Self:
        """Return entity instance initialized from storage."""
        input_color = cls(config)
        input_color.editable = True  # Set to True for entities loaded from storage
        return input_color

    @classmethod
    def from_yaml(cls, config: ConfigType) -> Self:
        """Return entity instance initialized from YAML."""
        input_color = cls(config)
        input_color.editable = False  # YAML-based entities are not editable via UI
        return input_color

    async def async_update_config(self, config: ConfigType) -> None:
        """Handle when the config is updated."""
        self._config = config

        # Optionally, update the current color value if needed.
        if self._state is not None:
            if not self.validate_color(self._state):
                self._state = config.get(CONF_INITIAL, DEFAULT_COLOR)

        self.async_write_ha_state()  # Update state after config changes

    @property
    def name(self):
        """Return the name of the input color."""
        return self._config.get(CONF_NAME)

    @property
    def icon(self):
        """Return the icon of the input color."""
        return self._config.get(CONF_ICON)

    @property
    def state(self):
        """Return the current state."""
        return self.hex_color

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_INITIAL: self._config.get(CONF_INITIAL),
            ATTR_EDITABLE: self.editable,
            'hex_color': self.hex_color,
            'rgb_color': self.rgb_color,
            'hsv_color': self.hsv_color,
            'hex_color_without_hash': self.hex_color.lstrip("#"),
            'red': self.red,
            'green': self.green,
            'blue': self.blue,
            'hue': self.hue,
            'saturation': self.saturation,
            'value': self.value,
        }

    @property
    def unique_id(self) -> str | None:
        """Return the unique ID of the entity."""
        return self._config.get(CONF_ID)

    # RGB methods
    @property
    def rgb_color(self) -> tuple[int, int, int]:
        """Return the RGB color as a tuple from the hex color."""
        if self._state is None:
            return (255, 255, 255)  # Default to white if no state
        hex_color = self._state.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @property
    def hex_color(self) -> str:
        """Return the current hex color in uppercase."""
        if self._state is None:
            return DEFAULT_COLOR
        return self._state

    async def set_rgb_color(self, red: int, green: int, blue: int) -> None:
        """Set the color using RGB values."""
        if not all(0 <= v <= 255 for v in (red, green, blue)):
            _LOGGER.error("RGB values must be between 0 and 255")
            return
        hex_value = f"#{red:02X}{green:02X}{blue:02X}"
        await self.set_hex_color(hex_value)

    async def set_hex_color(self, hex_value: str) -> None:
        """Set the color using a hex value."""
        if not HEX_SCHEMA(hex_value):
            _LOGGER.error("Invalid color format: %s", hex_value)
            return
        self._state = hex_value.upper()
        self.async_write_ha_state()

    # HSV methods
    @property
    def hsv_color(self) -> tuple[float, float, float]:
        """Return the current color as HSV."""
        r, g, b = self.rgb_color
        return colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)

    async def set_hsv_color(self, h: float, s: float, v: float) -> None:
        """Set the color using HSV values."""
        if not (0.0 <= h <= 1.0):
            _LOGGER.error("Hue (h) must be between 0 and 1.")
            return
        if not (0.0 <= s <= 1.0):
            _LOGGER.error("Saturation (s) must be between 0 and 1.")
            return
        if not (0.0 <= v <= 1.0):
            _LOGGER.error("Value (v) must be between 0 and 1.")
            return
        r, g, b = self.hsv_to_rgb(h, s, v)
        await self.set_rgb_color(r, g, b)

    def hsv_to_rgb(self, h: float, s: float, v: float) -> tuple[int, int, int]:
        """Convert HSV to RGB. H, S, V values should be in the range [0, 1]."""
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return int(r * 255), int(g * 255), int(b * 255)

    # RGB component methods
    @property
    def red(self) -> int:
        """Get the red component of the current color."""
        return self.rgb_color[0]

    async def set_red(self, red: int) -> None:
        """Set the red component of the color."""
        green, blue = self.rgb_color[1:]
        await self.set_rgb_color(red, green, blue)

    @property
    def green(self) -> int:
        """Get the green component of the current color."""
        return self.rgb_color[1]

    async def set_green(self, green: int) -> None:
        """Set the green component of the color."""
        red, blue = self.rgb_color[0], self.rgb_color[2]
        await self.set_rgb_color(red, green, blue)

    @property
    def blue(self) -> int:
        """Get the blue component of the current color."""
        return self.rgb_color[2]

    async def set_blue(self, blue: int) -> None:
        """Set the blue component of the color."""
        red, green = self.rgb_color[:2]
        await self.set_rgb_color(red, green, blue)

    # HSV component methods
    @property
    def hue(self) -> float:
        """Get the hue component of the current color."""
        return self.hsv_color[0]

    async def set_hue(self, hue: float) -> None:
        """Set the hue component of the color."""
        saturation, value = self.hsv_color[1:]
        await self.set_hsv_color(hue, saturation, value)

    @property
    def saturation(self) -> float:
        """Get the saturation component of the current color."""
        return self.hsv_color[1]

    async def set_saturation(self, saturation: float) -> None:
        """Set the saturation component of the color."""
        hue, value = self.hsv_color[0], self.hsv_color[2]
        await self.set_hsv_color(hue, saturation, value)

    @property
    def value(self) -> float:
        """Get the value (brightness) component of the current color."""
        return self.hsv_color[2]

    async def set_value(self, value: float) -> None:
        """Set the value (brightness) component of the color."""
        hue, saturation = self.hsv_color[:2]
        await self.set_hsv_color(hue, saturation, value)

    # Lifecycle methods
    async def async_added_to_hass(self):
        """Handle entity being added to Home Assistant."""
        await super().async_added_to_hass()
        if self._state is None:
            last_state = await self.async_get_last_state()
            if last_state and HEX_SCHEMA(last_state.state):
                self._state = last_state.state
            else:
                self._state = self._config.get(CONF_INITIAL, DEFAULT_COLOR)
        self.async_write_ha_state()

    async def async_set_color(
        self,
        hex_value: str | None = None,
        rgb_value: dict[str, int] | None = None,
        hsv_value: dict[str, float] | None = None,
        red: int | None = None,
        green: int | None = None,
        blue: int | None = None,
        hue: float | None = None,
        saturation: float | None = None,
        value: float | None = None
    ) -> None:
        """Set a new color using either HEX, RGB, or HSV format.

        Also can accept single parameters red, green, blue, hue,
        saturation, value.

        Args:
            hex_value (str, optional): The hex color value.
            rgb_value (dict[str, int], optional): The RGB color value as a dictionary.
            hsv_value (dict[str, float], optional): The HSV color value as a dictionary.
            red (int, optional): The red component of the color.
            green (int, optional): The green component of the color.
            blue (int, optional): The blue component of the color.
            hue (float, optional): The hue component of the color.
            saturation (float, optional): The saturation component of the color.
            value (float, optional): The value (brightness) component of the color.

        """
        if hex_value:
            # First ensure upper case, and if no #, add it.
            hex_value = hex_value.upper()
            if not hex_value.startswith("#"):
                hex_value = f"#{hex_value}"
            # Now validate
            if not HEX_SCHEMA(hex_value):
                _LOGGER.error("Invalid color format: %s", hex_value)
                return
            await self.set_hex_color(hex_value)
        elif rgb_value:
            if all(k in rgb_value for k in ('red', 'green', 'blue')):
                await self.set_rgb_color(rgb_value['red'], rgb_value['green'], rgb_value['blue'])
            else:
                _LOGGER.error("RGB value must contain 'red', 'green', and 'blue'.")
        elif hsv_value:
            if all(k in hsv_value for k in ('h', 's', 'v')):
                await self.set_hsv_color(hsv_value['h'], hsv_value['s'], hsv_value['v'])
            else:
                _LOGGER.error("HSV value must contain 'h', 's', and 'v'.")
        elif red is not None:
            await self.set_red(red)
        elif green is not None:
            await self.set_green(green)
        elif blue is not None:
            await self.set_blue(blue)
        elif hue is not None:
            await self.set_hue(hue)
        elif saturation is not None:
            await self.set_saturation(saturation)
        elif value is not None:
            await self.set_value(value)
        else:
            _LOGGER.error("No valid color format provided.")
