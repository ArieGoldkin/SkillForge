import { useState } from 'react'

function generateTimestamps() {
  const now = Date.now()
  return {
    twoMinAgo: new Date(now - 120000).toISOString(),
    ninetySecAgo: new Date(now - 90000).toISOString(),
    oneMinAgo: new Date(now - 60000).toISOString(),
    fortyFiveSecAgo: new Date(now - 45000).toISOString(),
    now: new Date().toISOString(),
  }
}

export function useMockTimestamps() {
  const [timestamps] = useState(generateTimestamps)
  return timestamps
}
