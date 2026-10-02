import {
  AIModeConfig,
  AIModeKnowledgeSource,
  AIModeSearchResponse,
  AIModeChatResponse,
  AIModeDeployment
} from '../types';

export class AIModeApiClient {
  private static async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const res = await fetch(endpoint, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {})
      }
    });

    if (!res.ok) {
      let errorMsg = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        errorMsg = errJson.detail || errJson.error?.message || errorMsg;
      } catch {
        // use fallback string
      }
      throw new Error(errorMsg);
    }

    return res.json();
  }

  // Config
  static async getConfig(): Promise<AIModeConfig> {
    return this.request<AIModeConfig>('/api/ai-mode/config');
  }

  static async updateConfig(updates: Partial<AIModeConfig>): Promise<{ success: boolean; is_enabled: boolean }> {
    return this.request('/api/ai-mode/config', {
      method: 'POST',
      body: JSON.stringify(updates)
    });
  }

  // Search
  static async search(query: string, page = 1, pageSize = 6): Promise<AIModeSearchResponse> {
    return this.request<AIModeSearchResponse>('/api/ai-mode/search', {
      method: 'POST',
      body: JSON.stringify({ query, page, page_size: pageSize })
    });
  }

  // Conversational Chat / Preview
  static async chat(
    message: string,
    conversationId?: string,
    channel = 'PREVIEW'
  ): Promise<AIModeChatResponse> {
    return this.request<AIModeChatResponse>('/api/ai-mode/chat', {
      method: 'POST',
      body: JSON.stringify({ message, conversation_id: conversationId, channel })
    });
  }

  // Product Comparison
  static async compare(productIds: string[], userQuery?: string) {
    return this.request('/api/ai-mode/compare', {
      method: 'POST',
      body: JSON.stringify({ product_ids: productIds, user_query: userQuery })
    });
  }

  // Recommendations
  static async getRecommendations(productId?: string, limit = 4) {
    return this.request('/api/ai-mode/recommendations', {
      method: 'POST',
      body: JSON.stringify({ product_id: productId, limit })
    });
  }

  // Knowledge Sources
  static async getKnowledgeSources(): Promise<AIModeKnowledgeSource[]> {
    return this.request<AIModeKnowledgeSource[]>('/api/ai-mode/knowledge');
  }

  static async createKnowledgeSource(source: {
    name: string;
    source_type: string;
    config?: Record<string, any>;
    content?: string;
  }): Promise<AIModeKnowledgeSource> {
    return this.request<AIModeKnowledgeSource>('/api/ai-mode/knowledge', {
      method: 'POST',
      body: JSON.stringify(source)
    });
  }

  static async syncKnowledgeSource(sourceId: string): Promise<AIModeKnowledgeSource> {
    return this.request<AIModeKnowledgeSource>(`/api/ai-mode/knowledge/sync?source_id=${sourceId}`, {
      method: 'POST'
    });
  }

  static async deleteKnowledgeSource(sourceId: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/api/ai-mode/knowledge?source_id=${sourceId}`, {
      method: 'DELETE'
    });
  }

  // Deployments
  static async getDeployments(): Promise<AIModeDeployment[]> {
    return this.request<AIModeDeployment[]>('/api/ai-mode/deployment');
  }

  static async createDeployment(data: {
    name: string;
    allowed_domains?: string[];
    theme_config?: Record<string, any>;
    welcome_message?: string;
    launcher_text?: string;
  }): Promise<AIModeDeployment> {
    return this.request<AIModeDeployment>('/api/ai-mode/deployment', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  static async updateDeployment(id: string, updates: Partial<AIModeDeployment>): Promise<AIModeDeployment> {
    return this.request<AIModeDeployment>(`/api/ai-mode/deployment?id=${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    });
  }
}
