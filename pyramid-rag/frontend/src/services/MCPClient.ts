/**
 * MCP Client Service for unified AI interactions
 * Handles all communication with the MCP server
 */

export interface MCPMessage {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
  name?: string;
}

export interface ToolCall {
  tool: string;
  parameters: Record<string, any>;
  id?: string;
}

export interface MCPResponse {
  success: boolean;
  messages: MCPMessage[];
  citations?: Citation[];
  metadata?: Record<string, any>;
  error?: string;
}

export interface Citation {
  document_id: string;
  document_title: string;
  chunk_id?: string;
  relevance_score: number;
  snippet: string;
}

export interface MCPToolsResponse {
  tools: Record<string, MCPToolDefinition>;
}

export interface MCPToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, any>;
  returns: Record<string, any>;
}

class MCPClient {
  private baseUrl: string;
  private token: string | null;

  constructor(baseUrl: string = 'http://localhost:18000') {
    this.baseUrl = baseUrl;
    this.token = localStorage.getItem('access_token');
  }

  /**
   * Stream a message response using Server-Sent Events
   */
  async streamMessage(
    content: string,
    options: {
      tools?: string[];
      rag_enabled?: boolean;
      session_id?: string;
      department?: string;
      uploaded_documents?: any[];
      onChunk?: (chunk: string) => void;
      onComplete?: () => void;
      onError?: (error: string) => void;
    } = {}
  ): Promise<void> {
    // Since EventSource doesn't support POST with custom headers, we'll use fetch with ReadableStream
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/mcp/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify({
          messages: [{
            role: 'user',
            content
          }],
          tools: options.tools || ['chat'],
          session_id: options.session_id,
          context: {
            rag_enabled: options.rag_enabled ?? true,
            department: options.department,
            uploaded_documents: options.uploaded_documents
          }
        })
      });

      if (!response.ok) {
        throw new Error(`Stream request failed: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          if (options.onComplete) {
            options.onComplete();
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Process SSE messages
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.chunk && options.onChunk) {
                options.onChunk(data.chunk);
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          } else if (line.startsWith('event: ')) {
            const event = line.slice(7);
            if (event === 'error' && options.onError) {
              options.onError('Stream error');
            } else if (event === 'done' && options.onComplete) {
              options.onComplete();
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream error:', error);
      if (options.onError) {
        options.onError(error instanceof Error ? error.message : 'Unknown error');
      }
    }
  }

  /**
   * Send a message through MCP with optional tool selection
   */
  async sendMessage(
    content: string,
    options: {
      tools?: string[];
      rag_enabled?: boolean;
      session_id?: string;
      department?: string;
      uploaded_documents?: any[];
    } = {}
  ): Promise<MCPResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/mcp/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify({
          messages: [{
            role: 'user',
            content
          }],
          tools: options.tools || ['chat'],
          session_id: options.session_id,
          context: {
            rag_enabled: options.rag_enabled ?? true,
            department: options.department,
            uploaded_documents: options.uploaded_documents
          }
        })
      });

      if (!response.ok) {
        throw new Error(`MCP request failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('MCP Client Error:', error);
      return {
        success: false,
        messages: [],
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Execute a specific MCP tool directly
   */
  async executeTool(
    tool: string,
    parameters: Record<string, any>
  ): Promise<MCPResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/mcp/tools/${tool}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify({
          tool,
          parameters
        })
      });

      if (!response.ok) {
        throw new Error(`Tool execution failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('MCP Tool Error:', error);
      return {
        success: false,
        messages: [],
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Search documents using hybrid search
   */
  async searchDocuments(
    query: string,
    options: {
      limit?: number;
      department?: string;
      threshold?: number;
    } = {}
  ): Promise<MCPResponse> {
    return this.executeTool('hybrid_search', {
      query,
      limit: options.limit || 5,
      department: options.department,
      threshold: options.threshold || 0.5
    });
  }

  /**
   * Get available MCP tools
   */
  async getAvailableTools(): Promise<MCPToolsResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/mcp/tools`, {
        headers: {
          'Authorization': `Bearer ${this.token}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to get tools: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Get tools error:', error);
      return { tools: {} };
    }
  }

  /**
   * Get MCP context for a session
   */
  async getContext(sessionId: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/mcp/context/${sessionId}`, {
        headers: {
          'Authorization': `Bearer ${this.token}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to get context: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Get context error:', error);
      return null;
    }
  }

  /**
   * Clear MCP context for a session
   */
  async clearContext(sessionId: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/mcp/context/${sessionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${this.token}`
        }
      });

      return response.ok;
    } catch (error) {
      console.error('Clear context error:', error);
      return false;
    }
  }

  /**
   * Upload document as MCP resource
   */
  async uploadDocument(
    file: File,
    metadata: {
      scope: 'GLOBAL' | 'CHAT';
      visibility: 'all' | 'department';
      session_id?: string;
    }
  ): Promise<MCPResponse> {
    // This will be implemented in Phase 2
    // For now, use existing REST endpoint
    const formData = new FormData();
    formData.append('file', file);
    formData.append('scope', metadata.scope);
    formData.append('visibility', metadata.visibility);
    if (metadata.session_id) {
      formData.append('session_id', metadata.session_id);
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/documents/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const result = await response.json();
      return {
        success: true,
        messages: [{
          role: 'system',
          content: `Document uploaded: ${result.document_id}`
        }],
        metadata: result
      };
    } catch (error) {
      return {
        success: false,
        messages: [],
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Update auth token
   */
  updateToken(token: string): void {
    this.token = token;
  }
}

// Export singleton instance
export const mcpClient = new MCPClient();

// Export class for testing
export default MCPClient;