import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Check, Copy, Mail, MapPin, Phone } from 'lucide-react'
import { api } from '../services/api'
import { useApp } from '../components/AppContext'
import OrderPanel from '../components/OrderPanel'
import { Button, Card, EmptyState, ErrorBox, Spinner, StatusBadge, fmtDate, fmtDateTime, money, useFetch } from '../components/ui'

const today = () => new Date().toISOString().slice(0, 10)
const plusDays = (n) => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10)

function Notes({ id }) {
  const { toast, reloadStatus } = useApp()
  const { data, loading, error, reload } = useFetch(() => api.interactions(id), [id])
  const [type, setType] = useState('note'), [text, setText] = useState(''), [busy, setBusy] = useState(false)
  async function add(e) {
    e.preventDefault(); setBusy(true)
    try { await api.addInteraction(id, { type, summary: text }); setText(''); toast('success', 'Note added.'); reload(); reloadStatus() }
    catch (err) { toast('error', err.message) } finally { setBusy(false) }
  }
  return (
    <Card title="Interaction history">
      <form onSubmit={add} className="space-y-2 border-b border-line p-4">
        <div className="flex gap-2">
          <select className="input w-32" aria-label="Interaction type" value={type} onChange={(e) => setType(e.target.value)}>
            {['note', 'call', 'email', 'meeting'].map((t) => <option key={t}>{t}</option>)}</select>
          <input className="input" placeholder="What happened? e.g. Called about delivery" aria-label="Note" value={text} maxLength={2000} onChange={(e) => setText(e.target.value)} />
          <Button type="submit" loading={busy} disabled={!text.trim()}>Add note</Button>
        </div>
      </form>
      {loading && !data ? <Spinner /> : error ? <div className="p-4"><ErrorBox message={error} onRetry={reload} /></div>
        : data.length === 0 ? <EmptyState title="No interactions logged">Record calls, emails and notes here.</EmptyState> : (
          <ul className="divide-y divide-line/70">{data.map((i) => (
            <li key={i.id} className="flex gap-3 px-4 py-3 text-sm">
              <span className={`mt-0.5 h-fit rounded px-1.5 py-0.5 text-xs font-medium ${i.type === 'system' ? 'bg-blue-50 text-blue-700' : 'bg-slate-100 text-slate-700'}`}>{i.type === 'system' ? 'automatic' : i.type}</span>
              <div className="flex-1"><p className="whitespace-pre-wrap">{i.summary}</p><p className="mt-0.5 text-xs text-muted">{fmtDateTime(i.created_at)}</p></div></li>))}</ul>)}
    </Card>
  )
}

function Tasks({ id, prefill }) {
  const { toast } = useApp()
  const { data, loading, error, reload } = useFetch(() => api.followUps({ customer_id: id }), [id])
  const [title, setTitle] = useState(''), [due, setDue] = useState(plusDays(3)), [busy, setBusy] = useState(false)
  const t = prefill || title
  async function add(e) {
    e.preventDefault(); setBusy(true)
    try { await api.addFollowUp({ customer_id: Number(id), title: t, due_date: due }); setTitle(''); toast('success', 'Follow-up created.'); reload() }
    catch (err) { toast('error', err.message) } finally { setBusy(false) }
  }
  async function toggle(task) {
    try { await api.setFollowUp(task.id, task.status === 'pending' ? 'completed' : 'pending'); toast('success', task.status === 'pending' ? 'Follow-up completed.' : 'Follow-up reopened.'); reload() }
    catch (err) { toast('error', err.message) }
  }
  return (
    <Card title="Follow-ups">
      <form onSubmit={add} className="flex flex-wrap gap-2 border-b border-line p-4">
        <input className="input min-w-[12rem] flex-1" placeholder="Follow-up title" aria-label="Follow-up title" maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />
        <input type="date" className="input w-40" aria-label="Due date" min={today()} value={due} onChange={(e) => setDue(e.target.value)} />
        <Button type="submit" loading={busy} disabled={!title.trim() || !due}>Create follow-up</Button>
      </form>
      {loading && !data ? <Spinner /> : error ? <div className="p-4"><ErrorBox message={error} onRetry={reload} /></div>
        : data.length === 0 ? <EmptyState title="No follow-ups">Create one to remember the next step with this customer.</EmptyState> : (
          <ul className="divide-y divide-line/70">{data.map((k) => (
            <li key={k.id} className="flex items-center gap-3 px-4 py-3 text-sm">
              <div className="flex-1"><p className={k.status === 'completed' ? 'text-muted line-through' : 'font-medium'}>{k.title}</p>
                <p className="text-xs text-muted">Due {fmtDate(k.due_date)}{k.automatic && ' · created automatically from a WooCommerce order'}</p></div>
              <Button variant="secondary" onClick={() => toggle(k)}>{k.status === 'pending' ? <><Check className="h-4 w-4" />Mark complete</> : 'Reopen'}</Button></li>))}</ul>)}
    </Card>
  )
}

