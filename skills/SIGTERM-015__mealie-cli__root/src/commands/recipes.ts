import { Command } from "commander";
import { getClient } from "../api";
import { handleAction, ensureOrganizer } from "../utils";
import * as fs from "fs";
import * as path from "path";
import FormData from "form-data";
import * as crypto from "crypto";
import { AgentRecipeSchema } from "../models/schema";
import { RecipeInput, RecipeOutput, TagOut, CategoryOut, RecipeToolOut, PaginatedResponse, IngredientUnitInput, IngredientFoodInput, RecipeIngredientInput, RecipeStep, RecipeTag, RecipeCategory, RecipeTool } from "../models/types";

import { tagToRecipeTag, categoryToRecipeCategory, toolToRecipeTool } from "../utils/mappers";

export function setupRecipeCommands(program: Command) {
  const recipeCmd = program.command("recipe").description("Manage recipes");

  recipeCmd
    .command("create")
    .description("Create a recipe using the Agent JSON schema")
    .requiredOption("--data <path>", "Path to the JSON file or JSON string")
    .action((options) => {
      handleAction(async () => {
        let inputData: unknown;

        try {
          // Check if data is a file path or direct JSON
          const trimmedData = options.data.trim();
          if (trimmedData.startsWith("{")) {
            inputData = JSON.parse(trimmedData);
          } else if (fs.existsSync(options.data)) {
            const fileContent = fs.readFileSync(options.data, "utf8");
            inputData = JSON.parse(fileContent);
          } else {
            inputData = JSON.parse(options.data);
          }
        } catch (e: unknown) {
          throw new Error(`Failed to parse input data: ${(e as Error).message}`);
        }

        // Validate using Zod
        const result = AgentRecipeSchema.safeParse(inputData);
        if (!result.success) {
          throw new Error(`Validation Error: ${result.error.message}`);
        }

        const agentRecipe = result.data;
        const client = getClient();

        // 1. Create base recipe to get slug
        const initialSlug = await client.post<string>("/api/recipes", {
          name: agentRecipe.name,
        });

        // 2. Get the full recipe skeleton
        const recipeData = await client.get<RecipeInput>(`/api/recipes/${initialSlug}`);

        if (!recipeData.slug) {
          throw new Error(`Recipe skeleton missing required field: slug`);
        }

        // 3. Populate the skeleton with Agent data
        if (agentRecipe.description) recipeData.description = agentRecipe.description;
        if (agentRecipe.orgURL) recipeData.orgURL = agentRecipe.orgURL;
        if (agentRecipe.prepTime) recipeData.prepTime = agentRecipe.prepTime;
        if (agentRecipe.totalTime) recipeData.totalTime = agentRecipe.totalTime;
        
        // Mealie UI quirk: The "Cook time" shown in the UI is actually the `performTime` field in the API
        if (agentRecipe.cookTime) {
          recipeData.performTime = agentRecipe.cookTime;
        }
        if (agentRecipe.recipeYield) recipeData.recipeYield = agentRecipe.recipeYield;
        if (agentRecipe.recipeServings !== undefined) recipeData.recipeServings = agentRecipe.recipeServings;

        // Ensure tags, categories, tools
        if (agentRecipe.tags && agentRecipe.tags.length > 0) {
          const resolvedTags = await Promise.all(
            agentRecipe.tags.map(t => ensureOrganizer<TagOut>(client, "/api/organizers/tags", t))
          );
          const validTags = resolvedTags.filter(Boolean);
          if (validTags.length !== agentRecipe.tags.length) {
            console.error(`Warning: Only ${validTags.length}/${agentRecipe.tags.length} tags were resolved`);
          }
          recipeData.tags = validTags.map(tagToRecipeTag);
        } else if (agentRecipe.tags && agentRecipe.tags.length === 0) {
          recipeData.tags = [];
        }

        if (agentRecipe.categories && agentRecipe.categories.length > 0) {
          const resolvedCats = await Promise.all(
            agentRecipe.categories.map(c => ensureOrganizer<CategoryOut>(client, "/api/organizers/categories", c))
          );
          const validCats = resolvedCats.filter(Boolean);
          if (validCats.length !== agentRecipe.categories.length) {
            console.error(`Warning: Only ${validCats.length}/${agentRecipe.categories.length} categories were resolved`);
          }
          recipeData.recipeCategory = validCats.map(categoryToRecipeCategory);
        } else if (agentRecipe.categories && agentRecipe.categories.length === 0) {
          recipeData.recipeCategory = [];
        }

        if (agentRecipe.tools && agentRecipe.tools.length > 0) {
          const resolvedTools = await Promise.all(
            agentRecipe.tools.map(t => ensureOrganizer<RecipeToolOut>(client, "/api/organizers/tools", t))
          );
          const validTools = resolvedTools.filter(Boolean);
          if (validTools.length !== agentRecipe.tools.length) {
            console.error(`Warning: Only ${validTools.length}/${agentRecipe.tools.length} tools were resolved`);
          }
          recipeData.tools = validTools.map(toolToRecipeTool);
        } else if (agentRecipe.tools && agentRecipe.tools.length === 0) {
          recipeData.tools = [];
        }

        // Map ingredients and instructions
        const ingredientIds: string[] = [];
        if (agentRecipe.ingredients) {
          recipeData.recipeIngredient = await Promise.all(
            agentRecipe.ingredients.map(async (ing) => {
              const id = crypto.randomUUID();
              
              const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
              if (!uuidRegex.test(id)) {
                throw new Error(`Generated invalid UUID: ${id}`);
              }
              
              ingredientIds.push(id);
              if (typeof ing === "string") {
                return {
                  referenceId: id,
                  note: ing,
                } as RecipeIngredientInput;
              } else {
                const ingObj: Partial<RecipeIngredientInput> = {
                  referenceId: id,
                  note: ing.note || "",
                };
                if (ing.quantity !== undefined && ing.quantity !== null) ingObj.quantity = ing.quantity;
                if (ing.display) ingObj.display = ing.display;
                if (ing.title) ingObj.title = ing.title;
                if (ing.originalText) ingObj.originalText = ing.originalText;
                
                if (ing.unit && ing.unit.name) {
                  const extraData = {
                    description: ing.unit.description || "",
                    fraction: ing.unit.fraction ?? true,
                    abbreviation: ing.unit.abbreviation || ""
                  };
                  const resolvedUnit = await ensureOrganizer<IngredientUnitInput>(client, "/api/units", ing.unit.name, extraData);
                  if (resolvedUnit) ingObj.unit = resolvedUnit as unknown as IngredientUnitInput;
                }
                
                if (ing.food && ing.food.name) {
                  const extraData = {
                    description: ing.food.description || ""
                  };
                  const resolvedFood = await ensureOrganizer<IngredientFoodInput>(client, "/api/foods", ing.food.name, extraData);
                  if (resolvedFood) ingObj.food = resolvedFood as unknown as IngredientFoodInput;
                }
                
                return ingObj as RecipeIngredientInput;
              }
            })
          );
        }

        if (agentRecipe.instructions) {
          recipeData.recipeInstructions = agentRecipe.instructions.map((inst) => {
            if (typeof inst === "string") {
              return { title: "", summary: "", text: inst, ingredientReferences: [] } as unknown as RecipeStep;
            } else {
              const refs = inst.ingredientIndices
                ? inst.ingredientIndices
                    .filter((idx) => Number.isInteger(idx) && idx >= 0 && idx < ingredientIds.length)
                    .map((idx) => ({ referenceId: ingredientIds[idx] }))
                : [];
                
              const refIds = new Set(refs.map(r => r.referenceId));
              if (refIds.size !== refs.length) {
                console.warn(`Warning: Duplicate ingredient references in instruction: "${inst.text || ''}"`);
              }

              return {
                title: inst.section || "",
                summary: inst.title || "",
                text: inst.text,
                ingredientReferences: refs,
              } as unknown as RecipeStep;
            }
          });
        }

        // 4. Update the recipe with the populated data
        const updatedRecipe = await client.put<RecipeOutput>(
          `/api/recipes/${initialSlug}`,
          recipeData
        );

        // 5. Upload image if provided
        if (agentRecipe.image) {
          const imagePath = path.resolve(agentRecipe.image);
          if (fs.existsSync(imagePath)) {
            const formData = new FormData();
            let imageStream: fs.ReadStream | undefined;

            try {
              imageStream = fs.createReadStream(imagePath);
              formData.append("image", imageStream);
              formData.append("extension", path.extname(imagePath).replace(".", ""));

              await client.put(`/api/recipes/${updatedRecipe.slug || initialSlug}/image`, formData, {
                headers: {
                  ...formData.getHeaders(),
                },
              });
            } catch (imgError: unknown) {
              throw new Error(`Failed to upload image: ${(imgError as Error).message}`);
            } finally {
              if (imageStream) {
                imageStream.destroy();
              }
            }
          } else {
            throw new Error(`Image file not found at path: ${imagePath}`);
          }
        }

        return updatedRecipe;
      });
    });

  recipeCmd
    .command("get")
    .description("Get a recipe by slug")
    .requiredOption("--slug <slug>", "Slug of the recipe")
    .option("--concise", "Return a concise version of the recipe (omit heavy fields)")
    .action((options) => {
      handleAction(async () => {
        const client = getClient();
        const recipe = await client.get<RecipeOutput>(`/api/recipes/${options.slug}`);

        if (options.concise) {
          return {
            name: recipe.name,
            slug: recipe.slug,
            description: recipe.description,
            recipeYield: recipe.recipeYield,
            recipeServings: recipe.recipeServings,
            totalTime: recipe.totalTime,
            prepTime: recipe.prepTime,
            cookTime: recipe.performTime, // Map Mealie's performTime to Cook Time
            performTime: recipe.performTime,
            tags: recipe.tags,
            categories: recipe.recipeCategory,
            tools: recipe.tools,
            ingredients: recipe.recipeIngredient,
            instructions: recipe.recipeInstructions,
          };
        }

        return recipe;
      });
    });

  recipeCmd
    .command("search")
    .description("Search recipes with filters")
    .option("--query <query>", "Search query for name or description")
    .option("--tags <tags>", "Comma-separated tags")
    .option("--categories <categories>", "Comma-separated categories")
    .option("--tools <tools>", "Comma-separated tools")
    .option("--foods <foods>", "Comma-separated foods (ingredients)")
    .option("--require-all", "If set, recipes must have ALL specified tags/categories/tools instead of ANY")
    .action((options) => {
      handleAction(async () => {
        const client = getClient();
        const params: Record<string, unknown> = {};
        
        if (options.query) params.search = options.query;
        if (options.tags) params.tags = options.tags.split(",");
        if (options.categories) params.categories = options.categories.split(",");
        if (options.tools) params.tools = options.tools.split(",");
        if (options.foods) params.foods = options.foods.split(",");
        
        if (options.requireAll) {
          if (options.tags) params.requireAllTags = true;
          if (options.categories) params.requireAllCategories = true;
          if (options.tools) params.requireAllTools = true;
          if (options.foods) params.requireAllFoods = true;
        }

        const recipes = await client.get<PaginatedResponse<RecipeOutput>>("/api/recipes", params);
        return recipes; // Returns paginated result
      });
    });
}
