/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#ffffff",
        canvas: "#f4f5f7",
        ink: {
          900: "#111827",
          800: "#1f2937",
          700: "#374151",
          600: "#4b5563",
          500: "#6b7280",
          400: "#9ca3af",
        },
        line: "#e5e7eb",
        brand: {
          700: "#1e3a5f",
          600: "#254b73",
          500: "#2f5f8f",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "Segoe UI",
          "-apple-system",
          "BlinkMacSystemFont",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 1px 2px 0 rgba(17,24,39,0.06), 0 1px 1px 0 rgba(17,24,39,0.04)",
      },
    },
  },
  plugins: [],
};
