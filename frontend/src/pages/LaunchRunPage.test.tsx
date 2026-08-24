import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { LaunchRunPage } from './LaunchRunPage'

describe('LaunchRunPage', () => {
  it('selects quota-safe defaults for the free ZeroGPU target', () => {
    render(
      <MemoryRouter>
        <LaunchRunPage />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('radio', { name: /free hf space/i }))

    expect(screen.getByLabelText('Model name')).toHaveValue(
      'Qwen/Qwen2.5-0.5B-Instruct',
    )
    expect(screen.getByLabelText('Live-run access key')).toHaveAttribute(
      'type',
      'password',
    )
    expect(screen.getByRole('spinbutton', { name: /Prompt limit/i })).toHaveValue(6)
    expect(screen.getByLabelText('Concurrency')).toHaveValue('1')
    expect(screen.getByPlaceholderText('https://owner-space.hf.space')).toBeInTheDocument()
    expect(screen.getByText(/five GPU-minute daily/i)).toBeInTheDocument()
  })

  it('protects DeepEval launches with the same live-integration controls', () => {
    render(
      <MemoryRouter>
        <LaunchRunPage />
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByLabelText('Evaluator'), {
      target: { value: 'deepeval' },
    })

    expect(screen.getByLabelText('Live-run access key')).toHaveAttribute(
      'type',
      'password',
    )
    expect(screen.getByRole('spinbutton', { name: /Prompt limit/i })).toHaveValue(6)
    expect(screen.getByLabelText('Concurrency')).toHaveValue('1')
  })
})
