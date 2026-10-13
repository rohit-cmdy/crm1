import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search } from 'lucide-react'
import { api } from '../services/api'
import OrderPanel from '../components/OrderPanel'
import { Card, EmptyState, ErrorBox, ORDER_STATUSES, Pagination, Spinner, StatusBadge, fmtDate, fmtDateTime, money, useDebounced, useFetch } from '../components/ui'

const PAGE_SIZE = 15

export default function Orders() {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState(null)
  const dq = useDebounced(q)
  const { data, loading, error, reload } = useFetch(() => api.orders({ q: dq, status, page, page_size: PAGE_SIZE }), [dq, status, page])

  return (
    <div className="space-y-4">
      <div><h1 className="text-xl font-semibold">Orders</h1>
        <p className="text-sm text-muted">Status shown is the latest value synchronized from WooCommerce. Orders can't be changed from the CRM.</p></div>
      <div className="flex flex-wrap gap-3">
        <div className="relative w-full max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted" />
          <input className="input pl-9" placeholder="Search order number or customer" aria-label="Search orders"
            value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} />
        </div>
        <select className="input w-48" aria-label="Filter by status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          <option value="">All statuses</option>
          {ORDER_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      {error && <ErrorBox message={error} onRetry={reload} />}
      <Card>
        {loading && !data ? <Spinner /> : data && (data.items.length === 0 ? (
          <EmptyState title={dq || status ? 'No orders match these filters' : 'No orders yet'}>
            {dq || status ? 'Clear the search or status filter.' : 'Sync from WooCommerce (or load demo data) on the dashboard.'}</EmptyState>
        ) : (
          <>
            <div className="overflow-x-auto"><table className="w-full">
              <thead><tr><th className="th">Order</th><th className="th">Customer</th><th className="th">Date</th><th className="th text-right">Total</th><th className="th">Status</th><th className="th">Synced</th></tr></thead>
              <tbody>{data.items.map((o) => (
                <tr key={o.id} className="cursor-pointer hover:bg-slate-50" onClick={() => setOpen(o.id)}>
                  <td className="td font-medium"><button className="text-brand hover:underline" onClick={(e) => { e.stopPropagation(); setOpen(o.id) }}>#{o.order_number}</button></td>
                  <td className="td" onClick={(e) => e.stopPropagation()}>
                    {o.customer_id ? <Link className="text-brand hover:underline" to={`/customers/${o.customer_id}`}>{o.customer_name}</Link>
                      : <span>{o.customer_name || 'Guest'} <span className="text-xs text-muted">(guest)</span></span>}</td>
                  <td className="td text-muted">{fmtDate(o.order_date)}</td>
                  <td className="td text-right">{money(o.total, o.currency)}</td>
                  <td className="td"><StatusBadge status={o.status} /></td>
                  <td className="td text-xs text-muted">{fmtDateTime(o.last_synced_at)}</td></tr>))}</tbody></table></div>
            <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={setPage} />
          </>
        ))}
      </Card>
      {open && <OrderPanel orderId={open} onClose={() => setOpen(null)} />}
    </div>
  )
}
