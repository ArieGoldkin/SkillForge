import type { StorybookConfig } from '@storybook/react-vite'
import { mergeConfig } from 'vite'

const config: StorybookConfig = {
  stories: ['../src/**/*.mdx', '../src/**/*.stories.@(js|jsx|mjs|ts|tsx)'],
  addons: [
    '@chromatic-com/storybook',
    '@storybook/addon-vitest',
    '@storybook/addon-a11y',
    '@storybook/addon-docs',
    '@storybook/addon-onboarding',
  ],
  framework: '@storybook/react-vite',
  viteFinal: async (config) => {
    return mergeConfig(config, {
      resolve: {
        alias: {
          '@': '/src',
          '@features': '/src/features',
          '@shared': '/src/shared',
          '@stores': '/src/stores',
          '@hooks': '/src/hooks',
          '@app-types': '/src/types',
          '@lib': '/src/lib',
          '@services': '/src/services',
          '@router': '/src/router',
        },
      },
    })
  },
}

export default config