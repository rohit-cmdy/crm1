import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Check } from 'lucide-react'
import { api } from '../services/api'
import { useApp } from '../components/AppContext'
import { Button, Card, EmptyState, ErrorBox, Spinner, fmtDate, useFetch } from '../components/ui'

const TABS = [['pending', 'Pending'], ['completed', 'Completed'], ['', 'All']]

export default function FollowUps() {
  const { toast } = useApp()
  const [tab, setTab] = useState('pending')
  const { data, loading, error, reload } = useFetch(() => api.followUps({ status: tab }), [tab])
  const todayStr = new Date().toISOString().slice(0, 10)

  async function toggle(k) {
    const next = k.status === 'pending' ? 'completed' : 'pending'
    try { await api.setFollowUp(k.id, next); toast('success', next === 'completed' ? 'Follow-up completed.' : 'Follow-up reopened.'); reload() }
    catch (e) { toast('error', e.message) }
  }
  return (
    <div className="space-y-4">
      <div><h1 className="text-xl font-semibold">Follow-ups</h1>
        <p className="text-sm text-muted">Tasks linked to customers. Open a customer to create one or log a note.</p></div>
      <div className="flex gap-1 rounded-md border border-line bg-white p-1 w-fit" role="tablist">
        {TABS.map(([v, l]) => (
          <button key={l} role="tab" aria-selected={tab === v} onClick={() => setTab(v)}
            className={`rounded px-3 py-1.5 text-sm ${tab === v ? 'bg-brand text-white' : 'text-muted hover:text-ink'}`}>{l}</button>))}
      </div>
      {error && <ErrorBox message={error} onRetry={reload} />}
      <Card>
        {loading && !data ? <Spinner /> : data && (data.length === 0 ? (
          <EmptyState title={tab === 'completed' ? 'Nothing completed yet' : 'No follow-ups'}>
            Follow-ups are created manually on a customer, or automatically when an order reaches a status in your event rule.</EmptyState>
        ) : (
          <div className="overflow-x-auto"><table className="w-full"><thead><tr><th className="th">Task</th><th className="th">Customer</th><th className="th">Due</th><th className="th">Source</th><th className="th" /></tr></thead>
            <tbody>{data.map((k) => (
              <tr key={k.id}>
                <td className={`td ${k.status === 'completed' ? 'text-muted line-through' : 'font-medium'}`}>{k.title}</td>
                <td className="td"><Link className="text-brand hover:underline" to={`/customers/${k.customer_id}`}>{k.customer_name}</Link></td>
                <td className={`td ${k.status === 'pending' && k.due_date < todayStr ? 'font-medium text-red-700' : 'text-muted'}`}>{fmtDate(k.due_date)}{k.status === 'pending' && k.due_date < todayStr && ' (overdue)'}</td>
                <td className="td text-muted">{k.automatic ? `Order #${k.order_number ?? ''} event` : 'Manual'}</td>
                <td className="td text-right"><Button variant="secondary" onClick={() => toggle(k)}>{k.status === 'pending' ? <><Check className="h-4 w-4" />Mark complete</> : 'Reopen'}</Button></td></tr>))}</tbody></table></div>
        ))}
      </Card>
    </div>
  )
}
