import React, { useEffect, useState, useRef } from 'react'

export default function LogStream({ taskId }) {
  const [logs, setLogs] = useState([])
  const [socket, setSocket] = useState(null)
  const logsEndRef = useRef(null)

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/${taskId}`)
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'log') {
        setLogs(prev => [...prev, data])
      }
    }
    setSocket(ws)
    return () => ws.close()
  }, [taskId])

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const sendCommand = (cmd) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ command: cmd }))
    }
  }

  return (
    <div className="bg-gray-900 text-white rounded shadow-md p-4 mb-4">
      <div className="flex justify-between items-center mb-2">
        <h2 className="text-xl font-bold">实时日志</h2>
        <div className="flex gap-2">
          <button onClick={() => sendCommand('pause')} className="bg-yellow-500 hover:bg-yellow-600 px-2 py-1 rounded text-sm">⏸ 暂停</button>
          <button onClick={() => sendCommand('resume')} className="bg-green-500 hover:bg-green-600 px-2 py-1 rounded text-sm">▶ 继续</button>
          <button onClick={() => sendCommand('skip')} className="bg-blue-500 hover:bg-blue-600 px-2 py-1 rounded text-sm">⏭ 跳过</button>
          <button onClick={() => sendCommand('stop')} className="bg-red-500 hover:bg-red-600 px-2 py-1 rounded text-sm">⏹ 停止</button>
        </div>
      </div>
      <div className="h-64 overflow-y-auto font-mono text-sm">
        {logs.map((log, idx) => (
          <div key={idx} className={`${log.level === 'error' ? 'text-red-400' : log.level === 'warning' ? 'text-yellow-400' : 'text-green-400'}`}>
            [{log.timestamp}] [{log.level}] {log.message}
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>
    </div>
  )
}