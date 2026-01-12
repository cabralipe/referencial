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
    const response = await clientGet<PaginatedResponse<T>>(next, first ? options : undefined);
    results.push(...(response.data.results ?? []));
    next = response.data.next;
    page += 1;
    first = false;
  }

  return results;
}
