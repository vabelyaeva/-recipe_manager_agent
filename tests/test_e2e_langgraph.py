from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.db import get_connection
from app.graph import graph
from helpers.reset_db import clear_all_data


def print_header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_pass(message: str):
    print(f"PASS: {message}")


def print_fail(message: str):
    print(f"FAIL: {message}")


def check(condition: bool, success_msg: str, fail_msg: str):
    if condition:
        print_pass(success_msg)
        return 1
    else:
        print_fail(fail_msg)
        return 0


def message_to_text(message) -> str:
    content = getattr(message, "content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(text)
            else:
                parts.append(str(item))
        return "\n".join(parts)

    return str(content)


def get_last_ai_text(messages) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return message_to_text(msg)
    return ""


def get_last_tool_text(messages) -> str:
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            return message_to_text(msg)
    return ""


def run_turn(user_text: str, config: dict):
    print(f"\nUSER: {user_text}")
    result = graph.invoke(
        {"messages": [HumanMessage(content=user_text)]},
        config=config,
    )

    ai_text = get_last_ai_text(result["messages"])
    tool_text = get_last_tool_text(result["messages"])

    print("\nLAST TOOL OUTPUT:")
    print(tool_text if tool_text else "[no tool output found]")

    print("\nLAST AI OUTPUT:")
    print(ai_text if ai_text else "[no ai output found]")

    print("\nSTATE SNAPSHOT:")
    print({
        "active_collection_id": result.get("active_collection_id"),
        "active_collection_name": result.get("active_collection_name"),
        "active_recipe_id": result.get("active_recipe_id"),
        "active_recipe_name": result.get("active_recipe_name"),
        "last_listed_recipe_ids": result.get("last_listed_recipe_ids"),
    })

    return result, ai_text, tool_text


def get_db_snapshot():
    conn = get_connection()
    cursor = conn.cursor()

    counts = {}
    for table in ["collections", "recipes", "steps", "ingredients"]:
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
        counts[table] = cursor.fetchone()["cnt"]

    cursor.execute("SELECT name, description FROM collections ORDER BY id")
    collections = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT id, collection_id, name, description, servings, prep_time
        FROM recipes
        ORDER BY id
    """)
    recipes = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT recipe_id, order_num, description
        FROM steps
        ORDER BY recipe_id, order_num
    """)
    steps = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT recipe_id, name, amount, unit
        FROM ingredients
        ORDER BY recipe_id, id
    """)
    ingredients = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "counts": counts,
        "collections": collections,
        "recipes": recipes,
        "steps": steps,
        "ingredients": ingredients,
    }


def main():
    print_header("RESET DATABASE")
    clear_all_data()

    thread_id = f"e2e-test-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    total_checks = 0
    passed_checks = 0

    print_header("END-TO-END LANGGRAPH TEST")
    print(f"Using thread_id: {thread_id}")

    # ------------------------------------------------------------------
    # TURN 1: Create collection
    # ------------------------------------------------------------------
    result, ai_text, tool_text = run_turn(
        'Create a collection called "Italian Cuisine" with description "Classic Italian recipes".',
        config,
    )

    total_checks += 1
    passed_checks += check(
        result.get("active_collection_name") == "Italian Cuisine"
        and result.get("active_collection_id") is not None,
        "Collection created and active collection remembered",
        "Agent did not remember active collection correctly",
    )

    # ------------------------------------------------------------------
    # TURN 2: Add recipe without repeating collection
    # ------------------------------------------------------------------
    result, ai_text, tool_text = run_turn(
        'Add recipe "Carbonara", 2 servings, 30 minutes. Description: Pasta with eggs, cheese, and guanciale.',
        config,
    )

    total_checks += 1
    passed_checks += check(
        result.get("active_recipe_name") == "Carbonara"
        and result.get("active_recipe_id") is not None,
        "Recipe created and active recipe remembered",
        "Agent did not remember active recipe correctly",
    )

    # ------------------------------------------------------------------
    # TURN 3: Add steps without recipe name
    # ------------------------------------------------------------------
    result, ai_text, tool_text = run_turn(
        "Add steps: 1) Boil the pasta 2) Fry the guanciale 3) Mix eggs with pecorino 4) Combine everything together",
        config,
    )

    snapshot = get_db_snapshot()
    total_checks += 1
    passed_checks += check(
        snapshot["counts"]["steps"] == 4,
        "Agent added 4 steps using context only",
        f"Expected 4 steps after natural-language add-steps turn, got {snapshot['counts']['steps']}",
    )

    # ------------------------------------------------------------------
    # TURN 4: Add ingredients without recipe name
    # ------------------------------------------------------------------
    result, ai_text, tool_text = run_turn(
        "Add ingredients: spaghetti 400 g, guanciale 200 g, eggs 4 pcs, pecorino 100 g",
        config,
    )

    snapshot = get_db_snapshot()
    total_checks += 1
    passed_checks += check(
        snapshot["counts"]["ingredients"] == 4,
        "Agent added 4 ingredients using context only",
        f"Expected 4 ingredients after natural-language add-ingredients turn, got {snapshot['counts']['ingredients']}",
    )

    # ------------------------------------------------------------------
    # TURN 5: Show full recipe
    # ------------------------------------------------------------------
    result, ai_text, tool_text = run_turn(
        "Show the full recipe",
        config,
    )

    combined_text = (tool_text + "\n" + ai_text).lower()
    total_checks += 1
    passed_checks += check(
        "carbonara" in combined_text
        and "ingredients" in combined_text
        and "steps" in combined_text,
        "Agent returned full recipe in response to natural-language request",
        "Agent did not return a recognizable full recipe response",
    )

    # ------------------------------------------------------------------
    # TURN 6: List recipes in the collection
    # ------------------------------------------------------------------
    result, ai_text, tool_text = run_turn(
        "What recipes are in the collection?",
        config,
    )

    total_checks += 1
    passed_checks += check(
        result.get("last_listed_recipe_ids") is not None
        and len(result.get("last_listed_recipe_ids")) == 1,
        "Agent stored last listed recipe ids after listing recipes",
        "Agent did not save last listed recipe ids correctly",
    )

    # ------------------------------------------------------------------
    # TURN 7: Show the first one
    # ------------------------------------------------------------------
    result, ai_text, tool_text = run_turn(
        "Show the first one",
        config,
    )

    combined_text = (tool_text + "\n" + ai_text).lower()
    total_checks += 1
    passed_checks += check(
        result.get("active_recipe_name") == "Carbonara"
        and "carbonara" in combined_text,
        "Agent resolved 'the first one' using remembered recipe list",
        "Agent failed to resolve 'the first one' from context",
    )

    # ------------------------------------------------------------------
    # TURN 8: Edit step 2
    # ------------------------------------------------------------------
    result, ai_text, tool_text = run_turn(
        "Edit step 2: Fry the pancetta until crispy",
        config,
    )

    snapshot = get_db_snapshot()
    step_2_descriptions = [
        step["description"]
        for step in snapshot["steps"]
        if step["order_num"] == 2
    ]

    total_checks += 1
    passed_checks += check(
        "Fry the pancetta until crispy" in step_2_descriptions,
        "Agent edited step 2 through natural-language command",
        "Agent did not update step 2 correctly",
    )

    # ------------------------------------------------------------------
    # TURN 9: Show full recipe again
    # ------------------------------------------------------------------
    result, ai_text, tool_text = run_turn(
        "Show the full recipe again",
        config,
    )

    combined_text = (tool_text + "\n" + ai_text).lower()
    total_checks += 1
    passed_checks += check(
        "pancetta" in combined_text,
        "Updated recipe content is visible in final recipe output",
        "Final recipe output does not show the edited step",
    )

    # ------------------------------------------------------------------
    # FINAL DB CHECK
    # ------------------------------------------------------------------
    print_header("FINAL DATABASE SNAPSHOT")
    snapshot = get_db_snapshot()
    print(snapshot)

    total_checks += 1
    passed_checks += check(
        snapshot["counts"] == {
            "collections": 1,
            "recipes": 1,
            "steps": 4,
            "ingredients": 4,
        },
        "Final database counts are correct",
        f"Unexpected final database counts: {snapshot['counts']}",
    )

    # ------------------------------------------------------------------
    # FINAL RESULT
    # ------------------------------------------------------------------
    print_header("FINAL RESULT")
    print(f"Passed checks: {passed_checks}/{total_checks}")

    if passed_checks == total_checks:
        print_pass("ALL END-TO-END LANGGRAPH TESTS PASSED")
    else:
        print_fail("SOME END-TO-END LANGGRAPH TESTS FAILED")


if __name__ == "__main__":
    main()