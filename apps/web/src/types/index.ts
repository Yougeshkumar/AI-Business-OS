/** Shared frontend types. */

export interface ResponseMeta {
  request_id: string;
  trace_id: string;
  timestamp: string;
}

export interface Paginated<T> {
  data: T[];
  meta: ResponseMeta;
  pagination: {
    cursor: string | null;
    has_more: boolean;
    total_count: number | null;
  };
}
