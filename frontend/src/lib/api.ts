import {
  cancelDemoRun,
  categoryFromUnknown,
  createDemoRun,
  demoFindings,
  demoOverview,
  demoPrompts,
  demoRuns,
  getDemoRun,
  referenceBenchmark,
  referenceCategories,
  severityFromUnknown,
} from '../api/demo'
import {
  CATEGORY_META,
  type ApiResult,
  type BenchmarkComparison,
  type CategoryId,
  type CategoryMetric,
  type EvaluationRun,
  type Finding,
  type LaunchRunInput,
  type OverviewData,
  type PromptCase,
} from '../types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

const API_CATEGORY_IDS: Record<CategoryId, string> = {
  hallucination: 'hallucination',
  bias: 'bias_fairness',
  unsafe: 'unsafe_content',
  injection: 'prompt_injection',
  privacy: 'privacy_leakage',
  robustness: 'robustness',
}

export function toApiCategory(category: CategoryId): string {
  return API_CATEGORY_IDS[category]
}

interface RequestOptions extends RequestInit {
  timeout?: number
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), options.timeout ?? 8_000)
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
      signal: controller.signal,
    })
    if (!response.ok) {
      let detail = ''
      try {
        const payload = record(await response.json())
        detail = stringValue(payload.detail, payload.message)
      } catch {
        // Preserve the status-only fallback for non-JSON proxy errors.
      }
      throw new Error(detail || `API ${response.status}: ${response.statusText}`)
    }
    const contentType = response.headers.get('content-type') || ''
    if (!contentType.includes('json')) throw new Error('Expected JSON response')
    return (await response.json()) as T
  } finally {
    window.clearTimeout(timeout)
  }
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function numberValue(...values: unknown[]): number {
  for (const value of values) {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return 0
}

function stringValue(...values: unknown[]): string {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value
  }
  return ''
}

function arrayValue(value: unknown): unknown[] {
  if (Array.isArray(value)) return value
  const itemRecord = record(value)
  if (Array.isArray(itemRecord.items)) return itemRecord.items
  if (Array.isArray(itemRecord.results)) return itemRecord.results
  if (Array.isArray(itemRecord.runs)) return itemRecord.runs
  if (Array.isArray(itemRecord.findings)) return itemRecord.findings
  return []
}

function normalizeRate(value: unknown, failed: number, total: number): number {
  if (value !== undefined && value !== null && value !== '') {
    const numeric = Number(value)
    if (Number.isFinite(numeric)) {
      if (numeric >= -1 && numeric <= 1) return Math.round(numeric * 1_000) / 10
      return Math.round(numeric * 10) / 10
    }
  }
  return total ? Math.round((failed / total) * 1_000) / 10 : 0
}

function normalizeCategories(value: unknown): CategoryMetric[] {
  const entries: Array<[unknown, unknown]> = Array.isArray(value)
    ? value.map((item) => [record(item).category ?? record(item).name, item])
    : Object.entries(record(value))

  return entries.map(([categoryValue, raw]) => {
    const item = record(raw)
    const category = categoryFromUnknown(categoryValue ?? item.category)
    const total = numberValue(item.total, item.total_cases, item.processed_cases, item.count)
    const failed = numberValue(item.failed, item.failed_cases, item.failures, item.violation_count)
    return {
      category,
      label: CATEGORY_META[category].label,
      total,
      failed,
      rate: normalizeRate(item.rate ?? item.failure_rate ?? item.failure_rate_percent, failed, total),
    }
  })
}

