import { useCallback, useEffect, useMemo, useState } from "react";
import MapView from "./maps/MapView";
import { api } from "./services/api";
import { useWebSocket } from "./hooks/useWebSocket";
import { useDashboardStore } from "./store/dashboardStore";

type Tab = "overview"|"map"|"predictions"|"logistics"|"explain";

function Icon({name}:{name:string}){
  const common = { width:18, height:18, viewBox:"0 0 24 24", fill:"none", stroke:"currentColor", strokeWidth:1.75, strokeLinecap:"round" as const, strokeLinejoin:"round" as const };
  const icons: Record<string, JSX.Element> = {
    overview: <svg {...common}><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/></svg>,
    map: <svg {...common}><path d="M1 6l7-3 7 3 7-3v14l-7 3-7-3-7 3z"/><path d="M8 3v14M15 6v14"/></svg>,
    predictions: <svg {...common}><path d="M3 3v18h18"/><path d="M7 16l3-6 3 4 4-7"/></svg>,
    logistics: <svg {...common}><path d="M3 9l7-4 7 4-7 4z"/><path d="M3 13l7 4 7-4"/><path d="M3 17l7 4 7-4"/></svg>,
    explain: <svg {...common}><path d="M9 9a3 3 0 116 0c0 2-2 2.5-2 4"/><path d="M12 17h.01"/><circle cx="12" cy="12" r="10"/></svg>,
    activity: <svg {...common}><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>,
    shield: <svg {...common}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
    truck: <svg {...common}><path d="M1 8h11v8H1z"/><path d="M12 11h4l3 3v2h-7"/><circle cx="5.5" cy="18.5" r="1.5"/><circle cx="15.5" cy="18.5" r="1.5"/></svg>,
    alert: <svg {...common}><path d="M10.3 3.3l-8 14A1 1 0 003 19h18a1 1 0 00.9-1.7l-8-14a1 1 0 00-1.8 0z"/><path d="M12 9v5"/><path d="M12 17h.01"/></svg>,
    route: <svg {...common}><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><path d="M5 19l4-8h6l4 8"/><path d="M9 11V7h6"/></svg>,
    spark: <svg {...common}><path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8z"/><path d="M19 13l1 2 2 1-2 1-1 2-1-2-2-1 2-1z"/><path d="M5 13l1 2 2 1-2 1-1 2-1-2-2-1 2-1z"/></svg>,
  };
  return icons[name] ?? icons.overview;
}

function StatCard({label, value, sub, accent, icon, trend}:{label:string; value:string|number; sub:string; accent:string; icon:string; trend?:string}){
  return (
    <div className="glass card" style={{ position:"relative", overflow:"hidden" }}>
      <div style={{ position:"absolute", right:-18, top:-18, width:92, height:92, borderRadius:999, background:`radial-gradient(300px 300px at 30% 30%, ${accent}22, transparent 70%)`, pointerEvents:"none" }} />
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", gap:12 }}>
        <div style={{ width:36, height:36, borderRadius:12, display:"grid", placeItems:"center", background:`linear-gradient(135deg, ${accent}, ${accent}cc)`, color:"#001019", boxShadow:`0 8px 18px ${accent}33`, border:"1px solid rgba(255,255,255,0.22)" }}><Icon name={icon} /></div>
        {trend && <span className="badge" style={{ background:"rgba(16,185,129,0.14)", borderColor:"rgba(16,185,129,0.22)", color:"#6ee7b7" }}>{trend}</span>}
      </div>
      <div style={{ marginTop:12, fontSize:12, letterSpacing:"0.08em", textTransform:"uppercase", color:"var(--muted)", fontWeight:700 }}>{label}</div>
      <div style={{ marginTop:6, fontSize:28, fontWeight:800, letterSpacing:"-0.03em", lineHeight:1 }}>{value}</div>
      <div style={{ marginTop:6, fontSize:12, color:"var(--muted)" }}>{sub}</div>
    </div>
  );
}

