export type RoadStatus = "SAFE" | "MODERATE_RISK" | "HIGH_RISK" | "BLOCKED";
export type ResourceStatus = "AVAILABLE" | "DEPLOYED" | "EN_ROUTE" | "RETURNING" | "MAINTENANCE";
export type IncidentPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface Road {
  road_id: string;
  name?: string;
  status: RoadStatus;
  flood_probability?: number;
  water_level?: number;
  traffic_density?: number;
  elevation_m?: number;
  geometry?: { coordinates: { lat:number; lon:number }[] } | any;
  start_node?: string;
  end_node?: string;
}
export interface Shelter {
  shelter_id: string;
  name?: string;
  status: string;
  capacity: number;
  occupancy: number;
  risk_level?: string;
  geometry?: { coordinates: { lat:number; lon:number }[] } | any;
}
export interface Resource {
  resource_id: string;
  resource_type: string;
  status: ResourceStatus;
  geometry?: any;
  assigned_incident_id?: string;
  capacity?: number;
}
export interface Incident {
  incident_id: string;
  incident_type: string;
  priority: IncidentPriority;
  status: string;
  geometry?: any;
  reported_people?: number;
  severity?: number;
}
export interface DashboardSummary {
  total_roads: number;
  roads_by_status: Record<string, number>;
  total_shelters: number;
  shelters_operational: number;
  shelters_at_capacity: number;
  total_capacity: number;
  current_occupancy: number;
  total_resources: number;
  resources_available: number;
  resources_deployed: number;
  total_incidents: number;
  incidents_by_priority: Record<string, number>;
  active_incidents: number;
  timestamp: string;
}
export interface HeatmapCell { lat:number; lon:number; flood_probability:number; risk_level:string }
export interface PredictionResp { predictions: { road_id:string; flood_probability:number; water_level_m?:number }[]; model_version:string }
export interface ExplainPrediction {
  road_id:string; flood_probability:number; top_features:{feature:string; importance:number; description:string}[]; shap_values?: Record<string,number>; similar_disasters?: any[]; narrative?: string; counterfactuals?: any[];
}
export interface ExplainDecision {
  decision_type:string; decision_id:string; rationale:string; factors_considered:string[]; alternatives_evaluated:any[]; confidence:number; similar_disasters?:any[]; narrative?:string;
}
