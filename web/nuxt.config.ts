// https://nuxt.com/docs/api/configuration/nuxt-config
//
// Urban Data Platform - Nuxt Configuration
//
// TODO:
// - Configure Cloudflare Pages deployment preset
// - Add MapLibre GL CSS import
// - Configure SSR settings for map components

export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    '@nuxt/fonts'
  ],

  devtools: {
    enabled: true
  },

  css: ['~/assets/css/main.css'],

  // Runtime configuration for environment variables
  runtimeConfig: {
    // Server-side only (not exposed to client)
    r2AccountId: '',
    r2AccessKeyId: '',
    r2SecretAccessKey: '',
    r2Bucket: '',

    // Client-side (exposed via useRuntimeConfig)
    public: {
      r2BaseUrl: '',
      protomapsKey: ''
    }
  },

  routeRules: {
    '/': { prerender: true }
  },

  compatibilityDate: '2025-01-15',

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  },

  fonts: {
    provider: 'bunny',
    families: [
      { name: 'Crimson Pro', weights: [400, 600, 700] },
      { name: 'Inter', weights: [300, 400, 500, 600, 700] },
      { name: 'JetBrains Mono', weights: [400, 500, 600, 700] }
    ]
  },
})
