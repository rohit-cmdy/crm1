import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { useApp } from '../components/AppContext'
import SyncButton from '../components/SyncButton'
import { Card, EmptyState, ErrorBox, Spinner, StatusBadge, fmtDate, fmtDateTime, money, useFetch } from '../components/ui'

const Metric = ({ label, value, hint }) => (
  <div className="rounded-lg border border-line bg-white p-4">
    <p className="text-sm text-muted">{label}</p>
    <p className="mt-1 text-2xl font-semibold">{value}</p>
    {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
  </div>
)

export default function Dashboard() {
  const { data: d, loading, error, reload } = useFetch(() => api.dashboard(), [])
  const { statusError } = useApp()
  const demo = d?.integration.mode === 'demo'
  const intg = d?.integration

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-xl font-semibold">Dashboard</h1>
          <p className="text-sm text-muted">{demo ? 'Demo data' : 'Live from your synchronized WooCommerce data'}</p></div>
        <SyncButton />
      </div>
      {loading && !d && <Spinner />}
      {(error || statusError) && <ErrorBox message={error || statusError} onRetry={reload} />}
      {d && (
        <>
          {intg.state === 'error' && (
            <ErrorBox message={`Last synchronization failed: ${intg.last_error}`} />
          )}
          {intg.state === 'not_configured' && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              WooCommerce credentials are not configured. Add them to <code>.env</code> and restart the backend, or <Link to="/integration" className="font-medium underline">switch to demo mode</Link> to explore with sample data.
            </div>
          )}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Metric label="Customers" value={d.total_customers} />
            <Metric label="Orders" value={d.total_orders} />
            <Metric label="Order value" hint="Excludes cancelled, failed, refunded"
              value={d.order_value.length ? d.order_value.map((v) => money(v.total, v.currency)).join(' + ') : '—'} />
            <Metric label="Awaiting processing" value={d.awaiting_processing} hint="Pending, processing, on-hold" />
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <Card title="Recent orders" className="lg:col-span-2"
              action={<Link to="/orders" className="text-sm text-brand hover:underline">View all</Link>}>
              {d.recent_orders.length === 0 ? (
                <EmptyState title="No orders yet">{demo ? 'Select “Load demo data” to add sample orders.' : 'Select “Sync now” to import orders from WooCommerce.'}</EmptyState>
              ) : (
                <table className="w-full"><thead><tr><th className="th">Order</th><th className="th">Customer</th><th className="th">Date</th><th className="th text-right">Total</th><th className="th">Status</th></tr></thead>
                  <tbody>{d.recent_orders.map((o) => (
                    <tr key={o.id}><td className="td font-medium">#{o.order_number}</td>
                      <td className="td">{o.customer_id ? <Link className="text-brand hover:underline" to={`/customers/${o.customer_id}`}>{o.customer_name}</Link> : (o.customer_name || 'Guest')}</td>
                      <td className="td text-muted">{fmtDate(o.order_date)}</td><td className="td text-right">{money(o.total, o.currency)}</td>
                      <td className="td"><StatusBadge status={o.status} /></td></tr>))}</tbody></table>
              )}
            </Card>
            <div className="space-y-4">
              <Card title="Integration">
                <dl className="space-y-2 p-4 text-sm">
                  <div className="flex justify-between"><dt className="text-muted">Mode</dt><dd className="font-medium">{demo ? 'Demo' : 'Real'}</dd></div>
                  <div className="flex justify-between"><dt className="text-muted">Connection</dt><dd className="font-medium">{demo ? 'Not applicable' : ({ connected: 'Connected', error: 'Failing', not_configured: 'Not configured', not_synced: 'Not synced yet' }[intg.state])}</dd></div>
                  <div className="flex justify-between"><dt className="text-muted">Last sync</dt><dd>{demo ? '—' : intg.last_sync_at ? fmtDateTime(intg.last_sync_at) : 'Never'}</dd></div>
                  <div className="flex justify-between"><dt className="text-muted">Sync failures</dt><dd className={intg.failure_count ? 'font-medium text-red-700' : ''}>{intg.failure_count}</dd></div>
                </dl>
              </Card>
              <Card title="Recent customer activity">
                {d.recent_activity.length === 0 ? <EmptyState title="No activity yet">Add a note on a customer to see it here.</EmptyState> : (
                  <ul className="divide-y divide-line/70">{d.recent_activity.map((a) => (
                    <li key={a.id} className="px-4 py-3 text-sm">
                      <Link to={`/customers/${a.customer_id}`} className="font-medium text-brand hover:underline">{a.customer_name}</Link>
                      <p className="line-clamp-2 text-muted">{a.summary}</p>
                      <p className="mt-0.5 text-xs text-muted">{fmtDateTime(a.created_at)}</p></li>))}</ul>
                )}
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
