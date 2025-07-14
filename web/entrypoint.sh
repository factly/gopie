#!/bin/sh

# This script is executed when the container starts.
# It replaces placeholders in the built Next.js files with runtime environment variables.

set -e

# The directory where Next.js outputs the built application
NEXT_DIR="/app/.next"

echo "Running entrypoint script..."

# Find all JavaScript files in the .next directory and replace placeholders.
# We use a loop and temporary files for compatibility with alpine's sed.
# Find all JavaScript files in the .next directory and replace placeholders.
find "$NEXT_DIR" -type f -name "*.js" -print0 | while IFS= read -r -d $'\0' file; do
  echo "Processing $file..."
  # Replace placeholders with actual env var values
  sed -i "s|__NEXT_PUBLIC_COMPANION_URL__|$NEXT_PUBLIC_COMPANION_URL|g" "$file"
  sed -i "s|__NEXT_PUBLIC_GOPIE_API_URL__|$NEXT_PUBLIC_GOPIE_API_URL|g" "$file"
  sed -i "s|__NEXT_PUBLIC_LIVEKIT_URL__|$NEXT_PUBLIC_LIVEKIT_URL|g" "$file"
  sed -i "s|__NEXT_PUBLIC_ENABLE_AUTH__|$NEXT_PUBLIC_ENABLE_AUTH|g" "$file"
  sed -i "s|__NEXT_PUBLIC_APP_URL__|$NEXT_PUBLIC_APP_URL|g" "$file"
done

echo "Placeholder replacement complete."

# Execute the original command (CMD) for the container
exec "$@"