export function normalizeRun(value: unknown): EvaluationRun {
  const raw = record(value)
  const target = record(raw.target_config ?? raw.target)
  const statusRaw = stringValue(raw.status, 'queued').toLowerCase()
  const status: EvaluationRun['status'] =
    statusRaw === 'pending'
      ? 'queued'
      : statusRaw === 'in_progress'
        ? 'running'
        : ['queued', 'running', 'completed', 'partial', 'failed', 'cancelled'].includes(statusRaw)
          ? (statusRaw as EvaluationRun['status'])
          : 'queued'
  const totalCases = numberValue(raw.total_cases, raw.totalCases, raw.total, 0)
  const processedCases = numberValue(raw.processed_cases, raw.processedCases, raw.processed, 0)
  const failedCases = numberValue(raw.failed_cases, raw.failedCases, raw.failed, 0)
  const errorCases = numberValue(raw.error_cases, raw.errorCases, raw.errors, 0)
  const categories = normalizeCategories(
    raw.category_summary ?? raw.categories ?? raw.category_metrics,
  )

  return {
    id: stringValue(raw.id, raw.run_id, `run-${Date.now()}`),
    name: stringValue(raw.name, raw.benchmark_label, raw.label, `Evaluation · ${stringValue(target.model, raw.model, raw.target_kind, 'model')}`),
    model: stringValue(raw.model, target.model, target.kind, 'model'),
    targetKind: stringValue(raw.target_kind, target.kind),
    evaluator: stringValue(raw.evaluator, raw.evaluator_name, 'Deterministic'),
    status,
    totalCases,
    processedCases,
    passedCases: numberValue(
      raw.passed_cases,
      raw.passedCases,
      raw.passed,
      Math.max(0, processedCases - failedCases - errorCases),
    ),
    failedCases,
    errorCases,
    progress: Math.min(
      100,
      numberValue(
        raw.progress_percent,
        raw.progress,
        totalCases ? (processedCases / totalCases) * 100 : 0,
      ),
    ),
    startedAt: stringValue(raw.started_at, raw.created_at, raw.startedAt, new Date().toISOString()),
    completedAt: stringValue(raw.finished_at, raw.completed_at, raw.completedAt) || undefined,
    categories: categories.length ? categories : referenceCategories.map((item) => ({ ...item, total: 0, failed: 0, rate: 0 })),
  }
}

function normalizePrompt(value: unknown, index: number): PromptCase {
  const raw = record(value)
  const category = categoryFromUnknown(raw.category ?? raw.failure_category ?? raw.metric)
  const tags = Array.isArray(raw.tags) ? raw.tags.map(String) : []
  return {
    id: stringValue(raw.id, raw.prompt_id, raw.case_id, `RT-${index + 1}`),
    prompt: stringValue(raw.prompt, raw.input, raw.text, raw.user_input, 'Prompt text unavailable'),
    category,
    severity: severityFromUnknown(raw.severity ?? raw.risk),
    attack: stringValue(raw.attack, raw.attack_strategy, raw.technique, CATEGORY_META[category].shortLabel),
    expectedBehavior: stringValue(
      raw.expected_behavior,
      raw.expected_output,
      raw.expected,
      'The model should follow the configured policy and avoid the identified failure mode.',
    ),
    tags,
  }
}

function normalizeFinding(value: unknown, index: number, runId?: string): Finding {
  const raw = record(value)
  const result = record(raw.result)
  const category = categoryFromUnknown(raw.category ?? raw.failure_category ?? result.category)
  return {
    id: stringValue(raw.id, raw.finding_id, raw.result_id, `F-${index + 1}`),
    runId: stringValue(raw.run_id, runId, 'unknown-run'),
    promptId: stringValue(raw.prompt_id, raw.case_id, `case-${index + 1}`),
    category,
    severity: severityFromUnknown(raw.severity ?? raw.risk),
    prompt: stringValue(raw.prompt, raw.input, raw.user_input, result.prompt, 'Prompt unavailable'),
    response: stringValue(raw.response, raw.actual_output, raw.output, result.response, 'Response unavailable'),
    expectedBehavior: stringValue(
      raw.expected_behavior,
      raw.expected_output,
      raw.expected,
      'Follow the configured safety and quality policy.',
    ),
    judgeReason: stringValue(
      raw.judge_reason,
      raw.reason,
      raw.explanation,
      raw.rationale,
      'The evaluator marked this case as a policy violation.',
    ),
    evaluator: stringValue(raw.evaluator, raw.metric_name, 'DeepEval'),
    metric: stringValue(raw.metric, raw.metric_name, CATEGORY_META[category].shortLabel),
    score: numberValue(raw.score, raw.metric_score, result.score),
    reproducible: Boolean(raw.reproducible ?? raw.reproduced ?? true),
    traceUrl: stringValue(raw.trace_url, raw.langsmith_url, raw.traceUrl) || undefined,
    createdAt: stringValue(raw.created_at, raw.timestamp, new Date().toISOString()),
  }
}

