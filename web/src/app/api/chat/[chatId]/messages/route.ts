import { signUrl } from "@/lib/s3/signer";
import { NextRequest, NextResponse } from "next/server";

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ chatId: string }> }
) {
  try {
    const { chatId } = await context.params;

   
    const upstreamHeaders: Record<string, string> = {};

    req.headers.forEach((value, key) => {
      if (key.toLowerCase() === "host") return;
      upstreamHeaders[key] = value;
    });

    // Ensure JSON if not provided
    if (!upstreamHeaders["content-type"]) {
      upstreamHeaders["content-type"] = "application/json";
    }

    const queryString = req.nextUrl.search;

    // Forward request to Go API
    const gopieRes = await fetch(
      `${process.env.GOPIE_API_URL}/v1/api/chat/${chatId}/messages${queryString}`,
      {
        method: "GET",
        headers: upstreamHeaders,
        cache: "no-store",
      }
    );

    if (!gopieRes.ok) {
      const errorText = await gopieRes.text();
      console.error("GOPIE error:", errorText);
      return NextResponse.json(
        { error: "Upstream error" },
        { status: gopieRes.status }
      );
    }

    const json = await gopieRes.json();
    const data = json.data || [];

    // ---- Mutate ONLY URLs (signing step) ----
    for (const msg of data) {
      // upstream messages have msg.choices[].delta.tool_calls[]
      if (!Array.isArray(msg.choices)) continue;

      for (const choice of msg.choices) {
        const delta = choice.delta;
        if (!delta?.tool_calls) continue;

        for (const tc of delta.tool_calls) {
          // Only process function calls
          if (!tc.function) continue;

          const fn = tc.function;

          // Parse args safely
          let args;
          try {
            args = JSON.parse(fn.arguments || "{}");
          } catch {
            continue;
          }

          // ---- visualization_result ----
          if (fn.name === "visualization_result") {
            const arr = args.visualization_json_paths;
            if (Array.isArray(arr)) {
              for (const entry of arr) {
                if (entry.json_path) {
                  entry.json_path = await signUrl(entry.json_path);
                }
              }
            }

            fn.arguments = JSON.stringify(args);
          }

          // ---- visualization_paths ----
          if (fn.name === "visualization_paths") {
            const arr = args.paths;
            if (Array.isArray(arr)) {
              args.paths = await Promise.all(arr.map((p) => signUrl(p)));
            }

            fn.arguments = JSON.stringify(args);
          }
        }
      }
    }

   
    return NextResponse.json(json);
  } catch (err) {
    console.error("Proxy error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
