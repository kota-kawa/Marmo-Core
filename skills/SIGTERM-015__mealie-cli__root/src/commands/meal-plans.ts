import { Command } from "commander";
import { getClient } from "../api";
import { handleAction } from "../utils";
import { CreatePlanEntry, ReadPlanEntry, RecipeOutput } from "../models/types";

export function setupMealPlanCommands(program: Command) {
  const planCmd = program.command("meal-plan").description("Manage meal plans");

  planCmd
    .command("create")
    .description("Create a meal plan entry")
    .requiredOption("--date <date>", "Date in YYYY-MM-DD format")
    .option("--entry-type <type>", "Type of meal (breakfast, lunch, dinner, side, snack, drink, dessert)", "dinner")
    .option("--recipe-slug <slug>", "Slug of the recipe to add to the meal plan")
    .option("--title <title>", "Title of the entry (if no recipe)")
    .option("--text <text>", "Text description of the entry (if no recipe)")
    .action((options) => {
      handleAction(async () => {
        if (!/^\d{4}-\d{2}-\d{2}$/.test(options.date) || isNaN(Date.parse(options.date))) {
          throw new Error("Invalid date format. Please use a valid YYYY-MM-DD format.");
        }

        const client = getClient();
        let recipeId: string | null | undefined = null;

        if (options.recipeSlug) {
          const recipe = await client.get<RecipeOutput>(`/api/recipes/${options.recipeSlug}`);
          recipeId = recipe.id;
        }

        const payload: Partial<CreatePlanEntry> = {
          date: options.date,
          entryType: options.entryType,
        };

        if (recipeId) {
          payload.recipeId = recipeId;
        } else {
          payload.title = options.title || "";
          payload.text = options.text || "";
        }

        const created = await client.post<CreatePlanEntry>("/api/households/mealplans", payload);
        return created;
      });
    });

  planCmd
    .command("today")
    .description("Get today's meal plan")
    .action(() => {
      handleAction(async () => {
        const client = getClient();
        const plan = await client.get<ReadPlanEntry[]>("/api/households/mealplans/today");
        return plan;
      });
    });
}
