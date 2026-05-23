import * as React from 'react'
import { cn } from '../../lib/cn'

export const readerMarkdownComponents = {
  h1: ({ children }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h1 className="text-2xl font-bold mb-3 mt-6 first:mt-0 text-text-primary">{children}</h1>
  ),
  h2: ({ children }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h2 className="text-xl font-semibold mb-2 mt-5 first:mt-0 text-text-primary">{children}</h2>
  ),
  h3: ({ children }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h3 className="text-lg font-semibold mb-2 mt-4 first:mt-0 text-text-primary">{children}</h3>
  ),
  h4: ({ children }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h4 className="text-base font-semibold mb-1 mt-3 first:mt-0 text-text-primary">{children}</h4>
  ),
  p: ({ children }: React.HTMLAttributes<HTMLParagraphElement>) => (
    <p className="mb-3 last:mb-0">{children}</p>
  ),
  ul: ({ children }: React.HTMLAttributes<HTMLUListElement>) => (
    <ul className="list-disc pl-5 mb-3 last:mb-0 space-y-1">{children}</ul>
  ),
  ol: ({ children }: React.HTMLAttributes<HTMLOListElement>) => (
    <ol className="list-decimal pl-5 mb-3 last:mb-0 space-y-1">{children}</ol>
  ),
  li: ({ children }: React.HTMLAttributes<HTMLLIElement>) => (
    <li className="leading-relaxed">{children}</li>
  ),
  blockquote: ({ children }: React.HTMLAttributes<HTMLQuoteElement>) => (
    <blockquote className="border-l-4 border-surface-200 dark:border-surface-200 pl-4 my-3 italic text-text-secondary">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-4 border-t border-surface-200 dark:border-surface-200" />,
  strong: ({ children }: React.HTMLAttributes<HTMLElement>) => (
    <strong className="font-bold text-text-primary">{children}</strong>
  ),
  em: ({ children }: React.HTMLAttributes<HTMLElement>) => (
    <em className="italic">{children}</em>
  ),
  pre: ({ children, ...props }: React.HTMLAttributes<HTMLPreElement>) => (
    <pre
      className="bg-surface-100 dark:bg-surface-100 rounded-md p-4 my-3 text-sm font-mono overflow-x-auto"
      {...props}
    >
      {children}
    </pre>
  ),
  code: ({ children, className, ...props }: React.HTMLAttributes<HTMLElement> & { className?: string }) => {
    if (className) {
      return (
        <code className={cn('text-sm font-mono', className)} {...props}>
          {children}
        </code>
      )
    }
    return (
      <code
        className="bg-surface-100 dark:bg-surface-100 px-1.5 py-0.5 rounded text-sm font-mono"
        {...props}
      >
        {children}
      </code>
    )
  },
  img: ({ src, alt, ...props }: React.ImgHTMLAttributes<HTMLImageElement>) => (
    <img
      src={src}
      alt={alt ?? ''}
      className="max-w-full h-auto rounded-md my-4 mx-auto block"
      loading="lazy"
      {...props}
    />
  ),
  a: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary underline hover:text-primary-hover"
      {...props}
    >
      {children}
    </a>
  ),
  table: ({ children }: React.HTMLAttributes<HTMLTableElement>) => (
    <div className="overflow-x-auto my-3">
      <table className="w-full text-sm border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }: React.HTMLAttributes<HTMLTableSectionElement>) => (
    <thead className="border-b border-surface-200 dark:border-surface-200">{children}</thead>
  ),
  th: ({ children }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
    <th className="px-3 py-2 text-left font-semibold text-text-primary">{children}</th>
  ),
  td: ({ children }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
    <td className="px-3 py-2 border-t border-surface-200 dark:border-surface-200">{children}</td>
  ),
}
