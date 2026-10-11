class SafetyViolationError(Exception):
    """Custom exception raised when a tool call violates security guardrails."""
    pass


def validate_tool_call_safety(tool_name: str, tool_args: dict) -> dict:
    """
    Intercepts proposed tool calls before execution.
    Inspects parameters against safety boundaries.
    
    Returns:
        dict: {"safe": True, "reason": "Passed validation"}
        or raises SafetyViolationError if dangerous.
    """
    
    # 1. Guardrail: Thermostat Temperature Bounds
    if tool_name == "set_thermostat":
        temp = tool_args.get("target_temp")
        if temp is not None:
            if temp < 60 or temp > 80:
                raise SafetyViolationError(
                    f"GUARDRAIL BLOCKED: Target temperature {temp}°F is out of safe physical bounds (60°F - 80°F)."
                )

    # 2. Guardrail: Door Unlock Security Policy
    elif tool_name == "control_door_lock":
        action = tool_args.get("lock_action", "").lower()
        if action == "unlock":
            # Simulate requiring security verification
            has_verification = tool_args.get("verified", False)
            if not has_verification:
                raise SafetyViolationError(
                    "GUARDRAIL BLOCKED: Unlocking the front door requires explicit user confirmation/verification."
                )

    # 3. Guardrail: Light Brightness Bounds
    elif tool_name == "control_light":
        brightness = tool_args.get("brightness")
        if brightness is not None:
            if brightness < 0 or brightness > 100:
                raise SafetyViolationError(
                    f"GUARDRAIL BLOCKED: Brightness {brightness}% is invalid. Must be 0-100."
                )

    return {"safe": True, "reason": "All safety policies passed."}