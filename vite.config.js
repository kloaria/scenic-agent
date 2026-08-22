import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import { createDifyProxyMiddleware } from './server/difyProxy.js';

function difyProxyPlugin(mode) {
  const env = loadEnv(mode, process.cwd(), '');
  const middleware = createDifyProxyMiddleware({
    endpoint: env.DIFY_API_ENDPOINT,
    apiKey: env.DIFY_API_KEY,
    user: env.DIFY_USER || 'chenjiaci-web'
  });

  return {
    name: 'dify-chat-proxy',
    configureServer(server) {
      server.middlewares.use(middleware);
    },
    configurePreviewServer(server) {
      server.middlewares.use(middleware);
    }
  };
}

export default defineConfig(({ mode }) => ({
  plugins: [vue(), difyProxyPlugin(mode)]
}));
