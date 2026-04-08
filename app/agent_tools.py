import logging
from typing import List

from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.tools import (
    add_ingredients,
    add_steps,
    create_collection,
    create_full_recipe,
    create_recipe,
    delete_collection,
    delete_recipe,
    edit_ingredient,
    edit_step,
    get_collection_by_name,
    get_full_recipe,
    get_recipe_by_name,
    list_collections,
    list_recipes,
    remove_ingredient,
    remove_step,
    rename_recipe,
)

logger = logging.getLogger(__name__)


class IngredientInput(BaseModel):
    name: str = Field(description="Ingredient name")
    amount: float = Field(description="Numeric amount")
    unit: str = Field(description="Unit like g, kg, ml, l, pcs, tbsp, tsp")

class FullRecipeInput(BaseModel):
    name: str = Field(description="Recipe name")
    description: str = Field(default="", description="Recipe description")
    servings: int = Field(description="Number of servings")
    prep_time: int = Field(description="Preparation time in minutes")
    steps: List[str] = Field(description="Ordered recipe steps")
    ingredients: List[IngredientInput] = Field(description="Recipe ingredients")


class IngredientEditInput(BaseModel):
    ingredient_number: int = Field(description="Ingredient number in the displayed order, starting from 1")
    name: str = Field(description="New ingredient name")
    amount: float = Field(description="New numeric amount")
    unit: str = Field(description="New unit like g, kg, ml, l, pcs, tbsp, tsp")

def _tool_message(runtime: ToolRuntime, text: str) -> ToolMessage:
    return ToolMessage(content=text, tool_call_id=runtime.tool_call_id)


def _format_recipe(recipe_data: dict) -> str:
    recipe = recipe_data["recipe"]
    steps = recipe_data["steps"]
    ingredients = recipe_data["ingredients"]

    lines = [
        f'Recipe: {recipe["name"]}',
        f'Description: {recipe["description"]}',
        f'Servings: {recipe["servings"]}',
        f'Prep time: {recipe["prep_time"]} minutes',
        "",
        "Ingredients:",
    ]

    if ingredients:
        for ing in ingredients:
            lines.append(f'- {ing["name"]}: {ing["amount"]} {ing["unit"]}')
    else:
        lines.append("- No ingredients yet")

    lines.append("")
    lines.append("Steps:")

    if steps:
        for step in steps:
            lines.append(f'{step["order_num"]}. {step["description"]}')
    else:
        lines.append("No steps yet")

    return "\n".join(lines)


@tool
def create_collection_tool(
    name: str,
    description: str = "",
    runtime: ToolRuntime = None,
) -> Command:
    """Create a new recipe collection and make it the active collection."""
    logger.info("Tool call: create_collection_tool | name=%s", name)
    result = create_collection(name, description)

    if result["success"]:
        return Command(
            update={
                "active_collection_id": result["id"],
                "active_collection_name": name,
                "active_recipe_id": None,
                "active_recipe_name": None,
                "last_listed_recipe_ids": [],
                "messages": [
                    _tool_message(runtime, f'Collection "{name}" created.')
                ],
            }
        )

    return Command(
        update={
            "messages": [_tool_message(runtime, result["message"])]
        }
    )


@tool
def select_collection_tool(
    name: str,
    runtime: ToolRuntime = None,
) -> Command:
    """Select an existing collection by name and make it the active collection."""
    logger.info("Tool call: select_collection_tool | name=%s", name)
    collection = get_collection_by_name(name)

    if not collection:
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, f'Collection "{name}" not found.')
                ]
            }
        )

    return Command(
        update={
            "active_collection_id": collection["id"],
            "active_collection_name": collection["name"],
            "active_recipe_id": None,
            "active_recipe_name": None,
            "last_listed_recipe_ids": [],
            "messages": [
                _tool_message(runtime, f'Collection "{collection["name"]}" selected.')
            ],
        }
    )


