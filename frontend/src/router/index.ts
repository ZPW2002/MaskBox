import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/masks',
      name: 'masks',
      component: () => import('@/views/MasksView.vue'),
    },
  ],
})

export default router
