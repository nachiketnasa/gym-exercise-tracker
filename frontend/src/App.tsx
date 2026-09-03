import { Route, Routes } from 'react-router-dom'
import Layout from './layout/Layout'
import LogWorkout from './screens/LogWorkout'
import History from './screens/History'
import ExerciseDetail from './screens/ExerciseDetail'
import Goals from './screens/Goals'
import NotFound from './screens/NotFound'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<LogWorkout />} />
        <Route path="history" element={<History />} />
        <Route path="exercises/:exerciseId" element={<ExerciseDetail />} />
        <Route path="goals" element={<Goals />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
