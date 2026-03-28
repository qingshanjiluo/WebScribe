import React from 'react'

export default function TaskList({ tasks, onSelect, selectedId }) {
  const statusColors = {
    pending: 'bg-yellow-200 text-yellow-800',
    running: 'bg-blue-200 text-blue-800',
    completed: 'bg-green-200 text-green-800',
    failed: 'bg-red-200 text-red-800'
  }

  return (
    <div className="bg-white shadow-md rounded px-4 py-4">
      <h2 className="text-xl font-bold mb-4">任务列表</h2>
      {tasks.length === 0 ? (
        <p className="text-gray-500">暂无任务，创建第一个吧</p>
      ) : (
        <ul className="divide-y">
          {tasks.map(task => (
            <li key={task.id} className={`py-3 cursor-pointer hover:bg-gray-50 ${selectedId === task.id ? 'bg-blue-50' : ''}`} onClick={() => onSelect(task)}>
              <div className="flex justify-between items-center">
                <div className="truncate flex-1">
                  <div className="font-medium">{task.url}</div>
                  <div className="text-sm text-gray-500">{new Date(task.created_at).toLocaleString()}</div>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-semibold ${statusColors[task.status]}`}>
                  {task.status}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}