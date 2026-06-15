import { z } from "zod";

export const AgentIngredientSchema = z.union([
  z.string(),
  z.object({
    note: z.string().optional(),
    quantity: z.number().optional().nullable(),
    unit: z.object({
      name: z.string().optional(),
      description: z.string().optional(),
      fraction: z.boolean().optional(),
      abbreviation: z.string().optional()
    }).optional().nullable(),
    food: z.object({
      name: z.string().optional(),
      description: z.string().optional()
    }).optional().nullable(),
    display: z.string().optional(),
    title: z.string().optional().nullable(),
    originalText: z.string().optional().nullable()
  })
]);

export const AgentInstructionSchema = z.union([
  z.string(),
  z.object({
    section: z.string().optional(),
    title: z.string().optional(),
    text: z.string(),
    ingredientIndices: z.array(z.number()).optional()
  })
]);

export const AgentRecipeSchema = z.object({
  name: z.string(),
  description: z.string().optional(),
  orgURL: z.string().optional(),
  image: z.string().optional(),
  prepTime: z.string().optional(),
  cookTime: z.string().optional(),
  totalTime: z.string().optional(),
  performTime: z.string().optional(),
  recipeYield: z.string().optional(),
  recipeServings: z.number().optional(),
  tags: z.array(z.string()).optional(),
  categories: z.array(z.string()).optional(),
  tools: z.array(z.string()).optional(),
  ingredients: z.array(AgentIngredientSchema).optional(),
  instructions: z.array(AgentInstructionSchema).optional(),
});

export type AgentRecipe = z.infer<typeof AgentRecipeSchema>;
