/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
      extend: {
          // 响应式断点 (mobile-first)
          screens: {
              'xs': '475px',
              'sm': '640px',
              'md': '768px',
              'lg': '1024px',
              'xl': '1280px',
              '2xl': '1536px',
          },
          // 容器
          container: {
              center: true,
              padding: {
                  DEFAULT: '1rem',
                  sm: '2rem',
                  lg: '4rem',
              },
          },
      },
  },
  plugins: [],
};
