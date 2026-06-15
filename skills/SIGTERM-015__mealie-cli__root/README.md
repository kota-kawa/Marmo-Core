# Mealie CLI (Agent-Oriented)

A powerful, deterministic Command Line Interface (CLI) for interacting with the Mealie API, designed specifically from the ground up to be used by **AI Agents and LLMs**.

## Why this CLI?
When giving an AI Agent access to a Mealie instance to store scraped recipes or manage shopping lists, the complexity of Mealie's relational database (generating cross-referenced UUIDs for ingredients, steps, and foods) often causes LLMs to hallucinate or fail.

This CLI abstracts all that complexity. An Agent can pass a simple, flat JSON with arrays of strings, and the CLI will automatically parse, transform, and map the data into Mealie's expected nested format, generating all necessary relations, tags, categories, and image uploads flawlessly.

## Features
- **Recipe Creation from Flat JSON:** Create a complex recipe (with sections, linked ingredients, source URLs, and cover images) by just providing a flat JSON payload. No UUID generation required!
- **Idempotent Organizers:** Easily ensure Tags, Categories, Tools, and Labels exist using the `ensure` commands without worrying about HTTP 409 conflicts.
- **Advanced Search:** Robust recipe search utilizing all Mealie filters (`--tags`, `--categories`, `--foods`, `--tools`, `--require-all`).
- **Shopping Lists:** Create lists and add items dynamically, automatically generating Labels if they don't exist in the system.
- **Meal Plan Integration:** Schedule meals by attaching recipes or free-text notes to specific dates.
- **Agent Skill Documentation:** Includes a `Skill.md` file designed to be injected directly into your Agent's system prompt so it learns how to use the CLI instantly.

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/mealie-cli.git
cd mealie-cli

# Install dependencies and build
npm install
npm run build

# Link globally (optional)
npm link
```

## Configuration
The CLI requires no interactive prompts. Simply provide your Mealie credentials as environment variables:

```bash
export MEALIE_URL="http://localhost:9000"
export MEALIE_API_KEY="your_api_token"
```

## Usage Examples

### 1. Creating a Recipe
Save a flat JSON file `recipe.json` (as described in `Skill.md`) and run:
```bash
mealie recipe create --data recipe.json
```

### 2. Shopping Lists
```bash
# Creates a list or gets its ID if it already exists
mealie shopping-list ensure --name "Weekly Groceries"

# Add an item with a label (the label is created if it doesn't exist)
mealie shopping-list add-item --list-id <id> --note "Milk" --label "Dairy"
```

### 3. Meal Plans
```bash
# Add a recipe to tonight's dinner
mealie meal-plan create --date "2023-10-25" --entry-type "dinner" --recipe-slug "rigatoni-al-vodka"

# Add a free-text note to breakfast
mealie meal-plan create --date "2023-10-25" --entry-type "breakfast" --title "Pancakes" --text "With maple syrup"
```

### 4. Advanced Recipe Search
```bash
mealie recipe search --tags "pasta,italian" --foods "tomato" --require-all
```

For detailed instructions on the JSON schema required for recipe creation, check the [Skill.md](Skill.md) file.
