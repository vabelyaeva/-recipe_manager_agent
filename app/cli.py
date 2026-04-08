import logging
import os
from getpass import getpass
from pathlib import Path

from dotenv import dotenv_values
from langchain.messages import HumanMessage

from app.logging_config import setup_logging

logger = logging.getLogger(__name__)

THREAD_ID = "recipe-cli-thread-1"
ENV_PATH = Path(".env")


def ensure_api_key():
    """
    If .env contains OPENAI_API_KEY=ENTER_YOUR_KEY or an empty value,
    always ask the user to enter an API key in the console.

    The entered key is used only for the current session and is not saved.
    Any previously existing OPENAI_API_KEY in the process environment is ignored.
    """
    env_values = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}

    file_key = (env_values.get("OPENAI_API_KEY") or "").strip()
    placeholder = "ENTER_YOUR_KEY"

    if file_key in {"", placeholder}:
        os.environ.pop("OPENAI_API_KEY", None)

        print("Please paste your OpenAI API key for this session.")

        while True:
            key = getpass("OPENAI_API_KEY: ").strip()

            if not key:
                print("API key cannot be empty.")
                continue

            if key == placeholder:
                print("Please enter a real API key.")
                continue

            os.environ["OPENAI_API_KEY"] = key
            logger.info("OPENAI_API_KEY entered by user for current session only")
            return

    os.environ["OPENAI_API_KEY"] = file_key
    logger.info("Using OPENAI_API_KEY from .env")


def print_welcome():
    print("Recipe Manager Agent")
    print("Type 'exit' to quit.\n")
    print("You can start with commands like:")
    print('- Create a collection "Italian Cuisine"')
    print('- Add recipe "Carbonara", 2 servings, 30 minutes')
    print('- Add steps: boil pasta, fry guanciale, mix eggs with pecorino')
    print('- Add ingredients: spaghetti 400 g, guanciale 200 g, eggs 4 pcs')
    print('- Show the full recipe')
    print('- List collections')
    print('- Show collection contents "Italian Cuisine"')
    print()


def run_cli():
    setup_logging()
    logger.info("Starting Recipe Manager CLI")

    ensure_api_key()

    from app.graph import graph

    print_welcome()

    config = {"configurable": {"thread_id": THREAD_ID}}

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            logger.info("CLI stopped by user")
            print("Bye!")
            break

        logger.info("User input: %s", user_input)

        printed_text = False
        last_values = None

        print("Agent: ", end="", flush=True)

        for chunk in graph.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
            stream_mode=["messages", "values"],
            version="v2",
        ):
            if chunk["type"] == "messages":
                message_chunk, metadata = chunk["data"]

                if metadata.get("langgraph_node") != "agent":
                    continue

                text = getattr(message_chunk, "text", None)
                if text:
                    print(text, end="", flush=True)
                    printed_text = True
                else:
                    content = getattr(message_chunk, "content", None)
                    if isinstance(content, str) and content:
                        print(content, end="", flush=True)
                        printed_text = True

            elif chunk["type"] == "values":
                last_values = chunk["data"]

        if not printed_text and last_values:
            final_message = last_values["messages"][-1]
            final_text = getattr(final_message, "text", None) or getattr(final_message, "content", "")
            if isinstance(final_text, str) and final_text:
                print(final_text, end="", flush=True)

        print("\n")


if __name__ == "__main__":
    run_cli()