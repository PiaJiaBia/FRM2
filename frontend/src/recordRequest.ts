import type { CalculationRequest, Catalog, SavedRecord } from './types';

/** Persisted records may predate the browser contract. Only restore known, shaped requests. */
export function recordRequest(record: SavedRecord | undefined, catalog: Catalog | undefined): CalculationRequest | undefined {
  const request = record?.request;
  if (!record || record.legacy || !catalog || !request || typeof request !== 'object' || Array.isArray(request)) return undefined;
  if (!('dataset_id' in request) || typeof request.dataset_id !== 'string' || !request.dataset_id.trim()) return undefined;
  if (!('operation' in request) || typeof request.operation !== 'string' || !catalog.operations.some(item => item.id === request.operation)) return undefined;
  if (!('parameters' in request) || !request.parameters || typeof request.parameters !== 'object' || Array.isArray(request.parameters)) return undefined;
  return { dataset_id: request.dataset_id, operation: request.operation, parameters: request.parameters as Record<string, unknown> };
}
