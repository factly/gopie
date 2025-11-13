import { v4 as uuidv4 } from 'uuid';
/**
 * Generates a unique filename using UUID while preserving the original extension.
 * This prevents filename collisions and ensures safe storage.
 * 
 * @param originalName - The original filename 
 * @returns A UUID-based filename in format: "uuid.extension"
 * @example
 * sanitizeAndUniquifyFilename("my-file.csv") 
 * // Returns: "550e8400-e29b-41d4-a716-446655440000.csv"
 */
export function sanitizeAndUniquifyFilename(originalName: string): string {
     const uniqueId = uuidv4();
     const extensionMatch = originalName.match(/\.[^.]+$/);
     const extension = extensionMatch ? extensionMatch[0] : '';
     return `${uniqueId}${extension}`;
}