import { useAppStore } from '../../stores/app-store'
import type { UserLimits } from '../../types/api'

export function PlanPage() {
  const limits = useAppStore((state) => state.limits)

  if (!limits) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-surface-200 dark:bg-surface-200 rounded w-1/3"></div>
          <div className="h-32 bg-surface-200 dark:bg-surface-200 rounded"></div>
        </div>
      </div>
    )
  }

  return <PlanContent limits={limits} />
}

function PlanContent({ limits }: { limits: UserLimits }) {
  const treePercent = limits.max_knowledge_trees > 0
    ? Math.min((limits.current_knowledge_trees / limits.max_knowledge_trees) * 100, 100)
    : 0
  const docPercent = limits.max_documents > 0
    ? Math.min((limits.current_documents / limits.max_documents) * 100, 100)
    : 0

  const planName = limits.plan?.name ?? 'Free'
  const planDescription = limits.plan?.description

  return (
    <div className="p-6 max-w-2xl">
      <h2 className="text-2xl font-bold mb-6">Your Plan</h2>

      <div className="space-y-6">
        {/* Knowledge Trees */}
        <div className="bg-surface dark:bg-surface-200 border border-surface-200 dark:border-surface-200 rounded-lg p-5">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold text-text-primary">Knowledge Trees</h3>
            <span className="text-sm font-medium text-text-secondary">
              {limits.current_knowledge_trees} / {limits.max_knowledge_trees}
            </span>
          </div>
          <div className="w-full bg-surface-200 dark:bg-surface-200 rounded-full h-2.5 mb-3">
            <div
              className={`h-2.5 rounded-full transition-all ${
                treePercent >= 90 ? 'bg-error' : 'bg-primary'
              }`}
              style={{ width: `${treePercent}%` }}
            />
          </div>
          {!limits.can_create_tree && (
            <p className="text-sm text-error">
              You've reached your knowledge tree limit. Delete some trees or contact admin to upgrade.
            </p>
          )}
        </div>

        {/* Documents */}
        <div className="bg-surface dark:bg-surface-200 border border-surface-200 dark:border-surface-200 rounded-lg p-5">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold text-text-primary">Documents</h3>
            <span className="text-sm font-medium text-text-secondary">
              {limits.current_documents} / {limits.max_documents}
            </span>
          </div>
          <div className="w-full bg-surface-200 dark:bg-surface-200 rounded-full h-2.5 mb-3">
            <div
              className={`h-2.5 rounded-full transition-all ${
                docPercent >= 90 ? 'bg-error' : 'bg-success'
              }`}
              style={{ width: `${docPercent}%` }}
            />
          </div>
          {!limits.can_create_document && (
            <p className="text-sm text-error">
              You've reached your document limit. Delete some documents or contact admin to upgrade.
            </p>
          )}
        </div>

        {/* Plan Info */}
        <div className="bg-primary-light dark:bg-primary/12 border border-primary/20 dark:border-primary/30 rounded-lg p-4">
          <h4 className="font-medium text-primary mb-2">{planName} Plan</h4>
          <p className="text-sm text-primary">
            {planDescription
              ? `${planDescription} You have ${limits.max_knowledge_trees} knowledge trees and ${limits.max_documents} documents.`
              : `You're on the ${planName} plan with ${limits.max_knowledge_trees} knowledge trees and ${limits.max_documents} documents.`}{' '}
            Contact your admin to upgrade to a higher plan.
          </p>
        </div>
      </div>
    </div>
  )
}
