import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get current directory (ESM compatible)
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const duckdbWasmDir = path.resolve(__dirname, '../../node_modules/@duckdb/duckdb-wasm/dist');
const publicDir = path.resolve(__dirname, '../../public');

// Files to copy
const files = [
  'duckdb-mvp.wasm',
  'duckdb-eh.wasm',
  'duckdb-browser-mvp.worker.js',
  'duckdb-browser-eh.worker.js'
];

// Create public directory if it doesn't exist
if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

// Copy each file
files.forEach(file => {
  const srcPath = path.join(duckdbWasmDir, file);
  const destPath = path.join(publicDir, file);
  
  if (fs.existsSync(srcPath)) {
    fs.copyFileSync(srcPath, destPath);
    console.log(`Copied ${file} to public directory`);
  } else {
    console.error(`Warning: Source file ${srcPath} not found`);
  }
});

console.log('Done copying DuckDB WASM files to public directory'); 