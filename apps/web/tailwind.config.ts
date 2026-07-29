import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          green:   '#1A7A4A',
          amber:   '#E8A020',
          red:     '#C0392B',
          darkRed: '#7B241C',
          blue:    '#1A5276',
        },
      },
      fontFamily: { sans: ['Inter', 'sans-serif'] },
    },
  },
  plugins: [],
};
export default config;