function Template({ id, orders }) {
  const { toast } = useApp()
  const [orderId, setOrderId] = useState('')
  const { data, error } = useFetch(() => api.template(id, orderId || undefined), [id, orderId])
  async function copy() {
    try { await navigator.clipboard.writeText(`Subject: ${data.subject}\n\n${data.body}`); toast('success', 'Message copied.') }
    catch { toast('error', 'Copy failed. Select the text manually.') }
  }
  return (
    <Card title="Post-purchase message template">
      <div className="space-y-3 p-4 text-sm">
        {orders.length > 0 && (
          <select className="input w-64" aria-label="Order for template" value={orderId} onChange={(e) => setOrderId(e.target.value)}>
            <option value="">No specific order</option>
            {orders.map((o) => <option key={o.id} value={o.id}>Order #{o.order_number}</option>)}</select>)}
        {error && <ErrorBox message={error} />}
        {data && (<>
          <p className="font-medium">Subject: {data.subject}</p>
          <pre className="whitespace-pre-wrap rounded-md border border-line bg-slate-50 p-3 font-sans">{data.body}</pre>
          <div className="flex items-center gap-3"><Button variant="secondary" onClick={copy}><Copy className="h-4 w-4" />Copy message</Button>
            <span className="text-xs text-muted">{data.note}</span></div></>)}
      </div>
    </Card>
  )
}

export default function CustomerDetail() {
  const { id } = useParams()
  const [open, setOpen] = useState(null)
  const c = useFetch(() => api.customer(id), [id])
  const o = useFetch(() => api.customerOrders(id), [id])
  if (c.loading && !c.data) return <Spinner />
  if (c.error) return <div className="space-y-3"><Link to="/customers" className="text-sm text-brand">← Customers</Link><ErrorBox message={c.error} onRetry={c.reload} /></div>
  const x = c.data
  const addr = [x.address_line, x.city, x.state, x.postcode, x.country].filter(Boolean).join(', ')
  return (
    <div className="space-y-4">
      <Link to="/customers" className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink"><ArrowLeft className="h-4 w-4" />Customers</Link>
      <div className="rounded-lg border border-line bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><h1 className="text-xl font-semibold">{x.name}{x.is_guest && <span className="ml-2 rounded bg-slate-100 px-2 py-0.5 align-middle text-xs font-normal text-muted">Guest profile</span>}</h1>
            <div className="mt-2 space-y-1 text-sm text-muted">
              <p className="flex items-center gap-2"><Mail className="h-4 w-4" />{x.email || 'No email'}</p>
              <p className="flex items-center gap-2"><Phone className="h-4 w-4" />{x.phone || 'No phone'}</p>
              {addr && <p className="flex items-center gap-2"><MapPin className="h-4 w-4" />{addr}</p>}
              <p>WooCommerce customer ID: {x.woo_customer_id ?? 'none (guest checkout)'}</p></div></div>
          <dl className="grid grid-cols-3 gap-6 text-sm">
            <div><dt className="text-muted">Orders</dt><dd className="text-lg font-semibold">{x.total_orders}</dd></div>
            <div><dt className="text-muted">Spent</dt><dd className="text-lg font-semibold">{x.total_orders ? money(x.total_spent, x.currency) : '—'}</dd></div>
            <div><dt className="text-muted">Last order</dt><dd className="text-lg font-semibold">{fmtDate(x.last_order_date)}</dd></div></dl>
        </div>
      </div>
      <Card title="Orders">
        {o.loading && !o.data ? <Spinner /> : o.error ? <div className="p-4"><ErrorBox message={o.error} onRetry={o.reload} /></div>
          : o.data.length === 0 ? <EmptyState title="No orders for this customer" /> : (
            <div className="overflow-x-auto"><table className="w-full"><thead><tr><th className="th">Order</th><th className="th">Date</th><th className="th text-right">Total</th><th className="th">Status</th></tr></thead>
              <tbody>{o.data.map((r) => (<tr key={r.id} className="cursor-pointer hover:bg-slate-50" onClick={() => setOpen(r.id)}>
                <td className="td font-medium text-brand">#{r.order_number}</td><td className="td text-muted">{fmtDate(r.order_date)}</td>
                <td className="td text-right">{money(r.total, r.currency)}</td><td className="td"><StatusBadge status={r.status} /></td></tr>))}</tbody></table></div>)}
      </Card>
      <div className="grid gap-4 lg:grid-cols-2"><Notes id={id} /><Tasks id={id} /></div>
      <Template id={id} orders={o.data || []} />
      {open && <OrderPanel orderId={open} onClose={() => setOpen(null)} />}
    </div>
  )
}
