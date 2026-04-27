/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // 使用CSS变量，让主题系统可以动态控制颜色
        background: 'var(--color-background, hsl(var(--background)))',
        foreground: 'var(--color-foreground, hsl(var(--foreground)))',
        primary: 'var(--color-primary, #3b82f6)',
        secondary: 'var(--color-secondary, #64748b)',
        accent: 'var(--color-accent, #f59e0b)',
        muted: 'var(--color-muted, #f3f4f6)',
        border: 'var(--color-border, #e5e7eb)',

        // 保留原有的shadcn/ui颜色变量作为后备
        'shadcn-background': 'hsl(var(--background))',
        'shadcn-foreground': 'hsl(var(--foreground))',
      },
      fontFamily: {
        sans: ['var(--font-family, Inter)', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        base: ['var(--font-size-base, 16px)', {lineHeight: 'var(--line-height, 1.6)'}],
      },
      borderRadius: {
        DEFAULT: 'var(--border-radius, 0.5rem)',
      },
      maxWidth: {
        'content': 'var(--content-width, 56rem)', // max-w-4xl = 56rem
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'float-delayed': 'float-delayed 8s ease-in-out infinite',
        'gradient': 'gradient 3s ease infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        'float-delayed': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-30px)' },
        },
        gradient: {
          '0%, 100%': {
            'background-size': '200% 200%',
            'background-position': 'left center',
          },
          '50%': {
            'background-size': '200% 200%',
            'background-position': 'right center',
          },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}