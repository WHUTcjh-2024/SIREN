import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import CaptureView from './views/CaptureView.vue'
import ProcessingView from './views/ProcessingView.vue'
import QuizView from './views/QuizView.vue'
import TeacherDashboardView from './views/TeacherDashboardView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/teacher', name: 'teacher-dashboard', component: TeacherDashboardView, meta: { title: 'AI 实验教学工作台', layout: 'teacher' } },
    { path: '/', name: 'home', component: HomeView, meta: { title: '实验主页', subtitle: 'AI + 物理实验 · 预习测验 → 静态实验 → 动态实验' } },
    { path: '/preview-quiz', name: 'quiz', component: QuizView, meta: { title: '预习测验', subtitle: '实验前置学习 · 全部答对后进入正式实验' } },
    { path: '/laser-diffraction', name: 'capture', component: CaptureView, meta: { title: '静态图像采集', subtitle: 'SIREN 连续光场 · EasyOCR 标尺识别 · 亚像素寻峰' } },
    { path: '/data-processing', name: 'processing', component: ProcessingView, meta: { title: '静态实验数据处理', subtitle: '重力-毛细波色散 · 表面张力计算 · 多组数据拟合' } },
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

router.afterEach((to) => {
  document.title = `${String(to.meta.title || '实验主页')} · SIREN 约束拟合`
})
