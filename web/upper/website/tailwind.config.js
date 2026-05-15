/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'gray-light-5': '#FAFAFA',
        'primary': '#1867c0',
      },
    },
  },
  plugins: [],
}