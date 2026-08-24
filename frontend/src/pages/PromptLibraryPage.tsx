import { BookOpenText, CheckCircle2, Search, SlidersHorizontal } from 'lucide-react'
import { useMemo, useState } from 'react'
import { api } from '../lib/api'
import { DataSourceBadge, EmptyState, ErrorState, LoadingState, PageHeader } from '../components/ui'
import { useApiResource } from '../hooks/useApiResource'
import { CATEGORY_IDS, CATEGORY_META, type CategoryId, type PromptCase, type Severity } from '../types'

export function PromptLibraryPage() {
  const { data, source, loading, error, reload } = useApiResource(() => api.getPrompts(), [])
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<CategoryId | 'all'>('all')
  const [severity, setSeverity] = useState<Severity | 'all'>('all')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return (data?.items ?? []).filter((prompt) => {
      const matchesSearch = !query || `${prompt.prompt} ${prompt.attack} ${prompt.tags.join(' ')}`.toLowerCase().includes(query)
      return matchesSearch && (category === 'all' || prompt.category === category) && (severity === 'all' || prompt.severity === severity)
    })
  }, [category, data, search, severity])

  const selected: PromptCase | undefined = filtered.find((prompt) => prompt.id === selectedId) ?? filtered[0]

  if (loading && !data) return <LoadingState label="Loading prompt library" />
  if (error) return <ErrorState onRetry={reload} />

  return (
    <>
      <PageHeader eyebrow="redteam-v1" title="Adversarial prompt library" description="A versioned challenge surface spanning six model-failure categories." action={<DataSourceBadge source={source} />} />

      <section className="library-summary solid-panel">
        <div><BookOpenText aria-hidden="true" /><div><strong>{data?.total ?? 0} prompts</strong><span>Versioned reference suite</span></div></div>
        <div className="coverage-dots" aria-label="All six failure categories represented">{CATEGORY_IDS.map((item) => <span key={item} title={CATEGORY_META[item].shortLabel} style={{ background: CATEGORY_META[item].color }} />)}</div>
        <span className="version-chip"><CheckCircle2 aria-hidden="true" size={15} /> Coverage verified</span>
      </section>

      <section className="filter-bar solid-panel" aria-label="Prompt filters">
        <label className="search-field"><Search aria-hidden="true" size={18} /><span className="sr-only">Search prompts</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search prompts, attacks, or tags" /></label>
        <label className="select-field"><SlidersHorizontal aria-hidden="true" size={17} /><span className="sr-only">Category</span><select value={category} onChange={(event) => setCategory(event.target.value as CategoryId | 'all')}><option value="all">All categories</option>{CATEGORY_IDS.map((item) => <option value={item} key={item}>{CATEGORY_META[item].shortLabel}</option>)}</select></label>
        <label className="select-field"><span className="sr-only">Severity</span><select value={severity} onChange={(event) => setSeverity(event.target.value as Severity | 'all')}><option value="all">All severities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
        <span className="result-count" aria-live="polite">{filtered.length} shown</span>
      </section>

      {filtered.length ? (
        <section className="master-detail">
          <div className="prompt-list" aria-label="Prompt cases">
            {filtered.map((prompt) => (
              <button type="button" className="prompt-row pressable" data-selected={selected?.id === prompt.id} onClick={() => setSelectedId(prompt.id)} key={prompt.id} aria-pressed={selected?.id === prompt.id}>
                <span className="prompt-row__id">{prompt.id}</span>
                <span className="category-dot" style={{ background: CATEGORY_META[prompt.category].color }} />
                <span className="prompt-row__body"><strong>{prompt.attack}</strong><small>{prompt.prompt}</small></span>
                <span className={`severity-chip severity-chip--${prompt.severity}`}>{prompt.severity}</span>
              </button>
            ))}
          </div>
          {selected && (
            <aside className="inspector solid-panel" aria-label={`Prompt ${selected.id} details`}>
              <div className="inspector__top"><span className="id-chip">{selected.id}</span><span className={`severity-chip severity-chip--${selected.severity}`}>{selected.severity}</span></div>
              <p className="eyebrow" style={{ color: CATEGORY_META[selected.category].color }}>{CATEGORY_META[selected.category].label}</p>
              <h2>{selected.attack}</h2>
              <div className="evidence-block"><span>Adversarial prompt</span><p>{selected.prompt}</p></div>
              <div className="evidence-block evidence-block--expected"><span>Expected safe behavior</span><p>{selected.expectedBehavior}</p></div>
              <div className="tag-list">{selected.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
            </aside>
          )}
        </section>
      ) : <EmptyState title="No prompts match these filters" description="Clear one or more filters to return to the complete challenge surface." />}
    </>
  )
}
