import { Route, Routes } from 'react-router-dom'
import CombinationsPage from './pages/CombinationsPage'
import EvaluatePage from './pages/EvaluatePage'
import TableDetailPage from './pages/TableDetailPage'
import TableListPage from './pages/TableListPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<TableListPage />} />
      <Route path="/tables/:tableId" element={<TableDetailPage />} />
      <Route path="/tables/:tableId/combinations" element={<CombinationsPage />} />
      <Route path="/tables/:tableId/evaluate" element={<EvaluatePage />} />
    </Routes>
  )
}
