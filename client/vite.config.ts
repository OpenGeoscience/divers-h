import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import vuetify from 'vite-plugin-vuetify';

const devPort = 3000
export default defineConfig({
  envPrefix: 'VUE_APP_',
  plugins: [
    vue(),
    vuetify({ autoImport: true }), // Enabled by default
  ],
  server: {
    host: "0.0.0.0",
    port: devPort,
    strictPort: true,
    proxy: {
      // proxy configuration for mkdocs serve
      '/docs': {
        target: 'http://localhost:8003',
      },
      '/livereload': {
        target: 'http://localhost:8003',
      }
    },
  },
})
