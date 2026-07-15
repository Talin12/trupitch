/** @type {import('tailwindcss').Config} */
// `content` tells Tailwind which files to scan for class names so it
// only generates CSS for classes actually used — index.html plus every
// source file under src/. No theme customization: the app uses
// Tailwind's default zinc/teal/emerald/amber/red palette directly
// rather than a custom design-token layer.
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
