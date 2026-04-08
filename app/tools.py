import logging

from app.db import get_connection

logger = logging.getLogger(__name__)


def create_collection(name: str, description: str = ""):
    logger.info("Creating collection: name=%s", name)
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO collections (name, description) VALUES (?, ?)",
            (name, description)
        )
        conn.commit()
        collection_id = cursor.lastrowid
        logger.info("Collection created successfully: id=%s, name=%s", collection_id, name)
        return {
            "success": True,
            "id": collection_id,
            "message": f'Collection "{name}" created.'
        }
    except Exception as e:
        logger.exception("Failed to create collection: name=%s", name)
        return {
            "success": False,
            "message": f"Error creating collection: {e}"
        }
    finally:
        conn.close()


def list_collections():
    logger.info("Listing collections")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, description FROM collections ORDER BY name")
    rows = cursor.fetchall()
    conn.close()

    result = [dict(row) for row in rows]
    logger.info("Collections listed: count=%s", len(result))
    return result


def get_collection_by_name(name: str):
    logger.info("Getting collection by name: %s", name)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name, description
        FROM collections
        WHERE LOWER(name) = LOWER(?)
        LIMIT 1
        """,
        (name,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        logger.warning("Collection not found by name: %s", name)
        return None

    result = dict(row)
    logger.info("Collection found by name: id=%s, name=%s", result["id"], result["name"])
    return result


def create_recipe(
    collection_id: int,
    name: str,
    description: str,
    servings: int,
    prep_time: int
):
    logger.info(
        "Creating recipe: collection_id=%s, name=%s, servings=%s, prep_time=%s",
        collection_id, name, servings, prep_time
    )
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO recipes (collection_id, name, description, servings, prep_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (collection_id, name, description, servings, prep_time)
        )
        conn.commit()
        recipe_id = cursor.lastrowid
        logger.info("Recipe created successfully: id=%s, name=%s", recipe_id, name)
        return {
            "success": True,
            "id": recipe_id,
            "message": f'Recipe "{name}" created.'
        }
    except Exception as e:
        logger.exception("Failed to create recipe: collection_id=%s, name=%s", collection_id, name)
        return {
            "success": False,
            "message": f"Error creating recipe: {e}"
        }
    finally:
        conn.close()


def list_recipes(collection_id: int):
    logger.info("Listing recipes for collection_id=%s", collection_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name, description, servings, prep_time
        FROM recipes
        WHERE collection_id = ?
        ORDER BY name
        """,
        (collection_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    result = [dict(row) for row in rows]
    logger.info("Recipes listed: collection_id=%s, count=%s", collection_id, len(result))
    return result

def get_recipe_by_name(collection_id: int, name: str):
    logger.info("Getting recipe by name: collection_id=%s, name=%s", collection_id, name)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, collection_id, name, description, servings, prep_time
        FROM recipes
        WHERE collection_id = ? AND LOWER(name) = LOWER(?)
        LIMIT 1
        """,
        (collection_id, name)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        logger.warning("Recipe not found by name: collection_id=%s, name=%s", collection_id, name)
        return None

    result = dict(row)
    logger.info("Recipe found by name: id=%s, name=%s", result["id"], result["name"])
    return result


def create_full_recipe(
    collection_id: int,
    name: str,
    description: str,
    servings: int,
    prep_time: int,
    steps: list[str],
    ingredients: list[dict],
):
    logger.info(
        "Creating full recipe: collection_id=%s, name=%s, steps=%s, ingredients=%s",
        collection_id, name, len(steps), len(ingredients)
    )
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO recipes (collection_id, name, description, servings, prep_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (collection_id, name, description, servings, prep_time)
        )
        recipe_id = cursor.lastrowid

        for i, step_text in enumerate(steps, start=1):
            cursor.execute(
                """
                INSERT INTO steps (recipe_id, order_num, description)
                VALUES (?, ?, ?)
                """,
                (recipe_id, i, step_text)
            )

        for ingredient in ingredients:
            cursor.execute(
                """
                INSERT INTO ingredients (recipe_id, name, amount, unit)
                VALUES (?, ?, ?, ?)
                """,
                (
                    recipe_id,
                    ingredient["name"],
                    ingredient["amount"],
                    ingredient["unit"],
                )
            )

        conn.commit()
        logger.info("Full recipe created successfully: id=%s, name=%s", recipe_id, name)
        return {
            "success": True,
            "id": recipe_id,
            "message": f'Recipe "{name}" created with steps and ingredients.'
        }

    except Exception as e:
        conn.rollback()
        logger.exception("Failed to create full recipe: collection_id=%s, name=%s", collection_id, name)
        return {
            "success": False,
            "message": f"Error creating full recipe: {e}"
        }
    finally:
        conn.close()


def rename_recipe(recipe_id: int, new_name: str):
    logger.info("Renaming recipe: recipe_id=%s, new_name=%s", recipe_id, new_name)
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE recipes
            SET name = ?
            WHERE id = ?
            """,
            (new_name, recipe_id)
        )
        conn.commit()

        if cursor.rowcount == 0:
            logger.warning("Recipe not found for rename: recipe_id=%s", recipe_id)
            return {
                "success": False,
                "message": "Recipe not found."
            }

        logger.info("Recipe renamed successfully: recipe_id=%s, new_name=%s", recipe_id, new_name)
        return {
            "success": True,
            "message": f'Recipe renamed to "{new_name}".'
        }

    except Exception as e:
        logger.exception("Failed to rename recipe: recipe_id=%s", recipe_id)
        return {
            "success": False,
            "message": f"Error renaming recipe: {e}"
        }
    finally:
        conn.close()


