from langchain_core.tools import tool
from device_manager import SmartHomeDeviceManager

# Instantiate a global instance of our home state manager
# All tool calls will modify this single shared instance
home_manager = SmartHomeDeviceManager()


@tool
def get_home_status() -> dict:
    """
    Retrieves the current state of all smart home devices in the house.
    Use this tool whenever the user asks for an overall summary or status of the home.
    """
    return home_manager.get_all_states()


@tool
def control_light(state: str, brightness: int = None) -> dict:
    """
    Controls the living room light.
    
    Args:
        state: Required string, must be either 'on' or 'off'.
        brightness: Optional integer between 0 and 100 representing light brightness level.
    """
    # 1. Validate 'state' parameter
    state = state.lower()
    if state not in ["on", "off"]:
        return {"error": "Invalid state. Must be 'on' or 'off'."}
    
    updates = {"state": state}
    
    # 2. Validate 'brightness' parameter if provided
    if brightness is not None:
        if not (0 <= brightness <= 100):
            return {"error": "Brightness must be an integer between 0 and 100."}
        updates["brightness"] = brightness
    elif state == "off":
        # Automatically reset brightness to 0 if light is turned off
        updates["brightness"] = 0

    # 3. Update the state engine
    return home_manager.update_device_state("living_room_light", updates)


@tool
def set_thermostat(target_temp: int, mode: str = None) -> dict:
    """
    Sets the target temperature and optionally the mode for the central thermostat.
    
    Args:
        target_temp: Integer representing the target temperature in Fahrenheit (e.g., 70).
        mode: Optional string, must be either 'heat', 'cool', or 'off'.
    """
    updates = {"target_temp": target_temp}
    
    if mode is not None:
        mode = mode.lower()
        if mode not in ["heat", "cool", "off"]:
            return {"error": "Invalid mode. Must be 'heat', 'cool', or 'off'."}
        updates["mode"] = mode
        
    return home_manager.update_device_state("thermostat", updates)


@tool
def control_door_lock(lock_action: str, verified: bool = False) -> dict:
    """
    Locks or unlocks the front door.
    
    Args:
        lock_action: Required string, must be either 'lock' or 'unlock'.
        verified: Optional boolean, must be True to authorize unlocking.
    """
    action = lock_action.lower()
    if action == "lock":
        return home_manager.update_device_state("front_door_lock", {"locked": True})
    elif action == "unlock":
        return home_manager.update_device_state("front_door_lock", {
            "locked": False, 
            "verified": verified
        })
    else:
        return {"error": "Invalid action. Must be 'lock' or 'unlock'."}