'use client';
import {useEffect,useState} from 'react';
const IDLE_MS=15*60*1000;
export default function SessionGuard(){
 const [warning,setWarning]=useState(false);
 useEffect(()=>{
  let lastInput=Date.now(),lastSent=0,ended=false,pending=false;
  const end=()=>{if(ended)return;ended=true;window.location.replace('/?session=ended')};
  const check=async()=>{if(ended||pending)return;const idle=Date.now()-lastInput;setWarning(idle>=IDLE_MS-60000);
   if(idle>=IDLE_MS){ended=true;void fetch('/api/auth',{method:'POST',keepalive:true,headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'logout'})}).catch(()=>{});window.location.replace('/?session=ended');return;}
   pending=true;try{const active=lastInput>lastSent;const res=await fetch('/api/auth',active?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'activity'})}:{cache:'no-store'});if(res.status===401)end();else if(res.ok&&active)lastSent=lastInput;}catch{/* The server still enforces expiry while offline. */}finally{pending=false}
  };
  const activity=(event:Event)=>{if(event.isTrusted){lastInput=Date.now();setWarning(false)}};
  const events=['pointerdown','pointermove','keydown','scroll','touchstart'];events.forEach(name=>window.addEventListener(name,activity,{passive:true}));
  const visibility=()=>{if(document.visibilityState==='visible')void check()};document.addEventListener('visibilitychange',visibility);
  const timer=setInterval(()=>void check(),15000);void check();
  return()=>{ended=true;clearInterval(timer);events.forEach(name=>window.removeEventListener(name,activity));document.removeEventListener('visibilitychange',visibility)};
 },[]);
 return warning?<div className="session-warning" role="alert">You’ll be signed out in under a minute due to inactivity. Continue working to stay signed in. Unsaved details will be cleared.</div>:null;
}
