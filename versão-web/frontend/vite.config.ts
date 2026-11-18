import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em desenvolvimento, /api vai para o backend Python (porta 8000).
export default defineConfig({
  plugins: [react()],
  server: { port: 5190, strictPort: true, proxy: { "/api": "http://127.0.0.1:8000" } },
  preview: { port: 5190, strictPort: true, proxy: { "/api": "http://127.0.0.1:8000" } },
});