@tool
def show_collection_contents_tool(
    name: str,
    runtime: ToolRuntime = None,
) -> Command:
    """Select an existing collection by name and immediately show all recipes in it."""
    logger.info("Tool call: show_collection_contents_tool | name=%s", name)
    collection = get_collection_by_name(name)

    if not collection:
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, f'Collection "{name}" not found.')
                ]
            }
        )

    recipes = list_recipes(collection["id"])
    recipe_ids = [recipe["id"] for recipe in recipes]

    if not recipes:
        text = f'{collection["name"]} contents: 0 recipes found.'
    else:
        lines = [f'{collection["name"]} contents:']
        for i, recipe in enumerate(recipes, start=1):
            lines.append(
                f'{i}. {recipe["name"]} — {recipe["servings"]} servings, {recipe["prep_time"]} min'
            )
        text = "\n".join(lines)

    return Command(
        update={
            "active_collection_id": collection["id"],
            "active_collection_name": collection["name"],
            "active_recipe_id": None,
            "active_recipe_name": None,
            "last_listed_recipe_ids": recipe_ids,
            "messages": [_tool_message(runtime, text)],
        }
    )


@tool
def list_collections_tool() -> str:
    """List all collections."""
    logger.info("Tool call: list_collections_tool")
    collections = list_collections()

    if not collections:
        return "No collections found."

    lines = ["Collections:"]
    for i, collection in enumerate(collections, start=1):
        desc = collection["description"] or "No description"
        lines.append(f'{i}. {collection["name"]} — {desc}')

    return "\n".join(lines)


@tool
def create_recipe_tool(
    name: str,
    servings: int,
    prep_time: int,
    description: str = "",
    runtime: ToolRuntime = None,
) -> Command:
    """Create a recipe in the currently active collection and make it the active recipe."""
    logger.info("Tool call: create_recipe_tool | name=%s", name)
    active_collection_id = runtime.state.get("active_collection_id")
    active_collection_name = runtime.state.get("active_collection_name")

    if active_collection_id is None:
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, "No active collection selected. Select or create a collection first.")
                ]
            }
        )

    result = create_recipe(
        collection_id=active_collection_id,
        name=name,
        description=description,
        servings=servings,
        prep_time=prep_time,
    )

    if result["success"]:
        return Command(
            update={
                "active_recipe_id": result["id"],
                "active_recipe_name": name,
                "messages": [
                    _tool_message(
                        runtime,
                        f'Recipe "{name}" added to collection "{active_collection_name}".'
                    )
                ],
            }
        )

    return Command(
        update={
            "messages": [_tool_message(runtime, result["message"])]
        }
    )


@tool
def list_recipes_tool(runtime: ToolRuntime = None) -> Command:
    """List all recipes in the currently active collection."""
    logger.info("Tool call: list_recipes_tool")
    active_collection_id = runtime.state.get("active_collection_id")
    active_collection_name = runtime.state.get("active_collection_name")

    if active_collection_id is None:
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, "No active collection selected.")
                ]
            }
        )

    recipes = list_recipes(active_collection_id)
    recipe_ids = [recipe["id"] for recipe in recipes]

    if not recipes:
        text = f'No recipes found in collection "{active_collection_name}".'
    else:
        lines = [f'Recipes in "{active_collection_name}":']
        for i, recipe in enumerate(recipes, start=1):
            lines.append(
                f'{i}. {recipe["name"]} — {recipe["servings"]} servings, {recipe["prep_time"]} min'
            )
        text = "\n".join(lines)

    return Command(
        update={
            "last_listed_recipe_ids": recipe_ids,
            "messages": [_tool_message(runtime, text)],
        }
    )


@tool
def show_recipe_by_number_tool(number: int, runtime: ToolRuntime = None) -> Command:
    """Show a full recipe by its number from the last listed recipes and make it the active recipe."""
    logger.info("Tool call: show_recipe_by_number_tool | number=%s", number)
    last_ids = runtime.state.get("last_listed_recipe_ids", [])

    if not last_ids:
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, "No recent recipe list found. Please list recipes first.")
                ]
            }
        )

    if number < 1 or number > len(last_ids):
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, "Recipe number is out of range.")
                ]
            }
        )

    recipe_id = last_ids[number - 1]
    recipe_data = get_full_recipe(recipe_id)

    if not recipe_data:
        return Command(
            update={
                "messages": [_tool_message(runtime, "Recipe not found.")]
            }
        )

    recipe_name = recipe_data["recipe"]["name"]

    return Command(
        update={
            "active_recipe_id": recipe_id,
            "active_recipe_name": recipe_name,
            "messages": [_tool_message(runtime, _format_recipe(recipe_data))],
        }
    )


