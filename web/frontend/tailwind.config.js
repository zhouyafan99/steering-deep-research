/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        'pixel': ['"Press Start 2P"', 'monospace'],
      },
      animation: {
        'text-focus-in': 'text-focus-in 1s cubic-bezier(0.550, 0.085, 0.680, 0.530) both',
        'cursor-blink': 'cursor-blink 1.2s steps(2, start) infinite',
      },
      keyframes: {
        'text-focus-in': {
          '0%': { 
            filter: 'blur(12px)', 
            opacity: 0 
          },
          '100%': { 
            filter: 'blur(0px)', 
            opacity: 1 
          },
        },
        'cursor-blink': {
          'to': { visibility: 'hidden' },
        },
      },
    },
  },
  plugins: [],
}