def delete_collection(collection_id: int):
    logger.info("Deleting collection: collection_id=%s", collection_id)
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, name
            FROM collections
            WHERE id = ?
            """,
            (collection_id,)
        )
        collection = cursor.fetchone()

        if not collection:
            logger.warning("Collection not found for delete: collection_id=%s", collection_id)
            return {
                "success": False,
                "message": "Collection not found."
            }

        collection_name = collection["name"]

        cursor.execute(
            """
            DELETE FROM collections
            WHERE id = ?
            """,
            (collection_id,)
        )
        conn.commit()

        logger.info("Collection deleted successfully: collection_id=%s, name=%s", collection_id, collection_name)
        return {
            "success": True,
            "message": f'Collection "{collection_name}" deleted.'
        }

    except Exception as e:
        logger.exception("Failed to delete collection: collection_id=%s", collection_id)
        return {
            "success": False,
            "message": f"Error deleting collection: {e}"
        }
    finally:
        conn.close()


def edit_ingredient(
    recipe_id: int,
    ingredient_number: int,
    new_name: str,
    new_amount: float,
    new_unit: str,
):
    logger.info(
        "Editing ingredient: recipe_id=%s, ingredient_number=%s",
        recipe_id, ingredient_number
    )
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM ingredients
        WHERE recipe_id = ?
        ORDER BY id
        """,
        (recipe_id,)
    )
    rows = cursor.fetchall()

    if ingredient_number < 1 or ingredient_number > len(rows):
        conn.close()
        logger.warning(
            "Ingredient number out of range: recipe_id=%s, ingredient_number=%s",
            recipe_id, ingredient_number
        )
        return {
            "success": False,
            "message": f"Ingredient {ingredient_number} not found."
        }

    ingredient_id = rows[ingredient_number - 1]["id"]

    cursor.execute(
        """
        UPDATE ingredients
        SET name = ?, amount = ?, unit = ?
        WHERE id = ?
        """,
        (new_name, new_amount, new_unit, ingredient_id)
    )
    conn.commit()
    conn.close()

    logger.info(
        "Ingredient updated successfully: recipe_id=%s, ingredient_number=%s",
        recipe_id, ingredient_number
    )
    return {
        "success": True,
        "message": f"Ingredient {ingredient_number} updated."
    }


def remove_ingredient(recipe_id: int, ingredient_number: int):
    logger.info(
        "Removing ingredient: recipe_id=%s, ingredient_number=%s",
        recipe_id, ingredient_number
    )
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM ingredients
        WHERE recipe_id = ?
        ORDER BY id
        """,
        (recipe_id,)
    )
    rows = cursor.fetchall()

    if ingredient_number < 1 or ingredient_number > len(rows):
        conn.close()
        logger.warning(
            "Ingredient number out of range for delete: recipe_id=%s, ingredient_number=%s",
            recipe_id, ingredient_number
        )
        return {
            "success": False,
            "message": f"Ingredient {ingredient_number} not found."
        }

    ingredient_id = rows[ingredient_number - 1]["id"]

    cursor.execute(
        """
        DELETE FROM ingredients
        WHERE id = ?
        """,
        (ingredient_id,)
    )
    conn.commit()
    conn.close()

    logger.info(
        "Ingredient removed successfully: recipe_id=%s, ingredient_number=%s",
        recipe_id, ingredient_number
    )
    return {
        "success": True,
        "message": f"Ingredient {ingredient_number} removed."
    }


def remove_step(recipe_id: int, step_number: int):
    logger.info("Removing step: recipe_id=%s, step_number=%s", recipe_id, step_number)
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM steps
            WHERE recipe_id = ? AND order_num = ?
            """,
            (recipe_id, step_number)
        )
        row = cursor.fetchone()

        if not row:
            logger.warning("Step not found for delete: recipe_id=%s, step_number=%s", recipe_id, step_number)
            return {
                "success": False,
                "message": f"Step {step_number} not found."
            }

        cursor.execute(
            """
            DELETE FROM steps
            WHERE recipe_id = ? AND order_num = ?
            """,
            (recipe_id, step_number)
        )

        cursor.execute(
            """
            UPDATE steps
            SET order_num = order_num - 1
            WHERE recipe_id = ? AND order_num > ?
            """,
            (recipe_id, step_number)
        )

        conn.commit()
        logger.info("Step removed successfully: recipe_id=%s, step_number=%s", recipe_id, step_number)
        return {
            "success": True,
            "message": f"Step {step_number} removed."
        }

    except Exception as e:
        conn.rollback()
        logger.exception("Failed to remove step: recipe_id=%s, step_number=%s", recipe_id, step_number)
        return {
            "success": False,
            "message": f"Error removing step: {e}"
        }
    finally:
        conn.close()

        
