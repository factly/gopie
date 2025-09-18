/**
 * Utility functions for transforming messages between different formats
 */

interface MessagePart {
  type: string;
  text?: string;
}

interface UIMessage {
  role: string;
  content?: string;
  text?: string;
  parts?: MessagePart[];
}

interface BackendMessage {
  role: string;
  content: string;
}

/**
 * Convert UI messages from AI SDK v5 format to backend OpenAI format
 * Handles various message formats including:
 * - AI SDK v5 parts array format
 * - Simple text format from sendMessage({ text: 'message' })
 * - Fallback to content field
 *
 * @param messages - Array of UI messages to transform
 * @returns Array of backend-compatible messages
 */
export function transformUIMessagesToBackend(messages?: UIMessage[]): BackendMessage[] {
  if (!messages) return [];

  return messages
    .map((msg) => {
      // Handle AI SDK v5 message format
      let content = '';
      const role = msg.role || 'user'; // Default to 'user' if role is not specified

      // Check if the message has parts array (AI SDK v5 format)
      if (msg.parts && Array.isArray(msg.parts)) {
        // Extract text from parts array
        const textParts = msg.parts.filter((p: MessagePart) => p.type === 'text');
        content = textParts.map((p: MessagePart) => p.text || '').join('');
      }
      // Handle simple text format from sendMessage({ text: 'message' })
      else if (msg.text) {
        content = msg.text;
      }
      // Fallback to content field
      else if (msg.content) {
        content = msg.content;
      }

      // Only return valid messages with content
      if (!content) {
        return null;
      }

      return {
        role,
        content,
      };
    })
    .filter((msg): msg is BackendMessage => msg !== null);
}