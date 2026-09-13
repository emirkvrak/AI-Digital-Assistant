import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom", "zustand"],
          markdown: ["react-markdown", "remark-gfm"],
          ui: ["@react-oauth/google", "react-toastify", "react-textarea-autosize"],
        },
      },
    },
  },
})
