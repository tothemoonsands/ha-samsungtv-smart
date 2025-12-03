"""Samsung Frame TV Art Mode switch entity."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PORT,
    CONF_TOKEN,
    STATE_ON,
    STATE_OFF,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er

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

# Time to wait for TV to be ready after WOL
TV_STARTUP_DELAY = 8  # seconds


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
        FrameArtModeSwitch(hass, entry, art_api, device_name, host),
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
        hass: HomeAssistant,
        entry: ConfigEntry,
        art_api: SamsungTVAsyncArt,
        device_name: str,
        host: str,
    ) -> None:
        """Initialize the Art Mode switch."""
        self._hass = hass
        self._entry = entry
        self._art_api = art_api
        self._device_name = device_name
        self._host = host
        self._attr_unique_id = f"{entry.entry_id}_art_mode_switch"
        self._attr_is_on = None
        self._available = True
        self._updating = False
        self._media_player_entity_id: str | None = None

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

    def _get_media_player_entity_id(self) -> str | None:
        """Get the media_player entity_id for this TV."""
        if self._media_player_entity_id:
            return self._media_player_entity_id
        
        # Find media_player entity for this config entry using the correct API
        entity_registry = er.async_get(self._hass)
        for entity in entity_registry.entities.values():
            if (
                entity.config_entry_id == self._entry.entry_id
                and entity.domain == "media_player"
            ):
                self._media_player_entity_id = entity.entity_id
                return entity.entity_id
        
        return None

    async def _is_tv_on(self) -> bool:
        """Check if TV is currently on."""
        entity_id = self._get_media_player_entity_id()
        if not entity_id:
            return False
        
        state = self._hass.states.get(entity_id)
        if state is None:
            return False
        
        # TV is "on" if state is not off/unavailable
        return state.state not in (STATE_OFF, "unavailable", "unknown")

    async def _turn_on_tv(self) -> bool:
        """Turn on the TV using media_player service."""
        entity_id = self._get_media_player_entity_id()
        if not entity_id:
            _LOGGER.warning("Could not find media_player entity for %s", self._device_name)
            return False
        
        _LOGGER.info("Turning on TV %s before activating Art Mode", entity_id)
        
        try:
            await self._hass.services.async_call(
                "media_player",
                "turn_on",
                {"entity_id": entity_id},
                blocking=True,
            )
            return True
        except Exception as ex:
            _LOGGER.error("Failed to turn on TV: %s", ex)
            return False

    async def _wait_for_tv_ready(self, max_wait: int = 15) -> bool:
        """Wait for TV to be ready after turning on."""
        _LOGGER.debug("Waiting for TV to be ready (max %ds)...", max_wait)
        
        for i in range(max_wait):
            await asyncio.sleep(1)
            
            # Try to connect to Art API
            try:
                async with asyncio.timeout(3):
                    is_supported = await self._art_api.supported()
                    if is_supported:
                        _LOGGER.debug("TV ready after %d seconds", i + 1)
                        return True
            except Exception:
                pass
            
            _LOGGER.debug("TV not ready yet, waiting... (%d/%d)", i + 1, max_wait)
        
        _LOGGER.warning("TV did not become ready within %d seconds", max_wait)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn Art Mode on."""
        _LOGGER.debug("Turning Art Mode ON for %s", self._device_name)
        
        # Check if TV is on
        tv_is_on = await self._is_tv_on()
        
        if not tv_is_on:
            _LOGGER.info("TV is off, turning it on first...")
            
            # Turn on TV
            if not await self._turn_on_tv():
                _LOGGER.error("Failed to turn on TV, cannot activate Art Mode")
                return
            
            # Wait for TV to be ready
            if not await self._wait_for_tv_ready(max_wait=20):
                _LOGGER.warning("TV may not be fully ready, attempting Art Mode anyway...")
            
            # Additional delay for TV to stabilize
            await asyncio.sleep(2)
        
        # Now activate Art Mode
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
        """Turn Art Mode off (switch to normal TV mode)."""
        _LOGGER.debug("Turning Art Mode OFF for %s", self._device_name)
        
        # Check if TV is on
        tv_is_on = await self._is_tv_on()
        
        if not tv_is_on:
            _LOGGER.debug("TV is already off, Art Mode is already off")
            self._attr_is_on = False
            self.async_write_ha_state()
            return
        
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
