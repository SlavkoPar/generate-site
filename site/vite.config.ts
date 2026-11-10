import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Base must match the GitHub repo name for gh-pages project sites.
export default defineConfig({
  base: '/generate-site/',
  plugins: [react()],
});
