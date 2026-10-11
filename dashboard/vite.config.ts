import { defineConfig } from 'vite';

// Static-only: the dev server and build serve dashboard/public (bundled run
// manifests and their artifacts) and nothing else from the repository.
export default defineConfig({
  base: './',
  server: { fs: { strict: true, allow: ['.'] } },
  build: { outDir: 'dist', emptyOutDir: true },
});
