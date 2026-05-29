/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js"
  ],
  theme: {
    extend: {
      fontFamily: {
       // sans: ['Tajawal', 'sans-serif'],
      },
      colors: {
        primary: '#3b82f6',
        darkBg: '#0f172a'
      }
    }
  },
  plugins: [],
}