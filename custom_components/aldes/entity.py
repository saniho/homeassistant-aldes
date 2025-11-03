"""AldesEntity class"""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

class AldesEntity(CoordinatorEntity):
    """Aldes entity"""

    def __init__(
        self, coordinator, config_entry, product_serial_number, reference, modem
    ):
        super().__init__(coordinator)
        self._attr_config_entry = config_entry
        self.product_serial_number = product_serial_number
        self.reference = reference
        self.modem = modem

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attributes = super().extra_state_attributes or {}
        for product in self.coordinator.data:
            if product.get("modem") == self.modem:
                if "lastUpdatedDate" in product:
                    last_updated_str = product["lastUpdatedDate"].replace("Z", "+00:00")
                    attributes["last_api_update"] = dt_util.parse_datetime(last_updated_str)
                break
        return attributes
