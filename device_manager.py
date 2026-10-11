class SmartHomeDeviceManager:
    """
    Manages the current state of all simulated smart home devices.
    Acts as our in-memory database and state engine.
    """
    def __init__(self):
        # Initialize our home with a predefined set of devices and default states
        self._devices = {
            "living_room_light": {
                "name": "Living Room Main Light",
                "type": "light",
                "state": "off",
                "brightness": 0  # Percentage (0-100)
            },
            "thermostat": {
                "name": "Central Thermostat",
                "type": "thermostat",
                "target_temp": 72,  # Temperature in Fahrenheit
                "mode": "heat"  # Options: heat, cool, off
            },
            "front_door_lock": {
                "name": "Front Door Smart Lock",
                "type": "lock",
                "locked": True  # Boolean: True = Locked, False = Unlocked
            }
        }

    def get_all_states(self) -> dict:
        """Returns the current state of every device in the home."""
        return self._devices

    def get_device_state(self, device_id: str) -> dict:
        """Returns state for a single device, or an error if it doesn't exist."""
        if device_id not in self._devices:
            return {"error": f"Device '{device_id}' not found."}
        return self._devices[device_id]

    def update_device_state(self, device_id: str, updates: dict) -> dict:
        """
        Updates specific attributes of a device.
        Example: update_device_state("living_room_light", {"state": "on", "brightness": 80})
        """
        if device_id not in self._devices:
            return {"error": f"Device '{device_id}' not found."}
        
        # Apply the update to the dictionary
        self._devices[device_id].update(updates)
        return {
            "status": "success",
            "message": f"Updated '{device_id}'",
            "current_state": self._devices[device_id]
        }