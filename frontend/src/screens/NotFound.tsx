import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <section>
      <h1>Not Found</h1>
      <p>That page does not exist.</p>
      <Link to="/">Go to Log Workout</Link>
    </section>
  )
}
