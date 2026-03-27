import { Pool, PoolConfig } from "pg";

// Singleton database connection pool
// Prevents connection exhaustion by reusing a single pool across the application
let _pool: Pool | null = null;

const isProduction = process.env.NODE_ENV === "production";


function getPoolConfig(): PoolConfig {
  const config: PoolConfig = {
    connectionString: process.env.DATABASE_URL,
    max: parseInt("10", 10),
    min: parseInt("2", 10),
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 10000,
    statement_timeout: 30000,
    keepAlive: true,
    keepAliveInitialDelayMillis: 10000,
  };

  return config;
}

/**
 * Get the shared PostgreSQL connection pool
 * Uses lazy initialization to avoid creating connections during build time
 */
export function getPool(): Pool {
  if (!_pool) {
    _pool = new Pool(getPoolConfig());

    _pool.on("error", (err) => {
      console.error("[DB Pool] Unexpected error on idle client:", err.message);
    });

    if (!isProduction) {
      console.log("[DB Pool] Created new connection pool");
    }
  }
  return _pool;
}


