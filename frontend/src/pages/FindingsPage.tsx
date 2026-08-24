import { CheckCircle2, ExternalLink, Search, ShieldAlert, SlidersHorizontal } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { DataSourceBadge, EmptyState, ErrorState, LoadingState, PageHeader } from '../components/ui'
import { useApiResource } from '../hooks/useApiResource'
import { REMEDIATION } from '../lib/remediation'
import { CATEGORY_IDS, CATEGORY_META, type CategoryId, type Finding, type Severity } from '../types'

export function FindingsPage() {
  const [searchParams] = useSearchParams()
  const runId = searchParams.get('run') || undefined
  const { data, source, loading, error, reload } = useApiResource(() => api.getFindings(runId), [runId])
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<CategoryId | 'all'>('all')
  const [severity, setSeverity] = useState<Severity | 'all'>('all')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return (data ?? []).filter((finding) => {
      const searchable = `${finding.prompt} ${finding.response} ${finding.judgeReason} ${finding.metric}`.toLowerCase()
      return (!query || searchable.includes(query)) && (category === 'all' || finding.category === category) && (severity === 'all' || finding.severity === severity)
    })
  }, [category, data, search, severity])
  const selected: Finding | undefined = filtered.find((finding) => finding.id === selectedId) ?? filtered[0]

  if (loading && !data) return <LoadingState label="Loading evaluation findings" />
  if (error) return <ErrorState onRetry={reload} />

  return (
    <>
      <PageHeader eyebrow="Evidence registry" title="Findings inspector" description="Trace each violation from adversarial prompt to a targeted improvement and retest gate." action={<DataSourceBadge source={source} />} />

      <section className="filter-bar solid-panel" aria-label="Finding filters">
        <label className="search-field"><Search aria-hidden="true" size={18} /><span className="sr-only">Search findings</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search prompts, outputs, or rationale" /></label>
        <label className="select-field"><SlidersHorizontal aria-hidden="true" size={17} /><span className="sr-only">Category</span><select value={category} onChange={(event) => setCategory(event.target.value as CategoryId | 'all')}><option value="all">All categories</option>{CATEGORY_IDS.map((item) => <option value={item} key={item}>{CATEGORY_META[item].shortLabel}</option>)}</select></label>
        <label className="select-field"><span className="sr-only">Severity</span><select value={severity} onChange={(event) => setSeverity(event.target.value as Severity | 'all')}><option value="all">All severities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
        <span className="result-count" aria-live="polite">{filtered.length} findings</span>
      </section>

      {filtered.length ? (
        <section className="findings-layout">
          <div className="findings-list" aria-label="Evaluation findings">
            {filtered.map((finding) => (
              <button type="button" className="finding-card pressable" data-selected={selected?.id === finding.id} onClick={() => setSelectedId(finding.id)} key={finding.id} aria-pressed={selected?.id === finding.id}>
                <span className={`severity-marker severity-marker--${finding.severity}`} aria-hidden="true" />
                <span className="finding-card__body"><span><strong>{finding.severity}</strong><small>{finding.id}</small></span><b>{CATEGORY_META[finding.category].shortLabel}</b><p>{finding.judgeReason}</p><small>{finding.metric} · score {finding.score.toFixed(2)}</small></span>
              </button>
            ))}
          </div>

          {selected && (
            <aside className="finding-inspector solid-panel" aria-label={`Finding ${selected.id} evidence`}>
              <div className="inspector__top"><div><span className={`severity-chip severity-chip--${selected.severity}`}>{selected.severity}</span><span className="id-chip">{selected.id}</span></div>{selected.reproducible && <span className="verified-chip"><CheckCircle2 aria-hidden="true" size={15} /> Reproduced</span>}</div>
              <p className="eyebrow" style={{ color: CATEGORY_META[selected.category].color }}>{CATEGORY_META[selected.category].label}</p>
              <h2>{selected.metric}</h2>
              <div className="evidence-stack">
                <div className="evidence-block"><span>Adversarial prompt</span><p>{selected.prompt}</p></div>
                <div className="evidence-block evidence-block--response"><span>Model response</span><p>{selected.response}</p></div>
                <div className="evidence-block evidence-block--expected"><span>Expected behavior</span><p>{selected.expectedBehavior}</p></div>
                <div className="evidence-block evidence-block--judge"><span>Evaluator rationale</span><p>{selected.judgeReason}</p><small>{selected.evaluator} · score {selected.score.toFixed(2)}</small></div>
              </div>

              <section className="remediation-card" aria-labelledby="remediation-title">
                <ShieldAlert aria-hidden="true" />
                <div><p className="eyebrow">Targeted improvement</p><h3 id="remediation-title">{REMEDIATION[selected.category].title}</h3><p>{REMEDIATION[selected.category].action}</p><div className="retest-evidence"><strong>Retest evidence</strong><span>{REMEDIATION[selected.category].evidence}</span></div></div>
              </section>

              <div className="inspector-actions">
                {selected.traceUrl && <a href={selected.traceUrl} target="_blank" rel="noreferrer" className="button button--secondary pressable">Open LangSmith trace <ExternalLink aria-hidden="true" size={16} /></a>}
                <a href={`/runs/${encodeURIComponent(selected.runId)}`} className="button button--quiet pressable">Open source run</a>
              </div>
            </aside>
          )}
        </section>
      ) : <EmptyState title="No findings match these filters" description="Try another category, severity, or search term." />}
    </>
  )
}
