import nextjs from 'eslint-config-next'

const config = [
  ...nextjs,
  {
    ignores: [
      '.next/**',
      'out/**',
      'node_modules/**',
    ],
  },
  {
    files: ['**/*.{ts,tsx,js,jsx}'],
    rules: {
      '@next/next/google-font-display': 'warn',
      '@next/next/google-font-preconnect': 'warn',
      '@next/next/no-img-element': 'warn',
      '@next/next/no-typos': 'warn',
      'import/no-anonymous-default-export': 'off',
      'react-hooks/purity': 'warn',
    },
  },
]

export default config
