import '@testing-library/jest-dom/vitest'
import { createElement, forwardRef, type HTMLAttributes, type ReactNode } from 'react'

vi.mock('framer-motion', () => {
  const cache = new Map<PropertyKey, unknown>()
  const motion = new Proxy(
    {},
    {
      get: (_target, tag: string) => {
        if (!cache.has(tag)) {
          const Component = forwardRef<HTMLElement, Record<string, unknown>>((props, ref) => {
            const {
              initial: _initial,
              animate: _animate,
              exit: _exit,
              transition: _transition,
              whileTap: _whileTap,
              layout: _layout,
              layoutId: _layoutId,
              ...domProps
            } = props
            return createElement(tag, {
              ...(domProps as HTMLAttributes<HTMLElement>),
              ref,
            })
          })
          Component.displayName = `TestMotion.${tag}`
          cache.set(tag, Component)
        }
        return cache.get(tag)
      },
    },
  )

  return {
    motion,
    AnimatePresence: ({ children }: { children: ReactNode }) => children,
    useReducedMotion: () => true,
  }
})

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }),
})
