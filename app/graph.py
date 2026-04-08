import logging
import os

from dotenv import load_dotenv
from langchain.messages import SystemMessage
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from openai import AuthenticationError

from app.agent_tools import RECIPE_TOOLS
from app.state import AgentState

logger = logging.getLogger(__name__)

# IMPORTANT:
# override=True forces the value from .env to replace any old key
# inherited from PowerShell / system environment.
load_dotenv(override=True)

SYSTEM_PROMPT = """
You are a recipe manager assistant.

Rules:
- Use tools for cookbook operations.
- Use the active collection and active recipe from state whenever possible.
- If the user mentions an existing collection by name, you may use select_collection_tool.
- If the user asks to show the contents of a specific collection, use show_collection_contents_tool directly.
- If the user says "show the first one" or similar, use the last listed recipes.
- Keep responses very short and practical.
- After a successful tool call, respond in 1 short sentence.
- Do not ask follow-up questions like "Would you like...?" unless information is missing.
- When tool output already contains the answer, keep your reply close to it.
- Do not invent collections, recipes, steps, or ingredients.
- If the user asks to delete the current recipe, use delete_active_recipe_tool.
- If the user says "delete the first one" or similar, use delete_recipe_by_number_tool.
- Prefer a single state-changing tool call per turn.
"""


def build_context_text(state: AgentState) -> str:
    active_collection = state.get("active_collection_name") or "None"
    active_recipe = state.get("active_recipe_name") or "None"

    return (
        f"Current active collection: {active_collection}\n"
        f"Current active recipe: {active_recipe}\n"
    )

def build_model():
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()

    return ChatOpenAI(
        model="gpt-5-nano",
        api_key=api_key,
        model_kwargs={"parallel_tool_calls": False},
    ).bind_tools(RECIPE_TOOLS)


model_with_tools = build_model()


def call_model(state: AgentState):
    logger.info(
        "Calling model | active_collection=%s | active_recipe=%s | messages=%s",
        state.get("active_collection_name"),
        state.get("active_recipe_name"),
        len(state.get("messages", [])),
    )

    system_text = SYSTEM_PROMPT + "\n\n" + build_context_text(state)

    try:
        response = model_with_tools.invoke(
            [SystemMessage(content=system_text)] + state["messages"]
        )

        logger.info(
            "Model responded | has_tool_calls=%s",
            bool(getattr(response, "tool_calls", None))
        )
        return {"messages": [response]}

    except AuthenticationError:
        logger.exception("OpenAI authentication failed")
        return {
            "messages": [
                AIMessage(content="Check OpenAI key in .env. Insert it there.")
            ]
        }

    except Exception as e:
        logger.exception("Unexpected model error")
        return {
            "messages": [
                AIMessage(content=f"Unexpected error: {type(e).__name__}. Check OpenAI key in .env.")
            ]
        }


def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    has_tools = bool(getattr(last_message, "tool_calls", None))
    logger.info("Routing decision | has_tool_calls=%s", has_tools)
    if has_tools:
        return "tools"
    return END


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(RECIPE_TOOLS, handle_tool_errors=True))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, ["tools", END])
    builder.add_edge("tools", "agent")

    checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)


graph = build_graph()