import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Monitor, Moon, Sun } from 'lucide-react'

export type ThemePreference = 'light' | 'dark' | 'system'
type ResolvedTheme = 'light' | 'dark'

interface ThemeContextValue {
  preference: ThemePreference
  resolvedTheme: ResolvedTheme
  setPreference: (theme: ThemePreference) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)
const STORAGE_KEY = 'reliability-observatory-theme'

function getStoredPreference(): ThemePreference {
  const stored = window.localStorage.getItem(STORAGE_KEY)
  return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system'
}

function resolveTheme(preference: ThemePreference, darkQuery: MediaQueryList): ResolvedTheme {
  return preference === 'system' ? (darkQuery.matches ? 'dark' : 'light') : preference
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(getStoredPreference)
  const darkQuery = useMemo(() => window.matchMedia('(prefers-color-scheme: dark)'), [])
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() =>
    resolveTheme(preference, darkQuery),
  )

  useEffect(() => {
    const apply = () => {
      const resolved = resolveTheme(preference, darkQuery)
      setResolvedTheme(resolved)
      document.documentElement.dataset.theme = resolved
      document.documentElement.style.colorScheme = resolved
      document
        .querySelector('meta[name="theme-color"]')
        ?.setAttribute('content', resolved === 'dark' ? '#090b10' : '#f3f5f8')
    }
    apply()
    darkQuery.addEventListener('change', apply)
    return () => darkQuery.removeEventListener('change', apply)
  }, [darkQuery, preference])

  const setPreference = (theme: ThemePreference) => {
    window.localStorage.setItem(STORAGE_KEY, theme)
    setPreferenceState(theme)
  }

  const value = useMemo(
    () => ({ preference, resolvedTheme, setPreference }),
    [preference, resolvedTheme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const value = useContext(ThemeContext)
  if (!value) throw new Error('useTheme must be used inside ThemeProvider')
  return value
}

const choices: Array<{
  value: ThemePreference
  label: string
  Icon: typeof Sun
}> = [
  { value: 'light', label: 'Light', Icon: Sun },
  { value: 'dark', label: 'Dark', Icon: Moon },
  { value: 'system', label: 'System', Icon: Monitor },
]

export function ThemeControl({ compact = false }: { compact?: boolean }) {
  const { preference, setPreference } = useTheme()
  return (
    <div className={`theme-control ${compact ? 'theme-control--compact' : ''}`} aria-label="Appearance">
      {choices.map(({ value, label, Icon }) => (
        <button
          className="theme-control__option pressable"
          data-selected={preference === value}
          type="button"
          key={value}
          onClick={() => setPreference(value)}
          aria-pressed={preference === value}
          aria-label={`${label} appearance`}
          title={label}
        >
          <Icon aria-hidden="true" size={17} strokeWidth={1.9} />
          {!compact && <span>{label}</span>}
        </button>
      ))}
    </div>
  )
}
