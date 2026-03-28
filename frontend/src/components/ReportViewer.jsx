import React, { useState } from 'react'
import { api } from '../api'

export default function ReportViewer({ taskId }) {
  const [loading, setLoading] = useState(false)

  const downloadReport = async () => {
    setLoading(true)
    try {
      const data = await api.getReport(taskId)
      window.open(data.report_path, '_blank')
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white shadow-md rounded p-4">
      <h2 className="text-xl font-bold mb-2">报告与输出</h2>
      <button
        onClick={downloadReport}
        disabled={loading}
        className="bg-purple-500 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded w-full"
      >
        {loading ? '加载中...' : '📥 下载报告 & 代码包'}
      </button>
    </div>
  )
}