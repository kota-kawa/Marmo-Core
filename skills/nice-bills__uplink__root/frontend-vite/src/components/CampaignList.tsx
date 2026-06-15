import { useState, useEffect } from 'react'
import { fetchCampaigns, type Campaign } from '../lib/api'
import { CampaignCard } from './CampaignCard'
import { LoadingSpinner } from './LoadingSpinner'
import { AlertCircle } from 'lucide-react'

export function CampaignList() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadCampaigns()
  }, [])

  async function loadCampaigns() {
    try {
      setLoading(true)
      const data = await fetchCampaigns()
      setCampaigns(data)
      setError(null)
    } catch (err) {
      setError('Failed to load campaigns. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20">
        <LoadingSpinner />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center">
          <AlertCircle className="h-5 w-5 mr-2" />
          {error}
        </div>
      </div>
    )
  }

  return (
    <div id="campaigns" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <h2 className="text-3xl font-bold text-gray-900 mb-8">Active Campaigns</h2>
      
      {campaigns.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-500 text-lg mb-4">No campaigns yet. Be the first!</p>
          <div className="bg-gray-100 p-4 rounded-lg inline-block">
            <p className="font-semibold mb-2">To create a campaign:</p>
            <code className="text-sm bg-gray-200 px-2 py-1 rounded">
              @break_whileloop I need $500 for my project 0xYourAddress
            </code>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {campaigns.map((campaign) => (
            <CampaignCard key={campaign.id} campaign={campaign} />
          ))}
        </div>
      )}
    </div>
  )
}
