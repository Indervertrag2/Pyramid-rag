import apiClient from './apiClient';

export interface ApiChatSession {
  id: string;
  title: string;
  folder_path: string | null;
  chat_type: string;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ApiRetrievedDocument {
  id?: string;
  document_id?: string;
  title?: string;
  scope?: string;
  source?: string;
  content?: string;
  content_preview?: string;
  mime_type?: string;
  chunk_id?: string;
  score?: number;
  [key: string]: unknown;
}

export interface ApiChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  meta_data?: {
    use_rag?: boolean;
    retrieved_documents?: ApiRetrievedDocument[];
  };
  created_at: string;
}

export interface CreateSessionRequest {
  title?: string;
  folder_path?: string | null;
  is_temporary?: boolean;
}

export interface UpdateSessionRequest {
  title?: string;
  folder_path?: string | null;
}

export const chatApi = {
  async getSessions(): Promise<ApiChatSession[]> {
    const response = await apiClient.get<ApiChatSession[]>('/api/v1/chat/sessions');
    return response.data;
  },

  async listSessions(): Promise<ApiChatSession[]> {
    return this.getSessions();
  },

  async createSession(data: CreateSessionRequest): Promise<ApiChatSession> {
    const response = await apiClient.post<ApiChatSession>('/api/v1/chat/sessions', data);
    return response.data;
  },

  async updateSession(sessionId: string, data: UpdateSessionRequest): Promise<ApiChatSession> {
    const response = await apiClient.put<ApiChatSession>(`/api/v1/chat/sessions/${sessionId}`, data);
    return response.data;
  },

  async deleteSession(sessionId: string): Promise<void> {
    await apiClient.delete(`/api/v1/chat/sessions/${sessionId}`);
  },

  async getSessionMessages(sessionId: string): Promise<ApiChatMessage[]> {
    const response = await apiClient.get<ApiChatMessage[]>(`/api/v1/chat/sessions/${sessionId}/messages`);
    return response.data;
  },
};
