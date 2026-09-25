import { useEffect, useRef, useState } from "react";

const TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkYXNoYm9hcmQiLCJyb2xlcyI6WyJhZG1pbiJdLCJwZXJtaXNzaW9ucyI6WyIqIl0sImF1ZCI6ImVyZG9zLWFwaSIsImV4cCI6MTgyMTg1NTI5OX0._iPIh2GwTjWj6_5nEEQ6S0WKx8Pog2OtTrUwE2LQ5_s";

export function useWebSocket(onMessage: (msg:any)=>void){
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket|null>(null);
  useEffect(()=>{
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${location.host}/ws?token=${encodeURIComponent(TOKEN)}`;
    let ws: WebSocket;
    let retries=0;
    let closed=false;
    const connect=()=>{
      ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = ()=>{ setConnected(true); retries=0; };
      ws.onclose = ()=>{ setConnected(false); if(!closed && retries<5){ setTimeout(()=>{retries++; connect();}, 1200*Math.pow(1.6,retries)); } };
      ws.onerror = ()=>{ try{ws.close()}catch{} };
      ws.onmessage = (ev)=>{
        try{ const data=JSON.parse(ev.data); onMessage(data);}catch{}
      };
    };
    connect();
    return ()=>{ closed=true; try{wsRef.current?.close()}catch{} };
  }, [onMessage]);
  return { connected, ws: wsRef.current };
}
