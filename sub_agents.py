import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools import control_light, set_thermostat, control_door_lock, get_home_status

load_dotenv()

llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)

# -------------------------------------------------------------------
# 1. LIGHTING AGENT SETUP
# -------------------------------------------------------------------
lighting_tools = [control_light, get_home_status]
lighting_llm = llm.bind_tools(lighting_tools)
lighting_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are the specialized Smart Home Lighting Sub-Agent. "
               "Your sole responsibility is controlling lights and inspecting home status. "
               "Be direct and execute tool calls precisely based on user requests."),
    MessagesPlaceholder(variable_name="messages"),
    ])

def run_lighting_agent(user_message: str):
    """Executes the Lighting Agent on a targeted lighting task."""
    formatted_prompt = lighting_prompt.format_messages(messages=[("user", user_message)])
    response = lighting_llm.invoke(formatted_prompt)
    return response

# -------------------------------------------------------------------
# 2. CLIMATE AGENT SETUP
# -------------------------------------------------------------------
climate_tools = [set_thermostat, get_home_status]
climate_llm = llm.bind_tools(climate_tools)
climate_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are the specialized Smart Home Climate Sub-Agent. "
               "Your sole responsibility is controlling the thermostat, temperature, and HVAC modes. "
               "Execute tool calls precisely."),
    MessagesPlaceholder(variable_name="messages"),
])

def run_climate_agent(user_message: str):
    """Executes the Climate Agent on a targeted HVAC task."""
    formatted_prompt = climate_prompt.format_messages(messages=[("user", user_message)])
    response = climate_llm.invoke(formatted_prompt)
    return response

# -------------------------------------------------------------------
# 3. SECURITY AGENT SETUP
# -------------------------------------------------------------------
security_tools = [control_door_lock, get_home_status]
security_llm = llm.bind_tools(security_tools)

security_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are the specialized Smart Home Security Sub-Agent. "
               "Your sole responsibility is managing smart locks and door security states. "
               "SECURITY POLICY: When unlocking a door, you MUST set verified=True in the tool parameters "
               "if the user explicitly requested to open or unlock the door."),
    MessagesPlaceholder(variable_name="messages"),
])
def run_security_agent(user_message: str):
    """Executes the Security Agent on a targeted security task."""
    formatted_prompt = security_prompt.format_messages(messages=[("user", user_message)])
    response = security_llm.invoke(formatted_prompt)
    return response