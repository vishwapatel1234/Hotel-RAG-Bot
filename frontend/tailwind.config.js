/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#09090b",   // zinc-950 base dark
        card: "#18181b",         // zinc-900 card surface
        border: "#27272a",       // zinc-800 borders
        zinc: {
          850: "#1f1f23",        // Custom intermediate between 800 and 900
        },
        primary: {
          DEFAULT: "#6366f1",    // Indigo
          foreground: "#ffffff"
        },
        accent: {
          emerald: "#10b981",
          amber: "#f59e0b",
          rose: "#f43f5e",
          indigo: "#6366f1",
        }
      },
      fontFamily: {
        sans: ["Inter", "Outfit", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
      },
      boxShadow: {
        "glow-emerald": "0 0 20px rgba(16, 185, 129, 0.20), 0 0 8px rgba(16, 185, 129, 0.10)",
        "glow-amber":   "0 0 20px rgba(245, 158, 11, 0.25), 0 0 8px rgba(245, 158, 11, 0.12)",
        "glow-rose":    "0 0 20px rgba(244, 63, 94, 0.20), 0 0 8px rgba(244, 63, 94, 0.10)",
        "glow-indigo":  "0 0 20px rgba(99, 102, 241, 0.20), 0 0 8px rgba(99, 102, 241, 0.10)",
      },
      animation: {
        "pulse-slow":   "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in":      "fadeIn 0.3s ease-out forwards",
        "fade-in-up":   "fadeInUp 0.4s ease-out forwards",
        "slide-in":     "slideIn 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards",
        "slide-in-left":"slideInLeft 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards",
        "bounce-soft":  "bounceSoft 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        fadeInUp: {
          "0%":   { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideIn: {
          "0%":   { opacity: "0", transform: "translateX(24px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        slideInLeft: {
          "0%":   { opacity: "0", transform: "translateX(-24px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        bounceSoft: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-4px)" },
        },
      }
    },
  },
  plugins: [],
}
