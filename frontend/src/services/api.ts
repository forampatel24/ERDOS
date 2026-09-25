const TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkYXNoYm9hcmQiLCJyb2xlcyI6WyJhZG1pbiJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sImF1ZCI6ImVyZG9zLWFwaSIsImV4cCI6MTgyMTg1NTI5OX0._iPIh2GwTjWj6_5nEEQ6S0WKx8Pog2OtTrUwE2LQ5_s";

function headersAuth(): HeadersInit {
  return { "Content-Type": "application/json", Authorization: `Bearer ${TOKEN}` };
}
async function jfetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, { ...init, headers: { ...headersAuth(), ...(init.headers as any) } });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`${path} ${res.status} ${txt.slice(0,300)}`);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => jfetch<any>("/api/v1/health"),
  summary: () => jfetch<any>("/api/v1/dashboard/summary"),
  zones: () => jfetch<any>("/api/v1/dashboard/zones"),
  resources: () => jfetch<any>("/api/v1/dashboard/resources"),
  roads: () => jfetch<any[]>("/api/v1/twin/roads"),
  shelters: () => jfetch<any[]>("/api/v1/shelters"),
  resourceList: () => jfetch<any[]>("/api/v1/resources"),
  incidents: () => jfetch<any[]>("/api/v1/incidents"),
  flood: (road_ids: string[]) => jfetch<any>("/api/v1/prediction/flood", { method:"POST", body: JSON.stringify({ road_ids, horizon_hours:6 }) }),
  heatmap: (bbox:string) => jfetch<any>("/api/v1/prediction/heatmap", { method:"POST", body: JSON.stringify({ bbox, resolution_m:500, horizon_hours:6 }) }),
  models: () => jfetch<any[]>("/api/v1/prediction/models"),
  explainPrediction: (road_id:string, include_counterfactuals=false) => jfetch<any>("/api/v1/explainability/prediction", { method:"POST", body: JSON.stringify({ target_type:"prediction", target_id: road_id, include_counterfactuals }) }),
  explainDecision: (type:string, id:string) => jfetch<any>("/api/v1/explainability/decision", { method:"POST", body: JSON.stringify({ target_type: type, target_id: id }) }),
  route: (origin:string, dest:string) => jfetch<any>("/api/v1/orchestration/route", { method:"POST", body: JSON.stringify({ origin:{node_id:origin}, destination:{node_id:dest} }) }),
  evacuate: (incident_id:string, people:number) => jfetch<any>("/api/v1/orchestration/evacuate", { method:"POST", body: JSON.stringify({ incident_id, affected_people: people }) }),
  allocate: (incident_id:string, resource_type:string, origin:string) => jfetch<any>("/api/v1/orchestration/allocate", { method:"POST", body: JSON.stringify({ incident_id, resource_type, origin:{node_id:origin}, priority:"HIGH", min_capacity:1 }) }),
};
