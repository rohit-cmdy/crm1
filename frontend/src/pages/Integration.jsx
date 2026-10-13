import { useState } from 'react'
import { FlaskConical, PlugZap } from 'lucide-react'
import { api } from '../services/api'
import { useApp } from '../components/AppContext'
import SyncButton from '../components/SyncButton'
import { Button, Card, ErrorBox, Spinner, fmtDateTime } from '../components/ui'

const Row = ({ k, children }) => (<div className="flex justify-between gap-4 border-b border-line/70 py-2 text-sm last:border-0"><dt className="text-muted">{k}</dt><dd className="text-right font-medium">{children}</dd></div>)

export default function Integration() {
  const { status: s, statusError, toast, refreshAll } = useApp()
  const [busy, setBusy] = useState('')

  async function run(key, fn, okMsg) {
    setBusy(key)
    try { const r = await fn(); toast('success', okMsg(r)) } catch (e) { toast('error', e.message) }
    finally { setBusy(''); refreshAll() }
  }
  async function switchMode(mode) {
    const msg = mode === 'demo'
      ? 'Switch to demo mode? The CRM will show only clearly labeled sample data. Your real WooCommerce records stay in the database, hidden.'
      : 'Switch to real mode? The CRM will show only data synchronized from WooCommerce.'
    if (!window.confirm(msg)) return
    run('mode', () => api.setMode(mode), () => (mode === 'demo' ? 'Demo mode on.' : 'Real mode on.'))
  }

  if (statusError && !s) return <ErrorBox message={statusError} />
  if (!s) return <Spinner />
  const demo = s.mode === 'demo'
  return (
    <div className="space-y-4">
      <div><h1 className="text-xl font-semibold">Integration</h1>
        <p className="text-sm text-muted">WooCommerce owns customer and order data. The CRM owns notes and follow-ups.</p></div>
      {s.state === 'error' && <ErrorBox message={`Last synchronization failed: ${s.last_error}`} />}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Connection" action={demo ? null : <SyncButton />}>
          <dl className="px-4 py-2">
            <Row k="Mode">{demo ? 'Demo (sample data)' : 'Real'}</Row>
            <Row k="Store">{demo ? 'Not connected' : s.store_host || 'Not configured'}</Row>
            <Row k="API credentials">{s.configured ? 'Set in server environment' : 'Missing'}</Row>
            <Row k="Last successful sync">{demo ? '—' : s.last_sync_at ? fmtDateTime(s.last_sync_at) : 'Never'}</Row>
            <Row k="Failures logged">{s.failure_count}</Row>
            <Row k="Per-sync limit">{s.sync_limit_per_resource} customers and {s.sync_limit_per_resource} orders (newest first)</Row>
          </dl>
          {!demo && (
            <div className="border-t border-line p-4">
              <Button variant="secondary" loading={busy === 'test'} disabled={!s.configured}
                onClick={() => run('test', api.testConnection, (r) => `${r.message} Store has ${r.totals_in_store.customers} customers and ${r.totals_in_store.orders} orders.`)}>
                <PlugZap className="h-4 w-4" />Test connection</Button>
            </div>)}
        </Card>
        <Card title="Mode">
          <div className="space-y-3 p-4 text-sm">
            <p>{demo ? 'Demo mode shows sample records labeled as demo data. It never contacts WooCommerce and is kept separate from real records.'
              : 'Real mode uses your WooCommerce store. If a sync fails, the CRM reports the error and does not substitute sample data.'}</p>
            <Button variant="secondary" loading={busy === 'mode'} onClick={() => switchMode(demo ? 'real' : 'demo')}>
              <FlaskConical className="h-4 w-4" />{demo ? 'Switch to real mode' : 'Switch to demo mode'}</Button>
            {demo && <div className="flex items-center gap-2 pt-1"><SyncButton /><span className="text-muted">Adds sample customers and orders (safe to repeat).</span></div>}
          </div>
        </Card>
        <Card title="Order event rule">
          <div className="space-y-2 p-4 text-sm">
            <p>When a WooCommerce webhook reports an order with status <strong>{s.event_rule.order_statuses.join(' or ')}</strong>, the CRM creates one follow-up task (due in {s.event_rule.due_in_days} days) and logs an activity on the customer. Repeated deliveries never create duplicates.</p>
            <p className="text-muted">Change with <code>FOLLOWUP_ORDER_STATUSES</code> and <code>FOLLOWUP_DUE_DAYS</code> in <code>.env</code>.</p>
          </div>
        </Card>
        <Card title="Webhook">
          <div className="space-y-2 p-4 text-sm">
            <Row k="Endpoint path"><code>POST /api/webhooks/woocommerce</code></Row>
            <Row k="Signature secret">{s.webhook_secret_configured ? 'Configured' : <span className="text-red-700">Missing — webhooks are rejected</span>}</Row>
            <p className="text-muted">WooCommerce can only reach a public HTTPS URL (for local use, a tunnel). Requests are verified with HMAC-SHA256 before anything is processed. See the README for setup.</p>
            {demo && (<div className="flex flex-wrap gap-2 border-t border-line pt-3">
              <Button variant="secondary" loading={busy === 'sim'} onClick={() => run('sim', () => api.simulateOrder(false),
                (r) => `Simulated signed webhook: order ${r.order_id} ${r.status}. Follow-up ${r.follow_up_created ? 'created' : 'not created'}.`)}>Simulate completed order</Button>
              <Button variant="secondary" loading={busy === 'replay'} onClick={() => run('replay', () => api.simulateOrder(true),
                (r) => `Replayed same event: ${r.status}. No duplicate order or task.`)}>Replay last event</Button>
              <p className="w-full text-xs text-muted">Demo only: these go through the real webhook handler but are generated by the CRM, not sent by WooCommerce.</p></div>)}
          </div>
        </Card>
      </div>
    </div>
  )
}
