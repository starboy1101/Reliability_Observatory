import { fireEvent, render, screen } from '@testing-library/react'
import { referenceCategories } from '../api/demo'
import { ReliabilityLens } from './ReliabilityLens'

describe('ReliabilityLens', () => {
  it('exposes a meaningful accessible chart summary', () => {
    render(<ReliabilityLens score={92} categories={referenceCategories} />)

    expect(screen.getByRole('img', { name: /reliability lens: 92 out of 100/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /hallucination/i })).toHaveTextContent('9% failure rate')
  })

  it('supports keyboard-compatible category filtering', () => {
    const onSelect = vi.fn()
    render(<ReliabilityLens score={92} categories={referenceCategories} onSelect={onSelect} />)

    const category = screen.getByRole('button', { name: /privacy/i })
    fireEvent.click(category)
    expect(onSelect).toHaveBeenCalledWith('privacy')
    expect(category).toHaveAttribute('aria-pressed', 'true')

    fireEvent.click(category)
    expect(onSelect).toHaveBeenLastCalledWith(null)
  })
})
