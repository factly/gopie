import { NextResponse } from "next/server";
import * as Sentry from "@sentry/nextjs";

export const dynamic = "force-dynamic";

// Alternative test with explicit error capture
export async function GET() {
  
  try {
    // Explicitly capture a test message
    Sentry.captureMessage("Test message from API route", "info");
    
    // Create and capture an error
    const testError = new Error("Explicit Sentry Test Error - This should be captured!");
    
    // Explicitly capture the exception
    Sentry.captureException(testError, {
      tags: {
        source: "api-route",
        test: true,
      },
      contexts: {
        api: {
          endpoint: "/api/sentry-test-explicit",
          method: "GET",
        },
      },
    });
    
    // Wait a bit to ensure the error is sent
    await Sentry.flush(2000);
    
    // Also throw it for good measure
    throw testError;
  } catch (error) {
    
    // Return error response
    return NextResponse.json(
      { 
        error: "Test error thrown successfully", 
        message: error instanceof Error ? error.message : "Unknown error",
        sentryEnabled: Sentry.getCurrentScope().getClient()?.getOptions().enabled,
      },
      { status: 500 }
    );
  }
}