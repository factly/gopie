import { UIMessage } from 'ai';

// Define custom message type with data part schemas for type safety
export type GoPieUIMessage = UIMessage<
  unknown, // metadata type
  {
    'chat-created': {
      chatId: string;
    };
    'sql-query': {
      id: string;
      query: string;
      status: 'pending' | 'executing' | 'success' | 'error';
      result?: {
        data: unknown[];
        total: number;
        columns?: string[];
        executionTime?: number;
      };
      error?: string;
      errorDetails?: unknown;
    };
    'datasets-used': {
      datasets: string[];
    };
    'visualization': {
      id: string;
      paths: string[];
      status: 'loading' | 'ready' | 'error';
      error?: string;
    };
    'intermediate-thought': {
      content: string;
      // Transient thoughts that appear during processing but aren't persisted
    };
    'context-info': {
      projectIds: string[];
      datasetIds: string[];
    };
    'status-notification': {
      message: string;
      level: 'info' | 'warning' | 'error' | 'success';
    };
  }
>;