import React,{useEffect,useRef,useState} from "react";
import {createRoot} from "react-dom/client";
import "./styles.css";

const API="/api/game";
const tokenKey="horizon_game_token";
const getToken=()=>localStorage.getItem(tokenKey)||"";
async function api(path,opts={}){
  const headers={"Content-Type":"application/json",...(opts.headers||{})};
  const token=getToken(); if(token) headers.Authorization=`Bearer ${token}`;
  const controller=new AbortController(); const timer=setTimeout(()=>controller.abort(),12000); let r; try{r=await fetch(API+path,{...opts,headers,credentials:"same-origin",signal:controller.signal})}catch(e){if(e.name==="AbortError")throw new Error("Horizon server did not respond. Check Railway and retry.");throw e}finally{clearTimeout(timer)}
  if(!r.ok){
    let msg="";
    try{
      const raw=await r.text();
      if(raw){
        try{
          const data=JSON.parse(raw);
          msg=data.error||data.message||data.detail||"";
        }catch{
          msg=raw.replace(/<[^>]*>/g," ").replace(/\\s+/g," ").trim();
        }
      }
    }catch{}
    throw new Error(msg||("Request failed ("+r.status+")."));
  }
  const raw=await r.text();
  if(!raw)return {};
  try{return JSON.parse(raw)}catch{throw new Error("The server returned an invalid response.")}
}

