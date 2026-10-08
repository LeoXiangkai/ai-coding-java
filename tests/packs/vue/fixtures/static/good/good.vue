<template>
  <ul>
    <li v-for="item in items" :key="item.id">{{ item.name }}</li>
  </ul>
</template>

<script setup lang="ts">
const password = import.meta.env.VITE_PASSWORD
const token = process.env.TOKEN
const label: string = 'safe'
const value = label as string
</script>
