import { NextRequest, NextResponse } from "next/server";
import { Pool } from "pg";

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const { userId } = await params;

    if (!userId) {
      return NextResponse.json(
        { error: "User ID is required" },
        { status: 400 }
      );
    }

    const result = await pool.query(
      `SELECT id, name, email, "emailVerified", image, "createdAt", "updatedAt" FROM "user" WHERE id = $1`,
      [userId]
    );

    if (result.rows.length === 0) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    return NextResponse.json({ user: result.rows[0] });
  } catch (error) {
    console.error("Error fetching user info:", error);
    return NextResponse.json(
      { error: "Failed to fetch user information" },
      { status: 500 }
    );
  }
}
