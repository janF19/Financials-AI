// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {
        colors: {
          primary: {
            light: '#4dabf5',
            main: '#2196f3',
            dark: '#1769aa',
          },
          secondary: {
            light: '#f73378',
            main: '#f50057',
            dark: '#ab003c',
          },
        }
      },
    },
    plugins: [],
  }