from app.state import AgentState


def main():
    state: AgentState = {
        "active_collection_id": None,
        "active_collection_name": None,
        "active_recipe_id": None,
        "active_recipe_name": None,
        "last_listed_recipe_ids": [],
    }

    print("Initial state:")
    print(state)

    state["active_collection_id"] = 1
    state["active_collection_name"] = "Italian Cuisine"

    state["active_recipe_id"] = 1
    state["active_recipe_name"] = "Carbonara"

    state["last_listed_recipe_ids"] = [1, 2, 3]

    print("Updated state:")
    print(state)


if __name__ == "__main__":
    main()