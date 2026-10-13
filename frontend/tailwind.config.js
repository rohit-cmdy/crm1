export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'] },
      colors: {
        ink: '#0F1B33', muted: '#5B6B82', line: '#E3E8F0', canvas: '#F5F7FA',
        brand: { DEFAULT: '#2563EB', dark: '#1D4ED8', soft: '#EAF1FE' },
        navy: { DEFAULT: '#0F1B33', soft: '#1A2A4A' },
      },
    },
  },
  plugins: [],
}
