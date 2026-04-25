/**
 * Subject: src/components/ui/tabs.tsx — Tabs, TabsList, TabsTrigger, TabsContent
 * Scope:   Tab switching, default active tab, controlled value
 * Out of scope:
 *   - Radix UI keyboard navigation internals
 *   - Animation transitions between tabs
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Tabs, TabsList, TabsTrigger, TabsContent } from './tabs'

describe('Tabs', () => {
  // The tab corresponding to defaultValue should be active on initial render.
  it('shows default tab as active', () => {
    render(
      <Tabs defaultValue="tab1">
        <TabsList>
          <TabsTrigger value="tab1">First</TabsTrigger>
          <TabsTrigger value="tab2">Second</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Content 1</TabsContent>
        <TabsContent value="tab2">Content 2</TabsContent>
      </Tabs>,
    )
    expect(screen.getByRole('tab', { name: 'First' })).toHaveAttribute('data-state', 'active')
    expect(screen.getByText('Content 1')).toBeVisible()
  })

  // Clicking a different tab should switch the visible content and update active state.
  it('switches tabs when a trigger is clicked', async () => {
    const user = userEvent.setup()
    render(
      <Tabs defaultValue="tab1">
        <TabsList>
          <TabsTrigger value="tab1">First</TabsTrigger>
          <TabsTrigger value="tab2">Second</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Content 1</TabsContent>
        <TabsContent value="tab2">Content 2</TabsContent>
      </Tabs>,
    )
    await user.click(screen.getByRole('tab', { name: 'Second' }))
    expect(screen.getByRole('tab', { name: 'Second' })).toHaveAttribute('data-state', 'active')
    expect(screen.getByText('Content 2')).toBeVisible()
  })

  // Controlled mode: the active tab should follow the external value prop.
  it('respects controlled value prop', () => {
    const { rerender } = render(
      <Tabs value="tab1">
        <TabsList>
          <TabsTrigger value="tab1">First</TabsTrigger>
          <TabsTrigger value="tab2">Second</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Content 1</TabsContent>
        <TabsContent value="tab2">Content 2</TabsContent>
      </Tabs>,
    )
    expect(screen.getByRole('tab', { name: 'First' })).toHaveAttribute('data-state', 'active')
    rerender(
      <Tabs value="tab2">
        <TabsList>
          <TabsTrigger value="tab1">First</TabsTrigger>
          <TabsTrigger value="tab2">Second</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Content 1</TabsContent>
        <TabsContent value="tab2">Content 2</TabsContent>
      </Tabs>,
    )
    expect(screen.getByRole('tab', { name: 'Second' })).toHaveAttribute('data-state', 'active')
  })
})
