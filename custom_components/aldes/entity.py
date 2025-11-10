"""AldesEntity class"""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MANUFACTURER


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
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        # Find the product name from the coordinator data, fallback to reference
        product_data = next(
            (p for p in self.coordinator.data if p.get("modem") == self.modem),
            {},
        )
        product_name = product_data.get("name") or self.reference or "Aldes Product"

        return DeviceInfo(
            identifiers={(DOMAIN, self.modem)},
            name=product_name,
            manufacturer=MANUFACTURER,
            model=self.reference,
            sw_version=self.coordinator.version,
        )

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attributes = super().extra_state_attributes or {}
        for product in self.coordinator.data:
            if product.get("modem") == self.modem:
                if "lastUpdatedDate" in product:
                    last_updated_str = product["lastUpdatedDate"]
                    if last_updated_str:
                        try:
                            # Handle "Z" for UTC timezone
                            attributes["last_api_update"] = dt_util.parse_datetime(
                                last_updated_str.replace(" ", "T")
                            )
                        except (ValueError, TypeError):
                            attributes["last_api_update"] = last_updated_str
                break
        return attributes