export default function App(){
  const [tab, setTab] = useState<Tab>("overview");
  const { selectedRoad, setSelectedRoad } = useDashboardStore();
  const [summary, setSummary] = useState<any>(null);
  const [zones, setZones] = useState<any>(null);
  const [roads, setRoads] = useState<any[]>([]);
  const [shelters, setShelters] = useState<any[]>([]);
  const [resources, setResources] = useState<any[]>([]);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [liveMsg, setLiveMsg] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [routePath, setRoutePath] = useState<{lat:number;lon:number}[]|null>(null);
  const [evacResult, setEvacResult] = useState<any>(null);
  const [allocResult, setAllocResult] = useState<any>(null);
  const [explainPred, setExplainPred] = useState<any>(null);
  const [explainDec, setExplainDec] = useState<any>(null);
  const [predTable, setPredTable] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [now, setNow] = useState(new Date());

  const onWs = useCallback((m:any)=>{ setLiveMsg(m); if(m?.payload?.predictions) setPredTable(m.payload.predictions); }, []);
  const { connected } = useWebSocket(onWs);

  useEffect(()=>{ const id=setInterval(()=>setNow(new Date()), 1000); return ()=>clearInterval(id); },[]);

  const refresh = useCallback(async()=>{
    try{
      const [s, z, r, sh, re, inc, h, m, healthRes] = await Promise.allSettled([
        api.summary(), api.zones(), api.roads(), api.shelters(), api.resourceList(), api.incidents(),
        api.heatmap("76.2,9.9,76.3,10.0"), api.models(), api.health()
      ]);
      if(s.status==="fulfilled") setSummary(s.value);
      if(z.status==="fulfilled") setZones(z.value);
      if(r.status==="fulfilled") setRoads(r.value as any);
      if(sh.status==="fulfilled") setShelters(sh.value as any);
      if(re.status==="fulfilled") setResources(re.value as any);
      if(inc.status==="fulfilled") setIncidents(inc.value as any);
      if(h.status==="fulfilled") setHeatmap((h.value as any).cells ?? []);
      if(m.status==="fulfilled") setModels(m.value as any);
      if(healthRes.status==="fulfilled") setHealth(healthRes.value);
      if(r.status==="fulfilled" && sh.status==="fulfilled" && (r.value as any).length){
        try{
          const flood = await api.flood(((r.value as any).slice(0,6).map((x:any)=>x.road_id)));
          setPredTable(flood.predictions ?? []);
        }catch{}
      }
    } finally { setLoading(false); }
  }, []);

  useEffect(()=>{ refresh(); }, [refresh]);
  useEffect(()=>{ if(!selectedRoad && roads[0]) setSelectedRoad(roads[0].road_id); }, [roads, selectedRoad, setSelectedRoad]);

  // auto refresh every 12s
  useEffect(()=>{
    const id=setInterval(refresh, 12000); return ()=>clearInterval(id);
  }, [refresh]);

  const atRisk = useMemo(()=> roads.filter(r=> (r.flood_probability??0)>=0.35 || r.status==="HIGH_RISK"||r.status==="BLOCKED").length, [roads]);
  const blocked = useMemo(()=> roads.filter(r=> r.status==="BLOCKED").length, [roads]);
  const occupancyPct = summary ? Math.round((summary.current_occupancy / Math.max(1,summary.total_capacity))*100) : 0;

  const handleExplainPred = async (id:string)=>{
    setSelectedRoad(id);
    try{
      const res = await api.explainPrediction(id, true);
      setExplainPred(res);
    }catch{ setExplainPred(null); }
  };
  const handleExplainDec = async (type:string, id:string)=>{
    try{
      const res = await api.explainDecision(type, id);
      setExplainDec(res);
    }catch{ setExplainDec(null); }
  };
  const handleRoute = async ()=>{
    try{
      const res:any = await api.route(roads[0]?.road_id || "node_1", roads[1]?.road_id || "node_2");
      const path = res.route?.path ?? res.route ?? res.path ?? [];
      // path may be list of nodes with lat/lon
      const pts = (Array.isArray(path)? path: []).map((p:any)=> ({ lat: p.lat ?? p.latitude ?? 9.93 + Math.random()*0.04, lon: p.lon ?? p.longitude ?? 76.27+ Math.random()*0.05 }));
      setRoutePath(pts.length>=2? pts : [{lat:9.93,lon:76.26},{lat:9.95,lon:76.30}]);
    }catch{
      setRoutePath([{lat:9.93,lon:76.26},{lat:9.95,lon:76.30}]);
    }
  };

  return (
    <div style={{ minHeight:"100vh", display:"flex", flexDirection:"column" }}>
      {/* Top bar */}
      <header className="glass" style={{ position:"sticky", top:0, zIndex:30, height:64, display:"flex", alignItems:"center", justifyContent:"space-between", padding:"0 16px", borderLeft:"none", borderRight:"none", borderTop:"none", borderRadius:0 }}>
        <div style={{ display:"flex", alignItems:"center", gap:14 }}>
          <div style={{ width:38, height:38, borderRadius:12, background:"linear-gradient(135deg, #06b6d4, #14b8a6)", display:"grid", placeItems:"center", color:"#001018", fontWeight:900, letterSpacing:"-0.04em", boxShadow:"0 8px 20px rgba(6,182,214,0.35)", border:"1px solid rgba(255,255,255,0.18)" }}>ER</div>
          <div>
            <div style={{ fontWeight:800, letterSpacing:"-0.03em", lineHeight:1 }}>ERDOS</div>
            <div style={{ fontSize:11, color:"var(--muted)", fontWeight:600, letterSpacing:"0.06em", textTransform:"uppercase" }}>Kerala · Ernakulam · Kochi 9.9312, 76.2673</div>
          </div>
          <span className="badge" style={{ marginLeft:8, background: health?.status==="healthy" ? "rgba(16,185,129,0.16)" : "rgba(245,158,11,0.16)", borderColor: health?.status==="healthy" ? "rgba(16,185,129,0.28)": "rgba(245,158,11,0.28)", color: health?.status==="healthy" ? "#6ee7b7" : "#fcd34d" }}>
            <span className="badge-dot" style={{ background: health?.status==="healthy" ? "#10b981" : "#f59e0b" }} /> {health?.status ?? "loading"}
          </span>
          <span className="badge mono" style={{ display:"none" }}>{now.toLocaleTimeString()} IST</span>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <span className="badge" style={{ background: connected? "rgba(16,185,129,0.14)" : "rgba(239,68,68,0.14)", borderColor: connected? "rgba(16,185,129,0.22)": "rgba(239,68,68,0.22)", color: connected? "#6ee7b7":"#fca5a5" }}>
            <span className="badge-dot pulse" style={{ background: connected? "#10b981":"#ef4444", boxShadow: `0 0 0 4px ${connected? "rgba(16,185,129,0.18)":"rgba(239,68,68,0.18)"}` }} /> {connected? "LIVE":"RECONNECTING"} · WS
          </span>
          <span className="badge" style={{ background:"rgba(6,182,214,0.14)", borderColor:"rgba(6,182,214,0.22)", color:"#67e8f9" }}>ST-GNN v1.0 · XGBoost</span>
          <span className="badge mono" style={{ color:"var(--muted)" }}>{now.toLocaleDateString()}</span>
          <button className="btn btn-primary" onClick={refresh} style={{ padding:"8px 12px" }}>⟳ Refresh</button>
        </div>
      </header>

      <div style={{ display:"flex", flex:1, minHeight:0 }}>
        {/* Sidebar */}
        <aside className="glass" style={{ width:248, padding:14, display:"flex", flexDirection:"column", gap:10, borderTop:"none", borderBottom:"none", borderLeft:"none", borderRadius:0, position:"sticky", top:64, height:"calc(100vh - 64px)", overflow:"auto" }}>
          <div style={{ fontSize:11, letterSpacing:"0.12em", color:"var(--muted)", fontWeight:800, padding:"6px 8px" }}>COMMAND</div>
          {[
            ["overview","Overview"],["map","Live Map"],["predictions","Predictions"],["logistics","Logistics"],["explain","Explainability"]
          ].map(([id,label])=>(
            <button key={id} onClick={()=>setTab(id as Tab)} className="btn" style={{ justifyContent:"flex-start", gap:10, background: tab===id? "linear-gradient(135deg, rgba(6,182,214,0.22), rgba(20,184,166,0.18))": "rgba(255,255,255,0.04)", borderColor: tab===id? "rgba(6,182,214,0.32)": "var(--border)", color: tab===id? "#e0f2fe": "var(--text)", boxShadow: tab===id? "0 8px 18px rgba(6,182,214,0.14)": "none" }}>
              <span style={{ opacity: tab===id? 1: 0.85 }}><Icon name={id} /></span> {label}
            </button>
          ))}
          <div className="glass card" style={{ marginTop:8, padding:12, background:"rgba(255,255,255,0.04)" }}>
            <div style={{ fontSize:11, letterSpacing:"0.08em", color:"var(--muted)", fontWeight:800 }}>SYSTEM</div>
            <div style={{ display:"grid", gap:8, marginTop:10, fontSize:12, color:"var(--muted)" }}>
              <div style={{ display:"flex", justifyContent:"space-between" }}><span>PostGIS 3.6</span><span style={{color:"#6ee7b7"}}>● Postgres 18</span></div>
              <div style={{ display:"flex", justifyContent:"space-between" }}><span>Timescale 2.29</span><span style={{color:"#6ee7b7"}}>● Chroma 1.5</span></div>
              <div style={{ display:"flex", justifyContent:"space-between" }}><span>Groq LLM</span><span style={{color:"#67e8f9"}}>llama-3.3-70b</span></div>
              <div style={{ display:"flex", justifyContent:"space-between" }}><span>Kafka</span><span style={{color: connected?"#6ee7b7":"#fca5a5"}}>{connected?"● live":"○ idle"}</span></div>
            </div>
            {liveMsg && <div className="mono" style={{ marginTop:10, fontSize:11, color:"#67e8f9", background:"rgba(6,182,214,0.08)", border:"1px solid rgba(6,182,214,0.18)", padding:"8px 10px", borderRadius:12, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{liveMsg.event_type ?? liveMsg.type ?? "live event"}</div>}
          </div>
          <div style={{ marginTop:"auto", fontSize:11, color:"var(--muted-2)", lineHeight:1.5 }}>Tip: Click a road on the map to get a Groq-powered explanation with SHAP + similar historical floods.</div>
        </aside>

        {/* Main */}
        <main style={{ flex:1, padding:18, display:"grid", gap:16, alignContent:"start" }}>
          {loading ? (
            <div className="glass card-lg" style={{ padding:28 }}>
              <div style={{ display:"flex", gap:12, alignItems:"center" }}>
                <div className="shimmer" style={{ width:36, height:36, borderRadius:12, background:"rgba(255,255,255,0.08)" }} />
                <div><div style={{ fontWeight:800 }}>Loading digital twin…</div><div style={{ color:"var(--muted)", fontSize:13 }}>Fetching roads, shelters, predictions and health</div></div>
              </div>
              <div className="grid" style={{ gridTemplateColumns:"repeat(4,1fr)", marginTop:18 }}>
                {[1,2,3,4].map(i=> <div key={i} className="shimmer" style={{ height:96, borderRadius:16, background:"rgba(255,255,255,0.06)", border:"1px solid var(--border)" }} />)}
              </div>
            </div>
          ) : (
            <>
              {/* KPI */}
              <div className="grid" style={{ gridTemplateColumns:"repeat(4, minmax(0,1fr))" }}>
                <StatCard label="Roads" value={summary?.total_roads ?? roads.length} sub={`${atRisk} at risk · ${blocked} blocked`} accent="#06b6d4" icon="map" trend={`${roads.length? Math.round(atRisk/Math.max(1,roads.length)*100):0}% risk`} />
                <StatCard label="Shelters" value={`${summary?.current_occupancy ?? 0}/${summary?.total_capacity ?? 0}`} sub={`${summary?.shelters_operational ?? shelters.filter(s=>s.status==="OPERATIONAL").length} operational · ${occupancyPct}% full`} accent="#14b8a6" icon="shield" />
                <StatCard label="Resources" value={`${summary?.resources_available ?? resources.filter(r=>r.status==="AVAILABLE").length} avail`} sub={`${summary?.resources_deployed ?? 0} deployed · ${resources.length} total`} accent="#22d3ee" icon="truck" />
                <StatCard label="Incidents" value={summary?.active_incidents ?? incidents.filter(i=>i.status==="ACTIVE").length} sub={`${incidents.length} total · ${(zones?.overall_risk ?? "MODERATE")}`} accent={ (zones?.overall_risk==="HIGH" || atRisk>2) ? "#f43f5e" : "#f59e0b"} icon="alert" />
              </div>

              {/* Map + side */}
              <div className="grid" style={{ gridTemplateColumns:"1.7fr 0.9fr" }}>
                <div className="glass card-lg" style={{ padding:12 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10 }}>
                    <div style={{ fontWeight:800, letterSpacing:"-0.02em", display:"flex", alignItems:"center", gap:8 }}><Icon name="map" /> Live Digital Twin — Ernakulam</div>
                    <div style={{ display:"flex", gap:8 }}>
                      <button className="btn" onClick={()=>handleExplainPred(selectedRoad || roads[0]?.road_id)} disabled={!roads.length}>Explain selected</button>
                      <button className="btn btn-primary" onClick={handleRoute}>Plan route</button>
                    </div>
                  </div>
                  <MapView roads={roads} shelters={shelters} resources={resources} incidents={incidents} heatmap={heatmap} selectedRoad={selectedRoad} onSelectRoad={(id)=>{ setSelectedRoad(id); handleExplainPred(id); }} routePath={routePath} />
                </div>

                <div style={{ display:"grid", gap:14, alignContent:"start" }}>
                  <div className="glass card">
                    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                      <div style={{ fontWeight:800, display:"flex", gap:8, alignItems:"center" }}><Icon name="activity"/> Live feed</div>
                      <span className="badge" style={{ background: connected? "rgba(16,185,129,0.14)":"rgba(239,68,68,0.14)", color: connected? "#6ee7b7":"#fca5a5" }}>{connected? "streaming":"offline"}</span>
                    </div>
                    <div style={{ marginTop:10, display:"grid", gap:8, maxHeight:220, overflow:"auto", paddingRight:4 }}>
                      {incidents.slice(0,6).map((inc:any)=>(
                        <div key={inc.incident_id} style={{ display:"flex", gap:10, padding:"10px 12px", borderRadius:12, background:"rgba(255,255,255,0.04)", border:"1px solid var(--border)" }}>
                          <div style={{ width:8, height:8, borderRadius:99, marginTop:6, background: inc.priority==="CRITICAL"? "#ef4444": inc.priority==="HIGH"? "#f43f5e": "#f59e0b", boxShadow:`0 0 0 4px ${inc.priority==="CRITICAL"? "rgba(239,68,68,0.18)":"rgba(245,158,11,0.18)"}` }} />
                          <div style={{ flex:1, minWidth:0 }}>
                            <div style={{ fontWeight:700, fontSize:13, whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>{inc.incident_id} · {inc.incident_type}</div>
                            <div style={{ fontSize:12, color:"var(--muted)" }}>{inc.priority} · {inc.status} · {inc.reported_people ?? 0} people</div>
                          </div>
                          <button className="btn" style={{ padding:"6px 10px", fontSize:12 }} onClick={()=> setTab("explain")}>Explain</button>
                        </div>
                      ))}
                      {!incidents.length && <div style={{ color:"var(--muted)", fontSize:13 }}>No active incidents — twin is calm.</div>}
                    </div>
                  </div>

                  <div className="glass card">
                    <div style={{ fontWeight:800, marginBottom:8, display:"flex", gap:8, alignItems:"center" }}><Icon name="shield"/> Zones</div>
                    {(zones?.zones ?? []).map((z:any)=>(
                      <div key={z.zone} style={{ display:"flex", justifyContent:"space-between", padding:"10px 12px", borderRadius:12, background:"rgba(255,255,255,0.04)", border:"1px solid var(--border)" }}>
                        <div><div style={{ fontWeight:700, fontSize:13 }}>{z.district} · {z.zone}</div><div style={{ fontSize:12, color:"var(--muted)" }}>{z.affected_roads} affected · {z.blocked_roads} blocked · {z.available_shelters} shelters</div></div>
                        <span className="badge" style={{ background: z.flood_risk==="HIGH"? "rgba(239,68,68,0.14)": "rgba(6,182,214,0.14)", color: z.flood_risk==="HIGH"? "#fca5a5":"#67e8f9", height:"fit-content" }}>{z.flood_risk}</span>
                      </div>
                    ))}
                    <div style={{ marginTop:8, fontSize:12, color:"var(--muted)" }}>Overall risk: <b style={{ color: zones?.overall_risk==="HIGH"? "#fca5a5":"#67e8f9" }}>{zones?.overall_risk ?? "—"}</b></div>
                  </div>

                  <div className="glass card" style={{ background:"linear-gradient(135deg, rgba(6,182,214,0.14), rgba(20,184,166,0.10))" }}>
                    <div style={{ fontWeight:800, display:"flex", gap:8, alignItems:"center" }}><Icon name="spark"/> Groq narrative</div>
                    <div style={{ fontSize:12, color:"var(--muted)", marginTop:6 }}>LLM is Groq `llama-3.3-70b-versatile` — explains predictions with SHAP + similar historical floods from ChromaDB.</div>
                    <div className="mono" style={{ marginTop:10, fontSize:11, color:"#67e8f9", background:"rgba(2,10,24,0.6)", padding:"8px 10px", borderRadius:12, border:"1px solid rgba(6,182,214,0.18)" }}>{connected? "WS connected — live twin updates streaming":"Polling mode — refresh every 12s"}</div>
                  </div>
                </div>
              </div>

              {/* Predictions */}
              <div className="grid" style={{ gridTemplateColumns:"1.15fr 0.85fr" }}>
                <div className="glass card-lg">
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                    <div style={{ fontWeight:800, display:"flex", gap:8, alignItems:"center" }}><Icon name="predictions"/> Flood heatmap & predictions</div>
                    <span className="badge mono">{heatmap.length} cells · 500m</span>
                  </div>
                  <div style={{ marginTop:12, display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8 }}>
                    {heatmap.slice(0,9).map((c:any, i:number)=>{
                      const pct = Math.round((c.flood_probability||0)*100);
                      const bg = pct>=70? "linear-gradient(135deg,#ef4444,#f43f5e)" : pct>=50? "linear-gradient(135deg,#f59e0b,#f97316)" : pct>=30? "linear-gradient(135deg,#06b6d4,#14b8a6)" : "rgba(255,255,255,0.06)";
                      return <div key={i} className="card" style={{ padding:12, background: typeof bg==="string" && bg.startsWith("linear")? bg: bg as any, border: "1px solid var(--border)", color: pct>=30? "white":"var(--text)" }}><div style={{ fontSize:11, opacity:0.9 }}>{c.lat.toFixed(3)}, {c.lon.toFixed(3)}</div><div style={{ fontWeight:800, fontSize:18 }}>{pct}%</div><div style={{ fontSize:11, opacity:0.9 }}>{c.risk_level}</div></div>;
                    })}
                  </div>
                  <div style={{ marginTop:12, display:"grid", gap:8, maxHeight:220, overflow:"auto" }}>
                    {(predTable.length? predTable : roads.slice(0,6).map(r=> ({road_id:r.road_id, flood_probability:r.flood_probability??0})) ).map((p:any)=>(
                      <div key={p.road_id} style={{ display:"flex", alignItems:"center", gap:12, padding:"10px 12px", borderRadius:12, background:"rgba(255,255,255,0.04)", border:"1px solid var(--border)" }}>
                        <div style={{ fontWeight:800, minWidth:84 }}>{p.road_id}</div>
                        <div style={{ flex:1, height:10, borderRadius:999, background:"rgba(255,255,255,0.08)", overflow:"hidden" }}>
                          <div style={{ width:`${Math.round((p.flood_probability||0)*100)}%`, height:"100%", background: (p.flood_probability||0)>=0.7? "#ef4444": (p.flood_probability||0)>=0.4? "#f59e0b": "#06b6d4", transition:"width .6s ease" }} />
                        </div>
                        <div className="mono" style={{ minWidth:48, textAlign:"right", fontWeight:700 }}>{Math.round((p.flood_probability||0)*100)}%</div>
                        <button className="btn" style={{ padding:"6px 10px", fontSize:12 }} onClick={()=>handleExplainPred(p.road_id)}>Explain</button>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="glass card-lg">
                  <div style={{ fontWeight:800, display:"flex", gap:8, alignItems:"center" }}><Icon name="activity"/> Models & health</div>
                  <div style={{ display:"grid", gap:10, marginTop:12 }}>
                    {models.map((m:any)=>(
                      <div key={m.name} className="card" style={{ background:"rgba(255,255,255,0.04)", border:"1px solid var(--border)" }}>
                        <div style={{ display:"flex", justifyContent:"space-between" }}>
                          <div style={{ fontWeight:700, fontSize:13 }}>{m.name}</div>
                          <span className="badge mono" style={{ background:"rgba(6,182,214,0.12)", color:"#67e8f9" }}>{m.type} · {m.version}</span>
                        </div>
                        <div className="mono" style={{ fontSize:11, color:"var(--muted)", marginTop:6 }}>{Object.entries(m.metrics||{}).map(([k,v])=> `${k}:${v}`).join(" · ")}</div>
                      </div>
                    ))}
                    <div className="card" style={{ background:"rgba(255,255,255,0.04)" }}>
                      <div style={{ fontWeight:700, fontSize:13 }}>ST-GNN propagation</div>
                      <div style={{ fontSize:12, color:"var(--muted)", marginTop:4 }}>Graph: 14 nodes · 48 edges · horizon 6 · hidden 32. Flood spread predicted via temporal GRU + GraphConv. Falls back to heuristic when checkpoint unavailable.</div>
                    </div>
                    <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                      <span className="badge" style={{ background:"rgba(16,185,129,0.12)", color:"#6ee7b7", borderColor:"rgba(16,185,129,0.22)" }}>● XGBoost 3.4 · 12 features</span>
                      <span className="badge" style={{ background:"rgba(6,182,214,0.12)", color:"#67e8f9", borderColor:"rgba(6,182,214,0.22)" }}>● ST-GNN 27KB · 60 epochs</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Logistics */}
              <div className="grid" style={{ gridTemplateColumns:"1fr 1fr" }}>
                <div className="glass card-lg">
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                    <div style={{ fontWeight:800, display:"flex", gap:8, alignItems:"center" }}><Icon name="shield"/> Shelters</div>
                    <span className="badge">{shelters.length} total</span>
                  </div>
                  <div style={{ marginTop:10, display:"grid", gap:8, maxHeight:360, overflow:"auto", paddingRight:4 }}>
                    {shelters.map((s:any)=> {
                      const pct = Math.round((s.occupancy/Math.max(1,s.capacity))*100);
                      const bar = pct>=90? "#ef4444" : pct>=70? "#f59e0b" : "#06b6d4";
                      return (
                        <div key={s.shelter_id} style={{ padding:12, borderRadius:14, background:"rgba(255,255,255,0.04)", border:"1px solid var(--border)" }}>
                          <div style={{ display:"flex", justifyContent:"space-between", gap:12 }}>
                            <div style={{ fontWeight:700, fontSize:13 }}>{s.shelter_id} <span style={{ color:"var(--muted)", fontWeight:500 }}>· {s.status}</span></div>
                            <span className="badge" style={{ background: s.risk_level==="HIGH"||s.risk_level==="CRITICAL"? "rgba(239,68,68,0.14)": "rgba(6,182,214,0.14)", color: s.risk_level==="HIGH"?"#fca5a5":"#67e8f9" }}>{s.risk_level||"LOW"}</span>
                          </div>
                          <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, color:"var(--muted)", marginTop:6 }}><span>{s.occupancy}/{s.capacity}</span><span>{pct}%</span></div>
                          <div style={{ height:8, borderRadius:999, background:"rgba(255,255,255,0.08)", overflow:"hidden", marginTop:6 }}><div style={{ width:`${pct}%`, height:"100%", background: bar }} /></div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="glass card-lg">
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                    <div style={{ fontWeight:800, display:"flex", gap:8, alignItems:"center" }}><Icon name="truck"/> Resources & deployments</div>
                    <span className="badge">{resources.length} total · {resources.filter((r:any)=>r.status==="AVAILABLE").length} avail</span>
                  </div>
                  <div style={{ display:"grid", gap:8, marginTop:10, maxHeight:360, overflow:"auto", paddingRight:4 }}>
                    {resources.map((r:any)=>(
                      <div key={r.resource_id} style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"12px", borderRadius:14, background: r.status==="AVAILABLE"? "rgba(16,185,129,0.08)": "rgba(255,255,255,0.04)", border:`1px solid ${r.status==="AVAILABLE"? "rgba(16,185,129,0.18)":"var(--border)"}` }}>
                        <div>
                          <div style={{ fontWeight:700, fontSize:13 }}>{r.resource_id} <span style={{ color:"var(--muted)", fontWeight:500 }}>· {r.resource_type}</span></div>
                          <div style={{ fontSize:12, color:"var(--muted)" }}>{r.status} {r.assigned_incident_id? `→ ${r.assigned_incident_id}`:""}</div>
                        </div>
                        <span className="badge" style={{ background: r.status==="AVAILABLE"? "rgba(16,185,129,0.14)": r.status==="DEPLOYED"? "rgba(245,158,11,0.14)":"rgba(255,255,255,0.06)", color: r.status==="AVAILABLE"? "#6ee7b7": r.status==="DEPLOYED"? "#fcd34d":"var(--muted)" }}>{r.status}</span>
                      </div>
                    ))}
                  </div>
                  <div className="grid" style={{ gridTemplateColumns:"1fr 1fr", marginTop:12 }}>
                    <div className="card" style={{ background:"rgba(255,255,255,0.04)" }}>
                      <div style={{ fontWeight:700, fontSize:12, color:"var(--muted)", letterSpacing:"0.06em", textTransform:"uppercase" }}>Quick evacuate</div>
                      <div style={{ display:"flex", gap:8, marginTop:8 }}>
                        <input className="input" placeholder="incident id" id="evac-id" defaultValue={incidents[0]?.incident_id||"inc_1"} />
                        <input className="input" placeholder="people" id="evac-people" defaultValue="50" style={{ maxWidth:90 }} />
                        <button className="btn btn-primary" onClick={async()=>{
                          const id=(document.getElementById("evac-id") as HTMLInputElement)?.value || "inc_1";
                          const p=parseInt((document.getElementById("evac-people") as HTMLInputElement)?.value||"50",10);
                          try{ const res=await api.evacuate(id,p); setEvacResult(res);}catch(e:any){ setEvacResult({error:e.message})}
                        }}>Go</button>
                      </div>
                      {evacResult && <pre className="mono" style={{ marginTop:8, fontSize:11, background:"rgba(2,10,24,0.6)", padding:8, borderRadius:10, border:"1px solid var(--border)", overflow:"auto", maxHeight:120 }}>{JSON.stringify(evacResult,null,2)}</pre>}
                    </div>
                    <div className="card" style={{ background:"rgba(255,255,255,0.04)" }}>
                      <div style={{ fontWeight:700, fontSize:12, color:"var(--muted)", letterSpacing:"0.06em", textTransform:"uppercase" }}>Allocate resource</div>
                      <div style={{ display:"flex", gap:8, marginTop:8 }}>
                        <input className="input" placeholder="type RESCUE_BOAT" id="alloc-type" defaultValue="RESCUE_BOAT" />
                        <button className="btn btn-primary" onClick={async()=>{
                          const t=(document.getElementById("alloc-type") as HTMLInputElement)?.value || "RESCUE_BOAT";
                          const inc=incidents[0]?.incident_id||"inc_1";
                          try{ const res=await api.allocate(inc,t, roads[0]?.road_id||"node_1"); setAllocResult(res);}catch(e:any){ setAllocResult({error:e.message})}
                        }}>Allocate</button>
                      </div>
                      {allocResult && <pre className="mono" style={{ marginTop:8, fontSize:11, background:"rgba(2,10,24,0.6)", padding:8, borderRadius:10, border:"1px solid var(--border)", overflow:"auto", maxHeight:120 }}>{JSON.stringify(allocResult,null,2)}</pre>}
                    </div>
                  </div>
                </div>
              </div>

              {/* Explainability */}
              <div className="grid" style={{ gridTemplateColumns:"1fr 1fr" }}>
                <div className="glass card-lg">
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                    <div style={{ fontWeight:800, display:"flex", gap:8, alignItems:"center" }}><Icon name="spark"/> Flood explanation</div>
                    <select className="select" value={selectedRoad||""} onChange={e=>handleExplainPred(e.target.value)} style={{ maxWidth:160 }}>
                      {roads.map((r:any)=> <option key={r.road_id} value={r.road_id}>{r.road_id}</option>)}
                    </select>
                  </div>
                  {!explainPred ? (
                    <div style={{ marginTop:12, padding:16, borderRadius:14, background:"rgba(255,255,255,0.04)", border:"1px dashed var(--border)", color:"var(--muted)", fontSize:13 }}>Select a road on the map or from the dropdown to see SHAP attributions, counterfactuals and the Groq narrative.</div>
                  ) : (
                    <div style={{ marginTop:12, display:"grid", gap:12 }}>
                      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"10px 12px", borderRadius:12, background:"linear-gradient(135deg, rgba(6,182,214,0.14), rgba(20,184,166,0.12))", border:"1px solid rgba(6,182,214,0.18)" }}>
                        <div style={{ fontWeight:800 }}>{explainPred.road_id} · {(explainPred.flood_probability*100).toFixed(1)}%</div>
                        <span className="badge" style={{ background:"rgba(2,10,24,0.6)", color:"#67e8f9" }}>{explainPred.top_features?.length||0} features</span>
                      </div>
                      <div style={{ display:"grid", gap:8 }}>
                        {(explainPred.top_features||[]).slice(0,5).map((f:any)=>{
                          const pct = Math.round((f.importance||0)*100);
                          const w = Math.min(100, Math.max(8, pct*2.2));
                          return (
                            <div key={f.feature} style={{ display:"grid", gap:6 }}>
                              <div style={{ display:"flex", justifyContent:"space-between", fontSize:12 }}><span style={{ fontWeight:700 }}>{f.feature}</span><span className="mono" style={{ color:"var(--muted)" }}>{f.importance?.toFixed(3)}</span></div>
                              <div style={{ height:8, borderRadius:999, background:"rgba(255,255,255,0.08)", overflow:"hidden" }}><div style={{ width:`${w}%`, height:"100%", background:"linear-gradient(90deg,#06b6d4,#14b8a6)" }} /></div>
                              <div style={{ fontSize:11, color:"var(--muted)" }}>{f.description}</div>
                            </div>
                          );
                        })}
                      </div>
                      {explainPred.counterfactuals && <div className="card" style={{ background:"rgba(255,255,255,0.04)" }}><div style={{ fontWeight:700, fontSize:12, color:"var(--muted)", letterSpacing:"0.06em", textTransform:"uppercase" }}>Counterfactuals</div><div className="mono" style={{ fontSize:11, marginTop:6, display:"grid", gap:4 }}>{explainPred.counterfactuals.map((c:any,i:number)=><div key={i}>{c.feature} → {c.value} ⇒ {(c.new_probability*100).toFixed(1)}%</div>)}</div></div>}
                      {explainPred.narrative && <div style={{ padding:12, borderRadius:14, background:"rgba(6,182,214,0.08)", border:"1px solid rgba(6,182,214,0.18)", fontSize:13, lineHeight:1.5 }}>{explainPred.narrative}</div>}
                      {explainPred.similar_disasters?.length>0 && (
                        <div>
                          <div style={{ fontWeight:700, fontSize:12, color:"var(--muted)", letterSpacing:"0.06em", textTransform:"uppercase" }}>Similar historical floods (ChromaDB)</div>
                          <div style={{ display:"grid", gap:8, marginTop:6 }}>
                            {explainPred.similar_disasters.slice(0,3).map((d:any,i:number)=>(
                              <div key={i} className="card" style={{ padding:10, background:"rgba(255,255,255,0.04)" }}>
                                <div style={{ fontWeight:700, fontSize:12 }}>{d.metadata?.disaster_type||"flood"} · {d.metadata?.district_name||"Kerala"}</div>
                                <div style={{ fontSize:11, color:"var(--muted)" }}>{d.metadata?.response_summary?.slice(0,110) || "Historical response"}</div>
                                <div className="mono" style={{ fontSize:10, color:"#67e8f9", marginTop:4 }}>distance {Number(d.distance).toFixed(3)}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div className="glass card-lg">
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", gap:8 }}>
                    <div style={{ fontWeight:800, display:"flex", gap:8, alignItems:"center" }}><Icon name="explain"/> Decision explanation</div>
                    <div style={{ display:"flex", gap:8 }}>
                      <select id="dec-type" className="select" defaultValue="decision" style={{ maxWidth:130 }}>
                        <option value="evacuation">evacuation</option>
                        <option value="routing">routing</option>
                        <option value="decision">allocation</option>
                      </select>
                      <input id="dec-id" className="input" placeholder="id d1" defaultValue="d1" style={{ maxWidth:90 }} />
                      <button className="btn btn-primary" onClick={()=>{
                        const t=(document.getElementById("dec-type") as HTMLSelectElement).value;
                        const id=(document.getElementById("dec-id") as HTMLInputElement).value||"d1";
                        handleExplainDec(t,id);
                      }}>Explain</button>
                    </div>
                  </div>
                  {!explainDec ? (
                    <div style={{ marginTop:12, padding:16, borderRadius:14, background:"rgba(255,255,255,0.04)", border:"1px dashed var(--border)", color:"var(--muted)", fontSize:13 }}>Ask for an evacuation, routing or allocation rationale — evidence is extracted from the live twin and summarized by Groq.</div>
                  ) : (
                    <div style={{ marginTop:12, display:"grid", gap:12 }}>
                      <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}><span className="badge" style={{ background:"rgba(6,182,214,0.14)", color:"#67e8f9" }}>{explainDec.decision_type}</span><span className="badge mono">{explainDec.decision_id}</span><span className="badge" style={{ background:"rgba(16,185,129,0.12)", color:"#6ee7b7" }}>{Math.round((explainDec.confidence||0)*100)}% confidence</span></div>
                      <div style={{ padding:12, borderRadius:14, background:"rgba(255,255,255,0.04)", border:"1px solid var(--border)", fontSize:13, lineHeight:1.5 }}>{explainDec.rationale}</div>
                      {explainDec.narrative && explainDec.narrative!==explainDec.rationale && <div style={{ padding:12, borderRadius:14, background:"rgba(20,184,166,0.08)", border:"1px solid rgba(20,184,166,0.18)", fontSize:13, lineHeight:1.5 }}><span style={{ fontWeight:800, color:"#5eead4" }}>Groq:</span> {explainDec.narrative}</div>}
                      <div>
                        <div style={{ fontWeight:700, fontSize:12, color:"var(--muted)", letterSpacing:"0.06em", textTransform:"uppercase" }}>Factors considered</div>
                        <div style={{ display:"flex", gap:6, flexWrap:"wrap", marginTop:6 }}>{(explainDec.factors_considered||[]).map((f:string)=><span key={f} className="badge" style={{ background:"rgba(255,255,255,0.06)" }}>{f}</span>)}</div>
                      </div>
                      <div>
                        <div style={{ fontWeight:700, fontSize:12, color:"var(--muted)", letterSpacing:"0.06em", textTransform:"uppercase" }}>Alternatives evaluated</div>
                        <div style={{ display:"grid", gap:6, marginTop:6 }}>{(explainDec.alternatives_evaluated||[]).map((a:any,i:number)=><div key={i} style={{ padding:"8px 10px", borderRadius:12, background:"rgba(255,255,255,0.04)", border:"1px solid var(--border)", fontSize:12 }}><b>{a.option}</b> · score {a.score} · <span style={{ color:"var(--muted)" }}>{a.rejected_reason}</span></div>)}</div>
                      </div>
                      {explainDec.similar_disasters?.length>0 && (
                        <div>
                          <div style={{ fontWeight:700, fontSize:12, color:"var(--muted)", letterSpacing:"0.06em", textTransform:"uppercase" }}>Relevant history</div>
                          <div style={{ display:"grid", gap:6, marginTop:6 }}>{explainDec.similar_disasters.slice(0,2).map((d:any,i:number)=><div key={i} className="mono" style={{ fontSize:11, padding:"8px 10px", borderRadius:12, background:"rgba(255,255,255,0.04)", border:"1px solid var(--border)" }}>{d.metadata?.district_name}: {String(d.metadata?.response_summary||"").slice(0,90)}</div>)}</div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Footer */}
              <div className="glass card" style={{ display:"flex", justifyContent:"space-between", alignItems:"center", flexWrap:"wrap", gap:12, background:"rgba(255,255,255,0.03)" }}>
                <div style={{ fontSize:12, color:"var(--muted)" }}>ERDOS · Kerala Flood Twin · PostGIS 3.6 · Timescale 2.29 · ChromaDB 1.5 · Groq llama-3.3-70b · ST-GNN 60 epochs · Vite {new Date().getFullYear()}</div>
                <div style={{ display:"flex", gap:8 }}>
                  <span className="badge mono">API 8000</span>
                  <span className="badge mono">WEB 5173</span>
                  <a className="badge" href="/api/v1/health" target="_blank" style={{ textDecoration:"none" }}>health →</a>
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
