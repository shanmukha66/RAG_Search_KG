import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export interface QueryRequest {
  text: string;
  type: 'factual' | 'summarization' | 'semantic_linkage' | 'reasoning';
  filters?: Record<string, any>;
  modalities?: string[];
}

export interface QueryResponse {
  answer: string;
  confidence: number;
  sources: Array<{
    title: string;
    type: string;
    relevance: number;
    content?: string;
  }>;
  cross_references: Array<{
    text: string;
    source: string;
    confidence: number;
  }>;
  evaluation: {
    relevancy: number;
    coherence: number;
    factual_accuracy: number;
  };
}

const api = {
  // File Upload
  uploadFile: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Query Processing
  processQuery: async (query: QueryRequest): Promise<QueryResponse> => {
    const response = await axios.post(`${API_BASE_URL}/query`, query);
    return response.data;
  },

  // Health Check
  checkHealth: async () => {
    const response = await axios.get(`${API_BASE_URL}/health`);
    return response.data;
  },
};

export default api; 