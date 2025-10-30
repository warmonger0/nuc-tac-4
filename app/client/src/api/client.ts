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

  // Image upload methods
  async uploadImages(files: FileList, folder: string = 'default'): Promise<ImageUploadResponse[]> {
    const formData = new FormData();

    // Append all files
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    return apiRequest<ImageUploadResponse[]>(`/images/upload?folder=${encodeURIComponent(folder)}`, {
      method: 'POST',
      body: formData
    });
  },

  async getImages(folder?: string): Promise<ImageListResponse> {
    const endpoint = folder ? `/images?folder=${encodeURIComponent(folder)}` : '/images';
    return apiRequest<ImageListResponse>(endpoint);
  },

  getImageUrl(imageId: string): string {
    return `${API_BASE_URL}/images/${imageId}`;
  },

  async deleteImage(imageId: string): Promise<{ message: string }> {
    return apiRequest<{ message: string }>(`/images/${imageId}`, {
      method: 'DELETE'
    });
  },

  // Duplicate check method
  async checkDuplicate(file: File, folder: string = 'default'): Promise<DuplicateCheckResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return apiRequest<DuplicateCheckResponse>(`/images/check-duplicate?folder=${encodeURIComponent(folder)}`, {
      method: 'POST',
      body: formData
    });
  },

  // Folder management methods
  async getFolders(): Promise<FolderListResponse> {
    return apiRequest<FolderListResponse>('/folders');
  },

  async createFolder(folderName: string): Promise<FolderOperationResponse> {
    return apiRequest<FolderOperationResponse>('/folders', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ folder_name: folderName })
    });
  },

  async renameFolder(oldName: string, newName: string): Promise<FolderOperationResponse> {
    return apiRequest<FolderOperationResponse>(`/folders/${encodeURIComponent(oldName)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ old_name: oldName, new_name: newName })
    });
  },

  async deleteFolder(folderName: string): Promise<FolderOperationResponse> {
    return apiRequest<FolderOperationResponse>(`/folders/${encodeURIComponent(folderName)}`, {
      method: 'DELETE'
    });
  }
};