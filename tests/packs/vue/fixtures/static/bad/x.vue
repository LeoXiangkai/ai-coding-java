<template>
  <div v-html="html"></div>
  <div v-for="item in items">{{ item.name }}</div>
  <div v-if="ready" v-for="item in items" :key="item.id">{{ item.name }}</div>
</template>

<script setup lang="ts">
const password = 'plain-text-password'
const config = { apiKey: "plain-text-api-key" }
const secret = ''
const token = import.meta.env.TOKEN
const result: any = eval(input)
const other = value as any
const list = <any>items
console.log(result)
debugger
const fn = new Function('return 1')
</script>
