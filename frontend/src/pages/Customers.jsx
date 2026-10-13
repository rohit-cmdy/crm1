import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search } from 'lucide-react'
import { api } from '../services/api'
import { Card, EmptyState, ErrorBox, Pagination, Spinner, fmtDate, money, useDebounced, useFetch } from '../components/ui'

const PAGE_SIZE = 15

export default function Customers() {
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const dq = useDebounced(q)
  const { data, loading, error, reload } = useFetch(() => api.customers({ q: dq, page, page_size: PAGE_SIZE }), [dq, page])

  return (
    <div className="space-y-4">
      <div><h1 className="text-xl font-semibold">Customers</h1>
        <p className="text-sm text-muted">Contact details come from WooCommerce and are read-only here.</p></div>
      <div className="relative max-w-sm">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted" />
        <input className="input pl-9" placeholder="Search by name or email" aria-label="Search customers"
          value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} />
      </div>
      {error && <ErrorBox message={error} onRetry={reload} />}
      <Card>
        {loading && !data ? <Spinner /> : data && (data.items.length === 0 ? (
          <EmptyState title={dq ? 'No customers match your search' : 'No customers yet'}>
            {dq ? 'Try a different name or email.' : 'Sync from WooCommerce (or load demo data) on the dashboard.'}</EmptyState>
        ) : (
          <>
            <div className="overflow-x-auto"><table className="w-full">
              <thead><tr><th className="th">Name</th><th className="th">Email</th><th className="th">Phone</th><th className="th">Woo ID</th><th className="th text-right">Orders</th><th className="th text-right">Spent</th><th className="th">Last order</th></tr></thead>
              <tbody>{data.items.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50">
                  <td className="td font-medium"><Link className="text-brand hover:underline" to={`/customers/${c.id}`}>{c.name}</Link>
                    {c.is_guest && <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs font-normal text-muted">Guest</span>}</td>
                  <td className="td">{c.email || '—'}</td><td className="td">{c.phone || '—'}</td>
                  <td className="td text-muted">{c.woo_customer_id ?? '—'}</td>
                  <td className="td text-right">{c.total_orders}</td>
                  <td className="td text-right">{c.total_orders ? money(c.total_spent, c.currency) : '—'}</td>
                  <td className="td text-muted">{fmtDate(c.last_order_date)}</td></tr>))}</tbody></table></div>
            <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={setPage} />
          </>
        ))}
      </Card>
    </div>
  )
}
