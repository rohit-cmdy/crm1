import { useState } from 'react'
import { RefreshCw, Database } from 'lucide-react'
import { api } from '../services/api'
import { useApp } from './AppContext'
import { Button } from './ui'

export default function SyncButton() {
  const { status, toast, refreshAll } = useApp()
  const [busy, setBusy] = useState(false)
  const demo = status?.mode === 'demo'

  async function run() {
    setBusy(true)
    try {
      if (demo) {
        const r = await api.seedDemo()
        toast('success', `Demo data loaded (${r.customers_created} new customers, ${r.orders_created} new orders).`)
      } else {
        const r = await api.sync()
        const { customers: c, orders: o } = r.stats
        let msg = `Sync complete: customers ${c.created} new / ${c.updated} updated, orders ${o.created} new / ${o.updated} updated.`
        if (r.truncated) msg += ` Limited to the newest ${r.limit_per_resource} per type (store has ${r.totals_in_store.customers} customers, ${r.totals_in_store.orders} orders).`
        toast('success', msg)
      }
    } catch (e) {
      toast('error', demo ? e.message : `Sync failed: ${e.message}`)
    } finally {
      setBusy(false)
      refreshAll()
    }
  }
  if (!status) return null
  return (
    <Button onClick={run} loading={busy} disabled={!demo && !status.configured}
      title={!demo && !status.configured ? 'Set WooCommerce credentials in .env first' : undefined}>
      {demo ? <Database className="h-4 w-4" /> : <RefreshCw className="h-4 w-4" />}
      {demo ? 'Load demo data' : 'Sync now'}
    </Button>
  )
}
