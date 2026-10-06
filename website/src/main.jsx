import React,{useEffect,useRef,useState} from "react";
import {createRoot} from "react-dom/client";
import "./styles.css";

const API="/api/game";
const tokenKey="horizon_game_token";
const getToken=()=>localStorage.getItem(tokenKey)||"";
async function api(path,opts={}){
  const headers={"Content-Type":"application/json",...(opts.headers||{})};
  const token=getToken(); if(token) headers.Authorization=`Bearer ${token}`;
  const r=await fetch(API+path,{...opts,headers});
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
  const [register,setRegister]=useState(false),[email,setEmail]=useState(""),[password,setPassword]=useState(""),[phone,setPhone]=useState(""),[code,setCode]=useState(""),[phoneMode,setPhoneMode]=useState(false),[codeSent,setCodeSent]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(""),[providers,setProviders]=useState({});
  useEffect(()=>{api("/auth/providers").then(setProviders).catch(()=>{})},[]);
  useEffect(()=>{const msg=new URLSearchParams(location.search).get("auth_error");if(msg)setError(msg)},[]);
  const submit=async e=>{e.preventDefault();setBusy(true);setError("");try{const r=await api(register?"/auth/register":"/auth/login",{method:"POST",body:JSON.stringify({email,password})});localStorage.setItem(tokenKey,r.token);onLogin()}catch(e){setError(e.message)}finally{setBusy(false)}};
  const sendCode=async()=>{setBusy(true);setError("");try{await api("/auth/phone/start",{method:"POST",body:JSON.stringify({phone})});setCodeSent(true)}catch(e){setError(e.message)}finally{setBusy(false)}};
  const verify=async()=>{setBusy(true);setError("");try{const r=await api("/auth/phone/verify",{method:"POST",body:JSON.stringify({phone,code})});localStorage.setItem(tokenKey,r.token);onLogin()}catch(e){setError(e.message)}finally{setBusy(false)}};
  const oauth=p=>{setError("");window.location.href=`/api/game/auth/${p}/start`};
  const provider=(id,label,icon)=>providers[id]?<button type="button" className={"provider "+id} onClick={()=>oauth(id)}><b>{icon}</b><span>Continue with {label}</span></button>:<button type="button" className="provider disabled" disabled><b>{icon}</b><span>{label} login needs setup</span></button>;
  return <div className="auth"><div className="auth-card">
    <div className="logo">HORIZON <span>FRONTIER</span></div><p className="eyebrow">A persistent open-world RPG</p>
    <h1>{phoneMode?"Verify your phone":register?"Create your adventurer account":"Enter the frontier"}</h1>
    <p className="muted">One Horizon account for your hero, inventory, pets, titles and progress.</p>
    {!phoneMode&&<div className="provider-grid">{provider("google","Google","G")} {provider("discord","Discord","D")} {provider("facebook","Facebook","f")}</div>}
    {!phoneMode&&<div className="or"><span>OR</span></div>}
    {!phoneMode?<form onSubmit={submit}><label>Email<input type="email" value={email} onChange={e=>setEmail(e.target.value)} required placeholder="you@example.com"/></label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required minLength={8} placeholder="At least 8 characters"/></label>{error&&<div className="error">{error}</div>}<button className="primary wide" disabled={busy}>{busy?"Connecting…":register?"CREATE ACCOUNT":"LOGIN"}</button></form>:
      <div><label>Phone number<input type="tel" value={phone} onChange={e=>setPhone(e.target.value)} placeholder="+91 9876543210" autoComplete="tel"/></label>{codeSent&&<label>Verification code<input inputMode="numeric" maxLength={6} value={code} onChange={e=>setCode(e.target.value.replace(/\D/g,""))} placeholder="6-digit code" autoComplete="one-time-code"/></label>}{error&&<div className="error">{error}</div>}{!codeSent?<button className="primary wide" disabled={busy||!phone} onClick={sendCode}>{busy?"SENDING…":"SEND SMS CODE"}</button>:<button className="primary wide" disabled={busy||code.length!==6} onClick={verify}>{busy?"VERIFYING…":"VERIFY & ENTER"}</button>}</div>}
    <div className="auth-links">{!phoneMode&&<button className="link" onClick={()=>{setRegister(!register);setError("")}}>{register?"Already have an account? Login":"New here? Create an account"}</button>}<button className="link" onClick={()=>{setPhoneMode(!phoneMode);setCodeSent(false);setError("")}}>{phoneMode?"Use email or social login":"Use phone number instead"}</button></div>
  </div></div>
}
function CharacterCreate({world,onDone}){
  const [name,setName]=useState(""),[race,setRace]=useState("human"),[cls,setCls]=useState("warrior"),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  const submit=async()=>{setBusy(true);setError("");try{await api("/character",{method:"POST",body:JSON.stringify({name,race,class_name:cls})});onDone()}catch(e){setError(e.message)}finally{setBusy(false)}};
  return <div className="auth"><div className="create-card"><div className="logo">HORIZON <span>FRONTIER</span></div><p className="eyebrow">Create your hero</p><h1>Who enters the Gate?</h1><label>Hero name<input value={name} onChange={e=>setName(e.target.value)} maxLength={24} placeholder="Choose your own name"/></label><div className="choice-grid"><div><h3>Race</h3>{Object.entries(world.races||{}).map(([k,v])=><button className={race===k?"choice active":"choice"} onClick={()=>setRace(k)} key={k}><b>{k}</b><small>{v.desc}</small></button>)}</div><div><h3>Class</h3>{Object.entries(world.classes||{}).filter(([k])=>!["void_knight","chronomancer","dragon_lord","soul_reaper"].includes(k)).map(([k,v])=><button className={cls===k?"choice active":"choice"} onClick={()=>setCls(k)} key={k}><b>{k}</b><small>{v.desc}</small></button>)}</div></div>{error&&<div className="error">{error}</div>}<button className="primary wide" disabled={busy||name.trim().length<2} onClick={submit}>{busy?"Creating…":"ENTER HORIZON"}</button></div></div>
}

