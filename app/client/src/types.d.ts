// These must match the Pydantic models exactly

// File Upload Types
interface FileUploadResponse {
  table_name: string;
  table_schema: Record<string, string>;
  row_count: number;
  sample_data: Record<string, any>[];
  error?: string;
}

// Query Types
interface QueryRequest {
  query: string;
  llm_provider: "openai" | "anthropic";
  table_name?: string;
}

interface QueryResponse {
  sql: string;
  results: Record<string, any>[];
  columns: string[];
  row_count: number;
  execution_time_ms: number;
  error?: string;
}

// Database Schema Types
interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
  primary_key: boolean;
}

interface TableSchema {
  name: string;
  columns: ColumnInfo[];
  row_count: number;
  created_at: string;
}

interface DatabaseSchemaResponse {
  tables: TableSchema[];
  total_tables: number;
  error?: string;
}

// Insights Types
interface InsightsRequest {
  table_name: string;
  column_names?: string[];
}

interface ColumnInsight {
  column_name: string;
  data_type: string;
  unique_values: number;
  null_count: number;
  min_value?: any;
  max_value?: any;
  avg_value?: number;
  most_common?: Record<string, any>[];
}

interface InsightsResponse {
  table_name: string;
  insights: ColumnInsight[];
  generated_at: string;
  error?: string;
}

// Health Check Types
interface HealthCheckResponse {
  status: "ok" | "error";
  database_connected: boolean;
  tables_count: number;
  version: string;
  uptime_seconds: number;
}

// Image Upload Types
interface ImageUploadResponse {
  image_id: number;
  filename: string;
  file_type: string;
  file_size: number;
  folder_name?: string;
  thumbnail_url?: string;
  error?: string;
}

interface ImageMetadata {
  id: number;
  filename: string;
  original_name: string;
  file_type: string;
  file_size: number;
  folder_id?: number;
  folder_name?: string;
  upload_date: string;
}

interface ImageListResponse {
  images: ImageMetadata[];
  total_count: number;
  error?: string;
}

// Folder Management Types
interface FolderCreateRequest {
  folder_name: string;
}

interface FolderData {
  id: number;
  folder_name: string;
  image_count: number;
  created_at: string;
  updated_at: string;
}

interface FolderListResponse {
  folders: FolderData[];
  error?: string;
}

interface FolderUpdateRequest {
  folder_id: number;
  new_folder_name: string;
}