// API client configuration

// Base URL configuration - works in both dev and production
const API_BASE_URL = import.meta.env.DEV 
  ? '/api'  // Proxy to backend in development
  : 'http://localhost:8000/api';  // Direct backend in production

// Generic API request function
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

// API methods
export const api = {
  // Upload file
  async uploadFile(file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    return apiRequest<FileUploadResponse>('/upload', {
      method: 'POST',
      body: formData
    });
  },
  
  // Process query
  async processQuery(request: QueryRequest): Promise<QueryResponse> {
    return apiRequest<QueryResponse>('/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });
  },
  
  // Get database schema
  async getSchema(): Promise<DatabaseSchemaResponse> {
    return apiRequest<DatabaseSchemaResponse>('/schema');
  },
  
  // Generate insights
  async generateInsights(request: InsightsRequest): Promise<InsightsResponse> {
    return apiRequest<InsightsResponse>('/insights', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });
  },
  
  // Health check
  async healthCheck(): Promise<HealthCheckResponse> {
    return apiRequest<HealthCheckResponse>('/health');
  },

  // Image Upload
  async uploadImage(file: File, folderId?: number): Promise<ImageUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (folderId !== undefined) {
      formData.append('folder_id', folderId.toString());
    }

    return apiRequest<ImageUploadResponse>('/images/upload', {
      method: 'POST',
      body: formData
    });
  },

  // List images
  async listImages(folderId?: number, limit: number = 100, offset: number = 0): Promise<ImageListResponse> {
    const params = new URLSearchParams();
    if (folderId !== undefined) {
      params.append('folder_id', folderId.toString());
    }
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

    return apiRequest<ImageListResponse>(`/images?${params.toString()}`);
  },

  // Get image (returns image URL for display)
  getImageUrl(imageId: number): string {
    return `${API_BASE_URL}/images/${imageId}`;
  },

  // Delete image
  async deleteImage(imageId: number): Promise<{ message: string }> {
    return apiRequest(`/images/${imageId}`, {
      method: 'DELETE'
    });
  },

  // Create folder
  async createFolder(folderName: string): Promise<FolderData> {
    return apiRequest<FolderData>('/images/folders', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ folder_name: folderName })
    });
  },

  // List folders
  async listFolders(): Promise<FolderListResponse> {
    return apiRequest<FolderListResponse>('/images/folders');
  },

  // Rename folder
  async renameFolder(folderId: number, newName: string): Promise<{ message: string }> {
    return apiRequest(`/images/folders/${folderId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ folder_id: folderId, new_folder_name: newName })
    });
  },

  // Delete folder
  async deleteFolder(folderId: number): Promise<{ message: string }> {
    return apiRequest(`/images/folders/${folderId}`, {
      method: 'DELETE'
    });
  }
};