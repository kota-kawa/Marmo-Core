import { components } from "./api";

export type Schema<T extends keyof components["schemas"]> = components["schemas"][T];

export type RecipeInput = Schema<"Recipe-Input">;
export type RecipeOutput = Schema<"Recipe-Output">;
export type RecipeIngredientInput = Schema<"RecipeIngredient-Input">;
export type RecipeStep = Schema<"RecipeStep">;
export type ShoppingListOut = Schema<"ShoppingListOut">;
export type ShoppingListPagination = Schema<"ShoppingListPagination">;
export type ShoppingListItemsCollectionOut = Schema<"ShoppingListItemsCollectionOut">;
export type MultiPurposeLabelOut = Schema<"MultiPurposeLabelOut">;
export type TagOut = Schema<"TagOut">;
export type CategoryOut = Schema<"CategoryOut">;
export type RecipeToolOut = Schema<"RecipeToolOut">;
export type CreatePlanEntry = Schema<"CreatePlanEntry">;
export type ReadPlanEntry = Schema<"ReadPlanEntry">;
export type IngredientUnitInput = Schema<"IngredientUnit-Input">;
export type IngredientFoodInput = Schema<"IngredientFood-Input">;
export type PaginatedResponse<T> = {
  items?: T[];
  page?: number;
  per_page?: number;
  total?: number;
  total_pages?: number;
  next?: string | null;
  previous?: string | null;
};

export type RecipeTag = Schema<"RecipeTag">;
export type RecipeCategory = Schema<"RecipeCategory">;
export type RecipeTool = Schema<"RecipeTool">;