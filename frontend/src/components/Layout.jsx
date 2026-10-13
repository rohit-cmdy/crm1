import { NavLink, Outlet } from 'react-router-dom'
import { LayoutDashboard, Users, ShoppingCart, MessageSquare, Plug, FlaskConical, RefreshCw } from 'lucide-react'
import { useApp } from './AppContext'
import { fmtDateTime } from './ui'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/customers', label: 'Customers', icon: Users },
  { to: '/orders', label: 'Orders', icon: ShoppingCart },
  { to: '/follow-ups', label: 'Follow-ups', icon: MessageSquare },
  { to: '/integration', label: 'Integration', icon: Plug },
]

const STATE_LABEL = {
  connected: ['bg-emerald-500', 'Connected'], not_synced: ['bg-amber-500', 'Not synced yet'],
  error: ['bg-red-500', 'Last sync failed'], not_configured: ['bg-slate-400', 'Not configured'],
  demo: ['bg-amber-500', 'Demo data'],
}

export default function Layout() {
  const { status, statusError } = useApp()
  const [dot, label] = STATE_LABEL[status?.state] || ['bg-slate-300', statusError ? 'Backend unreachable' : 'Checking…']
  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-56 shrink-0 flex-col bg-navy px-3 py-5 text-slate-300 md:flex">
        <div className="mb-6 flex items-center gap-2 px-2 text-white">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-brand text-sm font-semibold">S</span>
          <span className="font-semibold">Storefront CRM</span>
        </div>
        <nav className="flex flex-col gap-0.5">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end}
              className={({ isActive }) => `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors ${isActive ? 'bg-brand text-white' : 'hover:bg-navy-soft hover:text-white'}`}>
              <Icon className="h-4 w-4" />{label}
            </NavLink>
          ))}
        </nav>
        <p className="mt-auto px-2 text-xs text-slate-500">WooCommerce REST API v3</p>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        {status?.mode === 'demo' && (
          <div className="flex items-center justify-center gap-2 bg-amber-100 px-4 py-1.5 text-sm text-amber-900" role="status">
            <FlaskConical className="h-4 w-4" />
            <span><strong>Demo mode.</strong> Sample data only — not connected to a WooCommerce store.</span>
          </div>
        )}
        <header className="flex h-14 items-center justify-between border-b border-line bg-white px-6">
          <nav className="flex gap-1 md:hidden">
            {NAV.map(({ to, label, end }) => (
              <NavLink key={to} to={to} end={end} className={({ isActive }) => `rounded px-2 py-1 text-xs ${isActive ? 'bg-brand text-white' : 'text-muted'}`}>{label}</NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${dot}`} /><span className="font-medium">{status?.mode === 'demo' ? 'Demo data' : `WooCommerce: ${label}`}</span></span>
            {status?.mode === 'real' && (
              <span className="hidden items-center gap-1 text-muted lg:flex"><RefreshCw className="h-3.5 w-3.5" />Last sync: {status.last_sync_at ? fmtDateTime(status.last_sync_at) : 'never'}</span>
            )}
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-6"><Outlet /></main>
      </div>
    </div>
  )
}
