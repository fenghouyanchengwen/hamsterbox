const BASE = '/api'

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${BASE}/health`)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return response.json()
}
