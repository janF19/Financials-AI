import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react' // Or your specific framework plugin

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()], // Or your specific framework plugin
  server: {
    host: true, // This is equivalent to --host in CLI
    port: 5173 // Optional: ensure it's the port you expect
  }
}) 