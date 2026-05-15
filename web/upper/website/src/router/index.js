import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/monitor'
    },
    {
      path: '/monitor',
      name: 'monitor',
      component: () => import('../views/MonitorPage.vue')
    },
    {
      path: '/control',
      name: 'control',
      component: () => import('../views/ControlPage.vue')
    }
  ]
})

export default router
