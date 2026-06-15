import { Command } from "commander";
import { getClient } from "../api";
import { handleAction, extractItems } from "../utils";
import { ShoppingListOut, MultiPurposeLabelOut, ShoppingListItemsCollectionOut } from "../models/types";

export function setupShoppingListCommands(program: Command) {
  const listCmd = program.command("shopping-list").description("Manage shopping lists");

  listCmd
    .command("ensure")
    .description("Ensure a shopping list exists, creates it if it does not")
    .requiredOption("--name <name>", "Name of the shopping list")
    .action((options) => {
      handleAction(async () => {
        const client = getClient();
        const lists = await client.get<ShoppingListOut[]>("/api/households/shopping/lists");
        // /api/households/shopping/lists returns an array or pagination object? 
        // Based on openapi it returns ShoppingListOut[], wait let's assume it returns an array
        // In openapi it returns ShoppingListPagination... oh wait
        const items = extractItems<ShoppingListOut>(lists);
        const existing = items.find((l) => l.name?.toLowerCase() === options.name.toLowerCase());
        if (existing) {
          return existing;
        }
        const created = await client.post<ShoppingListOut>("/api/households/shopping/lists", { name: options.name });
        return created;
      });
    });

  listCmd
    .command("add-item")
    .description("Add an item to a shopping list")
    .requiredOption("--list-id <id>", "ID of the shopping list")
    .requiredOption("--note <text>", "Item description or note")
    .option("--label <name>", "Name of the label to attach (will be created if it does not exist)")
    .action((options) => {
      handleAction(async () => {
        const client = getClient();
        let labelId: string | null | undefined = null;

        if (options.label) {
          // Ensure label exists
          const labelsRes = await client.get<MultiPurposeLabelOut[]>("/api/groups/labels");
          const labels = extractItems<MultiPurposeLabelOut>(labelsRes);
          let label = labels.find((l) => l.name?.toLowerCase() === options.label.toLowerCase());

          if (!label) {
            label = await client.post<MultiPurposeLabelOut>("/api/groups/labels", {
              name: options.label,
              color: "#959595" // default color
            });
          }
          labelId = label.id;
        }

        const created = await client.post<ShoppingListItemsCollectionOut>("/api/households/shopping/items", {
          shoppingListId: options.listId,
          note: options.note,
          display: options.note,
          isFood: false,
          disableAmount: true,
          labelId: labelId
        });
        return created;
      });
    });

  listCmd
    .command("add-recipe")
    .description("Add a recipe's ingredients to a shopping list")
    .requiredOption("--list-id <id>", "ID of the shopping list")
    .requiredOption("--recipe-id <id>", "ID of the recipe to add")
    .action((options) => {
      handleAction(async () => {
        const client = getClient();
        const created = await client.post<ShoppingListOut>(`/api/households/shopping/lists/${options.listId}/recipe`, {
          recipeId: options.recipeId
        });
        return created;
      });
    });
}
