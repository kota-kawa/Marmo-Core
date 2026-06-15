import { MealieClient, MealieApiError } from "../api";
import { PaginatedResponse } from "../models/types";

export function outputSuccess(data: unknown): void {
  console.log(JSON.stringify({ status: "success", data }, null, 2));
}

export function outputError(message: string, details?: unknown): void {
  const output: Record<string, unknown> = { status: "error", message };
  if (details !== undefined) {
    output.details = details;
  }
  console.log(JSON.stringify(output, null, 2));
  process.exitCode = 1;
}

export function extractItems<T>(response: PaginatedResponse<T> | T[] | unknown): T[] {
  if (Array.isArray(response)) return response as T[];
  if (response && typeof response === "object" && "items" in response) {
    const paginated = response as PaginatedResponse<T>;
    return Array.isArray(paginated.items) ? paginated.items : [];
  }
  return [];
}

export async function ensureOrganizer<T extends { name: string }>(client: MealieClient, endpoint: string, name: string, extraData: Record<string, unknown> = {}): Promise<T> {
  const res = await client.get<PaginatedResponse<T> | T[]>(endpoint, { search: name });
  const items = extractItems<T>(res);
  let found = items.find((i) => i.name.toLowerCase() === name.toLowerCase());

  if (!found) {
    try {
      found = await client.post<T>(endpoint, { name, ...extraData });
    } catch (e) {
      const apiError = e as MealieApiError;
      // Solo reintentar si es un posible race condition (409 conflict o 500)
      if (apiError.statusCode === 409 || (apiError.statusCode && apiError.statusCode >= 500)) {
        const res2 = await client.get<PaginatedResponse<T> | T[]>(endpoint, { search: name });
        const items2 = extractItems<T>(res2);
        found = items2.find((i) => i.name.toLowerCase() === name.toLowerCase());
      }
      
      if (!found) {
        throw new Error(`Failed to create or find organizer: ${name}. API Error: ${apiError.message}`);
      }
    }
  }

  return found;
}

export function handleAction<T>(action: () => Promise<T>): Promise<void> {
  return action()
    .then((data) => {
      outputSuccess(data);
    })
    .catch((error: unknown) => {
      if (error instanceof MealieApiError) {
        outputError(error.message, {
          statusCode: error.statusCode,
          responseData: error.responseData,
        });
      } else if (error instanceof Error) {
        outputError(error.message, error.stack);
      } else {
        outputError("An unexpected error occurred", String(error));
      }
    });
}
