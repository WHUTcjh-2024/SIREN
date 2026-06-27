import { reactive, watch } from 'vue'
import { api } from '../api/client'

export interface Measurement {
  H0: number | null
  deltaX1: number | null
  deltaX2: number | null
  avgDeltaX: number | null
  annotatedImage?: string | null
  intensityProfile?: string | null
  grayImage?: string | null
  surface3d?: string | null
}

const state = reactive({
  quizPassed: localStorage.getItem('quizPassed') === '1',
  measurement: null as Measurement | null,
  calculations: [] as Array<Record<string, number>>,
  progress: 0
})

let saveTimer: number | undefined
watch(state, () => {
  window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => {
    localStorage.setItem('quizPassed', state.quizPassed ? '1' : '0')
    void api('/api/experiment-state', { method: 'POST', body: JSON.stringify({ state }) }).catch(() => undefined)
  }, 400)
}, { deep: true })

export function useExperiment() {
  const hydrate = async () => {
    const response = await api<{ data: Partial<typeof state> }>('/api/experiment-state')
    Object.assign(state, response.data || {})
  }
  const reset = async () => {
    await api('/api/experiment-reset', { method: 'POST' })
    state.quizPassed = false
    state.measurement = null
    state.calculations = []
    state.progress = 0
    localStorage.removeItem('quizPassed')
  }
  return { state, hydrate, reset }
}
