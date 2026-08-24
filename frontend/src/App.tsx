import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { ComparePage } from './pages/ComparePage'
import { FindingsPage } from './pages/FindingsPage'
import { LandingPage } from './pages/LandingPage'
import { LaunchRunPage } from './pages/LaunchRunPage'
import { OverviewPage } from './pages/OverviewPage'
import { PromptLibraryPage } from './pages/PromptLibraryPage'
import { RunDetailPage } from './pages/RunDetailPage'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route element={<AppShell />}>
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/runs/new" element={<LaunchRunPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="/prompts" element={<PromptLibraryPage />} />
        <Route path="/findings" element={<FindingsPage />} />
        <Route path="/compare" element={<ComparePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/overview" replace />} />
    </Routes>
  )
}
