// All data comes from the FastAPI backend (proxied at /api). No credentials exist in the browser.
async function request(path, { method = 'GET', body, params } = {}) {
  const qs = params
    ? '?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null)).toString()
    : ''
  let res
  try {
    res = await fetch(`/api${path}${qs}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error('Cannot reach the CRM backend. Is it running on port 8000?')
  }
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const d = data?.detail
    const msg = Array.isArray(d) ? d.map((e) => e.msg).join('; ') : d
    throw new Error(msg || `Request failed (HTTP ${res.status})`)
  }
  return data
}

export const api = {
  dashboard: () => request('/dashboard/summary'),
  status: () => request('/integrations/woocommerce/status'),
  customers: (params) => request('/customers', { params }),
  customer: (id) => request(`/customers/${id}`),
  customerOrders: (id) => request(`/customers/${id}/orders`),
  interactions: (id) => request(`/customers/${id}/interactions`),
  addInteraction: (id, body) => request(`/customers/${id}/interactions`, { method: 'POST', body }),
  template: (id, orderId) => request(`/customers/${id}/message-template`, { params: { order_id: orderId } }),
  orders: (params) => request('/orders', { params }),
  order: (id) => request(`/orders/${id}`),
  followUps: (params) => request('/follow-ups', { params }),
  addFollowUp: (body) => request('/follow-ups', { method: 'POST', body }),
  setFollowUp: (id, status) => request(`/follow-ups/${id}`, { method: 'PATCH', body: { status } }),
  sync: () => request('/integrations/woocommerce/sync', { method: 'POST' }),
  testConnection: () => request('/integrations/woocommerce/test', { method: 'POST' }),
  setMode: (mode) => request('/integrations/mode', { method: 'POST', body: { mode } }),
  seedDemo: () => request('/integrations/demo/seed', { method: 'POST' }),
  simulateOrder: (replay) => request('/integrations/demo/simulate-order', { method: 'POST', params: replay ? { replay: true } : {} }),
}
