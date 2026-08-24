import { motion, useReducedMotion } from 'framer-motion'
import { Check, CircleAlert } from 'lucide-react'
import { useId, useState } from 'react'
import { CATEGORY_META, type CategoryId, type CategoryMetric } from '../types'

interface ReliabilityLensProps {
  score: number
  categories: CategoryMetric[]
  selected?: CategoryId | null
  onSelect?: (category: CategoryId | null) => void
  compact?: boolean
  title?: string
}

function polarToCartesian(cx: number, cy: number, radius: number, angle: number) {
  const radians = ((angle - 90) * Math.PI) / 180
  return { x: cx + radius * Math.cos(radians), y: cy + radius * Math.sin(radians) }
}

function describeArc(startAngle: number, endAngle: number) {
  const start = polarToCartesian(160, 160, 116, endAngle)
  const end = polarToCartesian(160, 160, 116, startAngle)
  const largeArcFlag = endAngle - startAngle <= 180 ? 0 : 1
  return `M ${start.x} ${start.y} A 116 116 0 ${largeArcFlag} 0 ${end.x} ${end.y}`
}

export function ReliabilityLens({
  score,
  categories,
  selected: selectedProp,
  onSelect,
  compact = false,
  title = 'Reliability lens',
}: ReliabilityLensProps) {
  const reducedMotion = useReducedMotion()
  const [localSelected, setLocalSelected] = useState<CategoryId | null>(null)
  const selected = selectedProp === undefined ? localSelected : selectedProp
  const titleId = useId()
  const descriptionId = useId()
  const safeScore = Math.round(Math.max(0, Math.min(100, score)))

  const select = (category: CategoryId) => {
    const next = selected === category ? null : category
    setLocalSelected(next)
    onSelect?.(next)
  }

  return (
    <section className={`reliability-lens ${compact ? 'reliability-lens--compact' : ''}`} aria-label={title}>
      <div className="reliability-lens__visual">
        <svg viewBox="0 0 320 320" role="img" aria-labelledby={`${titleId} ${descriptionId}`}>
          <title id={titleId}>{title}: {safeScore} out of 100</title>
          <desc id={descriptionId}>Six segments summarize reliability across hallucination, bias, unsafe behavior, injection, privacy, and robustness.</desc>
          <circle className="lens-halo" cx="160" cy="160" r="91" />
          {categories.slice(0, 6).map((metric, index) => {
            const start = index * 60 + 4
            const end = (index + 1) * 60 - 4
            const path = describeArc(start, end)
            const reliability = Math.max(0.08, 1 - metric.rate / 100)
            const isDimmed = selected !== null && selected !== metric.category
            return (
              <g key={metric.category} aria-hidden="true">
                <path d={path} className="lens-track" />
                <motion.path
                  d={path}
                  className="lens-value"
                  style={{ stroke: CATEGORY_META[metric.category].color }}
                  initial={reducedMotion ? false : { pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: reliability, opacity: isDimmed ? 0.18 : 1 }}
                  transition={{ type: 'spring', bounce: 0, duration: 0.4, delay: reducedMotion ? 0 : index * 0.035 }}
                />
              </g>
            )
          })}
          <text x="160" y="148" textAnchor="middle" className="lens-score">{safeScore}</text>
          <text x="160" y="173" textAnchor="middle" className="lens-score-label">RELIABILITY</text>
          <text x="160" y="196" textAnchor="middle" className="lens-score-state">{safeScore >= 90 ? 'Ready' : safeScore >= 75 ? 'Review' : 'Blocked'}</text>
        </svg>
      </div>
      {!compact && (
        <div className="lens-legend" aria-label="Filter by failure category">
          {categories.slice(0, 6).map((metric) => {
            const isSelected = selected === metric.category
            return (
              <button
                type="button"
                className="lens-legend__item pressable"
                data-selected={isSelected}
                key={metric.category}
                onClick={() => select(metric.category)}
                aria-pressed={isSelected}
              >
                <span className="lens-legend__icon" style={{ color: CATEGORY_META[metric.category].color }}>
                  {metric.rate <= 10 ? <Check aria-hidden="true" size={15} /> : <CircleAlert aria-hidden="true" size={15} />}
                </span>
                <span>
                  <strong>{CATEGORY_META[metric.category].shortLabel}</strong>
                  <small>{metric.rate.toFixed(metric.rate % 1 ? 1 : 0)}% failure rate</small>
                </span>
              </button>
            )
          })}
        </div>
      )}
    </section>
  )
}
