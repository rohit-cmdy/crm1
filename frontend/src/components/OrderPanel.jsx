import { Link } from 'react-router-dom'
import { X } from 'lucide-react'
import { api } from '../services/api'
import { ErrorBox, Spinner, StatusBadge, fmtDateTime, money, useFetch } from './ui'

export default function OrderPanel({ orderId, onClose }) {
  const { data: o, loading, error } = useFetch(() => api.order(orderId), [orderId])
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-navy/30" onClick={onClose}>
      <aside className="h-full w-full max-w-md overflow-y-auto bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Order details">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{o ? `Order #${o.order_number}` : 'Order'}</h2>
          <button onClick={onClose} aria-label="Close"><X className="h-5 w-5 text-muted" /></button>
        </div>
        {loading && <Spinner />}
        {error && <ErrorBox message={error} />}
        {o && (
          <div className="space-y-5 text-sm">
            <dl className="grid grid-cols-2 gap-3">
              <div><dt className="text-muted">Status</dt><dd><StatusBadge status={o.status} /></dd></div>
              <div><dt className="text-muted">Total</dt><dd className="font-medium">{money(o.total, o.currency)}</dd></div>
              <div><dt className="text-muted">Order date</dt><dd>{fmtDateTime(o.order_date)}</dd></div>
              <div><dt className="text-muted">WooCommerce order ID</dt><dd>{o.woo_order_id}</dd></div>
              <div className="col-span-2"><dt className="text-muted">Customer</dt>
                <dd>{o.customer_id ? <Link className="text-brand hover:underline" to={`/customers/${o.customer_id}`} onClick={onClose}>{o.customer_name}</Link> : <>{o.customer_name || 'Guest'} <span className="text-muted">(guest, no email)</span></>}
                  {o.billing_email && <span className="block text-muted">{o.billing_email}</span>}</dd></div>
            </dl>
            <div>
              <h3 className="mb-2 font-semibold">Items</h3>
              {o.items.length === 0 ? <p className="text-muted">No line items synchronized.</p> : (
                <table className="w-full"><tbody>
                  {o.items.map((i, k) => (
                    <tr key={k} className="border-b border-line/70"><td className="py-2">{i.name}</td><td className="py-2 text-right text-muted">{i.quantity} × {money(i.unit_price, o.currency)}</td></tr>
                  ))}</tbody></table>
              )}
            </div>
            <p className="rounded-md bg-slate-50 p-3 text-xs text-muted">
              Read-only copy of WooCommerce data, last synchronized {fmtDateTime(o.last_synced_at)}. Status changes are made in WooCommerce and arrive via sync or webhook.
            </p>
          </div>
        )}
      </aside>
    </div>
  )
}
