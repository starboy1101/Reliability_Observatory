import { ArrowDownRight, CheckCircle2, FlaskConical, Info, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { ReliabilityLens } from '../components/ReliabilityLens'
import { DataSourceBadge, EmptyState, ErrorState, LoadingState, MetricCard, PageHeader } from '../components/ui'
import { useApiResource } from '../hooks/useApiResource'
import { REMEDIATION } from '../lib/remediation'
import { CATEGORY_META, type CategoryMetric } from '../types'

export function ComparePage() {
  const { data, source, loading, error, reload } = useApiResource(() => api.getBenchmark(), [])
  if (loading && !data) return <LoadingState label="Loading reference comparison" />
  if (error) return <ErrorState onRetry={reload} />
  if (!data) return <EmptyState title="No comparison available" description="Complete a baseline and candidate run against the same suite." actionLabel="Create evaluation" actionTo="/runs/new" />

  const baselineCategories: CategoryMetric[] = data.categories.map((item) => ({ category: item.category, label: CATEGORY_META[item.category].label, total: 84, failed: Math.round(item.baseline * 0.84), rate: item.baseline }))
  const candidateCategories: CategoryMetric[] = data.categories.map((item) => ({ category: item.category, label: CATEGORY_META[item.category].label, total: 84, failed: Math.round(item.candidate * 0.84), rate: item.candidate, delta: item.candidate - item.baseline }))
  const baselineScore = Math.round(100 - data.violations.baseline / data.violations.total * 100)
  const candidateScore = Math.round(100 - data.violations.candidate / data.violations.total * 100)
  const remaining = [...data.categories].sort((a, b) => b.candidate - a.candidate).slice(0, 2)

  return (
    <>
      <PageHeader eyebrow="Reference benchmark" title="Baseline vs. externally hardened candidate" description="This workspace evaluates an externally fine-tuned model; it does not train or fine-tune models itself." action={<DataSourceBadge source={source} />} />

      <div className="sample-banner" role="note"><Info aria-hidden="true" size={17} /><span><strong>Sample-labeled evidence.</strong> {data.sampleLabel}. Use it to explore the workflow, not as a claim about another model.</span></div>

      <section className="comparison-metrics">
        <MetricCard label="Baseline hallucination" value={`${data.hallucination.rate}%`} detail={`${data.hallucination.failures} of ${data.hallucination.total} edge-case prompts`} tone="warning" />
        <MetricCard label="Violation reduction" value={`${data.violations.reduction}%`} detail={`${data.violations.baseline} → ${data.violations.candidate} of ${data.violations.total} prompts`} tone="good" />
        <MetricCard label="Reliability change" value={`+${candidateScore - baselineScore} pts`} detail={`${baselineScore} baseline → ${candidateScore} candidate`} tone="good" />
      </section>

      <section className="lens-comparison">
        <article className="comparison-model solid-panel">
          <div><p className="eyebrow">Baseline</p><h2>{data.baselineModel}</h2><span>{data.violations.baseline} policy violations</span></div>
          <ReliabilityLens score={baselineScore} categories={baselineCategories} compact title="Baseline reliability" />
        </article>
        <div className="comparison-change" aria-label={`${data.violations.reduction}% reduction`}><ArrowDownRight aria-hidden="true" /><strong>{data.violations.reduction}%</strong><span>fewer violations</span></div>
        <article className="comparison-model comparison-model--candidate solid-panel">
          <div><p className="eyebrow">Externally fine-tuned candidate</p><h2>{data.candidateModel}</h2><span>{data.violations.candidate} policy violations</span></div>
          <ReliabilityLens score={candidateScore} categories={candidateCategories} compact title="Candidate reliability" />
        </article>
      </section>

      <section className="content-section">
        <div className="section-heading"><p className="eyebrow">Category movement</p><h2>Every failure surface, side by side</h2><p>Lower is better. Rates use the same reference suite for both candidates.</p></div>
        <div className="comparison-bars">
          {data.categories.map((item) => (
            <article key={item.category}>
              <div className="comparison-bars__label"><span className="category-dot" style={{ background: CATEGORY_META[item.category].color }} /><strong>{CATEGORY_META[item.category].shortLabel}</strong><span>{item.baseline - item.candidate > 0 ? `${(item.baseline - item.candidate).toFixed(0)} pts lower` : 'No improvement'}</span></div>
              <div className="bar-pair">
                <div><span>Baseline</span><div><i style={{ width: `${item.baseline}%` }} /></div><strong>{item.baseline}%</strong></div>
                <div><span>Candidate</span><div><i style={{ width: `${item.candidate}%`, background: CATEGORY_META[item.category].color }} /></div><strong>{item.candidate}%</strong></div>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="content-section">
        <div className="section-heading"><p className="eyebrow">Remaining opportunities</p><h2>What to improve next</h2><p>Target the highest residual rates, then rerun the identical suite.</p></div>
        <div className="opportunity-grid">
          {remaining.map((item) => (
            <article className="opportunity-card solid-panel" key={item.category}>
              <span className="category-dot" style={{ background: CATEGORY_META[item.category].color }} />
              <div><p className="eyebrow">{item.candidate}% residual failure rate</p><h3>{REMEDIATION[item.category].title}</h3><p>{REMEDIATION[item.category].action}</p><small><CheckCircle2 aria-hidden="true" size={15} /> {REMEDIATION[item.category].evidence}</small></div>
            </article>
          ))}
          <article className="opportunity-card opportunity-card--action solid-panel"><Sparkles aria-hidden="true" /><div><p className="eyebrow">Close the loop</p><h3>Evaluate the next candidate</h3><p>Fine-tune externally, register the resulting endpoint, and test it against the same versioned prompts.</p><Link to="/runs/new" className="button button--primary pressable"><FlaskConical aria-hidden="true" size={17} /> Launch comparison run</Link></div></article>
        </div>
      </section>
    </>
  )
}
