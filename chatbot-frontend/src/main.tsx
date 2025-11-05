import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import App from './App'
import AppGate from './pages/AppGate'
import './index.css'

const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/select" replace /> },
  { path: '/select', element: <AppGate /> },
  { path: '/app/:appId', element: <App /> },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
)
