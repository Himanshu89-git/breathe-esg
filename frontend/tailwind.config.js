/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        carbon: { 50: '#f0fdf4', 500: '#22c55e', 900: '#14532d' },
        slate: { 850: '#1e293b' }
      }
    }
  },
  plugins: []
}
