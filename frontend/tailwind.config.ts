import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14110F",
        paper: "#F4EFE6",
        cream: "#EBE4D6",
        copper: "#C46B3A",
        sage: "#5C7A6B",
        moss: "#2C3D34",
        mist: "#8A8178",
        coal: "#1C1917",
        slate: "#2A2623",
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["Outfit", "system-ui", "sans-serif"],
      },
      boxShadow: {
        lift: "0 18px 40px -24px rgba(20,17,15,0.45)",
      },
    },
  },
  plugins: [],
};

export default config;
