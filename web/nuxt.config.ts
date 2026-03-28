// https://nuxt.com/docs/api/configuration/nuxt-config
//
// Urban Data Platform - Nuxt Configuration

export default defineNuxtConfig({
  modules: [
    '@nuxtjs/seo',
    '@nuxt/content',
    '@nuxt/eslint',
    '@nuxt/ui',
    '@nuxt/fonts',
    '@nuxt/test-utils/module'
  ],

  site: {
    url: 'https://theurban.world',
    name: 'The Urban World',
    description: 'An observatory of urban complexity — telling the story of global urbanization through data.'
  },

  robots: {
    blockAiBots: true
  },

  sitemap: {
    sitemaps: {
      pages: {
        includeAppSources: true
      },
      cities: {
        sources: ['/api/__sitemap__/cities'],
        chunks: true
      }
    },
    defaultSitemapsChunkSize: 1000,
    cacheMaxAgeSeconds: 3600
  },

  schemaOrg: {
    identity: {
      type: 'Person',
      name: 'Jonathan Pichot',
      url: 'https://pichot.us'
    }
  },

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

  routeRules: {},

  content: {
    build: {
      markdown: {
        highlight: false
      }
    },
    database: {
      type: 'd1',
      bindingName: 'DB'
    }
  },

  compatibilityDate: '2025-01-15',

  nitro: {
    preset: 'cloudflare_module',
    cloudflare: {
      deployConfig: false,
      nodeCompat: true
    },
    rollupConfig: {
      plugins: [
        {
          name: 'mock-unused-heavy-deps',
          resolveId(id: string) {
            const stubbed = ['utf-8-validate', 'bufferutil', 'shiki', '@shikijs/core', '@shikijs/engine-oniguruma', '@shikijs/engine-javascript', '@shikijs/langs', '@shikijs/themes']
            if (stubbed.includes(id) || id.startsWith('shiki/') || id.startsWith('@shikijs/')) {
              return id
            }
          },
          load(id: string) {
            const stubbed = ['utf-8-validate', 'bufferutil', 'shiki', '@shikijs/core', '@shikijs/engine-oniguruma', '@shikijs/engine-javascript', '@shikijs/langs', '@shikijs/themes']
            if (stubbed.includes(id) || id.startsWith('shiki/') || id.startsWith('@shikijs/')) {
              return 'export default {}; export const createHighlighter = () => undefined; export const createHighlighterCore = () => undefined;'
            }
          }
        }
      ]
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
      { name: 'Crimson Pro', weights: [400, 600, 700], global: true },
      { name: 'Inter', weights: [300, 400, 500, 600, 700], global: true },
      { name: 'JetBrains Mono', weights: [400, 500, 600, 700], global: true }
    ]
  }
})
