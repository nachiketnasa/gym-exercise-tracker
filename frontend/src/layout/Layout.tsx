import { NavLink, Outlet } from 'react-router-dom'
import './Layout.css'

const NAV_ITEMS = [
  { to: '/', label: 'Log Workout', end: true },
  { to: '/history', label: 'History', end: false },
  { to: '/goals', label: 'Goals', end: false },
]

/**
 * Persistent app frame: a header with the app name and a navigation bar that
 * wraps every route via <Outlet />.
 *
 * Responsive breakpoint: 768px. At >= 768px the nav sits in the header as a
 * normal horizontal nav; below 768px it renders as a fixed bottom nav bar.
 * The markup is identical at both sizes — only CSS (media query) differs.
 */
export default function Layout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-title">Gym Exercise Tracker</span>
        <nav className="app-nav" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                isActive ? 'app-nav__link app-nav__link--active' : 'app-nav__link'
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
