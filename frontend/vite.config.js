import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    // Playwright specs live in e2e/ and must not be picked up by Vitest
    include: ['src/**/*.test.{js,jsx}'],
  },
})
