#!/usr/bin/env node

import { Command } from "commander";
import { setupOrganizerCommands } from "./commands/organizers";
import { setupRecipeCommands } from "./commands/recipes";
import { setupShoppingListCommands } from "./commands/shopping-lists";
import { setupMealPlanCommands } from "./commands/meal-plans";

const pkg = require("../package.json");
const program = new Command();

program
  .name("mealie")
  .description("CLI for Mealie API designed for AI Agents")
  .version(pkg.version);

setupOrganizerCommands(program);
setupRecipeCommands(program);
setupShoppingListCommands(program);
setupMealPlanCommands(program);

program.parse(process.argv);
