// https://nuxt.com/docs/api/configuration/nuxt-config
//
// Urban Data Platform - Nuxt Configuration

export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    '@nuxt/fonts',
    '@nuxt/test-utils/module'
  ],

  components: [
    {
      path: '~/components',
      pathPrefix: false
    }
  ],

  devtools: {
    enabled: true
  },

  css: [
    '~/assets/css/main.css',
    'maplibre-gl/dist/maplibre-gl.css'
  ],

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

  nitro: {
    preset: 'cloudflare_module',
    cloudflare: {
      deployConfig: true,
      nodeCompat: true
    }
  },

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
  }
})
