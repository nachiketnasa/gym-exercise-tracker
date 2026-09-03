import { useParams } from 'react-router-dom'

export default function ExerciseDetail() {
  const { exerciseId } = useParams<{ exerciseId: string }>()
  return (
    <section>
      <h1>Exercise Detail</h1>
      <p>Progress, personal records, and goals for exercise {exerciseId}.</p>
    </section>
  )
}
