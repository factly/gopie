/**
 * Sanitizes a filename and adds a unique prefix.
 * Replaces non-alphanumeric characters (excluding ., _, -) with underscores.
 * Adds a UUID prefix.
 * @param originalName The original file name.
 * @returns A sanitized and unique file name.
 */
export function sanitizeAndUniquifyFilename(originalName: string): string {
    const uniqueId = crypto.randomUUID().split('-')[0]; // Use a short UUID prefix
    const extensionMatch = originalName.match(/\.[^.]+$/);
    const extension = extensionMatch ? extensionMatch[0] : '';
    const baseName = extension
      ? originalName.substring(0, originalName.length - extension.length)
      : originalName;

    // Replace invalid characters with underscores
    const sanitizedBaseName = baseName
      .replace(/[^a-zA-Z0-9._-]/g, '_')
      // Replace multiple consecutive underscores with a single one
      .replace(/_+/g, '_')
      // Remove leading/trailing underscores
      .replace(/^_+|_+$/g, '');

    // Handle cases where sanitization results in an empty name
    const finalBaseName = sanitizedBaseName || 'file';

    return `${uniqueId}_${finalBaseName}${extension}`;
}