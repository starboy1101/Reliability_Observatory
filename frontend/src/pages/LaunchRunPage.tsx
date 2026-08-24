import { ArrowRight, Check, Cpu, FlaskConical, Info, Server, ShieldCheck, Sparkles } from 'lucide-react'
import { useMemo, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { PageHeader } from '../components/ui'
import { CATEGORY_IDS, CATEGORY_META, type CategoryId, type LaunchRunInput } from '../types'

const targets: Array<{
  value: LaunchRunInput['targetKind']
  name: string
  description: string
  Icon: typeof Cpu
}> = [
  { value: 'demo_hardened', name: 'Hardened demo', description: 'Safe built-in target with lower seeded failure rates.', Icon: ShieldCheck },
  { value: 'demo_baseline', name: 'Baseline demo', description: 'Safe built-in target that demonstrates common violations.', Icon: Sparkles },
  { value: 'openai_compatible', name: 'OpenAI-compatible', description: 'A server-approved endpoint configured for this workspace.', Icon: Server },
]

export function LaunchRunPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('Release candidate · adversarial suite')
  const [targetKind, setTargetKind] = useState<LaunchRunInput['targetKind']>('demo_hardened')
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [evaluator, setEvaluator] = useState<LaunchRunInput['evaluator']>('deterministic')
  const [categories, setCategories] = useState<CategoryId[]>(CATEGORY_IDS)
  const [limit, setLimit] = useState(600)
  const [concurrency, setConcurrency] = useState(4)
  const [launching, setLaunching] = useState(false)
  const [error, setError] = useState('')

  const estimatedMinutes = useMemo(
    () => Math.max(1, Math.ceil(limit / Math.max(1, concurrency) / 45)),
    [concurrency, limit],
  )

  const toggleCategory = (category: CategoryId) => {
    setCategories((current) =>
      current.includes(category)
        ? current.length > 1
          ? current.filter((item) => item !== category)
          : current
        : [...current, category],
    )
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!name.trim()) {
      setError('Give this evaluation a recognizable name.')
      return
    }
    if (targetKind === 'openai_compatible' && (!model.trim() || !baseUrl.trim())) {
      setError('Model name and server-approved base URL are required for this target.')
      return
    }
    setLaunching(true)
    setError('')
    try {
      const result = await api.launchRun({
        name: name.trim(),
        targetKind,
        model: model.trim() || undefined,
        baseUrl: baseUrl.trim() || undefined,
        evaluator,
        categories,
        limit,
        concurrency,
      })
      navigate(`/runs/${result.data.id}`, { state: { source: result.source } })
    } catch (value) {
      setError(
        value instanceof Error
          ? value.message
          : 'The evaluation could not be launched. No target requests were sent.',
      )
      setLaunching(false)
    }
  }

  return (
    <>
      <PageHeader eyebrow="New evaluation" title="Configure the evidence you need" description="Start with the common path, then tune scope and throughput only when needed." />
      <form className="launcher" onSubmit={submit} noValidate>
        <div className="launcher__main">
          <section className="form-section solid-panel" aria-labelledby="run-details-title">
            <div className="step-heading"><span>1</span><div><h2 id="run-details-title">Name the decision</h2><p>Make the run recognizable in reports and comparisons.</p></div></div>
            <label className="field"><span>Evaluation name</span><input value={name} onChange={(event) => setName(event.target.value)} required maxLength={100} /></label>
          </section>

          <section className="form-section solid-panel" aria-labelledby="target-title">
            <div className="step-heading"><span>2</span><div><h2 id="target-title">Choose a target</h2><p>Demo targets are isolated; external targets must pass server policy.</p></div></div>
            <div className="choice-grid">
              {targets.map(({ value, name: targetName, description, Icon }) => (
                <label className="choice-card pressable" data-selected={targetKind === value} key={value}>
                  <input type="radio" name="target" value={value} checked={targetKind === value} onChange={() => setTargetKind(value)} />
                  <Icon aria-hidden="true" size={23} />
                  <span><strong>{targetName}</strong><small>{description}</small></span>
                  <span className="choice-card__check" aria-hidden="true"><Check size={14} /></span>
                </label>
              ))}
            </div>
            {targetKind === 'openai_compatible' && (
              <div className="field-grid field-grid--two reveal-region">
                <label className="field"><span>Model name</span><input value={model} onChange={(event) => setModel(event.target.value)} placeholder="your-model-id" required /></label>
                <label className="field"><span>Base URL</span><input type="url" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="https://approved-host.example/v1" required /></label>
                <p className="field-note"><ShieldCheck aria-hidden="true" size={16} /> Credentials are never entered here. The server resolves a fixed environment secret and blocks private or unapproved hosts.</p>
              </div>
            )}
          </section>

          <section className="form-section solid-panel" aria-labelledby="scope-title">
            <div className="step-heading"><span>3</span><div><h2 id="scope-title">Set the challenge surface</h2><p>All six failure categories are selected by default.</p></div></div>
            <div className="category-choices">
              {CATEGORY_IDS.map((category) => (
                <label className="category-choice pressable" data-selected={categories.includes(category)} key={category}>
                  <input type="checkbox" checked={categories.includes(category)} onChange={() => toggleCategory(category)} />
                  <span className="category-dot" style={{ background: CATEGORY_META[category].color }} />
                  <span><strong>{CATEGORY_META[category].shortLabel}</strong><small>{CATEGORY_META[category].description}</small></span>
                  <span className="choice-card__check" aria-hidden="true"><Check size={14} /></span>
                </label>
              ))}
            </div>
            <div className="field-grid field-grid--three">
              <label className="field"><span>Evaluator</span><select value={evaluator} onChange={(event) => setEvaluator(event.target.value as LaunchRunInput['evaluator'])}><option value="deterministic">Deterministic policy</option><option value="deepeval">DeepEval (server setup required)</option></select></label>
              <label className="field"><span>Prompt limit</span><input type="number" min={6} max={600} step={6} value={limit} onChange={(event) => setLimit(Math.min(600, Math.max(6, Number(event.target.value))))} /><small>600 runs the complete suite; the reference comparison remains a fixed 500-case benchmark.</small></label>
              <label className="field"><span>Concurrency</span><select value={concurrency} onChange={(event) => setConcurrency(Number(event.target.value))}><option value={1}>1 worker</option><option value={2}>2 workers</option><option value={4}>4 workers</option><option value={8}>8 workers</option></select></label>
            </div>
          </section>
        </div>

        <aside className="launch-summary solid-panel" aria-label="Evaluation summary">
          <p className="eyebrow">Ready to launch</p>
          <h2>{limit} adversarial prompts</h2>
          <dl>
            <div><dt>Target</dt><dd>{targets.find((target) => target.value === targetKind)?.name}</dd></div>
            <div><dt>Categories</dt><dd>{categories.length} of 6</dd></div>
            <div><dt>Evaluator</dt><dd>{evaluator === 'deepeval' ? 'DeepEval' : 'Deterministic'}</dd></div>
            <div><dt>Estimated time</dt><dd>~{estimatedMinutes} min</dd></div>
          </dl>
          <div className="summary-note"><Info aria-hidden="true" size={17} /><p>Results stream into the run view. You can leave and return without interrupting evaluation.</p></div>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button type="submit" className="button button--primary button--large pressable" disabled={launching}>
            {launching ? <><span className="button-spinner" /> Launching…</> : <><FlaskConical aria-hidden="true" size={18} /> Launch evaluation <ArrowRight aria-hidden="true" size={18} /></>}
          </button>
        </aside>
      </form>
    </>
  )
}
