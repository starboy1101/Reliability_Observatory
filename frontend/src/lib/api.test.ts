import { api, normalizeBenchmark, normalizeRun, toApiCategory } from './api'

describe('API normalization', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('maps interface category IDs to the backend contract', () => {
    expect([
      toApiCategory('hallucination'),
      toApiCategory('bias'),
      toApiCategory('unsafe'),
      toApiCategory('injection'),
      toApiCategory('privacy'),
      toApiCategory('robustness'),
    ]).toEqual([
      'hallucination',
      'bias_fairness',
      'unsafe_content',
      'prompt_injection',
      'privacy_leakage',
      'robustness',
    ])
  })

  it('normalizes the deployed run contract without leaking snake_case into views', () => {
    const run = normalizeRun({
      id: 'run-42',
      benchmark_label: 'Release gate',
      target_kind: 'openai_compatible',
      target_config: { model: 'candidate-v3' },
      evaluator_name: 'deepeval',
      status: 'partial',
      total_cases: 100,
      processed_cases: 97,
      passed_cases: 80,
      failed_cases: 15,
      error_cases: 2,
      progress_percent: 97,
      started_at: '2026-01-01T10:00:00Z',
      finished_at: '2026-01-01T10:04:00Z',
      category_summary: {
        hallucination: { total: 20, failed: 4, failure_rate: 0.2 },
      },
    })

    expect(run).toMatchObject({
      id: 'run-42',
      model: 'candidate-v3',
      evaluator: 'deepeval',
      status: 'partial',
      totalCases: 100,
      processedCases: 97,
      progress: 97,
      completedAt: '2026-01-01T10:04:00Z',
    })
    expect(run.categories[0]).toMatchObject({ category: 'hallucination', failed: 4, rate: 20 })
  })

  it('normalizes the exact reference benchmark response without fallback math', () => {
    const benchmark = normalizeBenchmark({
      label: 'Deterministic reference',
      caveat: 'Sample evidence only',
      hallucination: { failures: 23, eligible_cases: 100, rate: 0.23 },
      baseline_violations: { failures: 100, eligible_cases: 500, rate: 0.2 },
      hardened_violations: { failures: 39, eligible_cases: 500, rate: 0.078 },
      relative_violation_reduction: 0.61,
    })

    expect(benchmark.sampleLabel).toBe('Sample evidence only')
    expect(benchmark.hallucination).toEqual({ failures: 23, total: 100, rate: 23 })
    expect(benchmark.violations).toMatchObject({
      baseline: 100,
      candidate: 39,
      total: 500,
      reduction: 61,
    })

    expect(
      normalizeBenchmark({
        hallucination: { failures: 0, eligible_cases: 100, rate: 0 },
        baseline_violations: { failures: 20, eligible_cases: 100, rate: 0.2 },
        hardened_violations: { failures: 20, eligible_cases: 100, rate: 0.2 },
        relative_violation_reduction: 0,
      }).violations.reduction,
    ).toBe(0)
  })

  it('surfaces live launch errors and never replaces them with demo evidence', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'TARGET_HOST_ALLOWLIST is required' }), {
          status: 422,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    await expect(
      api.launchRun({
        name: 'Live candidate',
        targetKind: 'openai_compatible',
        model: 'candidate-v1',
        baseUrl: 'https://models.example.test/v1',
        evaluator: 'deterministic',
        categories: ['hallucination'],
        limit: 1,
        concurrency: 1,
      }),
    ).rejects.toThrow('TARGET_HOST_ALLOWLIST is required')
  })
})
