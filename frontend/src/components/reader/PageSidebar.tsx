interface PageSidebarProps {
  numPages: number
  currentPage: number
  onPageClick: (pageNumber: number) => void
}

export function PageSidebar({ numPages, currentPage, onPageClick }: PageSidebarProps) {
  if (numPages === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-gray-400">
        No pages loaded
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-200 shrink-0">
        Pages
      </div>
      <div className="flex-1 overflow-y-auto p-1">
        {Array.from({ length: numPages }, (_, i) => {
          const pageNumber = i + 1
          const isActive = pageNumber === currentPage
          return (
            <button
              key={pageNumber}
              onClick={() => onPageClick(pageNumber)}
              className={`w-full text-left px-3 py-1.5 text-xs rounded-md transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700 font-medium border-l-2 border-blue-500'
                  : 'text-gray-600 hover:bg-gray-100 border-l-2 border-transparent'
              }`}
            >
              Page {pageNumber}
            </button>
          )
        })}
      </div>
    </div>
  )
}
