import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import CaptureView from './views/CaptureView.vue'
import ProcessingView from './views/ProcessingView.vue'
import QuizView from './views/QuizView.vue'
import PlaceholderView from './views/PlaceholderView.vue'
import TeacherDashboardView from './views/TeacherDashboardView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/teacher', name: 'teacher-dashboard', component: TeacherDashboardView, meta: { title: '教学数据驾驶舱', layout: 'teacher' } },
    { path: '/', name: 'home', component: HomeView, meta: { title: '实验主页', subtitle: 'AI + 物理实验 · 预习测验 → 静态实验 → 动态实验' } },
    { path: '/preview-quiz', name: 'quiz', component: QuizView, meta: { title: '预习测验', subtitle: '实验前置学习 · 全部答对后进入正式实验' } },
    { path: '/laser-diffraction', name: 'capture', component: CaptureView, meta: { title: '静态图像采集', subtitle: 'SIREN 连续光场 · EasyOCR 标尺识别 · 亚像素寻峰' } },
    { path: '/data-processing', name: 'processing', component: ProcessingView, meta: { title: '静态实验数据处理', subtitle: 'Kelvin 公式 · 表面张力计算 · 多组数据拟合' } },
    { path: '/dynamic-video-capture', name: 'dynamic-capture', component: PlaceholderView, meta: { title: '动态图像采集', subtitle: '表面张力 σ · 变温衍射图', icon: 'fa-video-camera' } },
    { path: '/dynamic-data-processing', name: 'dynamic-processing', component: PlaceholderView, meta: { title: '动态数据处理', subtitle: 'σ–T 关系 · 拟合与对比', icon: 'fa-line-chart' } }
  ]
})

router.afterEach((to) => {
  document.title = `${String(to.meta.title || '实验主页')} · SIREN-PINNs`
})
