import { ref, computed, onMounted, onUnmounted } from 'vue'
import { defineStore } from 'pinia'

export const useResizeStore = defineStore('resize', () => {
  const windowWidth = ref(window.innerWidth)
  const updateWidth = () => {
    windowWidth.value = window.innerWidth
  }

  onMounted(() => {
    window.addEventListener('resize', updateWidth)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', updateWidth)
  })
  
  return { windowWidth }
})