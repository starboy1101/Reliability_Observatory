export type CategoryId =
  | 'hallucination'
  | 'bias'
  | 'unsafe'
  | 'injection'
  | 'privacy'
  | 'robustness'

export type Severity = 'critical' | 'high' | 'medium' | 'low'

export type DataSource = 'live' | 'demo'

export interface CategoryMetric {
  category: CategoryId
  label: string
  total: number
  failed: number
  rate: number
  delta?: number
}

export interface EvaluationRun {
  id: string
  name: string
  model: string
  evaluator: string
  status: 'queued' | 'running' | 'completed' | 'partial' | 'failed' | 'cancelled'
  totalCases: number
  processedCases: number
  passedCases: number
  failedCases: number
  errorCases: number
  progress: number
  startedAt: string
  completedAt?: string
  categories: CategoryMetric[]
}

export interface PromptCase {
  id: string
  prompt: string
  category: CategoryId
  severity: Severity
  attack: string
  expectedBehavior: string
  tags: string[]
}

export interface Finding {
  id: string
  runId: string
  promptId: string
  category: CategoryId
  severity: Severity
  prompt: string
  response: string
  expectedBehavior: string
  judgeReason: string
  evaluator: string
  metric: string
  score: number
  reproducible: boolean
  traceUrl?: string
  createdAt: string
}

export interface BenchmarkComparison {
  label: string
  sampleLabel: string
  baselineModel: string
  candidateModel: string
  hallucination: {
    failures: number
    total: number
    rate: number
  }
  violations: {
    baseline: number
    candidate: number
    total: number
    reduction: number
  }
  categories: Array<{
    category: CategoryId
    baseline: number
    candidate: number
  }>
}

export interface OverviewData {
  readinessScore: number
  readiness: 'ready' | 'review' | 'blocked'
  hallucinationRate: number
  violationReduction: number
  promptCount: number
  categories: CategoryMetric[]
  recentRuns: EvaluationRun[]
  benchmark: BenchmarkComparison
}

export interface ApiResult<T> {
  data: T
  source: DataSource
}

export interface LaunchRunInput {
  name: string
  targetKind: 'demo_baseline' | 'demo_hardened' | 'openai_compatible'
  model?: string
  baseUrl?: string
  evaluator: 'deterministic' | 'deepeval'
  categories: CategoryId[]
  limit: number
  concurrency: number
}

export const CATEGORY_META: Record<
  CategoryId,
  { label: string; shortLabel: string; description: string; color: string }
> = {
  hallucination: {
    label: 'Hallucination & truthfulness',
    shortLabel: 'Hallucination',
    description: 'Unsupported facts, fabricated evidence, and ungrounded claims.',
    color: 'var(--risk-hallucination)',
  },
  bias: {
    label: 'Bias & fairness',
    shortLabel: 'Bias',
    description: 'Disparate treatment, stereotyping, and unfair recommendations.',
    color: 'var(--risk-bias)',
  },
  unsafe: {
    label: 'Unsafe behavior',
    shortLabel: 'Unsafe',
    description: 'Harmful, disallowed, or dangerously overconfident guidance.',
    color: 'var(--risk-unsafe)',
  },
  injection: {
    label: 'Jailbreak & injection',
    shortLabel: 'Injection',
    description: 'Instruction hierarchy bypasses and prompt-injection attacks.',
    color: 'var(--risk-injection)',
  },
  privacy: {
    label: 'Privacy & leakage',
    shortLabel: 'Privacy',
    description: 'Sensitive data disclosure, memorization, and secret extraction.',
    color: 'var(--risk-privacy)',
  },
  robustness: {
    label: 'Robustness & tools',
    shortLabel: 'Robustness',
    description: 'Edge cases, malformed inputs, ambiguity, and tool-use failures.',
    color: 'var(--risk-robustness)',
  },
}

export const CATEGORY_IDS = Object.keys(CATEGORY_META) as CategoryId[]
