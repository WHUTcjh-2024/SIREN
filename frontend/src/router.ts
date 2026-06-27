import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import CaptureView from './views/CaptureView.vue'
import ProcessingView from './views/ProcessingView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView, meta: { title: '实验主页' } },
    { path: '/laser-diffraction', component: CaptureView, meta: { title: '静态图像采集' } },
    { path: '/data-processing', component: ProcessingView, meta: { title: '静态实验数据处理' } }
  ]
})

router.afterEach((to) => {
  document.title = `${String(to.meta.title || '实验主页')} · SIREN-PINNs`
})
