import os
from typing import List, TypedDict, Annotated
import operator
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END, START

# Import our sub-agents and tools
from sub_agents import run_lighting_agent, run_climate_agent, run_security_agent
from tools import control_light, set_thermostat, control_door_lock, get_home_status, home_manager
from guardrails import validate_tool_call_safety, SafetyViolationError

# Import structured schemas from supervisor
from supervisor import RoutingPlan, TOOL_MAP, SYSTEM_PROMPT

load_dotenv()

# -------------------------------------------------------------------
# 1. DEFINE LANGGRAPH STATE
# -------------------------------------------------------------------
class AgentState(TypedDict):
    """
    The shared memory object that passes through every node in the graph.
    """
    user_input: str
    plan: List[dict]  # Sub-tasks assigned by Supervisor
    current_task_idx: int
    tool_calls: list
    execution_results: Annotated[list, operator.add]  # Appends outputs automatically
    final_home_state: dict


# Initialize LLM
llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
supervisor_router = llm.with_structured_output(RoutingPlan)


# -------------------------------------------------------------------
# 2. DEFINE GRAPH NODES
# -------------------------------------------------------------------

def supervisor_node(state: AgentState) -> dict:
    """Node A: Analyzes prompt and generates structured task list."""
    print("\n--- [NODE: Supervisor Router] ---")
    prompt = f"{SYSTEM_PROMPT}\n\nUser Input: {state['user_input']}"
    plan_obj: RoutingPlan = supervisor_router.invoke(prompt)
    
    tasks_as_dicts = [{"agent": t.agent, "task": t.task} for t in plan_obj.tasks]
    
    print(f"Plan Generated: {len(tasks_as_dicts)} task(s).")
    return {
        "plan": tasks_as_dicts,
        "current_task_idx": 0,
        "tool_calls": []
    }


def worker_node(state: AgentState) -> dict:
    """Node B: Executes the current sub-task using the assigned sub-agent."""
    idx = state["current_task_idx"]
    task_info = state["plan"][idx]
    agent_name = task_info["agent"]
    sub_task = task_info["task"]

    print(f"\n--- [NODE: {agent_name.upper()} Agent Worker] ---")
    print(f"Executing Sub-task ({idx + 1}/{len(state['plan'])}): '{sub_task}'")

    if agent_name == "lighting":
        response = run_lighting_agent(sub_task)
    elif agent_name == "climate":
        response = run_climate_agent(sub_task)
    elif agent_name == "security":
        response = run_security_agent(sub_task)
    else:
        response = None

    tool_calls = response.tool_calls if response else []
    return {
        "tool_calls": tool_calls
    }


def tool_execution_node(state: AgentState) -> dict:
    """Node C: Validates safety policies FIRST, then executes tools if safe."""
    print("\n--- [NODE: Tool Executor with Guardrails] ---")
    tool_calls = state.get("tool_calls", [])
    results = []

    for call in tool_calls:
        tool_name = call["name"]
        tool_args = call["args"]
        
        # Step 1: Run Guardrail Inspection
        try:
            safety_check = validate_tool_call_safety(tool_name, tool_args)
            print(f"   [Guardrail PASS] {safety_check['reason']}")
            
            # Step 2: Execute tool if safe
            if tool_name in TOOL_MAP:
                tool_func = TOOL_MAP[tool_name]
                out = tool_func.invoke(tool_args)
                results.append({"tool": tool_name, "status": "executed", "result": out})
                
        except SafetyViolationError as e:
            # Catch security block and return error back to the graph state safely
            print(f"   [CRITICAL] {str(e)}")
            results.append({
                "tool": tool_name, 
                "status": "blocked_by_guardrail", 
                "error": str(e)
            })

    # Increment task index
    next_idx = state["current_task_idx"] + 1

    return {
        "execution_results": results,
        "current_task_idx": next_idx,
        "final_home_state": home_manager.get_all_states()
    }


# -------------------------------------------------------------------
# 3. CONDITIONAL ROUTING LOGIC
# -------------------------------------------------------------------

def should_continue(state: AgentState) -> str:
    """
    Conditional Edge: Checks if there are more tasks left in the plan.
    If yes -> loops back to worker_node.
    If no -> routes to END.
    """
    if state["current_task_idx"] < len(state["plan"]):
        return "worker"
    return "end"


# -------------------------------------------------------------------
# 4. BUILD THE GRAPH
# -------------------------------------------------------------------

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("worker", worker_node)
workflow.add_node("tools", tool_execution_node)

# Set Graph Edges
workflow.add_edge(START, "supervisor")
workflow.add_edge("supervisor", "worker")
workflow.add_edge("worker", "tools")

# Conditional Edge from tools -> either back to worker OR to END
workflow.add_conditional_edges(
    "tools",
    should_continue,
    {
        "worker": "worker",
        "end": END
    }
)

# Compile the Graph executable
app = workflow.compile()