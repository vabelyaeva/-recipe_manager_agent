from app.context_manager import (
    create_empty_state,
    create_collection_and_activate,
    create_recipe_in_active_collection,
    list_recipes_in_active_collection,
    show_recipe_by_index,
    show_active_recipe,
    add_steps_to_active_recipe,
    add_ingredients_to_active_recipe,
    edit_step_in_active_recipe,
)
from helpers.reset_db import clear_all_data


def print_header(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_pass(message: str):
    print(f"PASS: {message}")


def print_fail(message: str):
    print(f"FAIL: {message}")


def check(condition: bool, success_msg: str, fail_msg: str):
    if condition:
        print_pass(success_msg)
        return True
    else:
        print_fail(fail_msg)
        return False


def main():
    print_header("RESET DATABASE")
    clear_all_data()

    total_checks = 0
    passed_checks = 0

    # ------------------------------------------------------------------
    # 1. CONTEXT TEST
    # ------------------------------------------------------------------
    print_header("1. CONTEXT TEST")

    state = create_empty_state()
    print("Initial state:", state)

    # Step 1: create collection
    result = create_collection_and_activate(
        state,
        "Italian Cuisine",
        "Classic Italian recipes"
    )
    print("\nCreate collection result:", result)
    print("State after create collection:", state)

    total_checks += 1
    passed_checks += check(
        result["success"]
        and state["active_collection_name"] == "Italian Cuisine"
        and state["active_collection_id"] is not None
        and state["active_recipe_id"] is None,
        "Collection created and active collection stored in state",
        "Collection context was not stored correctly",
    )

    # Step 2: create recipe without repeating collection name
    result = create_recipe_in_active_collection(
        state,
        name="Carbonara",
        description="Pasta with eggs, cheese, and guanciale",
        servings=2,
        prep_time=30
    )
    print("\nCreate recipe result:", result)
    print("State after create recipe:", state)

    total_checks += 1
    passed_checks += check(
        result["success"]
        and state["active_recipe_name"] == "Carbonara"
        and state["active_recipe_id"] is not None,
        "Recipe created and active recipe stored in state",
        "Recipe context was not stored correctly",
    )

    # Step 3: add steps without repeating recipe name
    result = add_steps_to_active_recipe(
        state,
        [
            "Boil the pasta",
            "Fry the guanciale",
            "Mix eggs with pecorino",
            "Combine everything together",
        ]
    )
    print("\nAdd steps result:", result)

    total_checks += 1
    passed_checks += check(
        result["success"] and "Added 4 steps" in result["message"],
        "Steps added using only active recipe context",
        "Steps were not added correctly through active recipe context",
    )

    # Add ingredients too, so full recipe is realistic
    result = add_ingredients_to_active_recipe(
        state,
        [
            {"name": "spaghetti", "amount": 400, "unit": "g"},
            {"name": "guanciale", "amount": 200, "unit": "g"},
            {"name": "eggs", "amount": 4, "unit": "pcs"},
            {"name": "pecorino", "amount": 100, "unit": "g"},
        ]
    )
    print("\nAdd ingredients result:", result)

    total_checks += 1
    passed_checks += check(
        result["success"] and "Added 4 ingredients" in result["message"],
        "Ingredients added using only active recipe context",
        "Ingredients were not added correctly through active recipe context",
    )

    # Step 4: show full recipe
    result = show_active_recipe(state)
    print("\nShow active recipe result:", result)

    total_checks += 1
    passed_checks += check(
        result["success"]
        and result["recipe_data"]["recipe"]["name"] == "Carbonara"
        and len(result["recipe_data"]["steps"]) == 4
        and len(result["recipe_data"]["ingredients"]) == 4,
        "Full active recipe displayed correctly",
        "Full active recipe was not returned correctly",
    )

    # Step 5: list recipes in collection
    result = list_recipes_in_active_collection(state)
    print("\nList recipes result:", result)
    print("State after listing recipes:", state)

    total_checks += 1
    passed_checks += check(
        result["success"]
        and len(result["recipes"]) == 1
        and state["last_listed_recipe_ids"] == [result["recipes"][0]["id"]],
        "Recipes listed and last_listed_recipe_ids saved in state",
        "Recipes list was not stored correctly in state",
    )

    # Step 6: show first one
    result = show_recipe_by_index(state, 1)
    print("\nShow recipe by index result:", result)
    print("State after show recipe by index:", state)

    total_checks += 1
    passed_checks += check(
        result["success"]
        and result["recipe_data"]["recipe"]["name"] == "Carbonara"
        and state["active_recipe_name"] == "Carbonara",
        "Recipe selected by index using saved list context",
        "Recipe was not selected correctly from last_listed_recipe_ids",
    )

    # ------------------------------------------------------------------
    # 2. ERROR HANDLING TEST
    # ------------------------------------------------------------------
    print_header("2. ERROR HANDLING TEST")

    # Case A: show recipe without active recipe
    empty_state = create_empty_state()
    result = show_active_recipe(empty_state)
    print("\nShow active recipe without active recipe:", result)

    total_checks += 1
    passed_checks += check(
        (not result["success"]) and ("No active recipe selected" in result["message"]),
        "Correct error for 'Show the full recipe' without active recipe",
        "Wrong behavior for 'Show the full recipe' without active recipe",
    )

    # Case B: add recipe without active collection
    empty_state = create_empty_state()
    result = create_recipe_in_active_collection(
        empty_state,
        name="Tiramisu",
        description="Classic dessert",
        servings=4,
        prep_time=25,
    )
    print("\nAdd recipe without active collection:", result)

    total_checks += 1
    passed_checks += check(
        (not result["success"]) and ("No active collection selected" in result["message"]),
        "Correct error for adding recipe without active collection",
        "Wrong behavior for adding recipe without active collection",
    )

    # Case C: edit non-existing step
    state_for_step_test = create_empty_state()
    create_collection_and_activate(state_for_step_test, "Desserts", "Sweet recipes")
    create_recipe_in_active_collection(
        state_for_step_test,
        name="Tiramisu",
        description="Coffee dessert",
        servings=4,
        prep_time=25,
    )
    add_steps_to_active_recipe(state_for_step_test, ["Prepare cream", "Layer biscuits"])

    result = edit_step_in_active_recipe(
        state_for_step_test,
        99,
        "This step does not exist",
    )
    print("\nEdit non-existing step 99:", result)

    total_checks += 1
    passed_checks += check(
        (not result["success"]) and ("Step 99 not found" in result["message"]),
        "Correct error for editing a non-existing step",
        "Wrong behavior for editing a non-existing step",
    )

    # Case D: duplicate collection
    dup_state = create_empty_state()
    result1 = create_collection_and_activate(dup_state, "French Cuisine", "French food")
    result2 = create_collection_and_activate(dup_state, "French Cuisine", "Duplicate name")
    print("\nCreate collection first time:", result1)
    print("Create duplicate collection:", result2)

    total_checks += 1
    passed_checks += check(
        result1["success"]
        and (not result2["success"])
        and ("UNIQUE constraint failed" in result2["message"]),
        "Correct error for duplicate collection name",
        "Wrong behavior for duplicate collection name",
    )

    # Case E: duplicate recipe in same collection
    dup_recipe_state = create_empty_state()
    create_collection_and_activate(dup_recipe_state, "Asian Cuisine", "Asian dishes")

    result1 = create_recipe_in_active_collection(
        dup_recipe_state,
        name="Ramen",
        description="Noodle soup",
        servings=2,
        prep_time=40,
    )
    result2 = create_recipe_in_active_collection(
        dup_recipe_state,
        name="Ramen",
        description="Duplicate noodle soup",
        servings=2,
        prep_time=45,
    )
    print("\nCreate recipe first time:", result1)
    print("Create duplicate recipe in same collection:", result2)

    total_checks += 1
    passed_checks += check(
        result1["success"]
        and (not result2["success"])
        and ("UNIQUE constraint failed" in result2["message"]),
        "Correct error for duplicate recipe name in same collection",
        "Wrong behavior for duplicate recipe name in same collection",
    )

    # ------------------------------------------------------------------
    # FINAL RESULT
    # ------------------------------------------------------------------
    print_header("FINAL RESULT")
    print(f"Passed checks: {passed_checks}/{total_checks}")

    if passed_checks == total_checks:
        print_pass("ALL CONTEXT AND ERROR HANDLING TESTS PASSED")
    else:
        print_fail("SOME TESTS FAILED")


if __name__ == "__main__":
    main()