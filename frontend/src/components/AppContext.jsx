import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { CheckCircle2, XCircle, X } from 'lucide-react'
import { api } from '../services/api'

const Ctx = createContext(null)
export const useApp = () => useContext(Ctx)

export function AppProvider({ children }) {
  const [status, setStatus] = useState(null)
  const [statusError, setStatusError] = useState(null)
  const [version, setVersion] = useState(0) // bump to make every page refetch (after sync / mode change)
  const [toasts, setToasts] = useState([])

  const reloadStatus = useCallback(async () => {
    try { setStatus(await api.status()); setStatusError(null) }
    catch (e) { setStatusError(e.message) }
  }, [])
  const refreshAll = useCallback(() => { reloadStatus(); setVersion((v) => v + 1) }, [reloadStatus])
  useEffect(() => { reloadStatus() }, [reloadStatus])

  const toast = useCallback((type, message) => {
    const id = Math.random()
    setToasts((t) => [...t, { id, type, message }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), type === 'error' ? 8000 : 4000)
  }, [])

  return (
    <Ctx.Provider value={{ status, statusError, reloadStatus, version, refreshAll, toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex w-[22rem] flex-col gap-2" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} role="status"
            className={`flex items-start gap-2 rounded-lg border bg-white p-3 text-sm shadow-lg ${t.type === 'error' ? 'border-red-200' : 'border-emerald-200'}`}>
            {t.type === 'error' ? <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" /> : <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />}
            <p className="flex-1">{t.message}</p>
            <button aria-label="Dismiss" onClick={() => setToasts((x) => x.filter((y) => y.id !== t.id))}><X className="h-4 w-4 text-muted" /></button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  )
}
