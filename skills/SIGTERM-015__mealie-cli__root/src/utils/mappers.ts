import { TagOut, CategoryOut, RecipeToolOut, RecipeTag, RecipeCategory, RecipeTool } from "../models/types";

export function tagToRecipeTag(tag: TagOut): RecipeTag {
  return {
    id: tag.id,
    name: tag.name,
    slug: tag.slug,
    groupId: tag.groupId,
  };
}

export function categoryToRecipeCategory(cat: CategoryOut): RecipeCategory {
  return {
    id: cat.id,
    name: cat.name,
    slug: cat.slug,
    groupId: cat.groupId,
  };
}

export function toolToRecipeTool(tool: RecipeToolOut): RecipeTool {
  return {
    id: tool.id,
    name: tool.name,
    // Note: the schema doesn't define slug/groupId strictly on RecipeTool but this structure conforms to what it allows via duck typing if needed, 
    // although based on the previous grep it only had id, name, groupId, slug
  } as RecipeTool; // doing casting if properties differ but let's see.
}