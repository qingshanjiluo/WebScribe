const API_BASE = '/api'

export const api = {
  async createTask(url, config) {
    const res = await fetch(`${API_BASE}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, config })
    })
    return res.json()
  },
  async getTasks() {
    const res = await fetch(`${API_BASE}/tasks`)
    return res.json()
  },
  async getLogs(taskId) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/logs`)
    return res.json()
  },
  async getReport(taskId) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/report`)
    return res.json()
  }
}