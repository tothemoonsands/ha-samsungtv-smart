"""Samsung Frame TV Art Mode switch entity."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.art import SamsungTVAsyncArt
from .const import (
    CONF_WS_NAME,
    DATA_ART_API,
    DATA_CFG,
    DEFAULT_PORT,
    DOMAIN,
    WS_PREFIX,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Samsung Frame Art Mode switch from config entry."""
    config = hass.data[DOMAIN][entry.entry_id][DATA_CFG]
    host = config[CONF_HOST]
    port = config.get(CONF_PORT, DEFAULT_PORT)
    token = config.get(CONF_TOKEN)
    ws_name = config.get(CONF_WS_NAME, "HomeAssistant")
    
    # Get device name from config or entry title, fallback to host
    device_name = config.get(CONF_NAME) or entry.title or host
    
    # Check if art_api already exists (created by sensor platform)
    art_api = hass.data[DOMAIN][entry.entry_id].get(DATA_ART_API)
    
    if art_api is None:
        # Create the Art API instance if not already created
        session = async_get_clientsession(hass)
        art_api = SamsungTVAsyncArt(
            host=host,
            port=port,
            token=token,
            session=session,
            timeout=5,
            name=f"{WS_PREFIX} {ws_name} Art",
        )
        
        # Quick check if Frame TV is supported
        try:
            async with asyncio.timeout(5):
                is_supported = await art_api.supported()
        except asyncio.TimeoutError:
            _LOGGER.debug("Timeout checking Frame TV support for %s", host)
            is_supported = False
        except Exception as ex:
            _LOGGER.debug("Frame TV support check failed: %s", ex)
            is_supported = False
        
        if not is_supported:
            _LOGGER.info("Frame TV art mode not supported on %s - switch not created", host)
            return
        
        # Store for later use
        hass.data[DOMAIN][entry.entry_id][DATA_ART_API] = art_api
    else:
        # Art API exists, so Frame TV is supported
        is_supported = True
    
    if not is_supported:
        return
    
    # Create the switch entity
    async_add_entities([
        FrameArtModeSwitch(entry, art_api, device_name, host),
    ])
    
    _LOGGER.info("Frame Art Mode switch created for %s", device_name)


class FrameArtModeSwitch(SwitchEntity):
    """Switch to control Samsung Frame TV Art Mode."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_has_entity_name = True
    _attr_name = "Art Mode"
    _attr_icon = "mdi:palette"

    def __init__(
        self,
        entry: ConfigEntry,
        art_api: SamsungTVAsyncArt,
        device_name: str,
        host: str,
    ) -> None:
        """Initialize the Art Mode switch."""
        self._entry = entry
        self._art_api = art_api
        self._device_name = device_name
        self._host = host
        self._attr_unique_id = f"{entry.entry_id}_art_mode_switch"
        self._attr_is_on = None
        self._available = True
        self._updating = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info to link this entity to the TV device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._device_name,
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def is_on(self) -> bool | None:
        """Return True if Art Mode is on."""
        return self._attr_is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn Art Mode on."""
        _LOGGER.debug("Turning Art Mode ON for %s", self._device_name)
        try:
            async with asyncio.timeout(10):
                result = await self._art_api.set_artmode(True)
                if result:
                    self._attr_is_on = True
                    self._available = True
                    _LOGGER.info("Art Mode turned ON for %s", self._device_name)
                else:
                    _LOGGER.warning("Failed to turn Art Mode ON for %s", self._device_name)
        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout turning Art Mode ON for %s", self._device_name)
            self._available = False
        except Exception as ex:
            _LOGGER.error("Error turning Art Mode ON: %s", ex)
            self._available = False
        
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn Art Mode off."""
        _LOGGER.debug("Turning Art Mode OFF for %s", self._device_name)
        try:
            async with asyncio.timeout(10):
                result = await self._art_api.set_artmode(False)
                if result:
                    self._attr_is_on = False
                    self._available = True
                    _LOGGER.info("Art Mode turned OFF for %s", self._device_name)
                else:
                    _LOGGER.warning("Failed to turn Art Mode OFF for %s", self._device_name)
        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout turning Art Mode OFF for %s", self._device_name)
            self._available = False
        except Exception as ex:
            _LOGGER.error("Error turning Art Mode OFF: %s", ex)
            self._available = False
        
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the Art Mode state."""
        if self._updating:
            return
        
        self._updating = True
        try:
            async with asyncio.timeout(8):
                art_mode = await self._art_api.get_artmode()
                if art_mode is not None:
                    self._attr_is_on = art_mode == "on"
                    self._available = True
                    _LOGGER.debug("Art Mode state updated: %s", self._attr_is_on)
                else:
                    _LOGGER.debug("Could not get Art Mode state")
        except asyncio.TimeoutError:
            _LOGGER.debug("Timeout updating Art Mode state")
            # Don't mark as unavailable on timeout - TV might be off
        except Exception as ex:
            _LOGGER.debug("Error updating Art Mode state: %s", ex)
        finally:
            self._updating = False

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to Home Assistant."""
        # Schedule initial state update
        self.hass.async_create_background_task(
            self.async_update(),
            f"frame_art_switch_initial_update_{self._entry.entry_id}",
        )
