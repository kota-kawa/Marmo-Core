/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#ea580c",
        background: "#09090b",
        surface: "#18181b",
      }
    },
  },
  plugins: [],
}
