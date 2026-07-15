// Standard Tailwind v3 PostCSS pipeline: tailwindcss expands utility
// classes into real CSS, autoprefixer adds vendor prefixes for older
// browsers. Invoked automatically by Vite during dev and build.
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
