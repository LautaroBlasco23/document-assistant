import * as React from 'react'
import { Eye, EyeOff, Loader2, CheckCircle2, XCircle, Key } from 'lucide-react'
import { Card } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { useProviderCredentials } from '../../hooks/useProviderCredentials'
import { cn } from '../../lib/cn'

const GEMINI_WARNING = 'Gemini Flash has a 250 request/day cap; Flash-Lite allows 1000. Avoid Flash for bulk generation.'

function ProviderRow({
  label,
  hint,
  needsKey,
  warning,
  configured,
  last4,
  lastTestedAt,
  lastTestOk,
  onSave,
  onDelete,
  onTest,
  saving,
  deleting,
  testing,
  error,
}: {
  label: string
  hint: string
  needsKey: boolean
  warning?: string
  configured: boolean
  last4: string | null
  lastTestedAt: string | null
  lastTestOk: boolean
  onSave: (key: string) => Promise<void>
  onDelete: () => Promise<void>
  onTest: () => Promise<void>
  saving: boolean
  deleting: boolean
  testing: boolean
  error: string | null
}) {
  const [key, setKey] = React.useState('')
  const [showKey, setShowKey] = React.useState(false)
  const [saveError, setSaveError] = React.useState('')
  const [testResult, setTestResult] = React.useState<{ ok: boolean; error?: string; model_count?: number } | null>(null)

  const handleSaveAndTest = async () => {
    setSaveError('')
    setTestResult(null)
    try {
      await onSave(key)
      await onTest()
    } catch (e) {
      setSaveError((e as Error).message || 'Failed to save')
    }
  }

  const handleTest = async () => {
    setTestResult(null)
    try {
      await onTest()
    } catch (e) {
      // error surfaced via hook
    }
  }

  const badge = React.useMemo(() => {
    if (lastTestOk) {
      return { icon: CheckCircle2, color: 'text-success', label: 'Connected' }
    }
    if (lastTestedAt && !lastTestOk) {
      return { icon: XCircle, color: 'text-danger', label: 'Failed' }
    }
    if (configured) {
      return { icon: CheckCircle2, color: 'text-success', label: 'Configured' }
    }
    if (!needsKey) {
      return { icon: CheckCircle2, color: 'text-info', label: 'No key needed' }
    }
    return null
  }, [configured, needsKey, lastTestOk, lastTestedAt])

  return (
    <div className="border-b border-surface-200 dark:border-surface-200 last:border-b-0 py-4 first:pt-0 last:pb-0">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-text-secondary">{label}</span>
          {badge && (
            <span className={cn('flex items-center gap-1 text-xs shrink-0', badge.color)}>
              <badge.icon className="h-3.5 w-3.5" />
              {badge.label}
            </span>
          )}
          {lastTestedAt && (
            <span className="text-xs text-text-tertiary">
              {new Date(lastTestedAt).toLocaleDateString()}
            </span>
          )}
        </div>
        {!needsKey && (
          <span className="text-xs text-text-tertiary">system-managed</span>
        )}
      </div>

      {hint && (
        <p className="text-xs text-text-tertiary mb-2">{hint}</p>
      )}

      {warning && (
        <p className="text-xs text-warning mb-2">{warning}</p>
      )}

      {needsKey && (
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={showKey ? 'text' : 'password'}
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder={configured ? `••••${last4 ?? ''}` : 'Enter API key...'}
                className="w-full px-3 py-2 pr-9 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
              <button
                type="button"
                onClick={() => setShowKey((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-secondary"
                title={showKey ? 'Hide key' : 'Show key'}
              >
                {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={handleSaveAndTest}
              disabled={saving || !key.trim()}
            >
              {saving ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
                  Saving...
                </>
              ) : (
                'Save & Test'
              )}
            </Button>
            {configured && (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleTest}
                disabled={testing}
              >
                {testing ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  'Test'
                )}
              </Button>
            )}
            {configured && (
              <Button
                variant="secondary"
                size="sm"
                onClick={onDelete}
                disabled={deleting}
                className="text-danger hover:text-red-700 hover:bg-danger-light dark:hover:bg-red-900/20"
              >
                {deleting ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  'Delete'
                )}
              </Button>
            )}
          </div>
          {(saveError || error) && (
            <p className="text-xs text-danger">{saveError || error}</p>
          )}
          {testResult && (
            <p className={cn('text-xs', testResult.ok ? 'text-success' : 'text-danger')}>
              {testResult.ok
                ? `Connection successful${testResult.model_count != null ? ` (${testResult.model_count} models available)` : ''}`
                : testResult.error ?? 'Connection failed'}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export function ApiKeysCard() {
  const {
    useProviders,
    useCredentials,
    useSaveCredential,
    useDeleteCredential,
    useTestConnection,
  } = useProviderCredentials()

  const { providers, loading: providersLoading } = useProviders()
  const { credentials, loading: credsLoading, refresh: refreshCreds } = useCredentials()
  const { execute: saveCred, loading: saving } = useSaveCredential()
  const { execute: delCred, loading: deleting } = useDeleteCredential()
  const { execute: testConn, loading: testing } = useTestConnection()

  const [activeProvider, setActiveProvider] = React.useState<string | null>(null)
  const [rowError, setRowError] = React.useState<string | null>(null)

  const credMap = React.useMemo(() => {
    const map = new Map<string, typeof credentials[number]>()
    for (const c of credentials) {
      map.set(c.provider, c)
    }
    return map
  }, [credentials])

  const getError = (provider: string) => (activeProvider === provider ? rowError : null)

  return (
    <Card
      title="API Keys"
      actions={<Key className="h-4 w-4 text-text-tertiary" />}
    >
      {providersLoading || credsLoading ? (
        <div className="flex items-center gap-2 text-sm text-text-tertiary py-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading providers...
        </div>
      ) : (
        <div>
          {providers.map((p) => {
            const cred = credMap.get(p.slug)
            return (
              <ProviderRow
                key={p.slug}
                label={p.label}
                hint={p.key_format_hint}
                needsKey={p.key_required}
                warning={p.slug === 'gemini' ? GEMINI_WARNING : undefined}
                configured={cred?.configured ?? false}
                last4={cred?.last4 ?? null}
                lastTestedAt={cred?.last_tested_at ?? null}
                lastTestOk={cred?.last_test_ok ?? false}
                onSave={async (key) => {
                  setActiveProvider(p.slug)
                  setRowError(null)
                  await saveCred(p.slug, key)
                  refreshCreds()
                }}
                onDelete={async () => {
                  setActiveProvider(p.slug)
                  setRowError(null)
                  await delCred(p.slug)
                  refreshCreds()
                }}
                onTest={async () => {
                  setActiveProvider(p.slug)
                  try {
                    await testConn(p.slug)
                  } catch (e) {
                    setRowError((e as Error).message || 'Test failed')
                  }
                  refreshCreds()
                }}
                saving={activeProvider === p.slug && saving}
                deleting={activeProvider === p.slug && deleting}
                testing={activeProvider === p.slug && testing}
                error={getError(p.slug)}
              />
            )
          })}
        </div>
      )}
    </Card>
  )
}