function Bar({label,value,max,type}){return <div className="bar-row"><span>{label} {value}/{max}</span><div><i className={type||""} style={{width:`${Math.max(0,Math.min(100,value/max*100))}%`}}/></div></div>}

function Game({world,initial,onLogout}){
  const [state,setState]=useState(initial),[tab,setTab]=useState("world"),[notice,setNotice]=useState("Explore the frontier. Find roads, resources, people and secrets."),[npc,setNpc]=useState(null),[shop,setShop]=useState(null),[dungeon,setDungeon]=useState(null),[adventure,setAdventure]=useState(null),[paused,setPaused]=useState(false),[mobileMenu,setMobileMenu]=useState(false),[worldMap,setWorldMap]=useState(false),[keys,setKeys]=useState({}),[timeOfDay,setTimeOfDay]=useState(1),[weather,setWeather]=useState("clear"),[craftOpen,setCraftOpen]=useState(false),[skills,setSkills]=useState([]),[equipment,setEquipment]=useState([]),[quests,setQuests]=useState(null),[professions,setProfessions]=useState([]);
  const canvas=useRef(null),joyRef=useRef(null),touch=useRef({x:0,y:0,id:null}),pos=useRef({x:0,y:0}),transition=useRef(false),facing=useRef("down"),lastMove=useRef(0),objectsRef=useRef([]);
  const player=state.character;
  const location=world.locations.find(x=>x.id===player?.area_key)||world.locations[0];
  const discovered=new Set(state.discovered_areas||[location?.id]);
  const localNpcs=(world.npcs||[]).filter(x=>x.location===player?.area_key);
  const canFight=!location||Number(player.level)>=Number(location.level||1);
  const scene=world.scenes?.[player?.area_key]||{};
  const clean=v=>cleanText(v);
  const refresh=async()=>setState(await api("/state"));
  const action=async(fn,success)=>{try{const r=await fn();const msg=r.message||r.result?.message||r.result?.error;if(msg)setNotice(clean(msg));if(r.state)setState(r.state);else await refresh();if(success)success(r)}catch(e){setNotice(e.message||"The frontier could not complete that action.")}};
  const cycleTime=()=>setTimeOfDay(v=>(v+1)%4),rerollWeather=()=>{const choices=scene.weather?.length?scene.weather:["clear","fog","rain","snow"];setWeather(choices[Math.floor(Math.random()*choices.length)])};
  const exitDirections=loc=>{const byId=new Map((world.locations||[]).map(x=>[x.id,x]));return (loc?.connections||[]).map(id=>{const t=byId.get(id);if(!t)return null;const dx=(t.map_x||0)-(loc.map_x||0),dy=(t.map_y||0)-(loc.map_y||0);return {id,dir:Math.abs(dx)>=Math.abs(dy)?(dx>=0?"east":"west"):(dy>=0?"south":"north")}}).filter(Boolean)};
  const directionVector=dir=>({north:[0,-1],east:[1,0],south:[0,1],west:[-1,0]}[dir]||[0,1]);
  const arrive=async id=>{if(transition.current)return;transition.current=true;try{const r=await api("/explore/arrive",{method:"POST",body:JSON.stringify({location:id})});setState(r.state||await api("/state"));pos.current={x:0,y:0};setNotice("Arrived at "+(r.area?.name||"a new area")+" — teleport unlocked.")}catch(e){setNotice(e.message||"The road ends here.")}finally{transition.current=false}};
  const updateWorld=dt=>{if(paused||transition.current)return;let x=(keys.d||keys.arrowright?1:0)-(keys.a||keys.arrowleft?1:0)+touch.current.x,y=(keys.s||keys.arrowdown?1:0)-(keys.w||keys.arrowup?1:0)+touch.current.y,m=Math.hypot(x,y);if(!m){lastMove.current=0;return}x/=m;y/=m;facing.current=Math.abs(x)>Math.abs(y)?(x>0?"right":"left"):(y>0?"down":"up");lastMove.current=performance.now();const speed=170,worldLimit=9000,exitTrigger=7100,roadHalfWidth=2700;pos.current.x=Math.max(-worldLimit,Math.min(worldLimit,pos.current.x+x*speed*dt));pos.current.y=Math.max(-worldLimit,Math.min(worldLimit,pos.current.y+y*speed*dt));const hit=exitDirections(location).find(e=>{const [dx,dy]=directionVector(e.dir),forward=pos.current.x*dx+pos.current.y*dy,lateral=Math.abs(pos.current.x*dy-pos.current.y*dx);return forward>=exitTrigger&&lateral<=roadHalfWidth});if(hit)arrive(hit.id)};
  useEffect(()=>{const down=e=>{if(["INPUT","TEXTAREA","BUTTON"].includes(e.target.tagName))return;const k=e.key.toLowerCase();setKeys(v=>({...v,[k]:true}));if(["w","a","s","d","arrowup","arrowdown","arrowleft","arrowright"].includes(k))e.preventDefault()};const up=e=>setKeys(v=>({...v,[e.key.toLowerCase()]:false}));addEventListener("keydown",down);addEventListener("keyup",up);return()=>{removeEventListener("keydown",down);removeEventListener("keyup",up)}},[]);
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
    const c=canvas.current;if(!c)return;const dpr=Math.min(2,devicePixelRatio||1),w=c.clientWidth,h=c.clientHeight;if(c.width!==w*dpr||c.height!==h*dpr){c.width=w*dpr;c.height=h*dpr}
    const ctx=c.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.imageSmoothingEnabled=false;
    const terrain=scene.biome||location?.terrain||location?.type||"wild",base={village:"#6aa15d",forest:"#315f42",enchanted_forest:"#284e43",thorn_forest:"#354a35",farmland:"#a7a95c",watchtower:"#66766c",mountain:"#68766f",ruins:"#746f61",underwater_ruins:"#496d70",cavern:"#4d5a53",crystal_cave:"#394e61",coast:"#568f91",lake:"#2d7185",volcano:"#7a4939",volcanic_town:"#6b4939",kingdom:"#718873",city:"#748976",cliff_city:"#647f91",sky:"#6685a1",snow_outpost:"#8798a1",frost_mountains:"#71808a",mist_forest:"#405d4e",verdant:"#5e925d",mine:"#505657",steppe:"#a89a57",crossroads:"#8d805d",desert:"#b99a55",fae:"#596d8b",aether:"#6f91a1",highlands:"#6f7771",celestial:"#676d8a",dragon_graveyard:"#6f655a",eclipse:"#514153",void_marsh:"#3b3b4b",astral:"#536b8c",worldroot:"#4f6d49",endgame:"#4b4658",reality_edge:"#313443"}[terrain]||"#5f8f55";
    ctx.fillStyle=base;ctx.fillRect(0,0,w,h);
    const camX=pos.current.x,camY=pos.current.y,tile=48;for(let sy=-tile;sy<h+tile;sy+=tile)for(let sx=-tile;sx<w+tile;sx+=tile){const wx=Math.floor((sx-w/2+camX)/tile),wy=Math.floor((sy-h/2+camY)/tile),n=hash(wx,wy);ctx.fillStyle=n>.72?"rgba(255,255,255,.028)":n<.12?"rgba(0,0,0,.045)":"rgba(0,0,0,0)";ctx.fillRect(sx,sy,tile,tile);if(n>.91&&["forest","village","meadow"].includes(terrain))drawTree(ctx,sx+20,sy+18,.55);else if(n<.055&&["mountain","ruins","cave","volcano"].includes(terrain))drawRock(ctx,sx+22,sy+25,.75)}
    const worldToScreen=(wx,wy)=>[w/2+wx-camX,h/2+wy-camY];objectsRef.current=[];
    exitDirections(location).forEach(e=>{const [dx,dy]=directionVector(e.dir),gx=w/2+dx*7100-camX,gy=h/2+dy*7100-camY;ctx.strokeStyle="#c1a86f";ctx.lineWidth=26;ctx.beginPath();ctx.moveTo(w/2-dx*10000-camX,h/2-dy*10000-camY);ctx.lineTo(w/2+dx*10000-camX,h/2+dy*10000-camY);ctx.stroke();ctx.strokeStyle="#e0ca8d";ctx.lineWidth=9;ctx.beginPath();ctx.moveTo(w/2-dx*10000-camX,h/2-dy*10000-camY);ctx.lineTo(w/2+dx*10000-camX,h/2+dy*10000-camY);ctx.stroke();ctx.fillStyle="#3a2d20";ctx.fillRect(gx-22,gy-28,44,56);ctx.fillStyle="#dfc476";ctx.fillRect(gx-14,gy-14,28,28);ctx.fillStyle="#17241f";ctx.font="bold 7px monospace";ctx.textAlign="center";ctx.fillText(world.locations.find(z=>z.id===e.id)?.name||"ROAD",gx,gy-36)});
    for(let i=0;i<5;i++){const wx=hash(i+3,location?.map_x||0)*5200-2600,wy=hash(i+40,(location?.map_y||0)+12)*4200-2100,[x,y]=worldToScreen(wx,wy);if(x>-80&&x<w+80&&y>-80&&y<h+80){if(["forest","village","meadow"].includes(terrain))drawTree(ctx,x,y,.85);else drawRock(ctx,x,y,1)}}
    const drawSceneLandmarks=()=>{
      const places=scene.landmarks||[];
      const spots=[[-2100,-1300],[-500,-1450],[1200,-1200],[1900,-200],[-1300,1350],[700,1550]];
      places.forEach((kind,i)=>{const [x,y]=worldToScreen(spots[i%spots.length][0],spots[i%spots.length][1]);const s=.65+(i%3)*.18;
        if(kind.includes("mountain")||kind.includes("peaks")||kind==="cliffs")drawMountain(ctx,x,y,s);
        else if(kind.includes("crystal")||kind.includes("ore"))drawCrystal(ctx,x,y,s);
        else if(kind.includes("cave")||kind.includes("gate")||kind.includes("entrance"))drawCave(ctx,x,y,s);
        else if(kind.includes("dune")||kind.includes("desert"))drawDesertDune(ctx,x,y,s);
        else if(kind.includes("water")||kind.includes("lake")||kind.includes("river"))drawWater(ctx,x,y,900,500);
        else if(kind.includes("bridge"))drawBridge(ctx,x,y,s);
        else if(kind.includes("tower")||kind.includes("watch"))drawTower(ctx,x,y,s);
        else if(kind.includes("castle")||kind.includes("palace")||kind.includes("fortress"))drawCastle(ctx,x,y,s);
        else if(kind.includes("volcano")||kind.includes("lava"))drawVolcano(ctx,x,y,s);
        else if(kind.includes("shipwreck")||kind.includes("boats"))drawBuilding(ctx,x,y,s,"#6d5541");
        else drawHouse(ctx,x,y,s,terrain.includes("snow")?"#71818b":"#8b4b3c");
      });
    };
    if(["village","farmland","kingdom","city","cliff_city","volcanic_town","snow_outpost","crossroads","fae"].includes(terrain)){
      for(let i=0;i<6;i++){const [x,y]=worldToScreen(-1900+(i%3)*1500,-900+Math.floor(i/3)*1700);drawHouse(ctx,x,y,.65+(i%2)*.15,terrain==="kingdom"?"#6e5364":terrain==="snow_outpost"?"#71818b":"#8b4b3c");}
    }
    if(terrain==="watchtower"){drawTower(ctx,...worldToScreen(-200,-300),1.5);drawTower(ctx,...worldToScreen(1550,1100),.7)}
    if(["mountain","frost_mountains","highlands"].includes(terrain)){drawMountain(ctx,...worldToScreen(-1500,-900),1.35);drawMountain(ctx,...worldToScreen(1200,-1100),1.05)}
    if(terrain==="crystal_cave"){drawCave(ctx,...worldToScreen(-400,100),1.25);for(let i=0;i<7;i++)drawCrystal(ctx,...worldToScreen(-1800+i*580,-1000+(i%3)*900),.55+(i%2)*.2)}
    if(terrain==="cavern"||terrain==="mine"){drawCave(ctx,...worldToScreen(0,0),1.4)}
    if(terrain==="volcano"||terrain==="volcanic_town"){drawVolcano(ctx,...worldToScreen(900,-900),1.25)}
    if(terrain==="coast"||terrain==="lake"||terrain==="underwater_ruins"){drawWater(ctx,...worldToScreen(900,-500),2800,1700)}
    if(terrain==="steppe"||terrain==="farmland"){for(let i=0;i<5;i++)drawDesertDune(ctx,...worldToScreen(-1800+i*900,1200+(i%2)*600),.5)}
    if(terrain==="dragon_graveyard"){for(let i=0;i<5;i++)drawBone(ctx,...worldToScreen(-1700+i*800,900+(i%2)*800),.8)}
    drawSceneLandmarks();
    landmarks.forEach(l=>{const [x,y]=worldToScreen(l.x||0,l.y||0),s=Number(l.scale||1);if(l.kind==="building")drawBuilding(ctx,x,y,s);else if(l.kind==="tree")drawTree(ctx,x,y,s);else drawRock(ctx,x,y,s*1.4)});
    for(let i=0;i<4;i++){const wx=-1700+i*950,wy=1100+(i%2)*900,[x,y]=worldToScreen(wx,wy);if(x>-100&&x<w+100&&y>-100&&y<h+100){drawChest(ctx,x,y,1);objectsRef.current.push({type:"chest",x,y,label:"Hidden Chest"})}}
    for(let i=0;i<5;i++){const wx=-1400+i*700,wy=-1700+((i*103)%2800),[x,y]=worldToScreen(wx,wy);if(x>-100&&x<w+100&&y>-100&&y<h+100){drawResource(ctx,x,y,1,i%2?"ore":"herb");objectsRef.current.push({type:"resource",x,y,label:i%2?"Ore Vein":"Moon Herb"})}}
    const t=performance.now()/700;for(let i=0;i<4;i++){const wx=-1800+i*1100+Math.sin(t+i)*90,wy=-700+(i%2)*1300+Math.cos(t+i)*70,[x,y]=worldToScreen(wx,wy);if(x>-80&&x<w+80&&y>-80&&y<h+80){drawEnemy(ctx,x,y,1);objectsRef.current.push({type:"enemy",x,y,label:"Wild Encounter"})}}
    for(let i=0;i<localNpcs.length;i++){const n=localNpcs[i],wx=-1900+(i%3)*1500,wy=-650+Math.floor(i/3)*1250,[x,y]=worldToScreen(wx,wy);if(x>-120&&x<w+120&&y>-120&&y<h+120){ctx.fillStyle="#efb47f";ctx.fillRect(x-7,y-25,14,14);ctx.fillStyle="#3e5368";ctx.fillRect(x-10,y-10,20,25);ctx.fillStyle="#eaf5ef";ctx.font="10px monospace";ctx.textAlign="center";ctx.fillText(n.name,x,y-32)}}
    const moving=lastMove.current&&performance.now()-lastMove.current<220,frame=moving?Math.floor(performance.now()/120)%2:0,bob=moving?Math.sin(performance.now()/55)*2:0,px=w/2,py=h/2+bob;ctx.fillStyle="rgba(0,0,0,.3)";ctx.fillRect(px-15,py+27,30,6);ctx.fillStyle="#17243b";ctx.fillRect(px-11,py+5,22,21);ctx.fillStyle="#2d405e";ctx.fillRect(px-15,py+8+(frame?2:0),7,17);ctx.fillRect(px+8,py+8+(frame?0:2),7,17);ctx.fillStyle="#3b9ac2";ctx.fillRect(px-13,py-11,26,18);ctx.fillStyle="#f0b583";ctx.fillRect(px-9,py-28,18,17);ctx.fillStyle="#252b3b";ctx.fillRect(px-11,py-31,22,7);ctx.fillStyle="#8be5ef";ctx.fillRect(px-14,py+27,28,3);ctx.fillStyle="#17202d";if(facing.current==="left")ctx.fillRect(px-8,py-22,4,3);else if(facing.current==="right")ctx.fillRect(px+4,py-22,4,3);else ctx.fillRect(px-5,py-22,3,3);ctx.fillStyle="rgba(0,0,0,.55)";ctx.font="bold 11px monospace";ctx.textAlign="center";ctx.fillText(player.name,px,py+43);
    const phase=["rgba(255,242,200,.06)","rgba(255,255,255,0)","rgba(255,170,110,.08)","rgba(10,16,32,.28)"][timeOfDay];ctx.fillStyle=phase;ctx.fillRect(0,0,w,h);if(weather==="fog")ctx.fillStyle="rgba(225,235,230,.12)",ctx.fillRect(0,0,w,h);if(weather==="rain"){ctx.strokeStyle="rgba(130,190,220,.24)";for(let i=0;i<45;i++){const x=(i*73+t*120)%w,y=(i*41+t*180)%h;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x-3,y+10);ctx.stroke()}}if(weather==="snow"){ctx.fillStyle="rgba(245,250,255,.85)";for(let i=0;i<28;i++){const x=(i*91+t*15)%w,y=(i*47+t*35)%h;ctx.fillRect(x,y,3,3)}}if(weather==="wind"){ctx.strokeStyle="rgba(238,220,160,.28)";for(let i=0;i<18;i++){const x=(i*91+t*95)%w,y=(i*53+t*22)%h;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+30,y-5);ctx.stroke()}}if(weather==="ash"){ctx.fillStyle="rgba(80,70,65,.55)";for(let i=0;i<35;i++){const x=(i*67+t*38)%w,y=(i*43+t*17)%h;ctx.fillRect(x,y,2,2)}}
    const vg=ctx.createRadialGradient(w/2,h/2,Math.min(w,h)*.2,w/2,h/2,Math.max(w,h)*.75);vg.addColorStop(0,"rgba(0,0,0,0)");vg.addColorStop(1,"rgba(0,0,0,.22)");ctx.fillStyle=vg;ctx.fillRect(0,0,w,h)
  };
  useEffect(()=>{let id,last=performance.now();const loop=t=>{const dt=Math.min(.05,(t-last)/1000);last=t;updateWorld(dt);drawCanvas();id=requestAnimationFrame(loop)};id=requestAnimationFrame(loop);return()=>cancelAnimationFrame(id)},[keys,paused,location?.id,player.name,timeOfDay,weather,landmarks.length]);
  const loadPanels=async()=>{try{const [q,s,e,p]=await Promise.all([api("/quests"),api("/skills"),api("/equipment"),api("/professions")]);setQuests(q);setSkills(s.skills||[]);setEquipment(e.equipment||[]);setProfessions(p.professions||[])}catch(e){setNotice(e.message)}};
  useEffect(()=>{loadPanels()},[tab]);
  const travel=async id=>action(()=>api("/travel",{method:"POST",body:JSON.stringify({location:id})}),()=>{pos.current={x:0,y:0};setWorldMap(false);setMobileMenu(false)});
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
  const mapNodes=mapOrder.map((id,i)=>{const l=world.locations.find(x=>x.id===id);return l?{...l,mx:12+(i%5)*19,my:8+Math.floor(i/5)*12}:null}).filter(Boolean);
  const mapPoint=id=>mapNodes.find(n=>n.id===id),mapIcon=n=>{const t=(world.scenes?.[n.id]?.biome||n.type||"").toLowerCase();if(t.includes("village")||t.includes("kingdom")||t.includes("city")||t.includes("town"))return "⌂";if(t.includes("cave")||t.includes("mine"))return "◇";if(t.includes("mountain")||t.includes("highland"))return "▲";if(t.includes("ruin"))return "▧";if(t.includes("volcano"))return "△";if(t.includes("lake")||t.includes("coast"))return "≈";return "•"};
  const mapClick=n=>{if(discovered.has(n.id))travel(n.id);else{const e=exitDirections(location).find(x=>x.id===n.id);setNotice(e?"Walk "+e.dir+" to "+n.name+" to discover it.":"That area is not connected to your current road.")}};
  if(!player)return null;
  return <div className="game" onPointerDown={objectTap}>
    <canvas ref={canvas}/>
    <header className="gamebar"><div className="logo mini">HORIZON <span>FRONTIER</span></div><div className="location-name">{location?.name} · {location?.region}</div><div className="bar-actions"><button onClick={()=>setWorldMap(true)}>MAP</button><button onClick={cycleTime}>TIME</button><button onClick={rerollWeather}>WEATHER</button><button onClick={()=>setPaused(!paused)}>{paused?"RESUME":"PAUSE"}</button><button onClick={onLogout}>LOG OUT</button></div></header>
    <aside className="hero-card"><div className="avatar">{player.name.slice(0,1).toUpperCase()}</div><div><b>{player.name}</b><small>{player.title||"Adventurer"} · Lv {player.level}</small></div><Bar label="HP" value={player.hp} max={player.max_hp}/><Bar label="MP" value={player.mp} max={player.max_mp} type="mana"/><div className="stats"><span>ATK <b>{player.atk}</b></span><span>SPD <b>{player.speed}</b></span><span>GOLD <b>{player.gold}</b></span></div></aside>
    <div className="area-banner"><b>{location?.name}</b><span>Lv {location?.level} · {canFight?"COMBAT":"EXPLORE"} · {["DAWN","DAY","DUSK","NIGHT"][timeOfDay]} · {weather.toUpperCase()}</span></div>
    <nav className="tabs">{[["world","WORLD"],["quests","QUESTS"],["inventory","INVENTORY"],["pets","PETS"],["titles","TITLES"],["dungeons","DUNGEONS"],["skills","SKILLS"],["gear","GEAR"]].map(([k,v])=><button className={tab===k?"active":""} onClick={()=>setTab(k)} key={k}>{v}</button>)}</nav>
    <section className={"panel "+(mobileMenu?"mobile-open":"")}><div className="panel-head"><h2>{tab==="world"?location?.name:tab.toUpperCase()}</h2><button className="panel-close" onClick={()=>setMobileMenu(false)}>×</button></div><div className="mobile-menu-nav">{[["world","WORLD"],["quests","QUESTS"],["inventory","INVENTORY"],["pets","PETS"],["titles","TITLES"],["dungeons","DUNGEONS"],["skills","SKILLS"],["gear","GEAR"]].map(([k,v])=><button className={tab===k?"active":""} onClick={()=>setTab(k)} key={k}>{v}</button>)}</div>
      {tab==="world"&&<><p>{location?.description}</p><div className="world-status"><b>{canFight?"FULL ACCESS":"EXPLORATION MODE"}</b><span>Walk to the marked gates to discover areas. Click nearby enemies, resources or chests.</span></div><div className="action-row"><button onClick={()=>gather("gather")}>GATHER</button><button onClick={()=>gather("mine")}>MINE</button><button onClick={()=>gather("fish")}>FISH</button><button onClick={()=>setCraftOpen(v=>!v)}>CRAFT</button></div>{craftOpen&&<div className="craft-box"><b>IRON SWORD</b><span>Uses your existing Crafting profession, recipe, stamina and materials.</span><button onClick={craft}>CRAFT</button></div>}<h3>People here</h3><div className="npc-list">{localNpcs.map(n=><button disabled={!canFight} onClick={()=>talk(n)} className="list-card" key={n.id}><span className="npc-icon">{n.name[0]}</span><span><b>{n.name}</b><small>{n.role}</small></span><em>{canFight?"TALK":"LOCKED"}</em></button>)}</div><h3>Roads</h3><div className="location-grid">{exitDirections(location).map(e=>{const x=world.locations.find(z=>z.id===e.id);return x?<button className="location-card road-card" onClick={()=>useKnownOrWalk(x)} key={x.id}><b>{x.name}</b><small>{e.dir.toUpperCase()} · Lv {x.level} · ~45 sec walk</small><em>{discovered.has(x.id)?"TELEPORT UNLOCKED":"WALK TO DISCOVER"}</em></button>:null})}</div><button className="map-open" onClick={()=>setWorldMap(true)}>OPEN WORLD MAP</button></>}
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
    {worldMap&&<div className="modal world-map-modal"><div className="world-map-dialog"><button className="close" onClick={()=>setWorldMap(false)}>×</button><div className="map-title"><p className="eyebrow">THE FRONTIER</p><h2>World Map</h2><small>{discovered.size}/{world.locations.length} discovered · discovered areas are teleportable</small></div><div className="map-canvas"><svg className="map-links" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">{mapNodes.map(n=>(n.connections||[]).map(id=>{const target=mapPoint(id);if(!target||n.id>id)return null;return <line key={n.id+"-"+id} x1={n.mx} y1={n.my} x2={target.mx} y2={target.my} className={(discovered.has(n.id)&&discovered.has(id))?"known-link":"unknown-link"}/>;}))}</svg>{mapNodes.map(n=><button type="button" key={n.id} className={"map-node "+(discovered.has(n.id)?"discovered ":"")+(n.id===location.id?"current ":"")+(discovered.has(n.id)?"":"unknown")} style={{left:n.mx+"%",top:n.my+"%"}} onClick={()=>mapClick(n)}><span>{n.id===location.id?"★":mapIcon(n)}</span><b>{n.name}</b><small>Lv {n.level} · {n.region}</small></button>)}</div><div className="map-legend"><span>◆ Discovered</span><span>★ Current</span><span>? Undiscovered</span></div></div></div>}
    <div className="ambient-pill"><span>{["DAWN","DAY","DUSK","NIGHT"][timeOfDay]}</span><span>{weather.toUpperCase()}</span></div>
    <div className="notice">{notice}</div>
    {paused&&<div className="pause-screen"><h1>PAUSED</h1><button className="primary" onClick={()=>setPaused(false)}>CONTINUE</button></div>}
  </div>
}
function App(){
  const [auth,setAuth]=useState(!!getToken()),[world,setWorld]=useState(fallbackWorld),[state,setState]=useState(null),[loading,setLoading]=useState(true);
  const load=async()=>{try{const w=await api("/world");setWorld(w);try{const s=await api("/state");setState(s);setAuth(true)}catch{localStorage.removeItem(tokenKey);setAuth(false);setState(null)}}catch(e){setLoading(false)}finally{setLoading(false)}};
  useEffect(()=>{load()},[auth]);
  if(loading)return <div className="loading"><div className="logo">HORIZON <span>FRONTIER</span></div><p>Loading the frontier…</p></div>;
  if(!auth)return <Auth onLogin={()=>setAuth(true)}/>;
  if(!state?.character)return <CharacterCreate world={world} onDone={async()=>setState(await api("/state"))}/>;
  return <Game world={world} initial={state} onLogout={async()=>{await api("/auth/logout",{method:"POST"});localStorage.removeItem(tokenKey);setAuth(false);setState(null)}}/>;
}
createRoot(document.getElementById("root")).render(<App/>);
