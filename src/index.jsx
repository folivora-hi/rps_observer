import React from 'react'
import { createRoot } from 'react-dom/client'   // ← 新 API
import './styles/index.css'
import App from './App.jsx'

const container = document.getElementById('root')
const root = createRoot(container)
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
