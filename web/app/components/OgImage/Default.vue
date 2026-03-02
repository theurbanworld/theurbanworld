<script setup lang="ts">
/**
 * Default OG image template for the home page.
 *
 * Branded image with title and subtitle.
 * Uses Satori renderer (edge-compatible).
 */
</script>

<template>
  <div
    :style="{
      width: '1200px',
      height: '630px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: '#FAFAF4',
      fontFamily: 'Inter, sans-serif',
      gap: '24px'
    }"
  >
    <!-- Decorative circle -->
    <div
      :style="{
        width: '80px',
        height: '80px',
        borderRadius: '50%',
        backgroundColor: 'rgba(106, 143, 94, 0.15)',
        border: '2px solid rgba(58, 82, 51, 0.3)',
        marginBottom: '8px'
      }"
    />

    <!-- Title -->
    <div
      :style="{
        fontFamily: 'Crimson Pro, serif',
        fontSize: '64px',
        fontWeight: 600,
        color: '#3A5233',
        letterSpacing: '0.02em',
        lineHeight: '1.1'
      }"
    >
      The Urban World
    </div>

    <!-- Subtitle -->
    <div
      :style="{
        fontSize: '24px',
        color: '#4A4238',
        lineHeight: '1.4'
      }"
    >
      an observatory of urban complexity
    </div>

    <!-- Decorative line -->
    <div
      :style="{
        width: '120px',
        height: '2px',
        backgroundColor: 'rgba(58, 82, 51, 0.2)',
        marginTop: '16px'
      }"
    />
  </div>
</template>
