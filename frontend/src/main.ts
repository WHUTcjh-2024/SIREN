import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import './styles.css'

document.body.className = 'app-dashboard'
createApp(App).use(router).mount('#app')
