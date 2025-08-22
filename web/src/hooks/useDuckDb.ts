import { useEffect } from "react";
import * as duckdb from "@duckdb/duckdb-wasm";
import { create } from "zustand";

// Use URL objects instead of direct imports with ?url
// Prioritize EH (Exception Handling) bundle for better extension support
export const DUCKDB_BUNDLES: duckdb.DuckDBBundles = {
  eh: {
    mainModule: "/duckdb-eh.wasm", // Will be served from the public directory
    mainWorker: "/duckdb-browser-eh.worker.js", // Will be served from the public directory
  },
  mvp: {
    mainModule: "/duckdb-mvp.wasm", // Will be served from the public directory
    mainWorker: "/duckdb-browser-mvp.worker.js", // Will be served from the public directory
  },
};

interface DuckDbState {
  db: duckdb.AsyncDuckDB | null;
  isInitialized: boolean;
  isInitializing: boolean;
  error: Error | null;
  extensionsLoaded: string[];
  initDb: () => Promise<void>;
}

export const useDuckDbStore = create<DuckDbState>((set, get) => ({
  db: null,
  isInitialized: false,
  isInitializing: false,
  error: null,
  extensionsLoaded: [],
  initDb: async () => {
    const { isInitialized, isInitializing } = get();

    if (isInitialized || isInitializing) {
      return;
    }

    try {
      set({ isInitializing: true });

      const bundle = await duckdb.selectBundle(DUCKDB_BUNDLES);
      const logger = new duckdb.ConsoleLogger();
      const worker = new Worker(bundle.mainWorker!);
      const db = new duckdb.AsyncDuckDB(logger, worker);
      await db.instantiate(bundle.mainModule);

      // Don't preload extensions during initialization - load them on demand
      // This prevents initialization failures due to extension loading issues
      const conn = await db.connect();
      const loadedExtensions: string[] = [];

      // Test basic connectivity
      try {
        await conn.query("SELECT 1");
        console.log("✓ DuckDB WASM initialized successfully");
      } catch (testError) {
        console.warn("DuckDB WASM initialization test failed:", testError);
      }

      await conn.close();

      set({
        db,
        isInitialized: true,
        isInitializing: false,
        extensionsLoaded: loadedExtensions,
      });
    } catch (error) {
      set({ error: error as Error, isInitializing: false });
      console.error("Failed to initialize DuckDB:", error);
    }
  },
}));

/**
 * Hook to use DuckDB in any component
 * Automatically initializes DuckDB if not already initialized
 */
export function useDuckDb() {
  const { db, initDb, isInitialized, isInitializing, error, extensionsLoaded } =
    useDuckDbStore();

  useEffect(() => {
    if (!isInitialized && !isInitializing) {
      initDb();
    }
  }, [initDb, isInitialized, isInitializing]);

  return {
    db,
    isInitialized,
    isInitializing,
    error,
    extensionsLoaded,
  };
}
