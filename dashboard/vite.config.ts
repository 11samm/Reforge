import { defineConfig } from 'vite';

// Static-only: the dev server and build serve dashboard/public (bundled run
// manifests and their artifacts) and nothing else from the repository.
export default defineConfig({
  base: './',
  server: { fs: { strict: true, allow: ['.'] }, proxy: { '/api/jobs': { target: 'http://127.0.0.1:5190', changeOrigin: true } } },
  preview: { proxy: { '/api/jobs': { target: 'http://127.0.0.1:5190', changeOrigin: true } } },
  build: { outDir: 'dist', emptyOutDir: true },
});
