import { NextRequest, NextResponse } from "next/server";
import { headers as nextHeaders } from "next/headers";
import { Pool } from "pg";
import { auth } from "@/lib/auth/auth";

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const isAuthEnabled =
      String(process.env.NEXT_PUBLIC_ENABLE_AUTH).trim() === "true";

    if (isAuthEnabled) {
      const session = await auth.api.getSession({ headers: await nextHeaders() });
      if (!session) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
      }
    }

    const { userId } = await params;

    if (!userId) {
      return NextResponse.json(
        { error: "User ID is required" },
        { status: 400 }
      );
    }

    const result = await pool.query(
      `SELECT id, name, image FROM "user" WHERE id = $1`,
      [userId]
    );

    if (result.rows.length === 0) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    const row = result.rows[0];
    const publicUserInfo = {
      displayName: row.name,
      profilePicture: row.image,
    };

    return NextResponse.json({ data: publicUserInfo });
  } catch (error) {
    console.error("Error fetching public user info:", error);
    return NextResponse.json(
      { error: "Failed to fetch user information" },
      { status: 500 }
    );
  }
}
