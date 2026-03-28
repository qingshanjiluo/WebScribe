import React, { useState, useEffect } from 'react'
import TaskForm from './components/TaskForm'
import TaskList from './components/TaskList'
import LogStream from './components/LogStream'
import ReportViewer from './components/ReportViewer'
import { api } from './api'

function App() {
  const [tasks, setTasks] = useState([])
  const [selectedTask, setSelectedTask] = useState(null)

  const loadTasks = async () => {
    const data = await api.getTasks()
    setTasks(data)
  }

  useEffect(() => {
    loadTasks()
    const interval = setInterval(loadTasks, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="container mx-auto p-4 max-w-6xl">
      <h1 className="text-3xl font-bold mb-6 text-center">🔍 WebScribe · 智能网页探索与复刻</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <TaskForm onTaskCreated={loadTasks} />
          <TaskList tasks={tasks} onSelect={setSelectedTask} selectedId={selectedTask?.id} />
        </div>
        <div>
          {selectedTask && <LogStream taskId={selectedTask.id} />}
          {selectedTask && <ReportViewer taskId={selectedTask.id} />}
        </div>
      </div>
    </div>
  )
}

export default App