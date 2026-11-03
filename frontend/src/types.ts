export type Cell = string | number | boolean | null;
export type Row = Record<string, Cell>;
export type FieldKind = 'date' | 'price' | 'payment' | 'rate' | 'arithmetic_return' | 'geometric_return' | 'pnl' | 'loss' | 'other';
export interface Field { kind: FieldKind; unit: 'decimal' | 'percent' | 'amount' | 'date' | 'other'; sign: 'profit' | 'loss' | 'none' }
export interface Metadata { fields?: Record<string, Field>; [key: string]: unknown }
export interface Dataset { id: string; name: string; description?: string; row_count: number; column_count: number; created_at?: string; archived: boolean; metadata: Metadata; columns?: string[]; rows?: Row[]; total_rows?: number }
export interface Preview { id: string; columns: string[]; rows: Row[]; row_count: number; metadata: Metadata; sheets?: string[]; changes?: { before_rows: number; after_rows: number; dropped_rows: number; added_columns: string[] } }
export interface ResultTable { name: string; columns: string[]; rows: Row[] }
export interface ChartData { title: string; x_label?: string; y_label?: string; series: { name: string; type: 'line' | 'bar' | 'scatter'; data: [number | string, number | null][] }[]; markers?: { name: string; value: number }[]; areas?: { from: number; to: number }[] }
export interface Result { metrics: { name: string; value: number | string | null; unit?: string }[]; tables: ResultTable[]; charts: ChartData[]; notes: string[] }
export interface CalculationRequest { dataset_id: string; operation: string; parameters: Record<string, unknown> }
export interface Job extends CalculationRequest { id: string; status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'; progress?: number | null; error?: string; result?: Result; record_id?: string }
export interface SavedRecord { id: string; name: string; dataset_id: string; operation: string; created_at?: string; archived: boolean; request?: CalculationRequest; result?: Result; legacy?: boolean }
export interface Parameter { name: string; label: string; type: 'select' | 'number' | 'column'; default?: unknown; options?: { value: string; label: string }[]; min?: number; max?: number }
export interface Operation { id: string; name: string; workspace: string; description: string; formula: string; pages: string; assumptions: string[] | string; parameters: Parameter[] }
export interface Catalog { chapters: { number: number; title: string; pages: string; available: boolean }[]; operations: Operation[] }
export interface Example { id: string; name: string; description: string }
export interface Page<T> { items: T[]; total: number }
