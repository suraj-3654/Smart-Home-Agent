import io
import os
import streamlit as st
from streamlit_mic_recorder import mic_recorder
from groq import Groq
from dotenv import load_dotenv

from graph_supervisor import app as agent_app
from tools import home_manager

load_dotenv()

# Initialize Groq client for Whisper Speech-To-Text
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Page Configuration
st.set_page_config(
    page_title="Smart Home Voice & Agentic Orchestrator",
    page_icon="🏠",
    layout="wide"
)

# Header Section with Title & Reset Button
col_header, col_reset = st.columns([3, 1])

with col_header:
    st.title("🏠 Voice-Controlled IoT Agent")
    st.caption("Powered by Groq Whisper, LangGraph Multi-Agents, Pydantic & Safety Guardrails")

with col_reset:
    st.write(" ")  # Spacer for vertical alignment
    if st.button("🧹 Clear Screen & Reset", type="secondary"):
        # 1. Reset Session State Messages & Audio Cache
        st.session_state["messages"] = []
        if "last_audio_bytes" in st.session_state:
            del st.session_state["last_audio_bytes"]
            
        # 2. Reset Device Manager State Back to Default
        home_manager.update_device_state("living_room_light", {"state": "off", "brightness": 0})
        home_manager.update_device_state("thermostat", {"target_temp": 72, "mode": "heat"})
        home_manager.update_device_state("front_door_lock", {"locked": True})
        
        st.toast("Dashboard and device states reset to default!")
        st.rerun()

# Initialize Session States
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Split Layout
col_chat, col_status = st.columns([1.2, 0.8])

# -------------------------------------------------------------------
# RIGHT PANEL: LIVE DEVICE MONITOR
# -------------------------------------------------------------------
with col_status:
    st.subheader("📊 Live Device Status")
    
    current_states = home_manager.get_all_states()
    
    # 1. Light Card
    light = current_states["living_room_light"]
    light_status = "🟢 ON" if light["state"] == "on" else "🔴 OFF"
    with st.container(border=True):
        st.markdown(f"### 💡 {light['name']}")
        st.write(f"**State:** {light_status}")
        st.progress(light["brightness"] / 100, text=f"Brightness: {light['brightness']}%")

    # 2. Thermostat Card
    thermostat = current_states["thermostat"]
    with st.container(border=True):
        st.markdown(f"### 🌡️ {thermostat['name']}")
        st.metric(
            label="Target Temp", 
            value=f"{thermostat['target_temp']}°F", 
            delta=thermostat['mode'].upper()
        )

    # 3. Smart Lock Card
    lock = current_states["front_door_lock"]
    lock_status = "🔒 LOCKED" if lock["locked"] else "🔓 UNLOCKED"
    with st.container(border=True):
        st.markdown(f"### 🔑 {lock['name']}")
        st.markdown(f"**Status:** `{lock_status}`")

# -------------------------------------------------------------------
# LEFT PANEL: CONVERSATIONAL AGENT INTERFACE
# -------------------------------------------------------------------
with col_chat:
    st.subheader("💬 Voice & Text Command Interface")

    # Audio Recording Widget
    st.write("🎙️ **Click below to speak your command:**")
    audio = mic_recorder(
        start_prompt="🔴 Start Recording",
        stop_prompt="⏹️ Stop & Send",
        key='recorder'
    )

    user_input = None

    # Handle Voice Input
    if audio and 'bytes' in audio and len(audio['bytes']) > 0:
        if "last_audio_bytes" not in st.session_state or st.session_state["last_audio_bytes"] != audio['bytes']:
            st.session_state["last_audio_bytes"] = audio['bytes']
            
            with st.spinner("🎙️ Transcribing audio with Groq Whisper..."):
                audio_file = ("command.wav", audio['bytes'], "audio/wav")
                transcription = groq_client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    response_format="text"
                )
                user_input = transcription.strip()
                st.info(f"🗣️ **Voice Recognized:** *\"{user_input}\"*")

    # Text Input Fallback
    text_input = st.chat_input("Or type e.g., Turn off lights and set thermostat to 68.")
    if text_input:
        user_input = text_input

    # Display Chat History
    for idx, msg in enumerate(st.session_state["messages"]):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            if "trace" in msg:
                with st.expander("🔍 Agent Reasoning & Guardrail Trace"):
                    st.json(msg["trace"])

            if msg.get("blocked_action"):
                st.warning(f"⚠️ Guardrail Interception: {msg['blocked_action']['error']}")
                if st.button(f"🔑 Authorize & Override Guardrail", key=f"override_{idx}"):
                    home_manager.update_device_state("front_door_lock", {"locked": False})
                    st.success("Authorization confirmed! Front door unlocked.")
                    st.rerun()

    # Process Input
    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Supervisor decomposing request & executing sub-agents..."):
                initial_state = {
                    "user_input": user_input,
                    "plan": [],
                    "current_task_idx": 0,
                    "tool_calls": [],
                    "execution_results": [],
                    "final_home_state": {}
                }
                
                final_output = agent_app.invoke(initial_state)
                executed_steps = final_output.get("execution_results", [])
                
                blocked_step = None
                for step in executed_steps:
                    if step.get("status") == "blocked_by_guardrail":
                        blocked_step = step
                        break

                if blocked_step:
                    response_text = "⚠️ **Action Requires Human Authorization**"
                else:
                    response_text = f"Executed **{len(executed_steps)} action(s)** across sub-agents."
                
                st.markdown(response_text)

                trace_data = {
                    "supervisor_plan": final_output.get("plan", []),
                    "execution_results": executed_steps
                }
                
                with st.expander("🔍 Agent Reasoning & Guardrail Trace"):
                    st.json(trace_data)

                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": response_text,
                    "trace": trace_data,
                    "blocked_action": blocked_step
                })

        st.rerun()