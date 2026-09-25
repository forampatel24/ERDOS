import { useEffect, useRef } from "react";

type Props = {
  roads: any[];
  shelters: any[];
  resources: any[];
  incidents: any[];
  heatmap?: { lat:number; lon:number; flood_probability:number }[];
  selectedRoad?: string | null;
  onSelectRoad?: (id:string)=>void;
  routePath?: { lat:number; lon:number }[] | null;
};

export default function MapView({ roads, shelters, resources, incidents, heatmap, selectedRoad, onSelectRoad, routePath }:Props){
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const layerRef = useRef<any>(null);

  useEffect(()=>{
    let L:any;
    let destroyed=false;
    (async()=>{
      const leaflet = await import("leaflet");
      L = (leaflet as any).default ?? leaflet;
      if(destroyed || !ref.current || mapRef.current) return;
      const map = L.map(ref.current, { zoomControl:false, attributionControl:false }).setView([9.9312, 76.2673], 11);
      mapRef.current = map;
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        maxZoom: 19, attribution: "&copy; OpenStreetMap & CARTO"
      }).addTo(map);
      L.control.zoom({ position:"bottomright" }).addTo(map);
      L.control.attribution({ position:"bottomright", prefix:false }).addTo(map).addAttribution("© OSM | ERDOS");
      layerRef.current = L.layerGroup().addTo(map);
      // inject custom CSS for markers
      const style = document.createElement("style");
      style.textContent = `.erdos-pin{width:14px;height:14px;border-radius:999px;border:2px solid rgba(255,255,255,0.9);box-shadow:0 2px 10px rgba(0,0,0,0.5)} .erdos-shelter{width:22px;height:22px;border-radius:8px;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:800;box-shadow:0 4px 16px rgba(0,0,0,0.45);border:1px solid rgba(255,255,255,0.22)}`;
      document.head.appendChild(style);
    })();
    return ()=>{ destroyed=true; try{ mapRef.current?.remove(); }catch{} mapRef.current=null; };
  }, []);

  useEffect(()=>{
    const map = mapRef.current; const group = layerRef.current;
    if(!map || !group) return;
    (async()=>{
      const leaflet = await import("leaflet");
      const L:any = (leaflet as any).default ?? leaflet;
      group.clearLayers();

      // heatmap rectangles
      if(heatmap && heatmap.length){
        heatmap.forEach(c=>{
          const col = c.flood_probability>=0.7? "#ef4444" : c.flood_probability>=0.5? "#f59e0b" : c.flood_probability>=0.3? "#06b6d4" : "rgba(6,182,214,0.12)";
          const r = L.rectangle([[c.lat-0.003, c.lon-0.003],[c.lat+0.003,c.lon+0.003]], { weight:1, color: c.flood_probability>0.25? col: "rgba(255,255,255,0.08)", fillColor: col, fillOpacity: c.flood_probability>0.25? 0.28: 0.06, dashArray: c.flood_probability>0.25? undefined: "2 4" });
          r.bindTooltip(`Flood ${(c.flood_probability*100).toFixed(0)}%`, { direction:"top" });
          r.addTo(group);
        });
      }

      const colorFor = (r:any)=>{
        const p = r.flood_probability ?? 0;
        if(r.status==="BLOCKED") return "#ef4444";
        if(r.status==="HIGH_RISK" || p>=0.7) return "#f43f5e";
        if(r.status==="MODERATE_RISK" || p>=0.35) return "#f59e0b";
        if(p>=0.18) return "#06b6d4";
        return "#22c55e";
      };

      roads.forEach((r:any)=>{
        const coords = r.geometry?.coordinates;
        let latlngs: [number,number][] = [];
        if(Array.isArray(coords)){
          latlngs = coords.map((c:any)=> Array.isArray(c)? [c[0], c[1]] as [number,number] : [c.lat, c.lon] as [number,number]);
          // coords stored as {lat,lon} or [lat,lon] — normalize
          latlngs = latlngs.map(([a,b])=> a>50 ? [b,a] as [number,number] : [a,b] as [number,number]); // handle lon/lat swap
        }
        // fallback: make synthetic line around Kochi if no geometry
        if(latlngs.length<2){
          const baseLat = 9.92 + (parseInt((r.road_id||"R0").slice(1)||"0")%7)*0.02;
          const baseLon = 76.25 + (parseInt((r.road_id||"R0").slice(1)||"0")%5)*0.03;
          latlngs = [[baseLat, baseLon],[baseLat+0.01, baseLon+0.018]];
        }
        const isSel = selectedRoad===r.road_id;
        const pl = L.polyline(latlngs, { weight: isSel? 7: 5, color: colorFor(r), opacity: isSel? 1: 0.92, lineCap:"round", lineJoin:"round" });
        (pl as any).on("click", ()=> onSelectRoad?.(r.road_id));
        pl.bindTooltip(`<b>${r.road_id}</b><br/>${r.status||"SAFE"} · ${( (r.flood_probability||0)*100).toFixed(0)}%`, { sticky:true });
        pl.addTo(group);
        if(isSel){
          L.circleMarker(latlngs[Math.floor(latlngs.length/2)], { radius:8, fillColor:"#fff", color: colorFor(r), weight:3, fillOpacity:0.95 }).addTo(group);
        }
      });

      // route
      if(routePath && routePath.length>=2){
        const L2 = L as any;
        L2.polyline(routePath.map(p=>[p.lat,p.lon]), { weight:8, color:"#22d3ee", opacity:0.95, dashArray:"10 10", lineCap:"round" }).addTo(group);
        L2.polyline(routePath.map(p=>[p.lat,p.lon]), { weight:3, color:"#fff", opacity:0.9 }).addTo(group);
      }

      shelters.forEach((s:any)=>{
        const c = s.geometry?.coordinates?.[0];
        const lat = c?.lat ?? c?.[0] ?? 9.94 + Math.random()*0.06;
        const lon = c?.lon ?? c?.[1] ?? 76.26 + Math.random()*0.08;
        const lat2 = Array.isArray(c)? c[0]: lat; const lon2 = Array.isArray(c)? c[1]: lon;
        // normalize
        const la = typeof lat2==="number" && lat2>50 ? lon : lat2;
        const lo = typeof lon2==="number" && lon2>50 ? lat2 : lon2;
        const capLeft = (s.capacity - s.occupancy);
        const bg = capLeft<=0? "#ef4444" : s.risk_level==="HIGH" || s.risk_level==="CRITICAL" ? "#f59e0b" : "#06b6d4";
        const icon = L.divIcon({ html:`<div class="erdos-shelter" style="background:${bg}">⌂</div>`, className:"", iconSize:[22,22], iconAnchor:[11,11] });
        const m = L.marker([la, lo], { icon });
        m.bindTooltip(`<b>${s.shelter_id||s.id}</b><br/>${s.status} · ${s.occupancy}/${s.capacity} · ${s.risk_level||"LOW"}`);
        m.addTo(group);
      });

      resources.forEach((r:any)=>{
        const c = r.geometry?.coordinates?.[0];
        const la = c?.lat ?? 9.96 + Math.random()*0.04;
        const lo = c?.lon ?? 76.28 + Math.random()*0.05;
        const latv = Array.isArray(c)? c[0]: la; const lonv = Array.isArray(c)? c[1]: lo;
        const nlat = latv>50 ? lonv: latv; const nlon = lonv>50 ? latv: lonv;
        const col = r.status==="AVAILABLE" ? "#10b981" : r.status==="DEPLOYED" ? "#f59e0b" : "#94a3b8";
        const icon = L.divIcon({ html:`<div class="erdos-pin" style="background:${col}"></div>`, className:"", iconSize:[14,14], iconAnchor:[7,7] });
        const m = L.marker([nlat, nlon], { icon });
        m.bindTooltip(`<b>${r.resource_id}</b> ${r.resource_type}<br/>${r.status}`);
        m.addTo(group);
      });

      incidents.forEach((inc:any)=>{
        const c = inc.geometry?.coordinates?.[0];
        const la = c?.lat ?? 9.93 + Math.random()*0.05;
        const lo = c?.lon ?? 76.27 + Math.random()*0.06;
        const latv = Array.isArray(c)? c[0]: la; const lonv = Array.isArray(c)? c[1]: lo;
        const nlat = latv>50 ? lonv: latv; const nlon = lonv>50 ? latv: lonv;
        const col = inc.priority==="CRITICAL" ? "#ef4444" : inc.priority==="HIGH" ? "#f43f5e" : "#f59e0b";
        const icon = L.divIcon({ html:`<div style="width:18px;height:18px;border-radius:999px;background:${col};border:2px solid white;box-shadow:0 0 0 6px ${col}22, 0 4px 14px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:white;font-size:10px">!</div>`, className:"", iconSize:[18,18], iconAnchor:[9,9] });
        const m = L.marker([nlat, nlon], { icon });
        m.bindTooltip(`<b>${inc.incident_id}</b> ${inc.incident_type}<br/>${inc.priority} · ${inc.status}`);
        m.addTo(group);
      });
    })();
  }, [roads, shelters, resources, incidents, heatmap, selectedRoad, routePath]);

  return (
    <div style={{ position:"relative", borderRadius:16, overflow:"hidden", border:"1px solid rgba(255,255,255,0.08)", background:"#0b1224" }}>
      <div ref={ref} style={{ height: 520 }} />
      <div style={{ position:"absolute", left:12, top:12, display:"flex", gap:8, flexWrap:"wrap" }}>
        <span className="badge" style={{ background:"rgba(2,10,24,0.75)", backdropFilter:"blur(8px)" }}><span style={{width:8,height:8,borderRadius:99,background:"#22c55e",display:"inline-block"}}/>SAFE</span>
        <span className="badge" style={{ background:"rgba(2,10,24,0.75)" }}><span style={{width:8,height:8,borderRadius:99,background:"#06b6d4",display:"inline-block"}}/>MODERATE</span>
        <span className="badge" style={{ background:"rgba(2,10,24,0.75)" }}><span style={{width:8,height:8,borderRadius:99,background:"#f59e0b",display:"inline-block"}}/>HIGH</span>
        <span className="badge" style={{ background:"rgba(2,10,24,0.75)" }}><span style={{width:8,height:8,borderRadius:99,background:"#ef4444",display:"inline-block"}}/>BLOCKED</span>
      </div>
      <div style={{ position:"absolute", right:12, bottom:12, fontSize:11, color:"#94a3b8", background:"rgba(2,10,24,0.72)", padding:"6px 10px", borderRadius:999, border:"1px solid rgba(255,255,255,0.08)", backdropFilter:"blur(8px)" }}>
        Kochi · Ernakulam · {roads.length} roads · {incidents.length} incidents
      </div>
    </div>
  );
}
