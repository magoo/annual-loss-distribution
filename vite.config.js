import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  base: process.env.GITHUB_ACTIONS ? '/annual-loss-distribution/' : '/',
  plugins: [svelte()],
  test: {
    include: ['src/**/*.test.js'],
  },
});
