import js from '@eslint/js';

export default [
  {
    ignores: [
      'node_modules/**',
      '.venv/**',
      '.git/**',
      '.next/**',
      'dist/**',
      'build/**',
      'package-lock.json',
      'scratch/**',
    ],
  },
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
    },
    rules: {
      'no-unused-vars': 'warn',
      'no-console': 'off',
    },
  },
];
