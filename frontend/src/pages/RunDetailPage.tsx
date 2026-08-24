import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { Ban, CheckCircle2, Clock3, Download, ExternalLink, Radio, RotateCcw, ShieldAlert, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, runExportUrl } from '../lib/api'
import { ReliabilityLens } from '../components/ReliabilityLens'
import { DataSourceBadge, EmptyState, ErrorState, LoadingState, PageHeader, ProgressBar, StatusPill } from '../components/ui'
import { useApiResource } from '../hooks/useApiResource'
import { useLiveRun } from '../hooks/useLiveRun'
import { REMEDIATION } from '../lib/remediation'
import { CATEGORY_META, type CategoryId } from '../types'

const transportLabels = {
  connecting: 'Connecting to live updates',
  sse: 'Live via secure event stream',
  polling: 'Live via resilient polling',
  settled: 'Final result',
}

export function RunDetailPage() {
  const { runId } = useParams()
  const { run, source, transport, loading, error, refresh } = useLiveRun(runId)
  const findingRefreshBucket = Math.floor((run?.processedCases ?? 0) / 25)
  const findings = useApiResource(
    () => api.getFindings(runId),
    [runId, findingRefreshBucket, run?.status],
  )
  const [confirmCancel, setConfirmCancel] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const reducedMotion = useReducedMotion()

  if (loading && !run) return <LoadingState label="Opening evaluation run" />
  if (error || !run) return <ErrorState title="This evaluation run is unavailable" onRetry={() => void refresh()} />

  const eligibleCases = run.passedCases + run.failedCases
  const score = eligibleCases
    ? Math.max(0, Math.round(100 - (run.failedCases / eligibleCases) * 100))
    : 0
  const active = run.status === 'queued' || run.status === 'running'
  const visibleFindings = (findings.data ?? []).filter((finding) => finding.runId === run.id || source === 'demo').slice(0, Math.max(2, Math.ceil(run.progress / 18)))

  const cancel = async () => {
    setCancelling(true)
    await api.cancelRun(run.id)
    await refresh()
    setConfirmCancel(false)
    setCancelling(false)
  }

  return (
    <>
      <PageHeader
        eyebrow="Evaluation run"
        title={run.name}
        description={`${run.model} · ${run.evaluator}`}
        action={<div className="header-actions"><DataSourceBadge source={source} /><StatusPill status={run.status} /></div>}
      />

      <section className="run-hero solid-panel">
        <div className="run-progress-panel">
          <div className="run-live-line"><span className={`live-indicator ${active ? 'live-indicator--active' : ''}`}><Radio aria-hidden="true" size={15} />{transportLabels[transport]}</span><span>{run.processedCases} / {run.totalCases} cases</span></div>
          <h2>{run.status === 'completed' ? 'Evaluation complete' : run.status === 'cancelled' ? 'Evaluation cancelled' : 'Challenging the model'}</h2>
          <p>{active ? 'Results appear as soon as each case is judged. This page can be safely closed and reopened.' : `${run.passedCases} passed, ${run.failedCases} failed, and ${run.errorCases} evaluator errors.`}</p>
          <ProgressBar value={run.progress} label="Evaluation progress" />
          <div className="run-stats">
            <div><strong>{run.passedCases}</strong><span>passed</span></div>
            <div><strong>{run.failedCases}</strong><span>failed</span></div>
            <div><strong>{run.errorCases}</strong><span>errors</span></div>
          </div>
        </div>
        <ReliabilityLens score={score} categories={run.categories} compact title="Current run reliability" />
      </section>

      <section className="run-content-grid">
        <div>
          <div className="section-heading section-heading--row"><div><p className="eyebrow">Failure surface</p><h2>Category results</h2></div><span className="section-meta">Updated automatically</span></div>
          <div className="run-category-list">
            {run.categories.map((metric) => (
              <article key={metric.category}>
                <span className="category-dot" style={{ background: CATEGORY_META[metric.category].color }} />
                <div><strong>{CATEGORY_META[metric.category].shortLabel}</strong><small>{metric.failed} failed of {metric.total || 0}</small></div>
                <div className="mini-bar" aria-label={`${CATEGORY_META[metric.category].shortLabel}: ${metric.rate}% failure rate`}><span style={{ width: `${Math.min(100, metric.rate)}%`, background: CATEGORY_META[metric.category].color }} /></div>
                <strong>{metric.rate.toFixed(metric.rate % 1 ? 1 : 0)}%</strong>
              </article>
            ))}
          </div>
        </div>

        <aside className="remediation-panel solid-panel">
          <p className="eyebrow">Targeted opportunity</p>
          <ShieldAlert aria-hidden="true" size={25} />
          {(() => {
            const highest = [...run.categories].sort((a, b) => b.rate - a.rate)[0]
            return highest ? <><h2>{REMEDIATION[highest.category].title}</h2><p>{REMEDIATION[highest.category].action}</p><dl><div><dt>Observed</dt><dd>{highest.failed} violations</dd></div><div><dt>Retest gate</dt><dd>&lt; 10% failure rate</dd></div></dl></> : <><h2>No evidence yet</h2><p>A category-specific improvement will appear after the first result.</p></>
          })()}
          <Link to="/prompts" className="button button--secondary pressable">Inspect challenge cases</Link>
        </aside>
      </section>

      <section className="content-section">
        <div className="section-heading section-heading--row"><div><p className="eyebrow">Evidence stream</p><h2>Latest findings</h2></div><Link className="text-link pressable" to={`/findings?run=${encodeURIComponent(run.id)}`}>Open inspector</Link></div>
        {findings.loading && !findings.data ? <LoadingState label="Loading findings" /> : visibleFindings.length ? (
          <div className="finding-feed" aria-live="polite" aria-atomic="false">
            <AnimatePresence initial={false}>
              {visibleFindings.map((finding) => (
                <motion.article
                  key={finding.id}
                  className="finding-row"
                  initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={reducedMotion ? { duration: 0.16 } : { type: 'spring', bounce: 0, duration: 0.35 }}
                >
                  <span className={`severity-marker severity-marker--${finding.severity}`} aria-hidden="true" />
                  <div><span className="finding-row__meta"><strong>{finding.severity}</strong> · {CATEGORY_META[finding.category].shortLabel}</span><p>{finding.judgeReason}</p></div>
                  <span className="score-chip">{finding.score.toFixed(2)}</span>
                </motion.article>
              ))}
            </AnimatePresence>
          </div>
        ) : <EmptyState title="No violations found yet" description="Passing cases remain summarized above; violations will appear here as they are judged." />}
      </section>

      {!active && (
        <section className="report-actions solid-panel">
          <div><CheckCircle2 aria-hidden="true" /><div><h2>Evidence package ready</h2><p>Export the immutable run summary for review or downstream analysis.</p></div></div>
          <div><a className="button button--secondary pressable" href={runExportUrl(run.id, 'csv')}><Download aria-hidden="true" size={17} /> CSV</a><a className="button button--secondary pressable" href={runExportUrl(run.id, 'json')}><Download aria-hidden="true" size={17} /> JSON</a><Link className="button button--primary pressable" to="/compare">Compare candidate</Link></div>
        </section>
      )}

      {active && (
        <div className="run-control-dock material" role="region" aria-label="Active run controls">
          <div><span className="live-dot" /><div><strong>{run.status === 'queued' ? 'Waiting for a worker' : 'Evaluation in progress'}</strong><small><Clock3 aria-hidden="true" size={13} /> {Math.round(run.progress)}% complete</small></div></div>
          <AnimatePresence mode="wait" initial={false}>
            {confirmCancel ? (
              <motion.div className="cancel-confirm" key="confirm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><span>Stop after the current case?</span><button type="button" className="button button--danger pressable" disabled={cancelling} onClick={() => void cancel()}>{cancelling ? 'Stopping…' : 'Stop run'}</button><button type="button" className="icon-button pressable" onClick={() => setConfirmCancel(false)} aria-label="Keep evaluation running"><X aria-hidden="true" size={18} /></button></motion.div>
            ) : (
              <motion.button key="cancel" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} type="button" className="button button--quiet pressable" onClick={() => setConfirmCancel(true)}><Ban aria-hidden="true" size={17} /> Cancel run</motion.button>
            )}
          </AnimatePresence>
        </div>
      )}
    </>
  )
}
