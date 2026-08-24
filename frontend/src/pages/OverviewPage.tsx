import { ArrowDownRight, ArrowRight, ArrowUpRight, Clock3, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { ReliabilityLens } from '../components/ReliabilityLens'
import { DataSourceBadge, EmptyState, ErrorState, LoadingState, MetricCard, PageHeader, StatusPill } from '../components/ui'
import { useApiResource } from '../hooks/useApiResource'
import { CATEGORY_META, type CategoryId } from '../types'

function formatTime(value: string) {
  const date = new Date(value)
  const minutes = Math.max(1, Math.round((Date.now() - date.getTime()) / 60_000))
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 48) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}

export function OverviewPage() {
  const { data, source, loading, error, reload } = useApiResource(() => api.getOverview(), [])
  const [selected, setSelected] = useState<CategoryId | null>(null)

  if (loading && !data) return <LoadingState label="Loading reliability overview" />
  if (error) return <ErrorState onRetry={reload} />
  if (!data) return <EmptyState title="No evaluation evidence yet" description="Launch an evaluation to establish a reliability baseline." actionLabel="Create evaluation" actionTo="/runs/new" />

  const selectedMetric = selected ? data.categories.find((item) => item.category === selected) : null

  return (
    <>
      <PageHeader
        eyebrow="Deployment readiness"
        title="Evidence at a glance"
        description="A calm, current view of model risk across the complete adversarial suite."
        action={<DataSourceBadge source={source} />}
      />

      <section className="overview-grid">
        <article className="readiness-card solid-panel">
          <div className="card-heading">
            <div>
              <p className="eyebrow">Current gate</p>
              <h2>{data.readiness === 'ready' ? 'Ready for staged release' : data.readiness === 'review' ? 'Review before release' : 'Release blocked'}</h2>
            </div>
            <span className={`readiness-badge readiness-badge--${data.readiness}`}><ShieldCheck aria-hidden="true" size={16} /> {data.readiness}</span>
          </div>
          <ReliabilityLens score={data.readinessScore} categories={data.categories} selected={selected} onSelect={setSelected} />
          <div className="insight-line" role="status">
            {selectedMetric ? (
              <><span style={{ color: CATEGORY_META[selectedMetric.category].color }}>●</span><strong>{CATEGORY_META[selectedMetric.category].shortLabel}</strong><span>{selectedMetric.failed} failures across {selectedMetric.total || '—'} evaluated cases.</span></>
            ) : (
              <><span className="connection-dot" /><strong>All six categories</strong><span>Select a segment to isolate its evidence.</span></>
            )}
          </div>
        </article>

        <div className="overview-metrics">
          <MetricCard label="Reference hallucination" value={`${data.hallucinationRate}%`} detail="23 failures across 100 edge cases" tone="warning" />
          <MetricCard label="Violation reduction" value={`${data.violationReduction}%`} detail="100 → 39 violations after hardening" tone="good" />
          <MetricCard label="Adversarial coverage" value={`${data.promptCount}+`} detail="Versioned prompts across six categories" />
          <article className="next-action-card">
            <div><p className="eyebrow">Recommended next action</p><h3>Retest prompt injection</h3><p>Candidate performance improved, but two high-severity bypasses remain in the sample evidence.</p></div>
            <Link to="/runs/new" className="button button--secondary pressable">Configure focused run <ArrowRight aria-hidden="true" size={17} /></Link>
          </article>
        </div>
      </section>

      <section className="content-section">
        <div className="section-heading section-heading--row">
          <div><p className="eyebrow">Run history</p><h2>Recent evaluations</h2></div>
          <Link to="/runs/new" className="text-link pressable">New evaluation <ArrowRight aria-hidden="true" size={16} /></Link>
        </div>
        {data.recentRuns.length ? (
          <div className="table-shell">
            <table>
              <thead><tr><th>Evaluation</th><th>Model</th><th>Status</th><th>Failures</th><th>Started</th><th><span className="sr-only">Open</span></th></tr></thead>
              <tbody>
                {data.recentRuns.slice(0, 6).map((run) => (
                  <tr key={run.id}>
                    <td><Link to={`/runs/${run.id}`} className="table-primary">{run.name}</Link><small>{run.evaluator}</small></td>
                    <td>{run.model}</td>
                    <td><StatusPill status={run.status} /></td>
                    <td><span className={run.failedCases > run.totalCases * 0.15 ? 'metric-danger' : ''}>{run.failedCases}</span> / {run.totalCases}</td>
                    <td><span className="inline-meta"><Clock3 aria-hidden="true" size={14} />{formatTime(run.startedAt)}</span></td>
                    <td><Link to={`/runs/${run.id}`} className="icon-button pressable" aria-label={`Open ${run.name}`}><ArrowRight aria-hidden="true" size={18} /></Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No runs yet" description="Your first completed evaluation will appear here." actionLabel="Create evaluation" actionTo="/runs/new" />
        )}
      </section>

      <section className="category-grid" aria-label="Category risk summary">
        {data.categories.map((metric) => {
          const improved = (metric.delta ?? 0) < 0
          return (
            <article className="category-card" key={metric.category}>
              <div className="category-card__top"><span className="category-dot" style={{ background: CATEGORY_META[metric.category].color }} /><span>{CATEGORY_META[metric.category].shortLabel}</span>{improved ? <ArrowDownRight aria-label="Improved" size={17} /> : <ArrowUpRight aria-label="Needs attention" size={17} />}</div>
              <strong>{metric.rate.toFixed(metric.rate % 1 ? 1 : 0)}%</strong>
              <small>{metric.delta === undefined ? 'current failure rate' : `${Math.abs(metric.delta)} points ${improved ? 'lower' : 'higher'}`}</small>
            </article>
          )
        })}
      </section>
    </>
  )
}