def delete_recipe(recipe_id: int):
    logger.info("Deleting recipe: recipe_id=%s", recipe_id)
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, name
            FROM recipes
            WHERE id = ?
            """,
            (recipe_id,)
        )
        recipe = cursor.fetchone()

        if not recipe:
            logger.warning("Recipe not found for delete: recipe_id=%s", recipe_id)
            return {
                "success": False,
                "message": "Recipe not found."
            }

        recipe_name = recipe["name"]

        cursor.execute(
            """
            DELETE FROM recipes
            WHERE id = ?
            """,
            (recipe_id,)
        )
        conn.commit()

        logger.info("Recipe deleted successfully: recipe_id=%s, name=%s", recipe_id, recipe_name)
        return {
            "success": True,
            "message": f'Recipe "{recipe_name}" deleted.'
        }

    except Exception as e:
        logger.exception("Failed to delete recipe: recipe_id=%s", recipe_id)
        return {
            "success": False,
            "message": f"Error deleting recipe: {e}"
        }
    finally:
        conn.close()

def add_steps(recipe_id: int, steps: list[str]):
    logger.info("Adding %s steps to recipe_id=%s", len(steps), recipe_id)
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT COALESCE(MAX(order_num), 0) as max_order FROM steps WHERE recipe_id = ?",
            (recipe_id,)
        )
        start_order = cursor.fetchone()["max_order"]

        for i, step_text in enumerate(steps, start=1):
            cursor.execute(
                """
                INSERT INTO steps (recipe_id, order_num, description)
                VALUES (?, ?, ?)
                """,
                (recipe_id, start_order + i, step_text)
            )

        conn.commit()
        logger.info("Steps added successfully: recipe_id=%s, count=%s", recipe_id, len(steps))
        return {
            "success": True,
            "message": f"Added {len(steps)} steps."
        }
    except Exception as e:
        logger.exception("Failed to add steps to recipe_id=%s", recipe_id)
        return {
            "success": False,
            "message": f"Error adding steps: {e}"
        }
    finally:
        conn.close()


def add_ingredients(recipe_id: int, ingredients: list[dict]):
    logger.info("Adding %s ingredients to recipe_id=%s", len(ingredients), recipe_id)
    conn = get_connection()
    cursor = conn.cursor()

    try:
        for ingredient in ingredients:
            cursor.execute(
                """
                INSERT INTO ingredients (recipe_id, name, amount, unit)
                VALUES (?, ?, ?, ?)
                """,
                (
                    recipe_id,
                    ingredient["name"],
                    ingredient["amount"],
                    ingredient["unit"]
                )
            )

        conn.commit()
        logger.info("Ingredients added successfully: recipe_id=%s, count=%s", recipe_id, len(ingredients))
        return {
            "success": True,
            "message": f"Added {len(ingredients)} ingredients."
        }
    except Exception as e:
        logger.exception("Failed to add ingredients to recipe_id=%s", recipe_id)
        return {
            "success": False,
            "message": f"Error adding ingredients: {e}"
        }
    finally:
        conn.close()


def get_full_recipe(recipe_id: int):
    logger.info("Getting full recipe for recipe_id=%s", recipe_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, collection_id, name, description, servings, prep_time
        FROM recipes
        WHERE id = ?
        """,
        (recipe_id,)
    )
    recipe = cursor.fetchone()

    if not recipe:
        conn.close()
        logger.warning("Recipe not found: recipe_id=%s", recipe_id)
        return None

    cursor.execute(
        """
        SELECT order_num, description
        FROM steps
        WHERE recipe_id = ?
        ORDER BY order_num
        """,
        (recipe_id,)
    )
    steps = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT name, amount, unit
        FROM ingredients
        WHERE recipe_id = ?
        ORDER BY id
        """,
        (recipe_id,)
    )
    ingredients = [dict(row) for row in cursor.fetchall()]

    conn.close()

    logger.info(
        "Full recipe loaded: recipe_id=%s, steps=%s, ingredients=%s",
        recipe_id, len(steps), len(ingredients)
    )

    return {
        "recipe": dict(recipe),
        "steps": steps,
        "ingredients": ingredients
    }


def edit_step(recipe_id: int, step_number: int, new_description: str):
    logger.info("Editing step: recipe_id=%s, step_number=%s", recipe_id, step_number)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE steps
        SET description = ?
        WHERE recipe_id = ? AND order_num = ?
        """,
        (new_description, recipe_id, step_number)
    )
    conn.commit()

    updated_rows = cursor.rowcount
    conn.close()

    if updated_rows == 0:
        logger.warning("Step not found for update: recipe_id=%s, step_number=%s", recipe_id, step_number)
        return {
            "success": False,
            "message": f"Step {step_number} not found."
        }

    logger.info("Step updated successfully: recipe_id=%s, step_number=%s", recipe_id, step_number)
    return {
        "success": True,
        "message": f"Step {step_number} updated."
    }