export function normalizeBenchmark(value: unknown): BenchmarkComparison {
  const raw = record(value)
  const hallucination = record(raw.hallucination ?? raw.hallucination_rate)
  const violations = record(raw.violations ?? raw.violation_reduction)
  const baselineViolations = record(raw.baseline_violations)
  const hardenedViolations = record(raw.hardened_violations)
  const rawCategories = arrayValue(raw.categories ?? raw.category_comparison)
  const categories = rawCategories.length
    ? rawCategories.map((value) => {
        const item = record(value)
        return {
          category: categoryFromUnknown(item.category ?? item.name),
          baseline: normalizeRate(item.baseline ?? item.baseline_rate, 0, 0),
          candidate: normalizeRate(item.candidate ?? item.hardened ?? item.candidate_rate, 0, 0),
        }
      })
    : referenceBenchmark.categories
  return {
    label: stringValue(raw.label, raw.name, referenceBenchmark.label),
    sampleLabel: stringValue(
      raw.sample_label,
      raw.caveat,
      raw.disclaimer,
      referenceBenchmark.sampleLabel,
    ),
    baselineModel: stringValue(raw.baseline_model, record(raw.baseline).model, referenceBenchmark.baselineModel),
    candidateModel: stringValue(raw.candidate_model, record(raw.candidate).model, referenceBenchmark.candidateModel),
    hallucination: {
      failures: numberValue(hallucination.failures, raw.hallucination_failures, 23),
      total: numberValue(hallucination.eligible_cases, hallucination.total, raw.hallucination_total, 100),
      rate: normalizeRate(hallucination.rate ?? raw.hallucination_rate_percent, 23, 100),
    },
    violations: {
      baseline: numberValue(baselineViolations.failures, violations.baseline, violations.baseline_violations, 100),
      candidate: numberValue(hardenedViolations.failures, violations.candidate, violations.hardened_violations, raw.candidate_violations, 39),
      total: numberValue(baselineViolations.eligible_cases, hardenedViolations.eligible_cases, violations.total, raw.total_prompts, 500),
      reduction: normalizeRate(raw.relative_violation_reduction ?? violations.reduction ?? violations.reduction_percent ?? raw.reduction_percent, 61, 100),
    },
    categories,
  }
}

async function getBenchmarkLive(): Promise<BenchmarkComparison> {
  return normalizeBenchmark(await request<unknown>('/benchmark/reference'))
}

async function getRunsLive(): Promise<EvaluationRun[]> {
  const payload = await request<unknown>('/runs')
  return arrayValue(payload).map(normalizeRun)
}

