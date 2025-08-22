import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const { url } = await request.json();

    if (!url) {
      return NextResponse.json({ error: "URL is required" }, { status: 400 });
    }

    // Validate URL
    try {
      const urlObj = new URL(url);
      if (!["http:", "https:"].includes(urlObj.protocol)) {
        return NextResponse.json(
          { error: "Only HTTP and HTTPS URLs are allowed" },
          { status: 400 }
        );
      }
    } catch {
      return NextResponse.json({ error: "Invalid URL" }, { status: 400 });
    }

    // Fetch the file from the URL
    const response = await fetch(url, {
      headers: {
        "User-Agent": "GoPie-Web/1.0",
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: `Failed to fetch URL: ${response.status} ${response.statusText}` },
        { status: response.status }
      );
    }

    // Get the content type and size
    const contentType = response.headers.get("content-type") || "application/octet-stream";
    const contentLength = response.headers.get("content-length");

    // Create headers for the response
    const headers = new Headers({
      "Content-Type": contentType,
    });

    if (contentLength) {
      headers.set("Content-Length", contentLength);
    }

    // Get filename from URL
    const pathname = new URL(url).pathname;
    const filename = pathname.split("/").pop() || "download";
    headers.set("Content-Disposition", `attachment; filename="${filename}"`);

    // Stream the response
    return new NextResponse(response.body, {
      status: 200,
      headers,
    });
  } catch (error) {
    console.error("Proxy URL error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}