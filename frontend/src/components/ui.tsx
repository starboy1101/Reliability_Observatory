import type { ReactNode } from 'react'
import { AlertCircle, CheckCircle2, LoaderCircle, Radio, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { DataSource, EvaluationRun } from '../types'

export function DataSourceBadge({ source }: { source: DataSource }) {
  return (
    <span className={`source-badge source-badge--${source}`} title={source === 'live' ? 'Connected to the API' : 'Using safe local reference data'}>
      <Radio aria-hidden="true" size={13} />
      {source === 'live' ? 'Live workspace' : 'Reference demo'}
    </span>
  )
}

export function StatusPill({ status }: { status: EvaluationRun['status'] }) {
  const Icon = status === 'completed' ? CheckCircle2 : status === 'failed' ? AlertCircle : status === 'cancelled' || status === 'partial' ? TriangleAlert : LoaderCircle
  return (
    <span className={`status-pill status-pill--${status}`}>
      <Icon aria-hidden="true" size={14} className={status === 'running' ? 'spin' : undefined} />
      {status === 'queued' ? 'Queued' : status === 'partial' ? 'Partial' : status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="page-header__description">{description}</p>}
      </div>
      {action && <div className="page-header__action">{action}</div>}
    </header>
  )
}

export function MetricCard({
  label,
  value,
  detail,
  tone = 'neutral',
}: {
  label: string
  value: string
  detail: string
  tone?: 'neutral' | 'good' | 'warning' | 'danger'
}) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <p className="metric-card__label">{label}</p>
      <p className="metric-card__value">{value}</p>
      <p className="metric-card__detail">{detail}</p>
    </article>
  )
}

export function ProgressBar({ value, label }: { value: number; label: string }) {
  const safeValue = Math.max(0, Math.min(100, value))
  return (
    <div className="progress" aria-label={label}>
      <div className="progress__track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(safeValue)}>
        <span className="progress__fill" style={{ width: `${safeValue}%` }} />
      </div>
      <span>{Math.round(safeValue)}%</span>
    </div>
  )
}

export function LoadingState({ label = 'Loading workspace' }: { label?: string }) {
  return (
    <div className="state-card" role="status">
      <LoaderCircle aria-hidden="true" className="spin" />
      <div>
        <strong>{label}</strong>
        <p>Gathering the latest evaluation evidence.</p>
      </div>
    </div>
  )
}

export function ErrorState({ title = 'This view could not be loaded', onRetry }: { title?: string; onRetry?: () => void }) {
  return (
    <div className="state-card state-card--error" role="alert">
      <AlertCircle aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        <p>The connection failed without changing any data.</p>
        {onRetry && <button className="button button--secondary pressable" type="button" onClick={onRetry}>Try again</button>}
      </div>
    </div>
  )
}

export function EmptyState({
  title,
  description,
  actionLabel,
  actionTo,
}: {
  title: string
  description: string
  actionLabel?: string
  actionTo?: string
}) {
  return (
    <div className="empty-state">
      <div className="empty-state__mark" aria-hidden="true"><span /></div>
      <h2>{title}</h2>
      <p>{description}</p>
      {actionLabel && actionTo && <Link className="button button--primary pressable" to={actionTo}>{actionLabel}</Link>}
    </div>
  )
}
