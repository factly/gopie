import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Environment configuration
  environment: process.env.NODE_ENV,

  // Adds request headers and IP for users
  sendDefaultPii: true,

  // Set tracesSampleRate to 1.0 to capture 100%
  // of transactions for tracing.
  // We recommend adjusting this value in production
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,

  // Session Replay
  integrations: [
    // Replay may only be enabled for the client-side
    Sentry.replayIntegration({
      // Mask all text content, but keep media playback
      maskAllText: true,
      blockAllMedia: false,
    }),
    // Capture console logs
    Sentry.captureConsoleIntegration({
      levels: ["error", "warn"],
    }),
    // Browser tracing
    Sentry.browserTracingIntegration(),
    // Extra error data
    Sentry.extraErrorDataIntegration({
      depth: 10,
    }),
    // User feedback integration
    Sentry.feedbackIntegration({
      // Use system color scheme (light/dark mode)
      colorScheme: "system",
      // Show name and email fields
      showName: true,
      showEmail: true,
      // Email is required for better follow-up
      isEmailRequired: true,
      // Use Sentry user context for pre-filling
      useSentryUser: {
        email: "email",
        name: "username",
      },
      // Don't auto-inject the widget, we'll control it manually
      autoInject: false,
    }),
  ],

  // Capture Replay for 10% of all sessions,
  // plus for 100% of sessions with an error
  replaysSessionSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 0.5,
  replaysOnErrorSampleRate: 1.0,

  // Always enable when DSN is present
  enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN,
  
  // Debug mode for development
  debug: process.env.NODE_ENV === "development",

  // Before send hook to filter out certain errors or add context
  beforeSend(event, hint) {
    // Add user context if available
    if (typeof window !== "undefined") {
      const userInfo = window.localStorage.getItem("userInfo");
      if (userInfo) {
        try {
          const user = JSON.parse(userInfo);
          Sentry.setUser({
            id: user.id,
            email: user.email,
            username: user.username,
          });
        } catch (e) {
          // Ignore parse errors
        }
      }
    }

    // Filter out specific errors if needed
    if (event.exception) {
      const error = hint.originalException;
      
      // Example: Don't send ResizeObserver errors
      if (error && error.toString().includes("ResizeObserver")) {
        return null;
      }

      // Show crash report modal for exceptions with event ID
      // ONLY if Sentry is properly configured with a DSN
      if (event.event_id && typeof window !== "undefined" && process.env.NEXT_PUBLIC_SENTRY_DSN) {
        // Use setTimeout to avoid blocking the error capture
        setTimeout(() => {
          // Double-check that Sentry client exists and is enabled
          const client = Sentry.getCurrentScope().getClient();
          if (client && client.getOptions().enabled !== false) {
            Sentry.showReportDialog({
              eventId: event.event_id,
              title: "Something went wrong!",
              subtitle: "Our team has been notified about this error.",
              subtitle2: "If you'd like to help, please tell us what happened below.",
              labelName: "Your Name",
              labelEmail: "Your Email",
              labelComments: "What were you doing when this error occurred?",
              labelClose: "Close",
              labelSubmit: "Send Report",
              successMessage: "Thank you for your feedback! This helps us improve GoPie.",
              onLoad: () => {
                console.log("Crash report dialog opened for event:", event.event_id);
              },
              onClose: () => {
                console.log("Crash report dialog closed for event:", event.event_id);
              },
            });
          }
        }, 100);
      }
    }

    return event;
  },

  // Ignore specific errors
  ignoreErrors: [
    // Browser extensions
    "top.GLOBALS",
    // Network errors
    "NetworkError",
    "Failed to fetch",
    // Common browser errors
    "Non-Error promise rejection captured",
    // Ignore specific error messages
    /ResizeObserver loop limit exceeded/,
    /ResizeObserver loop completed with undelivered notifications/,
    // Chrome extensions
    /extensions\//,
    /^chrome:\/\//,
    /^moz-extension:\/\//,
  ],

});

// This export will instrument router navigations
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;