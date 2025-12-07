module.exports = {
  content: ["./app/templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f2fbf5",
          100: "#e3f6e9",
          200: "#c7edcf",
          300: "#a1e0ae",
          400: "#6fcd84",
          500: "#35b65a",
          600: "#2c9b4c",
          700: "#257d3f",
          800: "#1f6233",
          900: "#194d2a"
        }
      },
      boxShadow: {
        card: "0 10px 30px rgba(0, 0, 0, 0.06)"
      }
    }
  },
  plugins: []
};
