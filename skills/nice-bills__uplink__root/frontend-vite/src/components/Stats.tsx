import { useState, useEffect } from 'react'
import { getCampaigns } from '../lib/api'

export function Stats() {
  const [stats, setStats] = useState({
    total: 0,
    raised: 0,
    active: 0,
  })

  useEffect(() => {
    async function loadStats() {
      try {
        const campaigns = await getCampaigns()
        setStats({
          total: campaigns.length,
          raised: campaigns.reduce((sum, c) => sum + (c.raised || 0), 0),
          active: campaigns.filter(c => c.status === 'active').length,
        })
      } catch {
        // Ignore errors
      }
    }
    loadStats()
  }, [])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-8">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-6 text-center">
          <div className="text-3xl font-bold text-blue-600">{stats.total}</div>
          <div className="text-gray-600 text-sm">Campaigns</div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 text-center">
          <div className="text-3xl font-bold text-purple-600">
            ${stats.raised.toLocaleString()}
          </div>
          <div className="text-gray-600 text-sm">Total Raised</div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 text-center">
          <div className="text-3xl font-bold text-green-600">{stats.active}</div>
          <div className="text-gray-600 text-sm">Active</div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 text-center">
          <div className="text-3xl font-bold text-orange-600">0.5%</div>
          <div className="text-gray-600 text-sm">Platform Fee</div>
        </div>
      </div>
    </div>
  )
}