@tool
def show_active_recipe_tool(runtime: ToolRuntime = None) -> str:
    """Show the currently active recipe with all ingredients and steps."""
    logger.info("Tool call: show_active_recipe_tool")
    active_recipe_id = runtime.state.get("active_recipe_id")

    if active_recipe_id is None:
        return "No active recipe selected."

    recipe_data = get_full_recipe(active_recipe_id)

    if not recipe_data:
        return "Recipe not found."

    return _format_recipe(recipe_data)


@tool
def add_steps_tool(steps: List[str], runtime: ToolRuntime = None) -> str:
    """Add a list of ordered steps to the currently active recipe."""
    logger.info("Tool call: add_steps_tool | count=%s", len(steps))
    active_recipe_id = runtime.state.get("active_recipe_id")

    if active_recipe_id is None:
        return "No active recipe selected."

    result = add_steps(active_recipe_id, steps)
    recipe_name = runtime.state.get("active_recipe_name") or "current recipe"
    if result["success"]:
        return f'Added {len(steps)} steps to recipe "{recipe_name}".'
    return result["message"]


@tool
def add_ingredients_tool(
    ingredients: List[IngredientInput],
    runtime: ToolRuntime = None,
) -> str:
    """Add ingredients to the currently active recipe."""
    logger.info("Tool call: add_ingredients_tool | count=%s", len(ingredients))
    active_recipe_id = runtime.state.get("active_recipe_id")

    if active_recipe_id is None:
        return "No active recipe selected."

    payload = [ingredient.model_dump() for ingredient in ingredients]
    result = add_ingredients(active_recipe_id, payload)
    recipe_name = runtime.state.get("active_recipe_name") or "current recipe"
    if result["success"]:
        return f'Added {len(payload)} ingredients to recipe "{recipe_name}".'
    return result["message"]


@tool
def edit_step_tool(
    step_number: int,
    new_description: str,
    runtime: ToolRuntime = None,
) -> str:
    """Edit a step in the currently active recipe by its step number."""
    logger.info("Tool call: edit_step_tool | step_number=%s", step_number)
    active_recipe_id = runtime.state.get("active_recipe_id")

    if active_recipe_id is None:
        return "No active recipe selected."

    result = edit_step(
        recipe_id=active_recipe_id,
        step_number=step_number,
        new_description=new_description,
    )
    if result["success"]:
        return f"Step {step_number} updated."
    return result["message"]


@tool
def delete_active_recipe_tool(runtime: ToolRuntime = None) -> Command:
    """Delete the currently active recipe."""
    logger.info("Tool call: delete_active_recipe_tool")
    active_recipe_id = runtime.state.get("active_recipe_id")
    last_ids = runtime.state.get("last_listed_recipe_ids", [])

    if active_recipe_id is None:
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, "No active recipe selected.")
                ]
            }
        )

    result = delete_recipe(active_recipe_id)

    if result["success"]:
        updated_last_ids = [rid for rid in last_ids if rid != active_recipe_id]

        return Command(
            update={
                "active_recipe_id": None,
                "active_recipe_name": None,
                "last_listed_recipe_ids": updated_last_ids,
                "messages": [
                    _tool_message(runtime, result["message"])
                ],
            }
        )

    return Command(
        update={
            "messages": [
                _tool_message(runtime, result["message"])
            ]
        }
    )


@tool
def delete_recipe_by_number_tool(number: int, runtime: ToolRuntime = None) -> Command:
    """Delete a recipe by its number from the last listed recipes."""
    logger.info("Tool call: delete_recipe_by_number_tool | number=%s", number)
    last_ids = runtime.state.get("last_listed_recipe_ids", [])
    active_recipe_id = runtime.state.get("active_recipe_id")

    if not last_ids:
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, "No recent recipe list found. Please list recipes first.")
                ]
            }
        )

    if number < 1 or number > len(last_ids):
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, "Recipe number is out of range.")
                ]
            }
        )

    recipe_id = last_ids[number - 1]
    result = delete_recipe(recipe_id)

    if result["success"]:
        updated_last_ids = [rid for rid in last_ids if rid != recipe_id]

        update_data = {
            "last_listed_recipe_ids": updated_last_ids,
            "messages": [_tool_message(runtime, result["message"])],
        }

        if active_recipe_id == recipe_id:
            update_data["active_recipe_id"] = None
            update_data["active_recipe_name"] = None

        return Command(update=update_data)

    return Command(
        update={
            "messages": [_tool_message(runtime, result["message"])]
        }
    )


