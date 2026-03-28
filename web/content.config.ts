import { defineContentConfig, defineCollection, z } from '@nuxt/content'

export default defineContentConfig({
  collections: {
    pages: defineCollection({
      source: '*.md',
      type: 'page'
    }),
    data: defineCollection({
      source: 'data/**',
      type: 'page',
      schema: z.object({
        modalTitle: z.string().optional(),
        parentPage: z.string().optional(),
        dataset: z.string().optional()
      })
    }),
    methodology: defineCollection({
      source: 'methodology/**',
      type: 'page',
      schema: z.object({
        modalTitle: z.string().optional(),
        parentPage: z.string().optional(),
        dataset: z.string().optional()
      })
    }),
    media: defineCollection({
      source: 'media/**',
      type: 'data',
      schema: z.object({
        type: z.enum(['article', 'video', 'book', 'podcast', 'film']),
        title: z.string(),
        url: z.string().optional(),
        description: z.string().optional(),
        cityIds: z.array(z.string()),
        author: z.string().optional(),
        channel: z.string().optional(),
        show: z.string().optional(),
        director: z.string().optional(),
        date: z.string().optional(),
        year: z.string().optional(),
        duration: z.string().optional()
      })
    })
  }
})
