import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Environment configuration
  environment: process.env.NODE_ENV,

  // Set tracesSampleRate to 1.0 to capture 100%
  // of transactions for tracing.
  // We recommend adjusting this value in production
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,

  // Send default PII (personally identifiable information)
  sendDefaultPii: true,

  // Always enable when DSN is present
  enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN,
  
  // Debug mode for development
  debug: process.env.NODE_ENV === "development",

  // Before send hook to filter out certain errors or add context
  beforeSend(event, hint) {
    // Filter out specific errors if needed
    if (event.exception) {
      const error = hint.originalException;
      
      // Example: Don't send ECONNREFUSED errors
      if (error && error.toString().includes("ECONNREFUSED")) {
        return null;
      }
    }

    return event;
  },

  // Ignore specific errors
  ignoreErrors: [
    // Network errors
    "NetworkError",
    "Failed to fetch",
    // Common errors
    "Non-Error promise rejection captured",
  ],
});