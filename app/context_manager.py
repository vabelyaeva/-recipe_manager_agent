from app.state import AgentState
from app.tools import (
    create_collection,
    list_collections,
    create_recipe,
    list_recipes,
    add_steps,
    add_ingredients,
    get_full_recipe,
    edit_step,
)


def create_empty_state() -> AgentState:
    return {
        "active_collection_id": None,
        "active_collection_name": None,
        "active_recipe_id": None,
        "active_recipe_name": None,
        "last_listed_recipe_ids": [],
    }


def create_collection_and_activate(
    state: AgentState,
    name: str,
    description: str = ""
):
    result = create_collection(name, description)

    if result["success"]:
        state["active_collection_id"] = result["id"]
        state["active_collection_name"] = name
        state["active_recipe_id"] = None
        state["active_recipe_name"] = None
        state["last_listed_recipe_ids"] = []

    return result


def get_all_collections():
    return list_collections()


def create_recipe_in_active_collection(
    state: AgentState,
    name: str,
    description: str,
    servings: int,
    prep_time: int
):
    if state["active_collection_id"] is None:
        return {
            "success": False,
            "message": "No active collection selected."
        }

    result = create_recipe(
        collection_id=state["active_collection_id"],
        name=name,
        description=description,
        servings=servings,
        prep_time=prep_time
    )

    if result["success"]:
        state["active_recipe_id"] = result["id"]
        state["active_recipe_name"] = name

    return result


def list_recipes_in_active_collection(state: AgentState):
    if state["active_collection_id"] is None:
        return {
            "success": False,
            "message": "No active collection selected.",
            "recipes": []
        }

    recipes = list_recipes(state["active_collection_id"])
    state["last_listed_recipe_ids"] = [recipe["id"] for recipe in recipes]

    return {
        "success": True,
        "recipes": recipes
    }


def show_recipe_by_index(state: AgentState, index: int):
    if not state["last_listed_recipe_ids"]:
        return {
            "success": False,
            "message": "No recipe list available. Please list recipes first."
        }

    if index < 1 or index > len(state["last_listed_recipe_ids"]):
        return {
            "success": False,
            "message": "Recipe number is out of range."
        }

    recipe_id = state["last_listed_recipe_ids"][index - 1]
    full_recipe = get_full_recipe(recipe_id)

    if not full_recipe:
        return {
            "success": False,
            "message": "Recipe not found."
        }

    state["active_recipe_id"] = full_recipe["recipe"]["id"]
    state["active_recipe_name"] = full_recipe["recipe"]["name"]

    return {
        "success": True,
        "recipe_data": full_recipe
    }


def show_active_recipe(state: AgentState):
    if state["active_recipe_id"] is None:
        return {
            "success": False,
            "message": "No active recipe selected."
        }

    full_recipe = get_full_recipe(state["active_recipe_id"])

    if not full_recipe:
        return {
            "success": False,
            "message": "Recipe not found."
        }

    return {
        "success": True,
        "recipe_data": full_recipe
    }


def add_steps_to_active_recipe(state: AgentState, steps: list[str]):
    if state["active_recipe_id"] is None:
        return {
            "success": False,
            "message": "No active recipe selected."
        }

    return add_steps(state["active_recipe_id"], steps)


def add_ingredients_to_active_recipe(state: AgentState, ingredients: list[dict]):
    if state["active_recipe_id"] is None:
        return {
            "success": False,
            "message": "No active recipe selected."
        }

    return add_ingredients(state["active_recipe_id"], ingredients)


def edit_step_in_active_recipe(
    state: AgentState,
    step_number: int,
    new_description: str
):
    if state["active_recipe_id"] is None:
        return {
            "success": False,
            "message": "No active recipe selected."
        }

    return edit_step(
        recipe_id=state["active_recipe_id"],
        step_number=step_number,
        new_description=new_description
    )