const fallbackWorld={locations:[],npcs:[],dungeons:[],titles:[],eggs:[],items:[],shops:[],races:{},classes:{}};
const cleanText=value=>String(value??"").replace(/\*\*/g,"").replace(/__+/g,"").replace(/\`/g,"");

function Auth({onLogin}){
  const [register,setRegister]=useState(true),[email,setEmail]=useState(""),[password,setPassword]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const submit=async e=>{
    e.preventDefault();
    setBusy(true);
    setError("");
    try{
      const r=await api(register?"/auth/register":"/auth/login",{method:"POST",body:JSON.stringify({email,password})});
      localStorage.setItem(tokenKey,r.token);
      onLogin();
    }catch(e){
      setError(e.message||"Could not connect to Horizon.");
    }finally{
      setBusy(false);
    }
  };
  return <div className="auth"><div className="auth-card">
    <div className="logo">HORIZON <span>FRONTIER</span></div>
    <p className="eyebrow">A persistent open-world RPG</p>
    <h1>{register?"Create your adventurer account":"Welcome back"}</h1>
    <p className="muted">Use your email and a password of your choice. That's all you need to enter the frontier.</p>
    <form onSubmit={submit}>
      <label>Email<input type="email" value={email} onChange={e=>setEmail(e.target.value)} required placeholder="you@example.com" autoComplete="email"/></label>
      <label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required minLength={1} maxLength={200} placeholder="Choose your password" autoComplete={register?"new-password":"current-password"}/></label>
      {error&&<div className="error">{error}</div>}
      <button className="primary wide" disabled={busy||!email||!password}>{busy?"Connecting…":register?"CREATE ACCOUNT":"LOGIN"}</button>
    </form>
    <div className="auth-divider"><span>OR</span></div>
    <a className="discord-login" href={API+"/auth/discord/start"}>CONTINUE WITH DISCORD</a>
    <div className="auth-links">
      <button className="link" onClick={()=>{setRegister(!register);setError("")}}>
        {register?"Already have an account? Login":"New here? Create an account"}
      </button>
    </div>
  </div></div>
}
function CharacterCreate({world,onDone}){
  const [name,setName]=useState(""),[race,setRace]=useState("human"),[cls,setCls]=useState("warrior"),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  const submit=async e=>{e?.preventDefault();setError("");const heroName=name.trim();if(heroName.length<2){setError("Enter a hero name with at least 2 characters.");return}if(busy)return;setBusy(true);try{await api("/character",{method:"POST",body:JSON.stringify({name:heroName,race,class_name:cls})});await onDone()}catch(e){setError(e.message||"Could not create your hero. Please try again.")}finally{setBusy(false)}};
  return <div className="auth"><div className="create-card"><div className="logo">HORIZON <span>FRONTIER</span></div><p className="eyebrow">Create your hero</p><h1>Who enters the Gate?</h1><label>Hero name<input value={name} onChange={e=>{setName(e.target.value);if(error)setError("")}} onKeyDown={e=>{if(e.key==="Enter"){e.preventDefault();submit(e)}}} maxLength={24} placeholder="Choose your own name" autoComplete="off" autoFocus/></label><div className="choice-grid"><div><h3>Race</h3>{Object.entries(world.races||{}).map(([k,v])=><button type="button" className={race===k?"choice active":"choice"} onClick={()=>setRace(k)} key={k}><b>{k}</b><small>{v.desc}</small></button>)}</div><div><h3>Class</h3>{Object.entries(world.classes||{}).filter(([k])=>!["void_knight","chronomancer","dragon_lord","soul_reaper"].includes(k)).map(([k,v])=><button type="button" className={cls===k?"choice active":"choice"} onClick={()=>setCls(k)} key={k}><b>{k}</b><small>{v.desc}</small></button>)}</div></div>{error&&<div className="error">{error}</div>}<button type="button" className="primary wide" onClick={submit} disabled={busy}>{busy?"Creating…":"ENTER HORIZON"}</button></div></div>
}

function Bar({label,value,max,type}){return <div className="bar-row"><span>{label} {value}/{max}</span><div><i className={type||""} style={{width:`${Math.max(0,Math.min(100,value/max*100))}%`}}/></div></div>}

function Game({world,initial,onLogout}){
  const [state,setState]=useState(initial),[tab,setTab]=useState("world"),[mapZoom,setMapZoom]=useState(1),[mapPan,setMapPan]=useState({x:0,y:0}),[mapTarget,setMapTarget]=useState(null),[notice,setNotice]=useState("Explore the frontier. Find roads, resources, people and secrets."),[npc,setNpc]=useState(null),[shop,setShop]=useState(null),[dungeon,setDungeon]=useState(null),[adventure,setAdventure]=useState(null),[paused,setPaused]=useState(false),[mobileMenu,setMobileMenu]=useState(false),[worldMap,setWorldMap]=useState(false),[keys,setKeys]=useState({}),[timeOfDay,setTimeOfDay]=useState(1),[weather,setWeather]=useState("clear"),[craftOpen,setCraftOpen]=useState(false),[skills,setSkills]=useState([]),[equipment,setEquipment]=useState([]),[quests,setQuests]=useState(null),[professions,setProfessions]=useState([]);
  const canvas=useRef(null),joyRef=useRef(null),touch=useRef({x:0,y:0,id:null}),pos=useRef({x:0,y:0,ready:false}),transition=useRef(false),facing=useRef("down"),lastMove=useRef(0),objectsRef=useRef([]),mapDrag=useRef({active:false,id:null,x:0,y:0,ox:0,oy:0});
  const player=state.character;
  const location=world.locations.find(x=>x.id===player?.area_key)||world.locations[0];
  const discovered=new Set(state.discovered_areas||[location?.id]);
  const localNpcs=(world.npcs||[]).filter(x=>x.location===player?.area_key);
  const canFight=!location||Number(player.level)>=Number(location.level||1);
  const scene=world.scenes?.[player?.area_key]||{};
  const landmarks=scene.landmarks||[];
  const clean=v=>cleanText(v);
  const refresh=async()=>setState(await api("/state"));
  const action=async(fn,success)=>{try{const r=await fn();const msg=r.message||r.result?.message||r.result?.error;if(msg)setNotice(clean(msg));if(r.state)setState(r.state);else await refresh();if(success)success(r)}catch(e){setNotice(e.message||"The frontier could not complete that action.")}};
  const cycleTime=()=>setTimeOfDay(v=>(v+1)%4),rerollWeather=()=>{const choices=scene.weather?.length?scene.weather:["clear","fog","rain","snow"];setWeather(choices[Math.floor(Math.random()*choices.length)])};
  const exitDirections=loc=>{const byId=new Map((world.locations||[]).map(x=>[x.id,x]));return (loc?.connections||[]).map(id=>{const t=byId.get(id);if(!t)return null;const dx=(t.map_x||0)-(loc.map_x||0),dy=(t.map_y||0)-(loc.map_y||0);return {id,dir:Math.abs(dx)>=Math.abs(dy)?(dx>=0?"east":"west"):(dy>=0?"south":"north")}}).filter(Boolean)};
  const directionVector=dir=>({north:[0,-1],east:[1,0],south:[0,1],west:[-1,0]}[dir]||[0,1]);
  const WORLD_SCALE=1150;
  const worldPoint=loc=>({x:Number(loc?.map_x||0)*WORLD_SCALE,y:Number(loc?.map_y||0)*WORLD_SCALE});
  const ensurePosition=()=>{if(!pos.current.ready&&location)Object.assign(pos.current,worldPoint(location),{ready:true})};
  const arrive=async id=>{if(transition.current)return;transition.current=true;try{const r=await api("/explore/arrive",{method:"POST",body:JSON.stringify({location:id})});setState(r.state||await api("/state"));setNotice("You reached "+(r.area?.name||"the next region")+" — keep walking.")}catch(e){setNotice(e.message||"The road ends here.")}finally{transition.current=false}};
  const tileSize=64;
  const localLayout=()=>{
    const t=(scene.biome||location?.terrain||location?.type||"forest").toLowerCase();
    const village=t.includes("village")||t.includes("kingdom")||t.includes("city")||t.includes("town");
    const snow=t.includes("snow")||t.includes("frost");
    const desert=t.includes("desert")||t.includes("steppe");
    const mountain=t.includes("mountain")||t.includes("highland")||t.includes("cliff");
    const ruins=t.includes("ruin")||t.includes("graveyard");
    const water=t.includes("lake")||t.includes("coast")||t.includes("underwater");
    return {village,snow,desert,mountain,ruins,water};
  };
  const nearestLocation=(x,y)=>{let best=null,bd=Infinity;for(const l of world.locations||[]){const p=worldPoint(l),d=Math.hypot(x-p.x,y-p.y);if(d<bd){bd=d;best=l}}return {location:best,distance:bd}};
  const blockedAt=(x,y)=>Math.abs(x)>WORLD_SCALE*15.5||Math.abs(y)>WORLD_SCALE*5.5;
  const updateWorld=dt=>{
    ensurePosition();if(paused||transition.current)return;
    let x=(keys.d||keys.arrowright?1:0)-(keys.a||keys.arrowleft?1:0)+touch.current.x,y=(keys.s||keys.arrowdown?1:0)-(keys.w||keys.arrowup?1:0)+touch.current.y;
    const m=Math.hypot(x,y);if(!m){lastMove.current=0;return}x/=m;y/=m;facing.current=Math.abs(x)>Math.abs(y)?(x>0?"right":"left"):(y>0?"down":"up");lastMove.current=performance.now();
    const speed=230,nx=pos.current.x+x*speed*dt,ny=pos.current.y+y*speed*dt;if(!blockedAt(nx,pos.current.y))pos.current.x=nx;if(!blockedAt(pos.current.x,ny))pos.current.y=ny;
    for(const id of location?.connections||[]){const target=world.locations.find(l=>l.id===id);if(target){const p=worldPoint(target);if(Math.hypot(pos.current.x-p.x,pos.current.y-p.y)<430){arrive(id);break}}}
  };
  const hash=(x,y)=>{const n=Math.sin(x*12.9898+y*78.233+(location?.id||"").length*31.7)*43758.5453;return n-Math.floor(n)};
  const drawTree=(ctx,x,y,s=1)=>{ctx.fillStyle="#6f472e";ctx.fillRect(x-3*s,y+8*s,6*s,14*s);ctx.fillStyle="#183f32";ctx.fillRect(x-13*s,y-5*s,26*s,17*s);ctx.fillRect(x-8*s,y-15*s,16*s,12*s);ctx.fillStyle="#286247";ctx.fillRect(x-10*s,y-7*s,20*s,9*s);ctx.fillStyle="#3c8053";ctx.fillRect(x-4*s,y-13*s,9*s,7*s)};
  const drawRock=(ctx,x,y,s=1)=>{ctx.fillStyle="#53666a";ctx.fillRect(x-8*s,y-4*s,16*s,9*s);ctx.fillStyle="#7c9090";ctx.fillRect(x-4*s,y-7*s,8*s,4*s)};
  const drawBuilding=(ctx,x,y,s=1,roof="#8b4b3c")=>{ctx.fillStyle="#d0ad78";ctx.fillRect(x-25*s,y-2*s,50*s,32*s);ctx.fillStyle=roof;ctx.fillRect(x-30*s,y-18*s,60*s,18*s);ctx.fillStyle="#4d3028";ctx.fillRect(x-7*s,y+10*s,14*s,20*s);ctx.fillStyle="#a9d7d1";ctx.fillRect(x-18*s,y+6*s,9*s,8*s);ctx.fillRect(x+9*s,y+6*s,9*s,8*s)};
  const drawWater=(ctx,x,y,w,h)=>{ctx.fillStyle="#245e72";ctx.fillRect(x-w/2,y-h/2,w,h);ctx.strokeStyle="#5fa7ad";ctx.lineWidth=2;for(let yy=y-h/2+18;yy<y+h/2;yy+=26){ctx.beginPath();ctx.moveTo(x-w/2+10,yy);ctx.quadraticCurveTo(x,yy-5,x+w/2-10,yy);ctx.stroke()}};
  const drawHouse=(ctx,x,y,s=1,roof="#8b4b3c")=>{drawBuilding(ctx,x,y,s,roof);ctx.fillStyle="#d7b978";ctx.fillRect(x-3*s,y-8*s,6*s,8*s)};
  const drawTower=(ctx,x,y,s=1)=>{ctx.fillStyle="#77736b";ctx.fillRect(x-15*s,y-42*s,30*s,72*s);ctx.fillStyle="#9b968b";ctx.fillRect(x-20*s,y-48*s,40*s,10*s);ctx.fillStyle="#343b3a";ctx.fillRect(x-7*s,y-25*s,14*s,12*s);ctx.fillRect(x-7*s,y+12*s,14*s,18*s)};
  const drawCastle=(ctx,x,y,s=1)=>{ctx.fillStyle="#b9c1bb";ctx.fillRect(x-45*s,y-18*s,90*s,48*s);ctx.fillStyle="#d1d8d1";ctx.fillRect(x-53*s,y-45*s,22*s,28*s);ctx.fillRect(x+31*s,y-45*s,22*s,28*s);ctx.fillStyle="#56636a";ctx.fillRect(x-39*s,y-12*s,78*s,7*s);ctx.fillStyle="#7e4c46";ctx.fillRect(x-8*s,y+8*s,16*s,22*s)};
  const drawMountain=(ctx,x,y,s=1)=>{ctx.fillStyle="#59666b";ctx.beginPath();ctx.moveTo(x-80*s,y+35*s);ctx.lineTo(x-15*s,y-55*s);ctx.lineTo(x+5*s,y-15*s);ctx.lineTo(x+42*s,y-72*s);ctx.lineTo(x+90*s,y+35*s);ctx.closePath();ctx.fill();ctx.fillStyle="#c5d0d0";ctx.beginPath();ctx.moveTo(x-15*s,y-55*s);ctx.lineTo(x-2*s,y-30*s);ctx.lineTo(x+5*s,y-15*s);ctx.lineTo(x+42*s,y-72*s);ctx.lineTo(x+57*s,y-35*s);ctx.closePath();ctx.fill()};
  const drawCrystal=(ctx,x,y,s=1)=>{ctx.fillStyle="#75cbd2";ctx.beginPath();ctx.moveTo(x-12*s,y+25*s);ctx.lineTo(x-5*s,y-35*s);ctx.lineTo(x+4*s,y-12*s);ctx.lineTo(x+15*s,y-45*s);ctx.lineTo(x+22*s,y+25*s);ctx.closePath();ctx.fill();ctx.fillStyle="#c0f5f0";ctx.fillRect(x-4*s,y-27*s,5*s,43*s)};
  const drawCave=(ctx,x,y,s=1)=>{ctx.fillStyle="#384248";ctx.beginPath();ctx.arc(x,y,48*s,Math.PI,0);ctx.lineTo(x+48*s,y+34*s);ctx.lineTo(x-48*s,y+34*s);ctx.closePath();ctx.fill();ctx.fillStyle="#101719";ctx.beginPath();ctx.arc(x,y+7*s,26*s,Math.PI,0);ctx.lineTo(x+26*s,y+34*s);ctx.lineTo(x-26*s,y+34*s);ctx.closePath();ctx.fill()};
  const drawDesertDune=(ctx,x,y,s=1)=>{ctx.fillStyle="#c4a65d";ctx.beginPath();ctx.arc(x,y+20*s,75*s,Math.PI,0);ctx.fill();ctx.fillStyle="#e0c87e";ctx.beginPath();ctx.arc(x-20*s,y+5*s,55*s,Math.PI,0);ctx.fill()};
  const drawBridge=(ctx,x,y,s=1)=>{ctx.fillStyle="#704d32";ctx.fillRect(x-65*s,y-8*s,130*s,16*s);for(let i=-55;i<=55;i+=22)ctx.fillRect(x+i*s,y-15*s,8*s,30*s)};
  const drawBone=(ctx,x,y,s=1)=>{ctx.strokeStyle="#d0c3a2";ctx.lineWidth=10*s;ctx.beginPath();ctx.moveTo(x-35*s,y+25*s);ctx.quadraticCurveTo(x,y-15*s,x+38*s,y-28*s);ctx.stroke();ctx.fillStyle="#e0d2ad";ctx.fillRect(x-42*s,y+18*s,14*s,14*s);ctx.fillRect(x+30*s,y-35*s,18*s,15*s)};

  const drawRoadside=(ctx,x,y,s=1)=>{ctx.fillStyle="#806e50";ctx.fillRect(x-3*s,y-22*s,6*s,44*s);ctx.fillStyle="#d5bf7b";ctx.fillRect(x-22*s,y-24*s,44*s,13*s)};
  const drawVolcano=(ctx,x,y,s=1)=>{ctx.fillStyle="#543c38";ctx.beginPath();ctx.moveTo(x-75*s,y+40*s);ctx.lineTo(x-20*s,y-60*s);ctx.lineTo(x+15*s,y-20*s);ctx.lineTo(x+55*s,y+40*s);ctx.closePath();ctx.fill();ctx.fillStyle="#e17a4e";ctx.beginPath();ctx.arc(x,y-35*s,12*s,0,Math.PI*2);ctx.fill()};

  const drawChest=(ctx,x,y,s=1)=>{ctx.fillStyle="#6e4328";ctx.fillRect(x-13*s,y-7*s,26*s,16*s);ctx.fillStyle="#ad7a3f";ctx.fillRect(x-13*s,y-10*s,26*s,7*s);ctx.fillStyle="#e0c36a";ctx.fillRect(x-3*s,y-2*s,6*s,6*s)};
  const drawResource=(ctx,x,y,s=1,kind="herb")=>{ctx.fillStyle=kind==="ore"?"#8f8eaa":"#65a95a";ctx.fillRect(x-6*s,y-2*s,12*s,8*s);ctx.fillStyle="#b4df76";ctx.fillRect(x-2*s,y-8*s,5*s,8*s)};
  const drawEnemy=(ctx,x,y,s=1)=>{ctx.fillStyle="#a64d50";ctx.fillRect(x-9*s,y-9*s,18*s,18*s);ctx.fillStyle="#f1d17d";ctx.fillRect(x-5*s,y-5*s,3*s,3*s);ctx.fillRect(x+2*s,y-5*s,3*s,3*s);ctx.fillStyle="#6f2d38";ctx.fillRect(x-12*s,y+8*s,24*s,6*s)};
  const drawCanvas=()=>{
    const c=canvas.current;if(!c)return;ensurePosition();
    const dpr=Math.min(2,devicePixelRatio||1),w=c.clientWidth,h=c.clientHeight;if(c.width!==w*dpr||c.height!==h*dpr){c.width=w*dpr;c.height=h*dpr}
    const ctx=c.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.imageSmoothingEnabled=false;
    const t=performance.now()/1000,camX=pos.current.x,camY=pos.current.y,zoom=Math.min(1.12,Math.max(.78,Math.min(w/470,h/820))),sx=x=>Math.round(w/2+(x-camX)*zoom),sy=y=>Math.round(h/2+(y-camY)*zoom);
    const seed=(x,y,k=0)=>{const n=Math.sin(x*127.1+y*311.7+k*74.3)*43758.5453;return n-Math.floor(n)};
    const line=(pts,color,width,dash=[])=>{ctx.save();ctx.strokeStyle=color;ctx.lineWidth=Math.max(1,Math.round(width*zoom));ctx.lineCap="square";ctx.lineJoin="round";ctx.setLineDash(dash.map(v=>Math.round(v*zoom)));ctx.beginPath();pts.forEach((p,i)=>i?ctx.lineTo(sx(p[0]),sy(p[1])):ctx.moveTo(sx(p[0]),sy(p[1])));ctx.stroke();ctx.restore()};
    const poly=(pts,color)=>{ctx.fillStyle=color;ctx.beginPath();pts.forEach((p,i)=>i?ctx.lineTo(sx(p[0]),sy(p[1])):ctx.moveTo(sx(p[0]),sy(p[1])));ctx.closePath();ctx.fill()};
    const blob=(x,y,rx,ry,color)=>{ctx.fillStyle=color;ctx.beginPath();ctx.ellipse(sx(x),sy(y),rx*zoom,ry*zoom,0,0,Math.PI*2);ctx.fill()};
    const shadow=(x,y,rx,ry)=>blob(x,y,rx,ry,"rgba(0,0,0,.28)");
    const nearest=(x,y)=>{let best=world.locations[0],bd=Infinity;for(const l of world.locations||[]){const p=worldPoint(l),d=Math.hypot(x-p.x,y-p.y);if(d<bd){bd=d;best=l}}return best};
    const biome=l=>{const b=String(world.scenes?.[l?.id]?.biome||l?.terrain||l?.type||"forest").toLowerCase();if(/desert|steppe/.test(b))return ["#c9aa69","#b9985a"];if(/snow|frost/.test(b))return ["#aebdb8","#d2ddda"];if(/mountain|highland|cliff/.test(b))return ["#687a72","#87958b"];if(/lake|coast|underwater/.test(b))return ["#4a7f82","#6a9998"];if(/volcano|ash/.test(b))return ["#66564e","#8b5b48"];if(/void|eclipse/.test(b))return ["#303e3c","#4a4d54"];if(/cave|mine/.test(b))return ["#5a635d","#737b70"];if(/fae|enchanted/.test(b))return ["#467052","#5d8660"];if(/field|meadow|verdant|plains/.test(b))return ["#648451","#84945a"];return ["#4b704c","#365c43"]};
    ctx.fillStyle="#365d47";ctx.fillRect(0,0,w,h);
    const view=Math.max(w,h)/zoom*.78,visible=(world.locations||[]).filter(l=>{const p=worldPoint(l);return Math.hypot(p.x-camX,p.y-camY)<view+1300});
    // Large overlapping biome regions create one continuous landmass.
    for(const l of visible){const p=worldPoint(l),col=biome(l),pts=[];for(let i=0;i<16;i++){const a=i*Math.PI*2/16,r=720+seed(l.map_x||0,l.map_y||0,i)*230;pts.push([p.x+Math.cos(a)*r,p.y+Math.sin(a)*r*.78])}poly(pts,col[0]);blob(p.x+(seed(l.map_x||0,1,9)-.5)*420,p.y+(seed(2,l.map_y||0,10)-.5)*340,300,220,col[1])}
    // One persistent river crosses the continent.
    const river=[];for(let x=-17500;x<=3000;x+=220)river.push([x,760+Math.sin(x*.00048)*620+Math.sin(x*.0012)*180]);line(river,"#294f59",148);line(river,"#4e8d92",126);
    // Roads use the exact same coordinates as the world-map nodes.
    const road=(a,b)=>{const A=worldPoint(a),B=worldPoint(b),dx=B.x-A.x,dy=B.y-A.y,len=Math.hypot(dx,dy)||1,nx=-dy/len,ny=dx/len,m=(seed(a.map_x||0,b.map_y||0,51)-.5)*130,p=[[A.x,A.y],[A.x+dx*.34+nx*m,A.y+dy*.34+ny*m],[A.x+dx*.68-nx*m,A.y+dy*.68-ny*m],[B.x,B.y]];line(p,"rgba(48,42,31,.55)",92);line(p,"#aa9161",72);line(p,"#d6bd7c",4,[18,24])};
    const seen=new Set();for(const a of world.locations||[])for(const id of a.connections||[]){const b=world.locations.find(x=>x.id===id),k=[a.id,id].sort().join("|");if(b&&!seen.has(k)){seen.add(k);road(a,b)}}
    // Global pixel props are anchored to world coordinates and never regenerate when crossing a region.
    const minX=Math.floor((camX-w/zoom/2)/95)-2,maxX=Math.ceil((camX+w/zoom/2)/95)+2,minY=Math.floor((camY-h/zoom/2)/95)-2,maxY=Math.ceil((camY+h/zoom/2)/95)+2;
    for(let gy=minY;gy<=maxY;gy++)for(let gx=minX;gx<=maxX;gx++){const l=nearest(gx*95,gy*95),b=String(world.scenes?.[l?.id]?.biome||"forest").toLowerCase(),r=seed(gx,gy,70),x=gx*95+seed(gx,gy,71)*50-25,y=gy*95+seed(gx,gy,72)*50-25,nearRoad=Math.abs((x+y*0.17)%140)<45;if(nearRoad||/lake|coast|underwater/.test(b))continue;if(/desert|steppe/.test(b)){if(r>.62){ctx.fillStyle="#a9874d";ctx.fillRect(sx(x-17),sy(y-5),34*zoom,9*zoom);ctx.fillStyle="#d6ba70";ctx.fillRect(sx(x-9),sy(y-10),18*zoom,5*zoom)}}else if(/snow|frost/.test(b)){if(r>.58){ctx.fillStyle="#385849";ctx.fillRect(sx(x-3),sy(y),6*zoom,20*zoom);ctx.fillStyle="#dce7e3";ctx.fillRect(sx(x-14),sy(y-22),28*zoom,22*zoom)}}else if(r>.70){shadow(x,y+17,18,6);ctx.fillStyle=r>.86?"#315f40":"#3f7148";ctx.fillRect(sx(x-16),sy(y-25),32*zoom,25*zoom);ctx.fillStyle="#67452f";ctx.fillRect(sx(x-3),sy(y-4),6*zoom,22*zoom)}else if(r<.08){shadow(x,y+8,12,4);ctx.fillStyle="#6d756f";ctx.fillRect(sx(x-12),sy(y-5),24*zoom,10*zoom)}}
    // Towns and landmarks remain physically present at their global positions.
    for(const l of visible){const p=worldPoint(l),b=String(world.scenes?.[l.id]?.biome||l.type||"").toLowerCase(),d=Math.hypot(p.x-camX,p.y-camY);if(d>1150)continue;const z=.85+Math.max(0,1-d/1150)*.15;shadow(p.x,p.y+78,90,18);
      if(/village|kingdom|city|town/.test(b)||l.type==="capital"){blob(p.x,p.y,270,205,"#718857");for(let i=0;i<6;i++){const a=i*Math.PI/3+.2,x=p.x+Math.cos(a)*175,y=p.y+Math.sin(a)*130;shadow(x,y+30*z,35*z,8*z);ctx.fillStyle="#d0b67d";ctx.fillRect(sx(x-25*z),sy(y-4*z),50*z*zoom,34*z*zoom);poly([[x-32*z,y-4*z],[x,y-36*z],[x+32*z,y-4*z]],l.type==="capital"?"#6d5a48":"#81463f");ctx.fillStyle="#4b342b";ctx.fillRect(sx(x-6*z),sy(y+11*z),12*z*zoom,23*z*zoom);ctx.fillStyle="#a9d9d2";ctx.fillRect(sx(x-19*z),sy(y+3*z),9*z*zoom,9*z*zoom);ctx.fillRect(sx(x+10*z),sy(y+3*z),9*z*zoom,9*z*zoom)}ctx.fillStyle="#777064";ctx.fillRect(sx(p.x-42),sy(p.y-17),84*zoom,42*zoom);ctx.fillStyle="#b8955d";ctx.fillRect(sx(p.x-8),sy(p.y+2),16*zoom,23*zoom)}
      else if(/mountain|cliff/.test(b)){ctx.fillStyle="#566761";poly([[p.x-120,p.y+60],[p.x-35,p.y-80],[p.x+15,p.y-15],[p.x+70,p.y-105],[p.x+145,p.y+60]],"#566761");poly([[p.x-35,p.y-80],[p.x+15,p.y-15],[p.x+70,p.y-105],[p.x+88,p.y-52]],"#c5d0cc")}
      else if(/ruin|graveyard/.test(b)){ctx.fillStyle="#77766e";ctx.fillRect(sx(p.x-32),sy(p.y-55),15*zoom,85*zoom);ctx.fillRect(sx(p.x+10),sy(p.y-35),15*zoom,65*zoom);ctx.fillStyle="#555852";ctx.fillRect(sx(p.x-32),sy(p.y-44),57*zoom,10*zoom)}
      else if(/cave|mine/.test(b)){ctx.fillStyle="#394448";ctx.beginPath();ctx.arc(sx(p.x),sy(p.y),55*zoom,Math.PI,0);ctx.lineTo(sx(p.x+55),sy(p.y+35));ctx.lineTo(sx(p.x-55),sy(p.y+35));ctx.fill();ctx.fillStyle="#11191b";ctx.beginPath();ctx.arc(sx(p.x),sy(p.y+5),29*zoom,Math.PI,0);ctx.lineTo(sx(p.x+29),sy(p.y+35));ctx.lineTo(sx(p.x-29),sy(p.y+35));ctx.fill()}
      else if(/desert/.test(b)){ctx.fillStyle="#b99550";ctx.beginPath();ctx.arc(sx(p.x),sy(p.y+18),80*zoom,Math.PI,0);ctx.fill()}
      ctx.fillStyle="#efe1b2";ctx.font=Math.max(9,Math.round(11*zoom))+"px monospace";ctx.textAlign="center";ctx.fillText(l.name.toUpperCase(),sx(p.x),sy(p.y-92))}
    // Active NPCs/resources stay tied to the settlement the player is physically near.
    const active=nearest(camX,camY),ap=worldPoint(active),nearby=[];
    for(const lm of landmarks){const x=ap.x+Number(lm.x||0),y=ap.y+Number(lm.y||0);if(Math.hypot(x-camX,y-camY)>700)continue;if(lm.type==="chest"){ctx.fillStyle="#704626";ctx.fillRect(sx(x-14),sy(y-11),28*zoom,20*zoom);ctx.fillStyle="#d4a74d";ctx.fillRect(sx(x-14),sy(y-14),28*zoom,6*zoom);nearby.push({type:"resource",x:sx(x),y:sy(y),label:"Chest"})}else if(lm.type==="resource"){ctx.fillStyle="#67a85a";ctx.fillRect(sx(x-6),sy(y),12*zoom,8*zoom);ctx.fillStyle="#b7df76";ctx.fillRect(sx(x-2),sy(y-9),5*zoom,9*zoom);nearby.push({type:"resource",x:sx(x),y:sy(y),label:lm.name||"Herb"})}
    }
    for(const n of localNpcs.slice(0,8)){const i=localNpcs.indexOf(n),x=ap.x-150+(i%4)*100,y=ap.y-25+Math.floor(i/4)*85;shadow(x,y+22,15,6);blob(x,y-20,12,12,"#d9ad89");ctx.fillStyle="#35242b";ctx.fillRect(sx(x-11),sy(y-31),22*zoom,8*zoom);ctx.fillStyle="#365b70";ctx.fillRect(sx(x-13),sy(y-7),26*zoom,27*zoom);nearby.push({type:"npc",x:sx(x),y:sy(y),label:n.name})}
    for(let i=0;i<7;i++){const x=Math.round((seed(Math.floor(camX/500)+i,7,81)*1600+camX-800)/56)*56,y=Math.round((seed(Math.floor(camY/420)+i,9,82)*1300+camY-650)/56)*56;if(Math.hypot(x-camX,y-camY)<150)continue;const px=sx(x),py=sy(y);if(px<-70||px>w+70||py<-70||py>h+70)continue;shadow(x,y+17,17,6);blob(x,y,16,18,"#8f4b55");ctx.fillStyle="#f1d17d";ctx.fillRect(sx(x-6),sy(y-5),4*zoom,4*zoom);ctx.fillRect(sx(x+3),sy(y-5),4*zoom,4*zoom);nearby.push({type:"enemy",x:px,y:py,label:"Wild Enemy"})}
    objectsRef.current=nearby;
    // Chunky player sprite.
    const moving=lastMove.current&&performance.now()-lastMove.current<180,bob=moving?Math.sin(t*11)*4:0;ctx.save();ctx.translate(w/2,h/2+bob);ctx.scale(facing.current==="left"?-1:1,1);ctx.fillStyle="rgba(0,0,0,.32)";ctx.fillRect(-24*zoom,31*zoom,48*zoom,9*zoom);ctx.fillStyle="#17283d";ctx.fillRect(-23*zoom,-6*zoom,46*zoom,36*zoom);ctx.fillStyle="#285e76";ctx.fillRect(-19*zoom,-3*zoom,38*zoom,24*zoom);ctx.fillStyle="#dcb38e";ctx.fillRect(-15*zoom,-33*zoom,30*zoom,27*zoom);ctx.fillStyle="#302028";ctx.fillRect(-16*zoom,-41*zoom,32*zoom,11*zoom);ctx.fillRect(-12*zoom,-45*zoom,24*zoom,7*zoom);ctx.fillStyle="#a9dbe4";ctx.fillRect(-10*zoom,-28*zoom,6*zoom,5*zoom);ctx.fillRect(4*zoom,-28*zoom,6*zoom,5*zoom);ctx.fillStyle="#70492f";ctx.fillRect(-29*zoom,-2*zoom,7*zoom,33*zoom);ctx.fillStyle="#d9bb70";ctx.fillRect(-15*zoom,0,30*zoom,7*zoom);ctx.fillStyle="#6c442e";ctx.fillRect(27*zoom,-8*zoom,7*zoom,44*zoom);ctx.fillStyle="#dfe7e3";ctx.fillRect(30*zoom,-22*zoom,6*zoom,17*zoom);ctx.fillStyle="#273648";ctx.fillRect(-24*zoom,31*zoom,15*zoom,10*zoom);ctx.fillRect(9*zoom,31*zoom,15*zoom,10*zoom);ctx.restore();
    const phase=["rgba(255,210,145,.05)","rgba(255,255,230,.015)","rgba(255,125,90,.07)","rgba(40,45,85,.15)"][timeOfDay];ctx.fillStyle=phase;ctx.fillRect(0,0,w,h);
    if(weather==="fog"){const g=ctx.createRadialGradient(w/2,h/2,90,w/2,h/2,Math.max(w,h)*.75);g.addColorStop(0,"rgba(235,245,240,0)");g.addColorStop(1,"rgba(220,235,230,.18)");ctx.fillStyle=g;ctx.fillRect(0,0,w,h)}
    if(weather==="rain"){ctx.strokeStyle="rgba(140,200,230,.28)";for(let i=0;i<70;i++){const x=(i*73+t*170)%w,y=(i*41+t*205)%h;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x-5,y+18);ctx.stroke()}}
    if(weather==="snow"){ctx.fillStyle="rgba(250,255,255,.8)";for(let i=0;i<60;i++){const x=(i*91+t*18)%w,y=(i*47+t*38)%h;ctx.fillRect(x,y,2,2)}}
    const vg=ctx.createRadialGradient(w/2,h/2,Math.min(w,h)*.28,w/2,h/2,Math.max(w,h)*.78);vg.addColorStop(0,"rgba(0,0,0,0)");vg.addColorStop(1,"rgba(0,0,0,.27)");ctx.fillStyle=vg;ctx.fillRect(0,0,w,h);
  };
  useEffect(()=>{let id,last=performance.now();const loop=t=>{const dt=Math.min(.05,(t-last)/1000);last=t;updateWorld(dt);drawCanvas();id=requestAnimationFrame(loop)};id=requestAnimationFrame(loop);return()=>cancelAnimationFrame(id)},[keys,paused,location?.id,player.name,timeOfDay,weather,landmarks.length,scene.biome,location?.terrain]);
  const loadPanels=async()=>{try{const [q,s,e,p]=await Promise.all([api("/quests"),api("/skills"),api("/equipment"),api("/professions")]);setQuests(q);setSkills(s.skills||[]);setEquipment(e.equipment||[]);setProfessions(p.professions||[])}catch(e){setNotice(e.message)}};
  useEffect(()=>{loadPanels()},[tab]);
  const travel=async id=>{const target=world.locations.find(x=>x.id===id);if(!target)return;action(()=>api("/travel",{method:"POST",body:JSON.stringify({location:id})}),()=>{Object.assign(pos.current,worldPoint(target),{ready:true});setWorldMap(false);setMobileMenu(false)})};
  const useKnownOrWalk=x=>discovered.has(x.id)?travel(x.id):setNotice("Walk the marked "+(exitDirections(location).find(e=>e.id===x.id)?.dir||"")+" road to discover "+x.name+".");
  const talk=n=>action(()=>api("/npc/talk",{method:"POST",body:JSON.stringify({npc:n.id})}),r=>setNpc(r));
  const buy=item=>action(()=>api("/shop/buy",{method:"POST",body:JSON.stringify({item,quantity:1})}),()=>setShop(null));
  const hatch=egg=>action(()=>api("/pet/hatch",{method:"POST",body:JSON.stringify({egg})}));
  const doAdventure=()=>{if(!canFight){setNotice("Combat unlocks here at level "+location.level+".");return}action(()=>api("/adventure",{method:"POST"}),r=>{if(r.result&&!r.result.error)setAdventure(r.result)})};
  const doDungeon=d=>{if(player.level<d.level){setNotice("Reach level "+d.level+" to enter this dungeon.");return}if(d.location!==location.id){setNotice("Walk to the dungeon entrance first.");return}action(()=>api("/dungeon",{method:"POST",body:JSON.stringify({dungeon:d.id})}),r=>setDungeon(r))};
  const useItem=i=>action(()=>api("/item/use",{method:"POST",body:JSON.stringify({item:i.item_key,quantity:1})}));
  const equipItem=i=>action(()=>api("/item/equip",{method:"POST",body:JSON.stringify({item:i.item_key})}));
  const craft=()=>action(()=>api("/craft",{method:"POST",body:JSON.stringify({item:"iron_sword",quantity:1})}));
  const gather=kind=>action(()=>api("/gather",{method:"POST",body:JSON.stringify({kind})}));
  const objectTap=e=>{if(e.target.closest("button"))return;const r=canvas.current?.getBoundingClientRect();if(!r)return;const x=e.clientX-r.left,y=e.clientY-r.top;const hit=objectsRef.current.reduce((best,o)=>{const d=Math.hypot(o.x-x,o.y-y);return d<(best?.d??Infinity)?{o,d}:best},null);if(!hit||hit.d>55)return;if(hit.o.type==="enemy")doAdventure();else if(hit.o.type==="resource")gather(hit.o.label.includes("Ore")?"mine":"gather");else if(hit.o.type==="chest")setNotice("The chest is locked. Keep exploring to find its key.");};
  const updateStick=(root,e)=>{if(!root||!e)return;const r=root.getBoundingClientRect(),dx=e.clientX-(r.left+r.width/2),dy=e.clientY-(r.top+r.height/2),limit=Math.max(1,Math.min(r.width,r.height)/2-24),m=Math.hypot(dx,dy)||1,s=Math.min(1,limit/m),nx=dx*s,ny=dy*s;touch.current.x=nx/limit;touch.current.y=ny/limit;const k=root.querySelector("span");if(k)k.style.transform="translate(calc(-50% + "+nx+"px),calc(-50% + "+ny+"px))"};
  const joystickStart=e=>{if(e.pointerType==="mouse"&&e.button!==0)return;e.preventDefault();e.stopPropagation();touch.current.id=e.pointerId;joyRef.current=e.currentTarget;try{e.currentTarget.setPointerCapture(e.pointerId)}catch{}updateStick(e.currentTarget,e)};
  const joystickMove=e=>{if(touch.current.id!==e.pointerId)return;e.preventDefault();updateStick(joyRef.current,e)};
  const stopTouch=e=>{if(touch.current.id!==null&&e.pointerId!==touch.current.id)return;e.preventDefault();touch.current.id=null;touch.current.x=0;touch.current.y=0;const k=joyRef.current?.querySelector("span");if(k)k.style.transform="translate(-50%,-50%)";joyRef.current=null};
  const mapOrder=["horizon_village","whispering_wilds","sunvale_fields","old_watchtower","moonlit_grove","thornwood","ashen_pass","sunken_ruins","golden_steppe","silverlake","fae_village","beast_den","emberfall","drowned_temple","caravan_crossroads","crystal_caverns","skyreach","crimson_caldera","sunscorch_desert","royal_capital","frostbound_gate","frostspire","mistwood","verdant_basin","ironroot_mines","shattered_coast","aether_plains","moonrise_plateau","celestial_ruins","dragonbone_expanse","eclipse_valley","void_marsh","astral_gate","worldroot_hollow","horizon_expanse","edge_of_reality"];
  const mapRaw=mapOrder.map(id=>world.locations.find(x=>x.id===id)).filter(Boolean);const mapXs=mapRaw.map(x=>Number(x.map_x||0)),mapYs=mapRaw.map(x=>Number(x.map_y||0));const minMapX=Math.min(...mapXs),maxMapX=Math.max(...mapXs),minMapY=Math.min(...mapYs),maxMapY=Math.max(...mapYs);const mapNodes=mapRaw.map(l=>({...l,mx:150+((Number(l.map_x||0)-minMapX)/Math.max(1,maxMapX-minMapX))*1500,my:120+((Number(l.map_y||0)-minMapY)/Math.max(1,maxMapY-minMapY))*660}));
  const mapPoint=id=>mapNodes.find(n=>n.id===id);
  const mapIcon=n=>{const t=(world.scenes?.[n.id]?.biome||n.type||"").toLowerCase();if(t.includes("village")||t.includes("kingdom")||t.includes("city")||t.includes("town"))return "⌂";if(t.includes("cave")||t.includes("mine"))return "◇";if(t.includes("mountain")||t.includes("highland"))return "▲";if(t.includes("ruin"))return "▧";if(t.includes("volcano"))return "△";if(t.includes("lake")||t.includes("coast"))return "≈";if(t.includes("desert"))return "◌";return "•"};
  const findRoute=target=>{if(!target||target===location?.id)return [location?.id];const q=[[location?.id]],seen=new Set([location?.id]);while(q.length){const path=q.shift(),id=path[path.length-1],node=mapPoint(id);for(const next of node?.connections||[]){if(seen.has(next))continue;const np=[...path,next];if(next===target)return np;seen.add(next);q.push(np)}}return []};
  const route=findRoute(mapTarget);
  const mapClick=n=>{setMapTarget(n.id);if(discovered.has(n.id)){travel(n.id)}else{const e=exitDirections(location).find(x=>x.id===n.id);setNotice(e?"Follow the highlighted "+e.dir+" road to "+n.name+".":"Select a connected destination first; undiscovered regions must be reached on foot.")}};
  const zoomMap=d=>setMapZoom(z=>Math.max(.65,Math.min(2.4,Number((z+d).toFixed(2)))));
  const resetMap=()=>{setMapZoom(1);setMapPan({x:0,y:0});setMapTarget(location?.id)};
  const mapPointerDown=e=>{mapDrag.current={active:true,id:e.pointerId,x:e.clientX,y:e.clientY,ox:mapPan.x,oy:mapPan.y};e.currentTarget.setPointerCapture?.(e.pointerId)};
  const mapPointerMove=e=>{const d=mapDrag.current;if(!d.active||d.id!==e.pointerId)return;setMapPan({x:d.ox+e.clientX-d.x,y:d.oy+e.clientY-d.y})};
  const mapPointerUp=e=>{if(mapDrag.current.id===e.pointerId)mapDrag.current.active=false};
  if(!player)return null;
  return <div className="game" onPointerDown={objectTap}>
    <canvas ref={canvas}/>
    <header className="gamebar"><div className="logo mini">HORIZON <span>FRONTIER</span></div><div className="location-name">{location?.name} · {location?.region}</div><div className="bar-actions"><button onClick={()=>setWorldMap(true)}>MAP</button><button onClick={cycleTime}>TIME</button><button onClick={rerollWeather}>WEATHER</button><button onClick={()=>setPaused(!paused)}>{paused?"RESUME":"PAUSE"}</button><button onClick={onLogout}>LOG OUT</button></div></header>
    <aside className="hero-card"><div className="avatar">{player.name.slice(0,1).toUpperCase()}</div><div><b>{player.name}</b><small>{player.title||"Adventurer"} · Lv {player.level}</small></div><Bar label="HP" value={player.hp} max={player.max_hp}/><Bar label="MP" value={player.mp} max={player.max_mp} type="mana"/><div className="stats"><span>ATK <b>{player.atk}</b></span><span>SPD <b>{player.speed}</b></span><span>GOLD <b>{player.gold}</b></span></div></aside>
    <div className="area-banner"><b>{location?.name}</b><span>Lv {location?.level} · {canFight?"COMBAT":"EXPLORE"} · {["DAWN","DAY","DUSK","NIGHT"][timeOfDay]} · {weather.toUpperCase()}</span></div>
    <nav className="tabs">{[["world","WORLD"],["quests","QUESTS"],["inventory","INVENTORY"],["pets","PETS"],["titles","TITLES"],["dungeons","DUNGEONS"],["skills","SKILLS"],["gear","GEAR"]].map(([k,v])=><button className={tab===k?"active":""} onClick={()=>setTab(k)} key={k}>{v}</button>)}</nav>
    <section className={"panel "+(mobileMenu?"mobile-open":"")}><div className="panel-head"><h2>{tab==="world"?location?.name:tab.toUpperCase()}</h2><button className="panel-close" onClick={()=>setMobileMenu(false)}>×</button></div><div className="mobile-menu-nav">{[["world","WORLD"],["quests","QUESTS"],["inventory","INVENTORY"],["pets","PETS"],["titles","TITLES"],["dungeons","DUNGEONS"],["skills","SKILLS"],["gear","GEAR"]].map(([k,v])=><button className={tab===k?"active":""} onClick={()=>setTab(k)} key={k}>{v}</button>)}</div>
      {tab==="world"&&<><p>{location?.description}</p><div className="world-status"><b>{canFight?"FULL ACCESS":"EXPLORATION MODE"}</b><span>Walk the roads to discover the world. Towns, ruins, enemies and resources exist along the same continuous map.</span></div><div className="action-row"><button onClick={()=>gather("gather")}>GATHER</button><button onClick={()=>gather("mine")}>MINE</button><button onClick={()=>gather("fish")}>FISH</button><button onClick={()=>setCraftOpen(v=>!v)}>CRAFT</button></div>{craftOpen&&<div className="craft-box"><b>IRON SWORD</b><span>Uses your existing Crafting profession, recipe, stamina and materials.</span><button onClick={craft}>CRAFT</button></div>}<h3>People here</h3><div className="npc-list">{localNpcs.map(n=><button disabled={!canFight} onClick={()=>talk(n)} className="list-card" key={n.id}><span className="npc-icon">{n.name[0]}</span><span><b>{n.name}</b><small>{n.role}</small></span><em>{canFight?"TALK":"LOCKED"}</em></button>)}</div><h3>Roads</h3><div className="location-grid">{exitDirections(location).map(e=>{const x=world.locations.find(z=>z.id===e.id);return x?<button className="location-card road-card" onClick={()=>useKnownOrWalk(x)} key={x.id}><b>{x.name}</b><small>{e.dir.toUpperCase()} · Lv {x.level} · ~45 sec walk</small><em>{discovered.has(x.id)?"FAST TRAVEL":"WALK THE ROAD"}</em></button>:null})}</div><button className="map-open" onClick={()=>setWorldMap(true)}>OPEN WORLD MAP</button></>}
      {tab==="quests"&&<><h2>Quest Board</h2>{quests?.quests?.map(q=><div className="quest-card" key={(q.period||"x")+q.objective_key}><b>{q.title}</b><small>{String(q.period||"story").toUpperCase()} · {q.progress}/{q.target}</small><span>{q.description}</span><em>+{q.reward_xp} XP · +{q.reward_gold} G</em></div>)}<p className="muted">Daily, weekly and monthly objectives rotate from the RPG backend.</p></>}
      {tab==="inventory"&&<><h2>Inventory</h2><div className="item-grid">{state.inventory?.map(i=>{const x=(world.items?.[i.item_key]||world.items?.find?.(z=>z.id===i.item_key))||{id:i.item_key,name:i.item_key,rarity:"Common",slot:"material"};const slot=x.slot||x.category;const consumable=["consumable","food"].includes(slot),equippable=["weapon","armor","offhand","accessory","ring","amulet","relic"].includes(slot);return <button className="item" onClick={()=>consumable?useItem(i):equippable?equipItem(i):setNotice("Material: use it for crafting, upgrades or trade.")} key={i.item_key}><b>{x.name}</b><small>{x.rarity} · ×{i.quantity}</small><em>{consumable?"USE":equippable?"EQUIP":"MATERIAL"}</em></button>})}</div></>}
      {tab==="pets"&&<><h2>Pets & Eggs</h2>{state.pets?.map(p=><div className="pet item" key={p.pet_id}><b>{p.name}</b><small>{p.species} · Lv {p.level}{p.equipped?" · EQUIPPED":""}</small></div>)}<h3>Eggs</h3><div className="item-grid">{world.eggs.map(e=>state.inventory?.find(i=>i.item_key===e.id)?.quantity?<button className="item" onClick={()=>hatch(e.id)} key={e.id}><b>{e.name}</b><small>{e.rarity} · HATCH</small></button>:null)}</div></>}
      {tab==="titles"&&<><h2>Titles & Achievements</h2><div className="title-grid">{world.titles.map(t=><div className="title-card" key={t.id}><b>{t.name}</b><small>{t.condition}</small></div>)}</div></>}
      {tab==="dungeons"&&<><h2>Dungeons</h2><p className="muted">Reach the entrance physically before entering.</p>{world.dungeons.map(d=>{const at=d.location===location.id,ok=player.level>=d.level;return <button className="dungeon-card" disabled={!at||!ok} onClick={()=>doDungeon(d)} key={d.id}><span><b>{d.name}</b><small>Lv {d.level} · {d.floors} floors · Boss: {d.boss}</small></span><em>{!at?"TRAVEL TO ENTRANCE":!ok?"LOCKED":"ENTER"}</em></button>})}</>}
      {tab==="skills"&&<><h2>Skill Loadout</h2>{skills.length?<div className="skill-grid">{skills.map((s,i)=><div className="skill-card" key={s.key||i}><b>{s.name}</b><small>Unlock Lv {s.unlock}</small><span>{s.description||s.desc||"Class skill"}</span></div>)}</div>:<p className="muted">No unlocked skills yet.</p>}<p className="muted">Class and subclass skills are pulled directly from the RPG system.</p></>}
      {tab==="gear"&&<><h2>Gear & Progression</h2>{equipment.length?<div className="gear-list">{equipment.map(g=><div className="gear-row" key={g.slot}><span><b>{g.item_key}</b><small>{g.slot} · +{g.upgrade_level}</small></span><em>{g.set_key||"NO SET"}</em></div>)}</div>:<p className="muted">Equip gear to manage upgrades, intrinsics and sets here.</p>}{equipment[0]&&<button className="primary" onClick={()=>action(()=>api("/upgrade",{method:"POST",body:JSON.stringify({slot:equipment[0].slot})}))}>UPGRADE FIRST GEAR</button>}</>}
    </section>
    <div className="touch-zone" ref={joyRef} onPointerDown={joystickStart} onPointerMove={joystickMove} onPointerUp={stopTouch} onPointerCancel={stopTouch} onPointerLeave={joystickMove} onContextMenu={e=>e.preventDefault()}><span/></div>
    <div className="touch-actions"><button onClick={doAdventure}>⚔</button><button onClick={cycleTime}>☼</button><button onClick={()=>setWorldMap(true)}>⌖</button><button onClick={()=>{setTab("inventory");setMobileMenu(true)}}>▣</button><button onClick={()=>{setTab("world");setMobileMenu(v=>!v)}}>{mobileMenu?"×":"☰"}</button></div>
    {npc&&<div className="modal"><div className="dialog"><button className="close" onClick={()=>setNpc(null)}>×</button><div className="npc-big">{npc.npc.name[0]}</div><h2>{npc.npc.name}</h2><small>{npc.npc.role}</small><p className="dialogue">“{clean(npc.dialogue?.text||"The NPC waits.")}”</p><div className="dialogue-choices">{(npc.dialogue?.choices||["Goodbye."]).map((x,i)=><button key={i} onClick={()=>{const next=npc.dialogue?.next?.[i];if(next===-1||/goodbye|leave|bye/i.test(x)){setNpc(null);return}if(Number.isInteger(next))talk(npc.npc,next);else setNotice("The conversation pauses.")}}>{x}</button>)}</div></div></div>}
    {adventure&&<div className="modal"><div className="dialog"><button className="close" onClick={()=>setAdventure(null)}>×</button><h2>{adventure.win?"Adventure Complete":"Adventure Failed"}</h2><p className="muted">{adventure.enemy?.name||"Wild Encounter"}</p>{(adventure.log||[]).map((x,i)=><p key={i}>{clean(x)}</p>)}<div className="reward">{adventure.win?"Victory":"You survived"}{adventure.win&&" · +"+(adventure.xp||0)+" XP · +"+(adventure.gold||0)+" G"}</div></div></div>}
    {shop&&<div className="modal"><div className="dialog"><button className="close" onClick={()=>setShop(null)}>×</button><h2>{shop.name}</h2>{shop.products.map(i=><button className="shop-row" onClick={()=>buy(i.id)} key={i.id}><span><b>{i.name}</b><small>{i.rarity}</small></span><em>{i.price} G</em></button>)}</div></div>}
    {dungeon&&<div className="modal"><div className="dialog"><button className="close" onClick={()=>setDungeon(null)}>×</button><h2>{dungeon.result?.name||"Dungeon Run"}</h2>{(dungeon.result?.log||[]).map((x,i)=><p key={i}>{clean(x)}</p>)}{dungeon.result?.win&&<div className="reward">Victory · +{dungeon.result.xp} XP · +{dungeon.result.gold} G</div>}</div></div>}
    {worldMap&&<div className="modal world-map-modal"><div className="world-map-dialog"><button className="close" onClick={()=>setWorldMap(false)}>×</button><div className="map-title"><div><p className="eyebrow">THE FRONTIER</p><h2>World Map</h2><small>{discovered.size}/{world.locations.length} discovered · roads connect the frontier</small></div><div className="map-controls"><button onClick={()=>zoomMap(.2)}>+</button><button onClick={()=>zoomMap(-.2)}>−</button><button onClick={resetMap}>RESET</button></div></div><div className="map-viewport" onPointerDown={mapPointerDown} onPointerMove={mapPointerMove} onPointerUp={mapPointerUp} onPointerCancel={mapPointerUp}><div className="map-world" style={{transform:"translate("+mapPan.x+"px,"+mapPan.y+"px) scale("+mapZoom+")"}}><svg className="map-art" viewBox="0 0 1800 900" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="mapLand" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#526f55"/><stop offset="45%" stopColor="#405f4c"/><stop offset="100%" stopColor="#263e3b"/></linearGradient><filter id="mapGlow"><feGaussianBlur stdDeviation="3"/></filter></defs><rect width="1800" height="900" fill="url(#mapLand)"/><path d="M0 170 C220 80 360 120 520 210 S820 280 980 160 S1260 30 1500 110 S1700 230 1800 160 L1800 0 L0 0Z" fill="#34544a"/><path d="M0 620 C260 520 390 650 620 600 S980 500 1180 620 S1500 720 1800 600 L1800 900 L0 900Z" fill="#3c5744"/><path d="M1120 0 L1230 170 L1320 40 L1420 210 L1540 75 L1680 250 L1800 130 L1800 0Z" fill="#56636a" opacity=".8"/><path d="M40 760 C320 650 520 760 730 700 S1080 610 1290 700 S1550 790 1800 680" fill="none" stroke="#3a8190" strokeWidth="70" opacity=".65"/><path d="M40 760 C320 650 520 760 730 700 S1080 610 1290 700 S1550 790 1800 680" fill="none" stroke="#8ab9b0" strokeWidth="3" opacity=".35"/><g fill="#66775a" opacity=".7"><circle cx="270" cy="250" r="120"/><circle cx="520" cy="390" r="150"/><circle cx="850" cy="230" r="110"/><circle cx="1120" cy="480" r="150"/><circle cx="1510" cy="470" r="180"/></g><g fill="#798078" opacity=".45"><path d="M1040 180 l90 -110 70 110 80 -135 95 135z"/><path d="M1250 390 l80 -100 65 100 75 -120 100 120z"/></g><g fill="#b99a55" opacity=".55"><path d="M80 500 q120 -90 240 0 q-120 100 -240 0Z"/><path d="M300 560 q150 -110 290 0 q-130 110 -290 0Z"/></g><circle cx="1510" cy="610" r="115" fill="#263f43" opacity=".65"/><circle cx="1510" cy="610" r="92" fill="#3f7f87" opacity=".7"/></svg><div className="map-region region-frontier"></div><div className="map-region region-wilds"></div><div className="map-region region-mountain"></div><div className="map-region region-desert"></div><svg className="map-links" viewBox="0 0 1800 900" preserveAspectRatio="none" aria-hidden="true">{mapNodes.map(n=>(n.connections||[]).map(id=>{const target=mapPoint(id);if(!target||n.id>id)return null;const active=route.includes(n.id)&&route.includes(id);return <line key={n.id+"-"+id} x1={n.mx} y1={n.my} x2={target.mx} y2={target.my} className={active?"route-link":discovered.has(n.id)&&discovered.has(id)?"known-link":"unknown-link"}/>;}))}</svg>{mapNodes.map(n=><button type="button" key={n.id} className={"map-node "+(discovered.has(n.id)?"discovered ":"")+(n.id===location.id?"current ":"")+(n.id===mapTarget?"selected ":"")+(discovered.has(n.id)?"":"unknown")} style={{left:n.mx,top:n.my}} onPointerDown={e=>e.stopPropagation()} onClick={e=>{e.stopPropagation();mapClick(n)}}><span>{n.id===location.id?"★":mapIcon(n)}</span><b>{n.name}</b><small>Lv {n.level}</small></button>)}<div className="player-marker" style={{left:mapPoint(location.id)?.mx||900,top:mapPoint(location.id)?.my||450}}><i></i><span>YOU</span></div></div></div><div className="map-route-info">{mapTarget&&route.length>1?<><b>ROAD TO {mapPoint(mapTarget)?.name?.toUpperCase()}</b><span>{route.length-1} road{route.length-1===1?"":"s"} · {discovered.has(mapTarget)?"Teleport available":"Follow the highlighted route on foot"}</span></>:<span>Select a location to highlight its road.</span>}</div><div className="map-legend"><span>◆ Discovered</span><span>★ You are here</span><span>▲ Terrain</span><span>━ Road</span><span>━ Route</span></div></div></div>}
    <div className="ambient-pill"><span>{["DAWN","DAY","DUSK","NIGHT"][timeOfDay]}</span><span>{weather.toUpperCase()}</span></div>
    <div className="notice">{notice}</div>
    {paused&&<div className="pause-screen"><h1>PAUSED</h1><button className="primary" onClick={()=>setPaused(false)}>CONTINUE</button></div>}
  </div>
}
function App(){
  const [auth,setAuth]=useState(!!getToken()),[world,setWorld]=useState(fallbackWorld),[state,setState]=useState(null),[loading,setLoading]=useState(true);
  const [bootError,setBootError]=useState(""); const load=async()=>{setBootError("");try{const w=await api("/world");setWorld(w);try{const s=await api("/state");setState(s);setAuth(true)}catch{localStorage.removeItem(tokenKey);setAuth(false);setState(null)}}catch(e){setBootError(e.message||"Could not reach the Horizon server.")}finally{setLoading(false)}};
  useEffect(()=>{load()},[auth]);
  if(loading)return <div className="loading"><div className="logo">HORIZON <span>FRONTIER</span></div><p>Loading the frontier…</p></div>;
  if(bootError)return <div className="loading"><div className="logo">HORIZON <span>FRONTIER</span></div><p className="error">{bootError}</p><button className="primary" onClick={()=>{setLoading(true);load()}}>RETRY</button></div>;
  if(!auth)return <Auth onLogin={()=>setAuth(true)}/>;
  if(!state?.character)return <CharacterCreate world={world} onDone={async()=>setState(await api("/state"))}/>;
  return <Game world={world} initial={state} onLogout={async()=>{await api("/auth/logout",{method:"POST"});localStorage.removeItem(tokenKey);setAuth(false);setState(null)}}/>;
}
createRoot(document.getElementById("root")).render(<App/>);
