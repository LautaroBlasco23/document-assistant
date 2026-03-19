import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useHealth } from '@/hooks/useHealth'
import { useAppStore } from '@/stores/appStore'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  useHealth()
  const location = useLocation()
  const serviceHealth = useAppStore((state) => state.serviceHealth)

  const isActive = (path: string) => location.pathname === path

  const navItems = [
    { label: 'Dashboard', path: '/', icon: '📊' },
    { label: 'Documents', path: '/documents', icon: '📄' },
    { label: 'Search', path: '/search', icon: '🔍' },
    { label: 'Ask Question', path: '/ask', icon: '❓' },
    { label: 'Analysis', path: '/analysis', icon: '📈' },
    { label: 'Settings', path: '/settings', icon: '⚙️' },
  ]

  return (
    <div className="flex h-screen bg-white">
      {/* Sidebar */}
      <div className="w-64 bg-gray-900 text-white flex flex-col">
        <div className="p-6 border-b border-gray-700">
          <h1 className="text-xl font-bold">Document Assistant</h1>
          <p className="text-xs text-gray-400 mt-1">v0.1.0</p>
        </div>

        <nav className="flex-1 p-4">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors ${
                isActive(item.path)
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800'
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        {/* Service Status */}
        <div className="p-4 border-t border-gray-700">
          <p className="text-xs font-semibold text-gray-400 mb-3">Services</p>
          {serviceHealth?.services.map((service) => (
            <div key={service.name} className="flex items-center gap-2 text-xs mb-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  service.healthy ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className="text-gray-400 capitalize">{service.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-auto">
          <div className="p-8">{children}</div>
        </div>
      </div>
    </div>
  )
}
