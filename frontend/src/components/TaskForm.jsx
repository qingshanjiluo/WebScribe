import React, { useState } from 'react'
import { api } from '../api'

export default function TaskForm({ onTaskCreated }) {
  const [url, setUrl] = useState('')
  const [maxDepth, setMaxDepth] = useState(3)
  const [maxPages, setMaxPages] = useState(20)
  const [headless, setHeadless] = useState(false)
  const [enableAI, setEnableAI] = useState(false)
  const [enableAIPath, setEnableAIPath] = useState(false)
  const [extractContent, setExtractContent] = useState(false)
  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [antiLevel, setAntiLevel] = useState('standard')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.createTask(url, {
        start_url: url,
        max_depth: maxDepth,
        max_pages: maxPages,
        headless,
        enable_ai: enableAI,
        enable_ai_path: enableAIPath,
        extract_content: extractContent,
        login_username: loginUsername,
        login_password: loginPassword,
        anti_spider_level: antiLevel
      })
      setUrl('')
      onTaskCreated()
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white shadow-md rounded px-8 pt-6 pb-8 mb-4">
      <div className="mb-4">
        <label className="block text-gray-700 text-sm font-bold mb-2">目标网址</label>
        <input
          type="url"
          required
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          placeholder="https://example.com"
        />
      </div>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-gray-700 text-sm font-bold mb-2">最大深度</label>
          <input type="number" value={maxDepth} onChange={(e) => setMaxDepth(parseInt(e.target.value))} className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700" />
        </div>
        <div>
          <label className="block text-gray-700 text-sm font-bold mb-2">最大页面数</label>
          <input type="number" value={maxPages} onChange={(e) => setMaxPages(parseInt(e.target.value))} className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700" />
        </div>
      </div>
      <div className="mb-4">
        <label className="block text-gray-700 text-sm font-bold mb-2">反爬策略</label>
        <select value={antiLevel} onChange={(e) => setAntiLevel(e.target.value)} className="shadow border rounded w-full py-2 px-3">
          <option value="dev">开发模式（无伪装）</option>
          <option value="standard">标准模式（基础伪装）</option>
          <option value="stealth">隐匿模式（指纹随机化）</option>
          <option value="aggressive">激进模式（代理+高伪装）</option>
        </select>
      </div>
      <div className="flex flex-wrap gap-4 mb-4">
        <label className="flex items-center">
          <input type="checkbox" checked={headless} onChange={(e) => setHeadless(e.target.checked)} className="mr-2" />
          <span className="text-sm">无头模式</span>
        </label>
        <label className="flex items-center">
          <input type="checkbox" checked={enableAI} onChange={(e) => setEnableAI(e.target.checked)} className="mr-2" />
          <span className="text-sm">AI生成代码</span>
        </label>
        <label className="flex items-center">
          <input type="checkbox" checked={enableAIPath} onChange={(e) => setEnableAIPath(e.target.checked)} className="mr-2" />
          <span className="text-sm">AI路径规划</span>
        </label>
        <label className="flex items-center">
          <input type="checkbox" checked={extractContent} onChange={(e) => setExtractContent(e.target.checked)} className="mr-2" />
          <span className="text-sm">提取内容</span>
        </label>
      </div>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-gray-700 text-sm font-bold mb-2">登录用户名</label>
          <input type="text" value={loginUsername} onChange={(e) => setLoginUsername(e.target.value)} className="shadow border rounded w-full py-2 px-3" />
        </div>
        <div>
          <label className="block text-gray-700 text-sm font-bold mb-2">登录密码</label>
          <input type="password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} className="shadow border rounded w-full py-2 px-3" />
        </div>
      </div>
      <button type="submit" disabled={loading} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline w-full">
        {loading ? '创建中...' : '开始探索'}
      </button>
    </form>
  )
}