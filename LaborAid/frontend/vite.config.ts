import fs from 'node:fs';
import path from 'node:path';
import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

const BRAND_DIR = path.resolve(__dirname, '../../resources/brand');
const PUBLIC_DIR = path.resolve(__dirname, 'public');

/** 将 resources/brand/ 同步到 frontend/public/（开发热更新与构建前执行） */
function syncBrandResources(): Plugin {
  const sync = () => {
    if (!fs.existsSync(BRAND_DIR)) return;
    fs.mkdirSync(PUBLIC_DIR, { recursive: true });
    for (const name of fs.readdirSync(BRAND_DIR)) {
      const src = path.join(BRAND_DIR, name);
      if (!fs.statSync(src).isFile()) continue;
      fs.copyFileSync(src, path.join(PUBLIC_DIR, name));
    }
  };
  return {
    name: 'sync-brand-resources',
    configureServer() {
      sync();
    },
    buildStart() {
      sync();
    },
  };
}

export default defineConfig({
  plugins: [react(), syncBrandResources()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@resources': path.resolve(__dirname, '../../resources'),
    },
  },
  server: {
    port: 5320,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8010',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: undefined,
      },
    },
  },
});
