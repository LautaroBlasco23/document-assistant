import * as React from 'react'
import { Link } from 'react-router-dom'
import { cn } from '../../lib/cn'

export interface BreadcrumbItem {
  label: string
  href?: string
}

export interface HeaderProps {
  title: string
  breadcrumbs?: BreadcrumbItem[]
  actions?: React.ReactNode
  className?: string
}

export function Header({ title, breadcrumbs, actions, className }: HeaderProps) {
  return (
    <div className={cn('flex items-center justify-between mb-6', className)}>
      <div className="flex flex-col gap-1">
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="flex items-center gap-1 text-xs text-text-tertiary" aria-label="Breadcrumb">
            {breadcrumbs.map((crumb, index) => (
              <React.Fragment key={index}>
                {index > 0 && <span className="text-text-tertiary">/</span>}
                {crumb.href ? (
                  <Link
                    to={crumb.href}
                    className="hover:text-text-secondary transition-colors"
                  >
                    {crumb.label}
                  </Link>
                ) : (
                  <span className="text-text-secondary">{crumb.label}</span>
                )}
              </React.Fragment>
            ))}
          </nav>
        )}
        <h1 className="text-xl font-semibold text-text-primary">{title}</h1>
      </div>
      {actions && (
        <div className="flex items-center gap-3 ml-4">{actions}</div>
      )}
    </div>
  )
}
