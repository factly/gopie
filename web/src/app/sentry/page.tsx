"use client";

import * as Sentry from "@sentry/nextjs";
import { useState, useEffect } from "react";

export default function SentryDebugPage() {
  const [sentryStatus, setSentryStatus] = useState<{
    clientExists?: boolean;
    enabled?: boolean;
    dsn?: string;
    environment?: string;
    debug?: boolean;
  }>({});

  useEffect(() => {
    // Check Sentry client status
    const client = Sentry.getCurrentScope().getClient();
    const options = client?.getOptions();
    
    setSentryStatus({
      clientExists: !!client,
      enabled: options?.enabled,
      dsn: options?.dsn,
      environment: options?.environment,
      debug: options?.debug,
    });
  }, []);

  const testClientError = () => {
    console.log("Testing client error...");
    const error = new Error("Client Test Error - Should appear in Sentry!");
    
    // Explicitly capture the error
    Sentry.captureException(error, {
      tags: { source: "client-test" },
      contexts: { test: { type: "manual" } }
    });
    
    // Also throw it for good measure
    setTimeout(() => {
      throw error;
    }, 100);
  };

  const testMessage = () => {
    console.log("Testing message capture...");
    Sentry.captureMessage("Test Message from Client", "info");
    alert("Message sent to Sentry!");
  };

  const testException = () => {
    console.log("Testing exception capture...");
    try {
      // @ts-expect-error - Intentionally call undefined function
      nonExistentFunction();
    } catch (error) {
      console.log("Caught error:", error);
      Sentry.captureException(error, {
        tags: { test: "manual-exception" },
        level: "error"
      });
      alert("Exception captured and sent to Sentry!");
    }
  };

  const testWithContext = () => {
    console.log("Testing context capture...");
    Sentry.withScope((scope) => {
      scope.setTag("test_type", "context");
      scope.setLevel("warning");
      scope.setContext("user_action", {
        button: "test-with-context",
        timestamp: new Date().toISOString(),
        environment: process.env.NODE_ENV,
      });
      scope.setUser({
        id: "test-user",
        email: "test@example.com"
      });
      
      Sentry.captureMessage("Test Message with Rich Context", "warning");
    });
    alert("Message with context sent to Sentry!");
  };

  const testFeedback = () => {
    console.log("Testing feedback widget...");
    const feedback = Sentry.getFeedback();
    if (feedback) {
      // Create and show the feedback widget
      feedback.createWidget();
      console.log("Feedback widget created successfully");
    } else {
      console.error("Sentry feedback integration not available");
      alert("Feedback integration not available. Check Sentry configuration.");
    }
  };

  const testFeedbackAPI = () => {
    console.log("Testing feedback API...");
    // Capture a test event first to get an event ID
    const eventId = Sentry.captureMessage("Test event for feedback association", "info");
    
    // Send feedback programmatically
    Sentry.captureFeedback({
      message: "This is a test feedback message sent via API",
      name: "Test User",
      email: "test@example.com",
      associatedEventId: eventId,
    });
    
    alert("Feedback sent via API! Check your Sentry dashboard.");
  };

  return (
    <div className="container mx-auto p-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-8">Sentry Debug & Status Page</h1>
      
      {/* Sentry Status */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Sentry Client Status</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <strong>Client Exists:</strong> {sentryStatus.clientExists ? "✅ Yes" : "❌ No"}
          </div>
          <div>
            <strong>Enabled:</strong> {sentryStatus.enabled ? "✅ Yes" : "❌ No"}
          </div>
          <div>
            <strong>Environment:</strong> {sentryStatus.environment || "Not set"}
          </div>
          <div>
            <strong>Debug:</strong> {sentryStatus.debug ? "✅ On" : "❌ Off"}
          </div>
          <div className="col-span-2">
            <strong>DSN:</strong> {sentryStatus.dsn ? "✅ Configured" : "❌ Missing"}
          </div>
        </div>
      </div>

      {/* Test Buttons */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Error Types</h2>
          <div className="space-y-3">
            <button
              onClick={testClientError}
              className="w-full bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 transition-colors"
            >
              Test Client Error
            </button>
          </div>
        </div>

        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Manual Capture</h2>
          <div className="space-y-3">
            <button
              onClick={testMessage}
              className="w-full bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors"
            >
              Capture Message
            </button>
            
            <button
              onClick={testException}
              className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
            >
              Capture Exception
            </button>
            
            <button
              onClick={testWithContext}
              className="w-full bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600 transition-colors"
            >
              Test with Context
            </button>
          </div>
        </div>

        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">User Feedback</h2>
          <div className="space-y-3">
            <button
              onClick={testFeedback}
              className="w-full bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 transition-colors"
            >
              Show Feedback Widget
            </button>
            
            <button
              onClick={testFeedbackAPI}
              className="w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors"
            >
              Send Feedback via API
            </button>
          </div>
        </div>
      </div>

      {/* Explanations */}
      <div className="mt-8 space-y-6">
        <div className="bg-gray-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-3">What Each Button Does:</h3>
          <div className="space-y-3 text-sm">
            <div>
              <strong>Test Client Error:</strong> Throws an actual JavaScript error that should be automatically caught by Sentry
            </div>
            <div>
              <strong>Capture Message:</strong> Sends a simple informational message to Sentry (appears in Issues)
            </div>
            <div>
              <strong>Capture Exception:</strong> Manually catches an error and sends it to Sentry with custom tags
            </div>
            <div>
              <strong>Test with Context:</strong> Sends a message with rich metadata (tags, user info, custom context)
            </div>
            <div>
              <strong>Show Feedback Widget:</strong> Opens the Sentry feedback widget for users to submit feedback
            </div>
            <div>
              <strong>Send Feedback via API:</strong> Programmatically sends feedback using the Sentry API
            </div>
          </div>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-3">Expected Results in Sentry:</h3>
          <ul className="list-disc list-inside space-y-1 text-sm">
            <li><strong>Issues Tab:</strong> All errors and messages appear here</li>
            <li><strong>Messages:</strong> Show up as &quot;Non-Error&quot; issues</li>
            <li><strong>Exceptions:</strong> Show up as &quot;Error&quot; issues with stack traces</li>
            <li><strong>Context:</strong> Additional data visible in issue details</li>
            <li><strong>Tags:</strong> Filterable metadata in the issue</li>
            <li><strong>Feedback:</strong> User feedback appears in the &quot;User Feedback&quot; section of your Sentry project</li>
          </ul>
        </div>
      </div>
    </div>
  );
}