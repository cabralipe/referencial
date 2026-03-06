import { API_BASE_URL } from '@/config/env';
import type { ApiResponse, RequestOptions } from '@/api/client';
import type { PaginatedResponse } from '@/api/types';

type ClientGet = <T>(path: string, options?: RequestOptions) => Promise<ApiResponse<T>>;

export async function fetchAllPaginated<T>(
  clientGet: ClientGet,
  path: string,
  options?: RequestOptions,
  maxPages = 20,
): Promise<T[]> {
  const results: T[] = [];
  let next: string | null = path;
  let page = 0;
  let first = true;

  while (next && page < maxPages) {
    // Prevent hitting direct backend origins to keep requests routed to the Vite proxy where headers load correctly.
    let targetPath: string = next;
    if (targetPath.startsWith('http')) {
      try {
        const urlObj = new URL(targetPath);
        // Extracts whatever trail paths are set after API_BASE_URL: (e.g., http://127.0.0.1:8000/api/v1/respostas?page=2 -> /respostas?page=2)
        targetPath = urlObj.pathname + urlObj.search;
        if (API_BASE_URL && targetPath.startsWith(API_BASE_URL)) {
          targetPath = targetPath.slice(API_BASE_URL.length);
        }
      } catch (e) {
        // Fallback silently if URL parse somehow fails
      }
    }

    const response = await clientGet<PaginatedResponse<T>>(targetPath, first ? options : undefined);
    results.push(...(response.data.results ?? []));
    next = response.data.next;
    page += 1;
    first = false;
  }

  return results;
}
