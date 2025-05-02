// Add support for WASM imports with ?url suffix
declare module "*?url" {
  const src: string;
  export default src;
}

// Add specific declarations for DuckDB WASM files
declare module "@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url" {
  const wasmUrl: string;
  export default wasmUrl;
}

declare module "@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url" {
  const wasmUrl: string;
  export default wasmUrl;
}

// Add declaration for DuckDB WASM shell
declare module "@duckdb/duckdb-wasm-shell/dist/shell_bg.wasm?url" {
  const wasmUrl: string;
  export default wasmUrl;
}

// TypeScript declarations for WebAssembly modules in Next.js
declare module "*.wasm" {
  const content: string;
  export default content;
}

// TypeScript declarations for Web Workers
declare module "*.worker.js" {
  const content: string;
  export default content;
}
