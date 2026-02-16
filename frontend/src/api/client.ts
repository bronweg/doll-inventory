// Use runtime configuration from window object, fall back to build-time env var, then relative URL
const API_BASE_URL = (window as any).__API_BASE_URL__ || import.meta.env.VITE_API_BASE_URL || '';

export interface ApiError {
  message: string;
  status?: number;
}

export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...options?.headers,
      },
    });

    if (!response.ok) {
      // Try to parse error message from response body
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          if (errorData.detail) {
            errorMessage = errorData.detail;
          }
        }
      } catch {
        // Ignore JSON parsing errors for error responses
      }

      const error: ApiError = {
        message: errorMessage,
        status: response.status,
      };
      throw error;
    }

    // Handle 204 No Content (successful DELETE, etc.)
    if (response.status === 204) {
      return null as T;
    }

    // Handle responses with JSON content
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }

    // Handle other successful responses with no content
    return null as T;
  } catch (error) {
    if ((error as ApiError).status) {
      throw error;
    }
    throw {
      message: 'Network error. Please check your connection.',
    } as ApiError;
  }
}

export function getMediaUrl(path: string | null): string {
  if (!path) return '';
  return `${API_BASE_URL}${path}`;
}

export const BAGS_COUNT = (window as any).__BAGS_COUNT__ || parseInt(import.meta.env.VITE_BAGS_COUNT || '3', 10);

