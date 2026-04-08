# Recipe Manager Agent

Recipe Manager Agent is a CLI-based AI assistant for managing a cookbook with natural-language commands. It can create and select collections, create recipes, add and edit steps and ingredients, show full recipes, list recipes in a collection, remember the current conversation context, and delete recipes.

## Main Features

- Create and list recipe collections
- Select an active collection
- Create recipes inside the active collection
- Create a full recipe with steps and ingredients
- Add steps and ingredients to the active recipe
- Show the full active recipe
- List recipes in the active collection
- Select a recipe by number or by name
- Edit recipe steps and ingredients
- Rename and delete recipes
- Keep conversation context between turns using active collection and active recipe state

## Example Requests

- `Create a collection called "Italian Cuisine"`
- `Add recipe "Carbonara", 2 servings, 30 minutes`
- `Show the full recipe`

## Model

The current OpenAI model used in the project is:

- `gpt-5-nano`

## How to Run

Run the project from the root folder with:

```bash
python run.py
```

Or, if you use the local virtual environment on Windows:

```bash
.\.venv\Scripts\python.exe run.py
```

## OpenAI API Key

An OpenAI API key is required to run the agent.

You can provide it in one of two ways:

1. Insert your key into the `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key
```

2. Or start the CLI and enter the key when prompted.

## Project Structure

- `app/` — the main agent logic: graph, CLI, tools, state, database, and context handling
- `helpers/` — helper utilities such as database reset scripts and other supporting functions
- `tests/` — test scripts for context, error handling, and end-to-end behavior
- `logs/` — log files with recorded communication and application activity

## Database Tools

The following tools and functions were implemented for working with the SQLite database.

### Collection Operations

- `create_collection` — create a new collection
- `list_collections` — list all collections
- `get_collection_by_name` — find a collection by name
- `delete_collection` — delete a collection

### Recipe Operations

- `create_recipe` — create a recipe in a collection
- `create_full_recipe` — create a recipe together with steps and ingredients
- `list_recipes` — list recipes in a collection
- `get_recipe_by_name` — find a recipe by name in a collection
- `get_full_recipe` — load a recipe with all steps and ingredients
- `rename_recipe` — rename a recipe
- `delete_recipe` — delete a recipe

### Step Operations

- `add_steps` — add multiple steps to a recipe
- `edit_step` — edit a step by step number
- `remove_step` — remove a step by step number

### Ingredient Operations

- `add_ingredients` — add multiple ingredients to a recipe
- `edit_ingredient` — edit an ingredient by its number
- `remove_ingredient` — remove an ingredient by its number

## Notes

- The project uses **LangGraph** for the agent workflow
- The database is implemented with **SQLite**
- The agent preserves context, so the user does not need to repeat the current collection or recipe name in every message
