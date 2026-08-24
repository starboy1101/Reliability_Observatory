import { motion, useReducedMotion } from 'framer-motion'
import {
  ArrowRight,
  CheckCircle2,
  CircleDotDashed,
  FlaskConical,
  GitCompareArrows,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { referenceCategories } from '../api/demo'
import { ReliabilityLens } from '../components/ReliabilityLens'
import { ThemeControl } from '../theme/ThemeProvider'

const spring = { type: 'spring' as const, bounce: 0, duration: 0.4 }

export function LandingPage() {
  const reducedMotion = useReducedMotion()
  const entrance = reducedMotion ? { opacity: 1 } : { opacity: 1, y: 0 }

  return (
    <div className="landing">
      <a href="#landing-main" className="skip-link">Skip to content</a>
      <header className="landing-nav material">
        <Link to="/" className="brand pressable" aria-label="Reliability Observatory home">
          <span className="brand__mark" aria-hidden="true"><CircleDotDashed size={22} /></span>
          <span><strong>Reliability</strong><small>Observatory</small></span>
        </Link>
        <div className="landing-nav__actions">
          <ThemeControl compact />
          <Link to="/overview" className="button button--secondary pressable">Open demo</Link>
        </div>
      </header>

      <main id="landing-main">
        <section className="hero section-shell">
          <motion.div
            className="hero__copy"
            initial={reducedMotion ? false : { opacity: 0, y: 18 }}
            animate={entrance}
            transition={spring}
          >
            <p className="eyebrow"><Sparkles aria-hidden="true" size={15} /> Evidence before deployment</p>
            <h1>Know how your model fails <span>before users do.</span></h1>
            <p className="hero__lead">
              Run repeatable DeepEval and LangSmith red-team workflows across 500+ adversarial prompts, retain every finding, and compare fixes with evidence.
            </p>
            <div className="hero__actions">
              <Link to="/runs/new" className="button button--primary button--large pressable">
                Launch an evaluation <ArrowRight aria-hidden="true" size={18} />
              </Link>
              <Link to="/overview" className="button button--quiet button--large pressable">Explore reference data</Link>
            </div>
            <p className="hero__assurance"><ShieldCheck aria-hidden="true" size={16} /> Secrets remain server-managed. Demo mode requires no credentials.</p>
          </motion.div>

          <motion.div
            className="hero__instrument solid-panel"
            initial={reducedMotion ? false : { opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ ...spring, delay: reducedMotion ? 0 : 0.08 }}
          >
            <div className="instrument-head">
              <div><span className="connection-dot" /><strong>Hardened candidate</strong></div>
              <span>Sample benchmark</span>
            </div>
            <ReliabilityLens score={92} categories={referenceCategories} title="Reference model reliability" />
          </motion.div>
        </section>

        <section className="proof-strip section-shell" aria-label="Reference benchmark results">
          <article><strong>500+</strong><span>adversarial prompts</span><small>six failure categories</small></article>
          <article><strong>23%</strong><span>hallucination rate</span><small>23 of 100 edge cases</small></article>
          <article><strong>61%</strong><span>fewer violations</span><small>100 → 39 of 500</small></article>
        </section>

        <section className="workflow section-shell">
          <div className="section-heading">
            <p className="eyebrow">One continuous evidence trail</p>
            <h2>From adversarial prompt to deployment decision.</h2>
            <p>Every result remains inspectable, reproducible, and comparable.</p>
          </div>
          <div className="workflow-grid">
            <article className="workflow-card">
              <span className="workflow-card__index">01</span>
              <FlaskConical aria-hidden="true" />
              <h3>Challenge the model</h3>
              <p>Launch a complete suite or focus on one risk category with deterministic or DeepEval judges.</p>
            </article>
            <article className="workflow-card">
              <span className="workflow-card__index">02</span>
              <CheckCircle2 aria-hidden="true" />
              <h3>Inspect the evidence</h3>
              <p>Review prompts, outputs, evaluator rationale, severity, reproduction state, and optional LangSmith run traces.</p>
            </article>
            <article className="workflow-card">
              <span className="workflow-card__index">03</span>
              <GitCompareArrows aria-hidden="true" />
              <h3>Prove the improvement</h3>
              <p>Compare baseline and hardened models against the same versioned suite before release.</p>
            </article>
          </div>
        </section>

        <section className="landing-cta section-shell solid-panel">
          <div>
            <p className="eyebrow">Deployment confidence, evidenced</p>
            <h2>Start with a safe local target.</h2>
            <p>The reference workflow runs immediately and upgrades to live API data automatically.</p>
          </div>
          <Link to="/runs/new" className="button button--primary button--large pressable">Create evaluation <ArrowRight aria-hidden="true" size={18} /></Link>
        </section>
      </main>

      <footer className="landing-footer section-shell">
        <span>Reliability Observatory</span>
        <span>DeepEval · LangSmith · repeatable red teaming</span>
      </footer>
    </div>
  )
}
