const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export interface HealthResponse {
  status: string;
  database: string;
}

export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }

  return response.json() as Promise<HealthResponse>;
}
