import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from "axios";
import * as dotenv from "dotenv";

dotenv.config();

export class MealieApiError extends Error {
  public statusCode: number | undefined;
  public responseData: unknown;

  constructor(message: string, statusCode?: number, responseData?: unknown) {
    super(message);
    this.name = "MealieApiError";
    this.statusCode = statusCode;
    this.responseData = responseData;
  }
}

export class MealieClient {
  private client: AxiosInstance;

  constructor(baseURL?: string, apiKey?: string) {
    const url = baseURL || process.env.MEALIE_URL;
    const token = apiKey || process.env.MEALIE_API_KEY;

    if (!url) {
      throw new Error("Mealie base URL is not configured. Set MEALIE_URL environment variable.");
    }

    if (!token) {
      throw new Error("Mealie API key is not configured. Set MEALIE_API_KEY environment variable.");
    }

    this.client = axios.create({
      baseURL: url,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      timeout: parseInt(process.env.MEALIE_TIMEOUT || "60000", 10),
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response) {
          throw new MealieApiError(
            `API Error: ${error.message}`,
            error.response.status,
            error.response.data
          );
        } else if (error.request) {
          throw new MealieApiError(
            `Network Error: Request to ${error.config?.url} failed. ${error.message}`,
            undefined,
            { config: error.config, code: error.code }
          );
        } else {
          throw new MealieApiError(`Request Setup Error: ${error.message}`);
        }
      }
    );
  }

  public async get<T = unknown>(url: string, params?: Record<string, unknown>): Promise<T> {
    const response = await this.client.get<T>(url, { params });
    return response.data;
  }

  public async post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  public async put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  public async patch<T = unknown>(url: string, data?: unknown): Promise<T> {
    const response = await this.client.patch<T>(url, data);
    return response.data;
  }

  public async delete<T>(url: string): Promise<T> {
    const response = await this.client.delete<T>(url);
    return response.data;
  }
}

let defaultClient: MealieClient | null = null;

export function getClient(): MealieClient {
  if (!defaultClient) {
    defaultClient = new MealieClient();
  }
  return defaultClient;
}
