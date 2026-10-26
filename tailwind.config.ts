/**
 * Kansai Nerolac Bangladesh Operations Dashboard
 * Bright Light Corporate Design System Tokens
 *
 * Strict Compliance:
 * - Canvas: Pure White (#FFFFFF)
 * - Containers: Warm Slate (#F8FAFC, #F1F5F9)
 * - Brand Accent: Nerolac Red (#D32F2F)
 * - Accents: Sapphire Blue (#0284C7), Emerald Green (#059669), Warm Amber (#D97706)
 * - Text: Slate Charcoal (#0F172A)
 * - Borders: Strict 1px solid #E2E8F0
 * - Tabular numbers enforced across numeric elements
 * - No dark mode, glassmorphism, or gradients
 */

export interface DesignTokensConfig {
  content: string[];
  theme: {
    extend: {
      colors: {
        canvas: string;
        container: {
          DEFAULT: string;
          subtle: string;
        };
        brand: {
          DEFAULT: string;
          hover: string;
          light: string;
        };
        accent: {
          sapphire: string;
          emerald: string;
          amber: string;
        };
        text: {
          primary: string;
          secondary: string;
          muted: string;
          subtle: string;
        };
        border: {
          DEFAULT: string;
          dark: string;
        };
      };
      borderWidth: {
        DEFAULT: string;
      };
      fontFamily: {
        sans: string[];
        mono: string[];
      };
    };
  };
  plugins: unknown[];
}

const config: DesignTokensConfig = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        canvas: '#FFFFFF',
        container: {
          DEFAULT: '#F8FAFC',
          subtle: '#F1F5F9',
        },
        brand: {
          DEFAULT: '#D32F2F',
          hover: '#B71C1C',
          light: '#FFEBEE',
        },
        accent: {
          sapphire: '#0284C7',
          emerald: '#059669',
          amber: '#D97706',
        },
        text: {
          primary: '#0F172A',
          secondary: '#334155',
          muted: '#64748B',
          subtle: '#94A3B8',
        },
        border: {
          DEFAULT: '#E2E8F0',
          dark: '#CBD5E1',
        },
      },
      borderWidth: {
        DEFAULT: '1px',
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
        mono: [
          '"SFMono-Regular"',
          'Menlo',
          'Monaco',
          'Consolas',
          '"Liberation Mono"',
          '"Courier New"',
          'monospace',
        ],
      },
    },
  },
  plugins: [],
};

export default config;
