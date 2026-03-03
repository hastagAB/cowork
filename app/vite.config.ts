import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const appDir = path.resolve(__dirname);

export default defineConfig({
  plugins: [react()],
  base: "./",
  root: path.resolve(appDir, "src"),
  build: {
    outDir: path.resolve(appDir, "dist"),
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(appDir, "src"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
});
