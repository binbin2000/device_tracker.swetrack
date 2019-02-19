"""
Support for the SweTrack platform.
Example config using an external ADB server:
device_tracker:
  - platform: swetrack
    username: <email>
    password: <password>
    scan_interval:
      seconds: 30
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.swetrack/
"""
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.components.device_tracker import PLATFORM_SCHEMA
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.util import slugify
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['https://github.com/binbin2000/pyswetrack/archive/master.zip#pyswetrack==0.1']

SCAN_INTERVAL = timedelta(seconds=300)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL):
        vol.All(cv.time_period, cv.positive_timedelta)
})


def setup_scanner(hass, config: dict, see, discovery_info=None):
    """Validate the configuration and return a SweTrack scanner."""
    SweTrackScanner(hass, config, see)
    return True


class SweTrackScanner:
    """A class representing a SweTrack device."""

    def __init__(self, hass, config: dict, see) -> None:
        """Initialize the SweTrack device scanner."""
        from pyswetrack import Api
        self.hass = hass
        self.api = Api(
            config.get(CONF_USERNAME), config.get(CONF_PASSWORD))
        interval = config.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL)
        _LOGGER.info('Polling interval: %s', interval)
        self.see = see
        self._update_info()
        self.update = Throttle(interval)(self._update_info)

    def _update_info(self, now=None) -> None:
        """Update the device info."""
        _LOGGER.debug("Updating devices %s", now)

        # Update self.devices to collect new devices added
        # to the users account.
        self.devices = self.api.getDevices()
        self.devices = self.devices[0]
        _LOGGER.debug('Found devices: %s', self.devices)
        for tracker in self.devices:
            tracker_id = tracker['uniqueid']
            dev_id = slugify(tracker['name'])
            if dev_id is None:
                dev_id = tracker_id
            lat = tracker['latitude']
            lon = tracker['longitude']
            entity_picture = 'http://{}'.format(tracker['PhotoLink'])
            attrs = {
                'last_updated': tracker['lastupdate'],
                'friendly_name': tracker['name'],
                'entity_picture': entity_picture,
                'id': tracker['id'],
                'IMEI': tracker['uniqueid'],
                'contact': tracker['contact'],
                'phone': tracker['phone'],
                'address': tracker['address'],
                'category': tracker['category'],
                'status': tracker['status'],
                'speed': tracker['speed'],
                'speed_limit': tracker['speedLimit'],
                'battery': tracker['Battery']
            }

            self.see(
                dev_id=dev_id, gps=(lat, lon), attributes=attrs
            )
