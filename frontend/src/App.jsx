import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Customers from './pages/Customers'
import CustomerDetail from './pages/CustomerDetail'
import Orders from './pages/Orders'
import FollowUps from './pages/FollowUps'
import Integration from './pages/Integration'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="customers" element={<Customers />} />
        <Route path="customers/:id" element={<CustomerDetail />} />
        <Route path="orders" element={<Orders />} />
        <Route path="follow-ups" element={<FollowUps />} />
        <Route path="integration" element={<Integration />} />
        <Route path="*" element={<p className="py-12 text-center text-sm text-muted">Page not found.</p>} />
      </Route>
    </Routes>
  )
}
