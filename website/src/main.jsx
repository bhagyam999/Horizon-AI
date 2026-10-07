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
  const canvas=useRef(null),joyRef=useRef(null),touch=useRef({x:0,y:0,id:null}),pos=useRef({x:0,y:0}),transition=useRef(false),facing=useRef("down"),lastMove=useRef(0),objectsRef=useRef([]),mapDrag=useRef({active:false,id:null,x:0,y:0,ox:0,oy:0});
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
    const c=canvas.current;if(!c)return;
    const dpr=Math.min(2,devicePixelRatio||1),w=c.clientWidth,h=c.clientHeight;
    if(c.width!==w*dpr||c.height!==h*dpr){c.width=w*dpr;c.height=h*dpr}
    const ctx=c.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.imageSmoothingEnabled=true;
    const terrain=scene.biome||location?.terrain||location?.type||"wild";
    const palettes={
      village:["#7d9f68","#b9a56c","#47664a"],forest:["#315d43","#234b38","#132f27"],enchanted_forest:["#284f49","#315e4e","#182f30"],thorn_forest:["#394a38","#26382f","#171f1c"],
      farmland:["#a8a15d","#c5b46a","#667347"],watchtower:["#6f7770","#59635f","#39443f"],mountain:["#6f7777","#53605f","#374140"],ruins:["#777064","#625d56","#3e403d"],
      underwater_ruins:["#3f7378","#2d5d65","#183b48"],cavern:["#4e5752","#3a4543","#202b2d"],crystal_cave:["#41566c","#31445a","#202c40"],coast:["#6f9d91","#477e7b","#245967"],
      lake:["#438291","#2e6878","#194b60"],volcano:["#784a3e","#5c3835","#321f24"],volcanic_town:["#765041","#563a35","#30262a"],kingdom:["#788d73","#596f5e","#35483e"],
      city:["#778c7b","#5d7265","#3b4b44"],cliff_city:["#617e8b","#4d6977","#314957"],sky:["#6e91a8","#567a94","#38536d"],snow_outpost:["#9aa9ac","#748a92","#4d6069"],
      frost_mountains:["#778a92","#5e727d","#3e515c"],mist_forest:["#466451","#304b40","#1e342f"],verdant:["#65965f","#4f814f","#315b3e"],mine:["#555b59","#414947","#292f31"],
      steppe:["#b0a05c","#92894e","#5d643b"],crossroads:["#9b8963","#7d704f","#514b39"],desert:["#c2a05a","#a47e45","#624d36"],fae:["#657b91","#4c6578","#293d4d"],
      aether:["#7898a6","#5e8191","#3c5e72"],highlands:["#727b76","#5d6964","#414d49"],celestial:["#737b99","#586481","#37415c"],dragon_graveyard:["#756b5c","#5d554c","#3b3735"],
      eclipse:["#5d4b58","#463c4d","#292934"],void_marsh:["#474959","#373b4c","#242a38"],astral:["#5e7da1","#4c6689","#303e61"],worldroot:["#52734e","#3e5d42","#273b30"],
      endgame:["#514c5c","#3e3c4c","#292936"],reality_edge:["#353847","#292b39","#1c1e2b"]
    };
    const [ground,dark,deep]=palettes[terrain]||["#5f8f55","#476a48","#2e4935"];
    ctx.fillStyle=ground;ctx.fillRect(0,0,w,h);
    const camX=pos.current.x,camY=pos.current.y;
    const worldToScreen=(wx,wy)=>[w/2+wx-camX,h/2+wy-camY];
    const seeded=(x,y,k=0)=>{const n=Math.sin(x*127.1+y*311.7+k*74.3+(location?.id||"").length*17.3)*43758.5453;return n-Math.floor(n)};
    const circle=(x,y,r,fill)=>{ctx.fillStyle=fill;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill()};
    const poly=(pts,fill)=>{ctx.fillStyle=fill;ctx.beginPath();pts.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.fill()};
    const drawTree=(x,y,s=1,kind="tree")=>{
      ctx.fillStyle="rgba(0,0,0,.22)";ctx.beginPath();ctx.ellipse(x,y+19*s,17*s,6*s,0,0,Math.PI*2);ctx.fill();
      ctx.fillStyle=kind==="pine"?"#4d3a2d":"#63442e";ctx.fillRect(x-3*s,y-1*s,6*s,23*s);
      if(kind==="pine"){poly([[x,y-38*s],[x-20*s,y+2*s],[x-10*s,y+1*s],[x-27*s,y+19*s],[x+27*s,y+19*s],[x+10*s,y+1*s],[x+20*s,y+2*s]],dark)}
      else {circle(x-10*s,y-6*s,13*s,deep);circle(x+9*s,y-8*s,16*s,dark);circle(x,y-19*s,14*s,ground);circle(x-3*s,y-25*s,8*s,"rgba(255,255,255,.09)")}
    };
    const drawRock=(x,y,s=1)=>{
      ctx.fillStyle="rgba(0,0,0,.2)";ctx.beginPath();ctx.ellipse(x,y+9*s,15*s,5*s,0,0,Math.PI*2);ctx.fill();
      poly([[x-15*s,y+6*s],[x-9*s,y-8*s],[x+3*s,y-14*s],[x+15*s,y-5*s],[x+12*s,y+8*s],[x-3*s,y+12*s]],"#596566");
      poly([[x-9*s,y-8*s],[x+3*s,y-14*s],[x+1*s,y-2*s],[x-5*s,y+1*s]],"#8b9790");
    };
    const drawMountain=(x,y,s=1)=>{
      poly([[x-180*s,y+90*s],[x-75*s,y-80*s],[x-30*s,y-20*s],[x+30*s,y-115*s],[x+105*s,y+90*s]],"#4f5e60");
      poly([[x-75*s,y-80*s],[x-52*s,y-42*s],[x-30*s,y-20*s],[x+30*s,y-115*s],[x+57*s,y-52*s],[x+30*s,y-35*s]],"#c1cbc4");
      poly([[x-180*s,y+90*s],[x-75*s,y-80*s],[x-30*s,y-20*s],[x+30*s,y-115*s],[x+105*s,y+90*s]],"rgba(20,28,29,.18)");
    };
    const drawWater=(x,y,ww,hh)=>{
      const g=ctx.createLinearGradient(x-ww/2,y-hh/2,x+ww/2,y+hh/2);g.addColorStop(0,"#5da1a0");g.addColorStop(.45,"#347b86");g.addColorStop(1,"#1d566a");ctx.fillStyle=g;ctx.fillRect(x-ww/2,y-hh/2,ww,hh);
      ctx.strokeStyle="rgba(190,235,225,.25)";ctx.lineWidth=2;
      for(let j=-hh/2+25;j<hh/2;j+=42){ctx.beginPath();for(let i=-ww/2;i<ww/2;i+=55){const yy=y+j+Math.sin(i*.035+j*.02+performance.now()*.0005)*5;i===-ww/2?ctx.moveTo(x+i,yy):ctx.lineTo(x+i,yy)}ctx.stroke()}
    };
    const drawHouse=(x,y,s=1,roof="#713f3a")=>{
      ctx.fillStyle="rgba(0,0,0,.24)";ctx.beginPath();ctx.ellipse(x,y+28*s,37*s,8*s,0,0,Math.PI*2);ctx.fill();
      ctx.fillStyle="#c5ad82";ctx.fillRect(x-28*s,y-4*s,56*s,34*s);ctx.fillStyle=roof;
      poly([[x-35*s,y-4*s],[x,y-27*s],[x+35*s,y-4*s]],roof);
      ctx.fillStyle="#49332b";ctx.fillRect(x-7*s,y+11*s,14*s,19*s);
      ctx.fillStyle="#a9d8d2";ctx.fillRect(x-21*s,y+5*s,10*s,9*s);ctx.fillRect(x+11*s,y+5*s,10*s,9*s);
    };
    const drawRoad=(x1,y1,x2,y2,width=48)=>{
      ctx.save();ctx.lineCap="round";ctx.strokeStyle="rgba(60,43,31,.48)";ctx.lineWidth=width+12;ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke();
      ctx.strokeStyle=terrain==="snow_outpost"||terrain==="frost_mountains"?"#d7d2bd":terrain==="desert"?"#d3b56c":"#9a805d";ctx.lineWidth=width;ctx.stroke();
      ctx.strokeStyle="rgba(255,238,184,.22)";ctx.lineWidth=5;ctx.setLineDash([18,26]);ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke();ctx.restore();
    };
    // Large terrain patches create the feeling of a continuous landscape instead of a flat tile.
    const patchCount=terrain.includes("forest")||terrain==="verdant"?18:10;
    for(let i=0;i<patchCount;i++){
      const wx=seeded(i,31)*9000-4500,wy=seeded(i,57)*6500-3250,[x,y]=worldToScreen(wx,wy);
      const r=260+seeded(i,91)*520;
      if(x<-r||x>w+r||y<-r||y>h+r)continue;
      ctx.globalAlpha=.10+seeded(i,13)*.08;circle(x,y,r,seeded(i,17)>.5?"#ffffff":"#101c18");ctx.globalAlpha=1;
    }
    // Terrain-specific detail density.
    const count=terrain.includes("forest")||terrain==="verdant"||terrain==="village"?44:terrain==="desert"||terrain==="steppe"?28:34;
    for(let i=0;i<count;i++){
      const wx=seeded(i,101)*15000-7500,wy=seeded(i,131)*11000-5500,[x,y]=worldToScreen(wx,wy);
      if(x<-100||x>w+100||y<-100||y>h+100)continue;
      if(terrain.includes("forest")||terrain==="verdant"||terrain==="village")drawTree(x,y,.55+seeded(i,151)*.75,terrain==="frost_mountains"?"pine":"tree");
      else if(terrain==="mountain"||terrain==="highlands"||terrain==="frost_mountains")drawRock(x,y,.55+seeded(i,161)*1.3);
      else if(terrain==="desert"||terrain==="steppe"){ctx.strokeStyle="rgba(255,232,158,.18)";ctx.lineWidth=2;ctx.beginPath();ctx.arc(x,y,25+seeded(i,171)*45,Math.PI*1.1,Math.PI*1.8);ctx.stroke()}
      else if(terrain.includes("snow")){circle(x,y,3+seeded(i,181)*6,"rgba(235,245,248,.45)")}
      else if(terrain==="dragon_graveyard"){drawRock(x,y,1);if(i%4===0)ctx.fillStyle="#b8ab91",ctx.fillRect(x-20,y-3,40,6)}
      else {drawRock(x,y,.35+seeded(i,191)*.8)}
    }
    // Major landmarks and settlement silhouettes.
    if(["coast","lake","underwater_ruins"].includes(terrain))drawWater(...worldToScreen(1100,-700),3200,1900);
    if(["mountain","frost_mountains","highlands","ashen_pass"].includes(terrain)){drawMountain(...worldToScreen(-1250,-900),1.35);drawMountain(...worldToScreen(1250,-1150),1.05)}
    if(["village","kingdom","city","cliff_city","volcanic_town","snow_outpost","crossroads","fae"].includes(terrain)){
      for(let i=0;i<8;i++){const wx=-1800+(i%4)*1200,wy=-1050+Math.floor(i/4)*1650;drawHouse(...worldToScreen(wx,wy),.65+(i%3)*.13,terrain==="snow_outpost"?"#718b94":terrain==="kingdom"?"#70536a":"#7a433b")}
      for(let i=0;i<4;i++){const [x1,y1]=worldToScreen(-2200+i*1450,0),[x2,y2]=worldToScreen(2200-i*900,0);drawRoad(x1,y1,x2,y2,30)}
    }
    if(terrain==="desert"){for(let i=0;i<6;i++){const [x,y]=worldToScreen(-2200+i*850,1000+(i%2)*500);ctx.fillStyle="rgba(235,205,126,.3)";ctx.beginPath();ctx.ellipse(x,y,260,75,0,0,Math.PI*2);ctx.fill()}}
    if(terrain==="volcano"||terrain==="volcanic_town"){const [x,y]=worldToScreen(1000,-1000);ctx.fillStyle="#4c2829";ctx.beginPath();ctx.arc(x,y,330,0,Math.PI*2);ctx.fill();ctx.fillStyle="#d75f3e";ctx.beginPath();ctx.arc(x,y,115,0,Math.PI*2);ctx.fill();ctx.fillStyle="#f3a34d";ctx.beginPath();ctx.arc(x,y,55,0,Math.PI*2);ctx.fill()}
    if(terrain==="crystal_cave"){for(let i=0;i<18;i++){const [x,y]=worldToScreen(-2200+i*260,-900+(i%6)*370);poly([[x,y-35],[x-15,y+28],[x+5,y+10],[x+20,y+34],[x+16,y-22]],i%2?"#6dc8d0":"#9b8fe1")}}
    if(terrain==="dragon_graveyard"){for(let i=0;i<6;i++){const [x,y]=worldToScreen(-2100+i*800,900+(i%2)*650);ctx.strokeStyle="#c5b899";ctx.lineWidth=18;ctx.beginPath();ctx.moveTo(x-90,y+35);ctx.quadraticCurveTo(x,y-55,x+90,y+20);ctx.stroke()}}
    // Connected roads actually lead to the exits; these are the playable navigation corridors.
    exitDirections(location).forEach(e=>{
      const [dx,dy]=directionVector(e.dir);
      const [x1,y1]=worldToScreen(-2000*dx,-2000*dy),[x2,y2]=worldToScreen(9200*dx,9200*dy);
      drawRoad(x1,y1,x2,y2,terrain==="desert"?68:58);
      const [gx,gy]=worldToScreen(7100*dx,7100*dy);
      circle(gx,gy,38,"rgba(0,0,0,.28)");circle(gx,gy,28,"#d8b768");circle(gx,gy,19,"#24342d");
      ctx.fillStyle="#f4e4aa";ctx.font="700 12px monospace";ctx.textAlign="center";ctx.fillText((world.locations.find(z=>z.id===e.id)?.name||"ROAD").toUpperCase(),gx,gy-48);
    });
    // Scene landmarks from the backend are placed into the world rather than replacing it.
    landmarks.forEach(l=>{const [x,y]=worldToScreen(l.x||0,l.y||0),s=Number(l.scale||1);if(l.kind==="building")drawHouse(x,y,s);else if(l.kind==="tree")drawTree(x,y,s);else drawRock(x,y,s*1.7)});
    objectsRef.current=[];
    for(let i=0;i<7;i++){const wx=-2200+i*700,wy=900+(i%3)*700,[x,y]=worldToScreen(wx,wy);if(x>-100&&x<w+100&&y>-100&&y<h+100){drawChest(ctx,x,y,.9);objectsRef.current.push({type:"chest",x,y,label:"Hidden Chest"})}}
    for(let i=0;i<9;i++){const wx=-1900+i*480,wy=-1700+((i*311)%3300),[x,y]=worldToScreen(wx,wy);if(x>-100&&x<w+100&&y>-100&&y<h+100){circle(x,y,7,"#65a95a");circle(x+4,y-6,4,"#b7e47e");objectsRef.current.push({type:"resource",x,y,label:i%2?"Ore Vein":"Moon Herb"})}}
    const t=performance.now()/700;
    for(let i=0;i<6;i++){const wx=-2100+i*820+Math.sin(t+i)*100,wy=-1000+(i%3)*1000+Math.cos(t+i)*70,[x,y]=worldToScreen(wx,wy);if(x>-90&&x<w+90&&y>-90&&y<h+90){circle(x,y+10,15,"rgba(0,0,0,.25)");circle(x,y,12,"#9d4f55");circle(x-4,y-3,3,"#f3d681");circle(x+4,y-3,3,"#f3d681");objectsRef.current.push({type:"enemy",x,y,label:"Wild Encounter"})}}
    for(let i=0;i<localNpcs.length;i++){const n=localNpcs[i],wx=-1900+(i%3)*1500,wy=-650+Math.floor(i/3)*1250,[x,y]=worldToScreen(wx,wy);if(x>-120&&x<w+120&&y>-120&&y<h+120){circle(x,y+18,13,"rgba(0,0,0,.28)");ctx.fillStyle="#e9b27f";ctx.beginPath();ctx.arc(x,y-18,10,0,Math.PI*2);ctx.fill();ctx.fillStyle="#35516a";ctx.fillRect(x-11,y-8,22,28);ctx.fillStyle="#f1e9d5";ctx.font="700 11px monospace";ctx.textAlign="center";ctx.fillText(n.name,x,y-35)}}
    // Player: shaded sprite with directional facing and a soft ground shadow.
    const moving=lastMove.current&&performance.now()-lastMove.current<220,frame=moving?Math.floor(performance.now()/130)%2:0,bob=moving?Math.sin(performance.now()/65)*2:0,px=w/2,py=h/2+bob;
    ctx.fillStyle="rgba(0,0,0,.35)";ctx.beginPath();ctx.ellipse(px,py+28,21,7,0,0,Math.PI*2);ctx.fill();
    ctx.fillStyle="#182638";ctx.fillRect(px-13,py+5,26,25);ctx.fillStyle="#345274";ctx.fillRect(px-17,py+7+(frame?2:0),8,20);ctx.fillRect(px+9,py+7+(frame?0:2),8,20);
    ctx.fillStyle="#4b9fc1";ctx.fillRect(px-15,py-11,30,20);ctx.fillStyle="#f0b98c";ctx.beginPath();ctx.arc(px,py-19,12,0,Math.PI*2);ctx.fill();ctx.fillStyle="#202837";ctx.fillRect(px-14,py-31,28,8);
    ctx.fillStyle="#8be5ef";ctx.fillRect(px-15,py+30,30,3);ctx.fillStyle="#1d2530";
    if(facing.current==="left")ctx.fillRect(px-9,py-22,4,3);else if(facing.current==="right")ctx.fillRect(px+5,py-22,4,3);else ctx.fillRect(px-6,py-22,3,3);
    ctx.fillStyle="rgba(0,0,0,.65)";ctx.font="700 11px monospace";ctx.textAlign="center";ctx.fillText(player.name,px,py+47);
    // Atmosphere: sky tint, depth haze, rain/snow and vignette.
    const phase=["rgba(255,238,190,.08)","rgba(255,255,255,0)","rgba(255,150,100,.10)","rgba(8,12,24,.32)"][timeOfDay];ctx.fillStyle=phase;ctx.fillRect(0,0,w,h);
    const horizon=ctx.createLinearGradient(0,0,0,h);horizon.addColorStop(0,"rgba(255,255,255,.04)");horizon.addColorStop(.55,"rgba(0,0,0,0)");horizon.addColorStop(1,"rgba(0,0,0,.16)");ctx.fillStyle=horizon;ctx.fillRect(0,0,w,h);
    if(weather==="fog"){ctx.fillStyle="rgba(225,235,230,.16)";ctx.fillRect(0,0,w,h)}
    if(weather==="rain"){ctx.strokeStyle="rgba(130,190,220,.28)";for(let i=0;i<65;i++){const x=(i*73+t*150)%w,y=(i*41+t*190)%h;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x-5,y+15);ctx.stroke()}}
    if(weather==="snow"){ctx.fillStyle="rgba(245,250,255,.86)";for(let i=0;i<55;i++){const x=(i*91+t*18)%w,y=(i*47+t*38)%h;circle(x,y,1.5+seeded(i,221)*2,"rgba(245,250,255,.8)")}}
    const vg=ctx.createRadialGradient(w/2,h/2,Math.min(w,h)*.22,w/2,h/2,Math.max(w,h)*.78);vg.addColorStop(0,"rgba(0,0,0,0)");vg.addColorStop(1,"rgba(0,0,0,.30)");ctx.fillStyle=vg;ctx.fillRect(0,0,w,h);
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
  const mapNodes=mapOrder.map(id=>world.locations.find(x=>x.id===id)).filter(Boolean).map(l=>({...l,mx:900+Number(l.map_x||0)*105,my:450+Number(l.map_y||0)*105}));
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
    {worldMap&&<div className="modal world-map-modal"><div className="world-map-dialog"><button className="close" onClick={()=>setWorldMap(false)}>×</button><div className="map-title"><div><p className="eyebrow">THE FRONTIER</p><h2>World Map</h2><small>{discovered.size}/{world.locations.length} discovered · roads connect the frontier</small></div><div className="map-controls"><button onClick={()=>zoomMap(.2)}>+</button><button onClick={()=>zoomMap(-.2)}>−</button><button onClick={resetMap}>RESET</button></div></div><div className="map-viewport" onPointerDown={mapPointerDown} onPointerMove={mapPointerMove} onPointerUp={mapPointerUp} onPointerCancel={mapPointerUp}><div className="map-world" style={{transform:"translate("+mapPan.x+"px,"+mapPan.y+"px) scale("+mapZoom+")"}}><div className="map-region region-frontier"></div><div className="map-region region-wilds"></div><div className="map-region region-mountain"></div><div className="map-region region-desert"></div><svg className="map-links" viewBox="0 0 1800 900" preserveAspectRatio="none" aria-hidden="true">{mapNodes.map(n=>(n.connections||[]).map(id=>{const target=mapPoint(id);if(!target||n.id>id)return null;const active=route.includes(n.id)&&route.includes(id);return <line key={n.id+"-"+id} x1={n.mx} y1={n.my} x2={target.mx} y2={target.my} className={active?"route-link":discovered.has(n.id)&&discovered.has(id)?"known-link":"unknown-link"}/>;}))}</svg>{mapNodes.map(n=><button type="button" key={n.id} className={"map-node "+(discovered.has(n.id)?"discovered ":"")+(n.id===location.id?"current ":"")+(n.id===mapTarget?"selected ":"")+(discovered.has(n.id)?"":"unknown")} style={{left:n.mx,top:n.my}} onPointerDown={e=>e.stopPropagation()} onClick={e=>{e.stopPropagation();mapClick(n)}}><span>{n.id===location.id?"★":mapIcon(n)}</span><b>{n.name}</b><small>Lv {n.level}</small></button>)}<div className="player-marker" style={{left:mapPoint(location.id)?.mx||900,top:mapPoint(location.id)?.my||450}}><i></i><span>YOU</span></div></div></div><div className="map-route-info">{mapTarget&&route.length>1?<><b>ROAD TO {mapPoint(mapTarget)?.name?.toUpperCase()}</b><span>{route.length-1} road{route.length-1===1?"":"s"} · {discovered.has(mapTarget)?"Teleport available":"Follow the highlighted route on foot"}</span></>:<span>Select a location to highlight its road.</span>}</div><div className="map-legend"><span>◆ Discovered</span><span>★ You are here</span><span>▲ Terrain</span><span>━ Road</span><span>━ Route</span></div></div></div>}
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
