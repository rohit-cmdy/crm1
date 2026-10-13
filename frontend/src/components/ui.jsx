import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'
import { useApp } from './AppContext'

export function useFetch(fn, deps = []) {
  const { version } = useApp()
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }))
    try { setState({ data: await fn(), loading: false, error: null }) }
    catch (e) { setState({ data: null, loading: false, error: e.message }) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, version])
  useEffect(() => { load() }, [load])
  return { ...state, reload: load }
}

export function useDebounced(value, ms = 300) {
  const [v, setV] = useState(value)
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t) }, [value, ms])
  return v
}

const BTN = {
  primary: 'bg-brand text-white hover:bg-brand-dark disabled:bg-brand/50',
  secondary: 'border border-line bg-white text-ink hover:bg-slate-50 disabled:text-muted',
  danger: 'bg-red-600 text-white hover:bg-red-700',
}
export function Button({ variant = 'primary', loading, children, className = '', ...p }) {
  return (
    <button {...p} disabled={p.disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${BTN[variant]} ${className}`}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}{children}
    </button>
  )
}

export const Card = ({ title, action, children, className = '' }) => (
  <section className={`rounded-lg border border-line bg-white ${className}`}>
    {(title || action) && (
      <header className="flex items-center justify-between border-b border-line px-4 py-3">
        <h2 className="text-sm font-semibold">{title}</h2>{action}
      </header>
    )}
    {children}
  </section>
)

export const Spinner = ({ label = 'Loading…' }) => (
  <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted" role="status">
    <Loader2 className="h-4 w-4 animate-spin" />{label}
  </div>
)

export const ErrorBox = ({ message, onRetry }) => (
  <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
    <div className="flex-1"><p className="font-medium">Something went wrong</p><p>{message}</p></div>
    {onRetry && <Button variant="secondary" onClick={onRetry}>Retry</Button>}
  </div>
)

export const EmptyState = ({ title, children }) => (
  <div className="px-6 py-12 text-center">
    <p className="text-sm font-medium">{title}</p>
    {children && <div className="mx-auto mt-1 max-w-md text-sm text-muted">{children}</div>}
  </div>
)

const STATUS_STYLE = {
  completed: 'bg-emerald-50 text-emerald-700', processing: 'bg-blue-50 text-blue-700',
  pending: 'bg-amber-50 text-amber-700', 'on-hold': 'bg-amber-50 text-amber-700',
  cancelled: 'bg-slate-100 text-slate-600', refunded: 'bg-slate-100 text-slate-600',
  failed: 'bg-red-50 text-red-700',
}
export const StatusBadge = ({ status }) => (
  <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[status] || 'bg-slate-100 text-slate-700'}`}>{status}</span>
)

export function Pagination({ page, pageSize, total, onChange }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (total <= pageSize) return null
  const from = (page - 1) * pageSize + 1, to = Math.min(total, page * pageSize)
  return (
    <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm text-muted">
      <span>{from}–{to} of {total}</span>
      <div className="flex items-center gap-1">
        <Button variant="secondary" disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label="Previous page"><ChevronLeft className="h-4 w-4" /></Button>
        <span className="px-2">Page {page} of {pages}</span>
        <Button variant="secondary" disabled={page >= pages} onClick={() => onChange(page + 1)} aria-label="Next page"><ChevronRight className="h-4 w-4" /></Button>
      </div>
    </div>
  )
}

export const money = (amount, currency) => {
  const n = Number(amount)
  if (Number.isNaN(n)) return '—'
  try { return new Intl.NumberFormat(undefined, { style: 'currency', currency: currency || 'USD' }).format(n) }
  catch { return `${n.toFixed(2)} ${currency || ''}` }
}
export const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '—')
export const fmtDateTime = (iso) => (iso ? new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—')
export const ORDER_STATUSES = ['pending', 'processing', 'on-hold', 'completed', 'cancelled', 'refunded', 'failed']