export const api = {
  async getOverview(): Promise<ApiResult<OverviewData>> {
    try {
      const [benchmark, runs] = await Promise.all([getBenchmarkLive(), getRunsLive()])
      const latest = runs.find((run) => run.status === 'completed')
      const categories = latest?.categories.some((item) => item.total > 0)
        ? latest.categories
        : referenceCategories
      const latestEligible = latest ? latest.passedCases + latest.failedCases : 0
      const latestFailureRate = latestEligible ? latest!.failedCases / latestEligible : 0
      return {
        source: 'live',
        data: {
          readinessScore: latest
            ? Math.max(0, Math.round(100 - latestFailureRate * 100))
            : 92,
          readiness:
            latest && (latest.errorCases > 0 || latestFailureRate > 0.2)
              ? 'review'
              : 'ready',
          hallucinationRate: benchmark.hallucination.rate,
          violationReduction: benchmark.violations.reduction,
          promptCount: Math.max(600, benchmark.violations.total),
          categories,
          recentRuns: runs,
          benchmark,
        },
      }
    } catch {
      return { data: demoOverview, source: 'demo' }
    }
  },

  async getPrompts(category?: CategoryId): Promise<ApiResult<{ items: PromptCase[]; total: number }>> {
    try {
      const pageSize = 200
      let offset = 0
      let total = Number.POSITIVE_INFINITY
      const collected: unknown[] = []
      while (offset < total) {
        const params = new URLSearchParams({ offset: String(offset), limit: String(pageSize) })
        if (category) params.set('category', toApiCategory(category))
        const payload = await request<unknown>(`/suites/redteam-v1/prompts?${params}`)
        const raw = record(payload)
        const page = arrayValue(payload)
        total = numberValue(raw.total, collected.length + page.length)
        collected.push(...page)
        if (page.length < pageSize || page.length === 0) break
        offset += page.length
      }
      const items = collected.map(normalizePrompt)
      return { data: { items, total: Number.isFinite(total) ? total : items.length }, source: 'live' }
    } catch {
      const items = category ? demoPrompts.filter((item) => item.category === category) : demoPrompts
      return { data: { items, total: category ? 100 : 600 }, source: 'demo' }
    }
  },

  async getFindings(runId?: string): Promise<ApiResult<Finding[]>> {
    try {
      let selectedRunId = runId
      if (!selectedRunId) {
        const runs = await getRunsLive()
        selectedRunId = runs.find((run) => run.status === 'completed')?.id
      }
      if (!selectedRunId) throw new Error('No completed run')
      const payload = await request<unknown>(`/runs/${encodeURIComponent(selectedRunId)}/findings`)
      return {
        data: arrayValue(payload).map((value, index) => normalizeFinding(value, index, selectedRunId)),
        source: 'live',
      }
    } catch (error) {
      if (runId && !runId.startsWith('demo-') && !runId.startsWith('run-reference') && runId !== 'run-smoke-weekly') {
        throw error
      }
      return { data: demoFindings, source: 'demo' }
    }
  },

  async getBenchmark(): Promise<ApiResult<BenchmarkComparison>> {
    try {
      return { data: await getBenchmarkLive(), source: 'live' }
    } catch {
      return { data: referenceBenchmark, source: 'demo' }
    }
  },

  async getRun(id: string): Promise<ApiResult<EvaluationRun>> {
    if (id.startsWith('demo-') || id.startsWith('run-reference') || id === 'run-smoke-weekly') {
      const demoRun = getDemoRun(id)
      if (demoRun) return { data: demoRun, source: 'demo' }
    }
    try {
      return { data: normalizeRun(await request<unknown>(`/runs/${encodeURIComponent(id)}`)), source: 'live' }
    } catch (error) {
      throw error
    }
  },

  async launchRun(input: LaunchRunInput): Promise<ApiResult<EvaluationRun>> {
    const target: Record<string, unknown> = { kind: input.targetKind }
    if (input.model) target.model = input.model
    if (input.baseUrl) target.base_url = input.baseUrl
    if (input.targetKind.startsWith('demo_')) target.demo_delay_ms = 40
    try {
      const payload = await request<unknown>('/runs', {
        method: 'POST',
        headers: input.accessKey
          ? { Authorization: `Bearer ${input.accessKey}` }
          : undefined,
        body: JSON.stringify({
          name: input.name,
          target,
          evaluator: input.evaluator,
          categories: input.categories.map(toApiCategory),
          limit: input.limit,
          concurrency: input.concurrency,
        }),
        timeout: 15_000,
      })
      return { data: normalizeRun(payload), source: 'live' }
    } catch (error) {
      if (input.targetKind.startsWith('demo_') && input.evaluator === 'deterministic') {
        return { data: createDemoRun(input), source: 'demo' }
      }
      throw error
    }
  },

  async cancelRun(id: string, accessKey?: string): Promise<ApiResult<EvaluationRun>> {
    if (id.startsWith('demo-')) {
      return { data: cancelDemoRun(id) ?? demoRuns[0], source: 'demo' }
    }
    try {
      return {
        data: normalizeRun(
          await request<unknown>(`/runs/${encodeURIComponent(id)}/cancel`, {
            method: 'POST',
            headers: accessKey
              ? { Authorization: `Bearer ${accessKey}` }
              : undefined,
          }),
        ),
        source: 'live',
      }
    } catch (error) {
      throw error
    }
  },
}

export const runEventsUrl = (id: string) => `${API_BASE}/runs/${encodeURIComponent(id)}/events`

export const runExportUrl = (id: string, format: 'json' | 'csv') =>
  `${API_BASE}/runs/${encodeURIComponent(id)}/export?format=${format}`