@tool
def create_full_recipe_tool(
    recipe: FullRecipeInput,
    runtime: ToolRuntime = None,
) -> Command:
    """Create a full recipe with steps and ingredients in the currently active collection."""
    logger.info("Tool call: create_full_recipe_tool | name=%s", recipe.name)
    active_collection_id = runtime.state.get("active_collection_id")
    active_collection_name = runtime.state.get("active_collection_name")

    if active_collection_id is None:
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, "No active collection selected. Select or create a collection first.")
                ]
            }
        )

    payload_ingredients = [ingredient.model_dump() for ingredient in recipe.ingredients]

    result = create_full_recipe(
        collection_id=active_collection_id,
        name=recipe.name,
        description=recipe.description,
        servings=recipe.servings,
        prep_time=recipe.prep_time,
        steps=recipe.steps,
        ingredients=payload_ingredients,
    )

    if result["success"]:
        return Command(
            update={
                "active_recipe_id": result["id"],
                "active_recipe_name": recipe.name,
                "messages": [
                    _tool_message(
                        runtime,
                        f'Recipe "{recipe.name}" with steps and ingredients added to collection "{active_collection_name}".'
                    )
                ],
            }
        )

    return Command(
        update={"messages": [_tool_message(runtime, result["message"])]}
    )


@tool
def select_recipe_by_name_tool(name: str, runtime: ToolRuntime = None) -> Command:
    """Select a recipe by name from the currently active collection and show its full contents."""
    logger.info("Tool call: select_recipe_by_name_tool | name=%s", name)
    active_collection_id = runtime.state.get("active_collection_id")

    if active_collection_id is None:
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, "No active collection selected.")
                ]
            }
        )

    recipe = get_recipe_by_name(active_collection_id, name)
    if not recipe:
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, f'Recipe "{name}" not found in the active collection.')
                ]
            }
        )

    recipe_data = get_full_recipe(recipe["id"])
    if not recipe_data:
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, "Recipe not found.")
                ]
            }
        )

    return Command(
        update={
            "active_recipe_id": recipe["id"],
            "active_recipe_name": recipe["name"],
            "messages": [_tool_message(runtime, _format_recipe(recipe_data))],
        }
    )


@tool
def show_overview_tool(runtime: ToolRuntime = None) -> str:
    """Show collections, current active collection, current active recipe, and recipes in the active collection."""
    logger.info("Tool call: show_overview_tool")
    collections = list_collections()
    active_collection_id = runtime.state.get("active_collection_id")
    active_collection_name = runtime.state.get("active_collection_name")
    active_recipe_name = runtime.state.get("active_recipe_name")

    lines = []

    if not collections:
        lines.append("Collections: none")
    else:
        lines.append("Collections:")
        for i, collection in enumerate(collections, start=1):
            lines.append(f'{i}. {collection["name"]}')

    lines.append("")
    lines.append(f'Active collection: {active_collection_name or "None"}')
    lines.append(f'Active recipe: {active_recipe_name or "None"}')

    if active_collection_id is not None:
        recipes = list_recipes(active_collection_id)
        lines.append("")
        if not recipes:
            lines.append(f'Recipes in "{active_collection_name}": none')
        else:
            lines.append(f'Recipes in "{active_collection_name}":')
            for i, recipe in enumerate(recipes, start=1):
                lines.append(
                    f'{i}. {recipe["name"]} — {recipe["servings"]} servings, {recipe["prep_time"]} min'
                )

    return "\n".join(lines)


