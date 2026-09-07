import { NavLink } from 'react-router-dom'

export default function TableNav({ tableId }: { tableId: number }) {
  const linkClass = ({ isActive }: { isActive: boolean }) => (isActive ? 'active' : '')
  return (
    <nav className="nav-tabs">
      <NavLink to={`/tables/${tableId}`} end className={linkClass}>
        Factors
      </NavLink>
      <NavLink to={`/tables/${tableId}/combinations`} className={linkClass}>
        Combinations
      </NavLink>
      <NavLink to={`/tables/${tableId}/rules`} className={linkClass}>
        Rules
      </NavLink>
      <NavLink to={`/tables/${tableId}/evaluate`} className={linkClass}>
        Evaluate
      </NavLink>
    </nav>
  )
}
