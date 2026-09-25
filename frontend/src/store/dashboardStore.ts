import { create } from "zustand";

type State = {
  selectedRoad: string | null;
  setSelectedRoad: (id:string|null)=>void;
  selectedIncident: string | null;
  setSelectedIncident: (id:string|null)=>void;
  autoRefresh: boolean;
  setAutoRefresh: (v:boolean)=>void;
};
export const useDashboardStore = create<State>((set)=>({
  selectedRoad:null,
  setSelectedRoad:(selectedRoad)=>set({selectedRoad}),
  selectedIncident:null,
  setSelectedIncident:(selectedIncident)=>set({selectedIncident}),
  autoRefresh:true,
  setAutoRefresh:(autoRefresh)=>set({autoRefresh}),
}));
