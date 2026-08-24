import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../theme/ThemeProvider'
import { LandingPage } from './LandingPage'

describe('LandingPage', () => {
  it('states the benchmark evidence and offers a real next action', () => {
    render(
      <MemoryRouter>
        <ThemeProvider>
          <LandingPage />
        </ThemeProvider>
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: /know how your model fails/i })).toBeInTheDocument()
    expect(screen.getByText('23%')).toBeInTheDocument()
    expect(screen.getByText('61%')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /launch an evaluation/i })).toHaveAttribute('href', '/runs/new')
  })
})
