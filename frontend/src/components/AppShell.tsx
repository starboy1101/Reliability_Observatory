import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import {
  BarChart3,
  BookOpenText,
  CircleDotDashed,
  FlaskConical,
  GitCompareArrows,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  SearchCheck,
} from 'lucide-react'
import { useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { ThemeControl } from '../theme/ThemeProvider'

const navigation = [
  { to: '/overview', label: 'Overview', Icon: BarChart3 },
  { to: '/runs/new', label: 'New evaluation', Icon: FlaskConical },
  { to: '/prompts', label: 'Prompt library', Icon: BookOpenText },
  { to: '/findings', label: 'Findings', Icon: SearchCheck },
  { to: '/compare', label: 'Compare', Icon: GitCompareArrows },
]

const pageNames: Record<string, string> = {
  '/overview': 'Overview',
  '/runs/new': 'New evaluation',
  '/prompts': 'Prompt library',
  '/findings': 'Findings',
  '/compare': 'Reference comparison',
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/overview" className="brand pressable" aria-label="Reliability Observatory overview">
      <span className="brand__mark" aria-hidden="true"><CircleDotDashed size={22} strokeWidth={1.75} /></span>
      {!compact && <span><strong>Reliability</strong><small>Observatory</small></span>}
    </Link>
  )
}

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const reducedMotion = useReducedMotion()
  const pageName = location.pathname.startsWith('/runs/') && location.pathname !== '/runs/new'
    ? 'Evaluation run'
    : pageNames[location.pathname] ?? 'Reliability Observatory'

  return (
    <div className={`app-shell ${collapsed ? 'app-shell--collapsed' : ''}`}>
      <a href="#main-content" className="skip-link">Skip to content</a>
      <aside className="side-rail material" aria-label="Primary navigation">
        <div className="side-rail__top">
          <Brand compact={collapsed} />
          <button
            type="button"
            className="icon-button pressable side-rail__collapse"
            onClick={() => setCollapsed((value) => !value)}
            aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
            aria-expanded={!collapsed}
          >
            {collapsed ? <PanelLeftOpen aria-hidden="true" size={19} /> : <PanelLeftClose aria-hidden="true" size={19} />}
          </button>
        </div>
        <nav className="side-rail__nav">
          {navigation.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-item pressable ${isActive ? 'nav-item--active' : ''}`}
              title={collapsed ? label : undefined}
            >
              <Icon aria-hidden="true" size={20} strokeWidth={1.8} />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="side-rail__footer">
          {!collapsed && <p><span className="connection-dot" /> API-ready · demo-safe</p>}
          <ThemeControl compact={collapsed} />
        </div>
      </aside>

      <div className="app-shell__content">
        <header className="mobile-header">
          <Brand />
          <ThemeControl compact />
        </header>
        <div className="context-bar">
          <span>{pageName}</span>
          <Link to="/runs/new" className="button button--primary button--small pressable"><Plus aria-hidden="true" size={16} /> New run</Link>
        </div>
        <AnimatePresence mode="wait" initial={false}>
          <motion.main
            id="main-content"
            key={location.pathname}
            className="page-canvas"
            initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: -5 }}
            transition={reducedMotion ? { duration: 0.16 } : { type: 'spring', bounce: 0, duration: 0.36 }}
          >
            <Outlet />
          </motion.main>
        </AnimatePresence>
      </div>

      <nav className="mobile-nav material" aria-label="Mobile navigation">
        {navigation.slice(0, 5).map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `mobile-nav__item pressable ${isActive ? 'mobile-nav__item--active' : ''}`}
          >
            <Icon aria-hidden="true" size={20} />
            <span>{label === 'New evaluation' ? 'New run' : label.replace(' library', '')}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