@tool
def delete_active_collection_tool(runtime: ToolRuntime = None) -> Command:
    """Delete the currently active collection."""
    logger.info("Tool call: delete_active_collection_tool")
    active_collection_id = runtime.state.get("active_collection_id")

    if active_collection_id is None:
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, "No active collection selected.")
                ]
            }
        )

    result = delete_collection(active_collection_id)

    if result["success"]:
        return Command(
            update={
                "active_collection_id": None,
                "active_collection_name": None,
                "active_recipe_id": None,
                "active_recipe_name": None,
                "last_listed_recipe_ids": [],
                "messages": [_tool_message(runtime, result["message"])],
            }
        )

    return Command(
        update={"messages": [_tool_message(runtime, result["message"])]}
    )


@tool
def edit_ingredient_tool(
    ingredient: IngredientEditInput,
    runtime: ToolRuntime = None,
) -> str:
    """Edit an ingredient in the currently active recipe by its number."""
    logger.info("Tool call: edit_ingredient_tool | ingredient_number=%s", ingredient.ingredient_number)
    active_recipe_id = runtime.state.get("active_recipe_id")

    if active_recipe_id is None:
        return "No active recipe selected."

    result = edit_ingredient(
        recipe_id=active_recipe_id,
        ingredient_number=ingredient.ingredient_number,
        new_name=ingredient.name,
        new_amount=ingredient.amount,
        new_unit=ingredient.unit,
    )
    return result["message"]


@tool
def remove_ingredient_tool(ingredient_number: int, runtime: ToolRuntime = None) -> str:
    """Remove an ingredient from the currently active recipe by its number."""
    logger.info("Tool call: remove_ingredient_tool | ingredient_number=%s", ingredient_number)
    active_recipe_id = runtime.state.get("active_recipe_id")

    if active_recipe_id is None:
        return "No active recipe selected."

    result = remove_ingredient(
        recipe_id=active_recipe_id,
        ingredient_number=ingredient_number,
    )
    return result["message"]


@tool
def remove_step_tool(step_number: int, runtime: ToolRuntime = None) -> str:
    """Remove a step from the currently active recipe by its number."""
    logger.info("Tool call: remove_step_tool | step_number=%s", step_number)
    active_recipe_id = runtime.state.get("active_recipe_id")

    if active_recipe_id is None:
        return "No active recipe selected."

    result = remove_step(
        recipe_id=active_recipe_id,
        step_number=step_number,
    )
    return result["message"]


@tool
def rename_active_recipe_tool(new_name: str, runtime: ToolRuntime = None) -> Command:
    """Rename the currently active recipe."""
    logger.info("Tool call: rename_active_recipe_tool | new_name=%s", new_name)
    active_recipe_id = runtime.state.get("active_recipe_id")

    if active_recipe_id is None:
        return Command(
            update={
                "messages": [
                    _tool_message(runtime, "No active recipe selected.")
                ]
            }
        )

    result = rename_recipe(active_recipe_id, new_name)

    if result["success"]:
        return Command(
            update={
                "active_recipe_name": new_name,
                "messages": [_tool_message(runtime, result["message"])],
            }
        )

    return Command(
        update={"messages": [_tool_message(runtime, result["message"])]}
    )


@tool
def clear_active_recipe_tool(runtime: ToolRuntime = None) -> Command:
    """Clear the currently active recipe from conversation context."""
    logger.info("Tool call: clear_active_recipe_tool")
    return Command(
        update={
            "active_recipe_id": None,
            "active_recipe_name": None,
            "messages": [_tool_message(runtime, "Active recipe cleared.")],
        }
    )

RECIPE_TOOLS = [
    create_collection_tool,
    select_collection_tool,
    show_collection_contents_tool,
    list_collections_tool,

    create_recipe_tool,
    create_full_recipe_tool,
    list_recipes_tool,
    show_recipe_by_number_tool,
    select_recipe_by_name_tool,
    show_active_recipe_tool,
    show_overview_tool,

    add_steps_tool,
    add_ingredients_tool,
    edit_step_tool,
    remove_step_tool,

    edit_ingredient_tool,
    remove_ingredient_tool,

    rename_active_recipe_tool,

    delete_active_recipe_tool,
    delete_recipe_by_number_tool,
    delete_active_collection_tool,

    clear_active_recipe_tool,
]