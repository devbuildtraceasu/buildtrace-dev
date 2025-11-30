/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        buildtrace: {
          primary: '#007bff',
          secondary: '#6c757d',
          success: '#28a745',
          warning: '#ffc107',
          danger: '#dc3545',
          light: '#f8f9fa',
          dark: '#343a40',
        }
      },
      animation: {
        'spin-slow': 'spin 2s linear infinite',
        'bounce-light': 'bounce 1s infinite',
        'pulse-subtle': 'pulse 3s ease-in-out infinite',
      },
      fontFamily: {
        mono: ['SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'monospace'],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      maxWidth: {
        '8xl': '88rem',
        '9xl': '96rem',
      }
    },
  },
  plugins: [],
}

