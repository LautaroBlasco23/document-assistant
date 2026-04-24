import * as React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  Home,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
} from 'lucide-react'
import { cn } from '../../lib/cn'
import { Tooltip } from '../ui/tooltip'

import { useAppStore } from '../../stores/app-store'
import { useAuth } from '../../auth/auth-context'

interface NavItem {
  label: string
  to: string
  icon: React.ComponentType<{ className?: string }>
}

const navItems: NavItem[] = [
  { label: 'Library', to: '/', icon: Home },
  { label: 'Settings', to: '/settings', icon: Settings },
]

export function Sidebar() {
  const collapsed = useAppStore((state) => state.sidebarCollapsed)
  const toggleSidebar = useAppStore((state) => state.toggleSidebar)

  return (
    <aside
      className={cn(
        'flex flex-col h-screen bg-white border-r border-gray-100 shrink-0',
        'transition-all duration-200',
        collapsed ? 'w-16' : 'w-64',
      )}
    >
      {/* Logo / app name */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-gray-100 overflow-hidden">
        <div className="shrink-0 h-7 w-7 rounded-md bg-primary flex items-center justify-center">
          <span className="text-white text-xs font-bold">D</span>
        </div>
        {!collapsed && (
          <span className="font-semibold text-gray-900 text-sm truncate">
            Doc Assistant
          </span>
        )}
      </div>

      {/* Nav items */}
      <nav className="flex-1 py-4 flex flex-col gap-1 px-2">
        {navItems.map(({ label, to, icon: Icon }) => {
          const item = (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-50 text-primary border-l-2 border-primary'
                    : 'text-gray-600 hover:bg-surface-100 hover:text-gray-900',
                  collapsed && 'justify-center px-2',
                )
              }
            >
              <Icon className="h-5 w-5 shrink-0" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          )

          return collapsed ? (
            <Tooltip key={to} content={label}>
              {item}
            </Tooltip>
          ) : (
            <React.Fragment key={to}>{item}</React.Fragment>
          )
        })}
      </nav>

      {/* User section */}
      <UserSection collapsed={collapsed} />

      {/* Health dots */}
      <ServiceHealthDots collapsed={collapsed} />

      {/* Collapse toggle */}
      <button
        onClick={toggleSidebar}
        className="flex items-center justify-center h-10 border-t border-gray-100 text-gray-400 hover:text-gray-700 hover:bg-surface-100 transition-colors"
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? (
          <ChevronRight className="h-4 w-4" />
        ) : (
          <ChevronLeft className="h-4 w-4" />
        )}
      </button>
    </aside>
  )
}

interface UserSectionProps {
  collapsed: boolean
}

function UserSection({ collapsed }: UserSectionProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  if (!user) return null

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const initials = user.display_name
    ? user.display_name.split(' ').map(n => n[0]).join('').toUpperCase()
    : user.email[0].toUpperCase()

  const content = (
    <div className={cn(
      'flex items-center border-t border-gray-100 text-gray-600',
      collapsed ? 'justify-center px-2 py-3' : 'px-4 py-3 gap-3'
    )}>
      <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
        <span className="text-blue-700 text-xs font-bold">{initials}</span>
      </div>
      {!collapsed && (
        <>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {user.display_name || user.email}
            </p>
            <p className="text-xs text-gray-400 truncate">{user.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 rounded-md hover:bg-gray-100 text-gray-400 hover:text-red-600 transition-colors"
            aria-label="Logout"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </>
      )}
    </div>
  )

  if (collapsed) {
    return (
      <Tooltip content={user.email}>
        {content}
      </Tooltip>
    )
  }

  return content
}

interface ServiceHealthDotsProps {
  collapsed: boolean
}

function ServiceHealthDots({ collapsed }: ServiceHealthDotsProps) {
  const serviceHealth = useAppStore((state) => state.serviceHealth)

  // Fall back to showing all healthy when health data is not yet available
  const services =
    serviceHealth?.services.length
      ? serviceHealth.services
      : [
          { name: 'LLM', healthy: true },
          { name: 'PostgreSQL', healthy: true },
        ]

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-4 py-3 border-t border-gray-100',
        collapsed && 'justify-center px-2',
      )}
    >
      {services.map(({ name, healthy }) => (
        <Tooltip key={name} content={healthy ? `${name}: healthy` : `${name}: unavailable`}>
          <span
            className={cn(
              'h-2 w-2 rounded-full shrink-0',
              healthy ? 'bg-green-400' : 'bg-red-400',
            )}
          />
        </Tooltip>
      ))}
      {!collapsed && (
        <span className="text-xs text-gray-400 ml-1">Services</span>
      )}
    </div>
  )
}
