import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#3D3453",
        paper: "#F3EEF9",
        cream: "#FAF7FF",
        copper: "#A78BFA",
        sage: "#7C5FC4",
        moss: "#5B4A8A",
        mist: "#8B83A3",
        coal: "#4A3F66",
        slate: "#6B6285",
        lilac: "#C9B8F0",
        mint: "#A7E3D0",
        peach: "#FFD3B0",
        blush: "#FFC2D8",
        pink: "#FFB6C9",
        line: "#ECE3FB",
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["Outfit", "system-ui", "sans-serif"],
      },
      boxShadow: {
        lift: "0 18px 40px -18px rgba(150,110,210,0.35)",
        card: "0 34px 70px rgba(150,110,210,0.28)",
        pill: "0 14px 26px rgba(167,139,250,0.45)",
      },
    },
  },
  plugins: [],
};

export default config;
