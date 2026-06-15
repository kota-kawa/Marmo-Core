import { Command } from "commander";
import { getClient } from "../api";
import { handleAction, ensureOrganizer } from "../utils";
import { TagOut, CategoryOut, RecipeToolOut } from "../models/types";

export function setupOrganizerCommands(program: Command) {
  const tagCmd = program.command("tag").description("Manage tags");
  
  tagCmd
    .command("ensure")
    .description("Ensure a tag exists, creates it if it does not")
    .requiredOption("--name <name>", "Name of the tag")
    .action((options) => {
      handleAction(async () => {
        const client = getClient();
        return await ensureOrganizer<TagOut>(client, "/api/organizers/tags", options.name);
      });
    });

  const categoryCmd = program.command("category").description("Manage categories");

  categoryCmd
    .command("ensure")
    .description("Ensure a category exists, creates it if it does not")
    .requiredOption("--name <name>", "Name of the category")
    .action((options) => {
      handleAction(async () => {
        const client = getClient();
        return await ensureOrganizer<CategoryOut>(client, "/api/organizers/categories", options.name);
      });
    });

  const toolCmd = program.command("tool").description("Manage tools");

  toolCmd
    .command("ensure")
    .description("Ensure a tool exists, creates it if it does not")
    .requiredOption("--name <name>", "Name of the tool")
    .action((options) => {
      handleAction(async () => {
        const client = getClient();
        return await ensureOrganizer<RecipeToolOut>(client, "/api/organizers/tools", options.name);
      });
    });
}
