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
  const [state,setState]=useState(initial),[tab,setTab]=useState("world"),[notice,setNotice]=useState("Walk the frontier. Every road can lead somewhere."),[npc,setNpc]=useState(null),[shop,setShop]=useState(null),[dungeon,setDungeon]=useState(null),[adventure,setAdventure]=useState(null),[paused,setPaused]=useState(false),[mobileMenu,setMobileMenu]=useState(false),[worldMap,setWorldMap]=useState(false),[keys,setKeys]=useState({});
  const canvas=useRef(null),joyRef=useRef(null),touch=useRef({x:0,y:0,id:null}),pos=useRef({x:0,y:0}),transition=useRef(false),facing=useRef("down"),lastMove=useRef(0);
  const player=state.character;
  const location=world.locations.find(x=>x.id===player?.area_key)||world.locations[0];
  const localNpcs=world.npcs.filter(x=>x.location===player?.area_key);
  const nearbyDungeons=world.dungeons.filter(x=>x.location===player?.area_key);
  const discovered=new Set(state.discovered_areas||[location?.id]);
  const canFight=!location||Number(player.level)>=Number(location.level||1);
  const clean=value=>cleanText(value);

  const refresh=async()=>setState(await api("/state"));
  const action=async(fn,success)=>{try{const r=await fn();const message=r.message||r.result?.message||r.result?.error;if(message)setNotice(clean(message));if(r.state)setState(r.state);else await refresh();if(success)success(r)}catch(e){setNotice(e.message||"The frontier could not complete that action.")}};
  useEffect(()=>{if(!notice)return;const id=setTimeout(()=>setNotice(""),3600);return()=>clearTimeout(id)},[notice]);
  useEffect(()=>{const down=e=>{if(["INPUT","TEXTAREA"].includes(e.target.tagName))return;const k=e.key.toLowerCase();setKeys(v=>({...v,[k]:true}));if(["w","a","s","d","arrowup","arrowdown","arrowleft","arrowright"].includes(k)){e.preventDefault()}};const up=e=>setKeys(v=>({...v,[e.key.toLowerCase()]:false}));addEventListener("keydown",down);addEventListener("keyup",up);return()=>{removeEventListener("keydown",down);removeEventListener("keyup",up)}},[]);

  const exitDirections=loc=>{
    const dirs=["north","east","south","west"];
    return (loc?.connections||[]).map((id,i)=>({id,dir:dirs[i%dirs.length]}));
  };
  const directionVector=dir=>({north:[0,-1],east:[1,0],south:[0,1],west:[-1,0]}[dir]||[0,1]);
  const arrive=async(id)=>{
    if(transition.current)return;
    transition.current=true;
    try{
      const r=await api("/explore/arrive",{method:"POST",body:JSON.stringify({location:id})});
      setState(r.state||await api("/state"));
      pos.current={x:0,y:0};
      setNotice("Arrived at "+(r.area?.name||"a new area")+" — teleport unlocked.");
      setTab("world");
    }catch(e){setNotice(e.message||"The road ends here.")}finally{transition.current=false}
  };

  const updateWorld=(dt)=>{
    if(paused||transition.current)return;
    let x=(keys.d||keys.arrowright?1:0)-(keys.a||keys.arrowleft?1:0)+touch.current.x;
    let y=(keys.s||keys.arrowdown?1:0)-(keys.w||keys.arrowup?1:0)+touch.current.y;
    const m=Math.hypot(x,y);
    if(!m){lastMove.current=0;return}
    x/=m;y/=m;
    if(Math.abs(x)>Math.abs(y))facing.current=x>0?"right":"left";else facing.current=y>0?"down":"up";
    lastMove.current=performance.now();
    // Roads are short enough to feel like actual traversal, not a loading screen.
    // A full straight run takes roughly 50–60 seconds at normal speed.
    const speed=165;
    const worldLimit=9000;
    const exitTrigger=8400;
    pos.current.x=Math.max(-worldLimit,Math.min(worldLimit,pos.current.x+x*speed*dt));
    pos.current.y=Math.max(-worldLimit,Math.min(worldLimit,pos.current.y+y*speed*dt));
    const exits=exitDirections(location);
    const hit=exits.find(e=>{
      const [dx,dy]=directionVector(e.dir);
      return (dx>0&&pos.current.x>=exitTrigger)||(dx<0&&pos.current.x<=-exitTrigger)||(dy>0&&pos.current.y>=exitTrigger)||(dy<0&&pos.current.y<=-exitTrigger);
    });
    if(hit)arrive(hit.id);
  };

  const hash=(x,y)=>{let n=Math.sin(x*12.9898+y*78.233+(location?.id||"").length*31.7)*43758.5453;return n-Math.floor(n)};
  const drawTree=(ctx,x,y,s=1)=>{
    ctx.fillStyle="#6f472e";ctx.fillRect(x-3*s,y+8*s,6*s,14*s);
    ctx.fillStyle="#183f32";ctx.fillRect(x-13*s,y-5*s,26*s,17*s);ctx.fillRect(x-8*s,y-15*s,16*s,12*s);
    ctx.fillStyle="#286247";ctx.fillRect(x-10*s,y-7*s,20*s,9*s);ctx.fillStyle="#3c8053";ctx.fillRect(x-4*s,y-13*s,9*s,7*s);
  };
  const drawRock=(ctx,x,y,s=1)=>{ctx.fillStyle="#53666a";ctx.fillRect(x-8*s,y-4*s,16*s,9*s);ctx.fillStyle="#7c9090";ctx.fillRect(x-4*s,y-7*s,8*s,4*s)};
  const drawWater=(ctx,x,y,w,h)=>{
    ctx.fillStyle="#24677a";ctx.fillRect(x,y,w,h);
    ctx.fillStyle="#4a9db0";for(let yy=y+10;yy<y+h;yy+=18){for(let xx=x+8;xx<x+w;xx+=38)ctx.fillRect(xx,yy,18,2)}
  };
  const drawBuilding=(ctx,x,y,s=1,roof="#8b4b3c")=>{
    ctx.fillStyle="#d0ad78";ctx.fillRect(x-25*s,y-2*s,50*s,32*s);ctx.fillStyle=roof;ctx.fillRect(x-30*s,y-18*s,60*s,18*s);ctx.fillStyle="#4d3028";ctx.fillRect(x-7*s,y+10*s,14*s,20*s);ctx.fillStyle="#a9d7d1";ctx.fillRect(x-18*s,y+6*s,9*s,8*s);ctx.fillRect(x+9*s,y+6*s,9*s,8*s);
  };
  const drawCanvas=()=>{
    const c=canvas.current;if(!c)return;
    const dpr=Math.min(2,devicePixelRatio||1),w=c.clientWidth,h=c.clientHeight;
    if(c.width!==w*dpr||c.height!==h*dpr){c.width=w*dpr;c.height=h*dpr}
    const ctx=c.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.imageSmoothingEnabled=false;
    const terrain=location?.terrain||location?.type||"wild";
    const base={village:"#5f9658",forest:"#356b48",meadow:"#7ca85c",mountain:"#65736c",ruins:"#6c7565",cave:"#4d5a52",coast:"#4f8f91",lake:"#2e7184",volcano:"#74483b",city:"#71856f",sky:"#6b86a0",void:"#392f54",worldroot:"#496044",bones:"#766b5f",eclipse:"#4b4052"}[terrain]||"#5f8f55";
    ctx.fillStyle=base;ctx.fillRect(0,0,w,h);
    const camX=pos.current.x,camY=pos.current.y;
    const tile=48;
    for(let sy=-tile;sy<h+tile;sy+=tile)for(let sx=-tile;sx<w+tile;sx+=tile){
      const wx=Math.floor((sx-w/2+camX)/tile),wy=Math.floor((sy-h/2+camY)/tile),n=hash(wx,wy);
      ctx.fillStyle=n>.72?"rgba(255,255,255,.025)":n<.12?"rgba(0,0,0,.045)":"rgba(0,0,0,0)";
      ctx.fillRect(sx,sy,tile,tile);
      if(n>.91&&["forest","village","meadow","wild"].includes(terrain))drawTree(ctx,sx+20,sy+18,.55);
      else if(n<.055&&["mountain","ruins","cave","volcano"].includes(terrain))drawRock(ctx,sx+22,sy+25,.75);
    }
    // Long roads radiate from the current zone's central settlement toward each exit.
    const exits=exitDirections(location);
    exits.forEach((e,i)=>{
      const [dx,dy]=directionVector(e.dir);
      const roadLength=10000;
      ctx.strokeStyle="#b99b68";ctx.lineWidth=22;ctx.beginPath();ctx.moveTo(w/2-dx*roadLength-camX,h/2-dy*roadLength-camY);ctx.lineTo(w/2+dx*roadLength-camX,h/2+dy*roadLength-camY);ctx.stroke();
      ctx.strokeStyle="#d9c38d";ctx.lineWidth=10;ctx.beginPath();ctx.moveTo(w/2-dx*roadLength-camX,h/2-dy*roadLength-camY);ctx.lineTo(w/2+dx*roadLength-camX,h/2+dy*roadLength-camY);ctx.stroke();
      const gx=w/2+dx*8000-camX,gy=h/2+dy*8000-camY;
      ctx.fillStyle="#2b4439";ctx.fillRect(gx-18,gy-18,36,36);ctx.fillStyle="#e2cf91";ctx.fillRect(gx-7,gy-7,14,14);
      ctx.fillStyle="#f0ead0";ctx.font="bold 10px monospace";ctx.textAlign="center";ctx.fillText((world.locations.find(z=>z.id===e.id)||{}).name||"Road",gx,gy-27);
    });

    // Local scenery uses fixed WORLD coordinates so buildings and NPCs do not
    // follow the camera when the player walks away.
    const worldToScreen=(wx,wy)=>[w/2+wx-camX,h/2+wy-camY];
    const drawBuildingAt=(wx,wy,s,roof)=>{const [x,y]=worldToScreen(wx,wy);drawBuilding(ctx,x,y,s,roof)};
    const drawRockAt=(wx,wy,s=1)=>{const [x,y]=worldToScreen(wx,wy);drawRock(ctx,x,y,s)};

    if(terrain==="lake"||terrain==="coast"){
      const [x,y]=worldToScreen(2100,-1800);drawWater(ctx,x,y,2600,1900);
    }
    if(terrain==="village"||terrain==="city"){
      drawBuildingAt(-2200,-1100,1);
      drawBuildingAt(1700,-1450,.85,"#596c84");
      drawBuildingAt(350,2100,.7,"#80613d");
      drawBuildingAt(-1300,1700,.75,"#745342");
    }
    if(terrain==="ruins"){for(let i=0;i<7;i++)drawRockAt(-2600+i*900,-900+(i%2)*800,1.2)}
    if(terrain==="mountain"){
      for(let i=0;i<6;i++){
        const [x,y]=worldToScreen(-3000+i*1200,-1700+(i%3)*700);
        ctx.fillStyle="#75817b";ctx.fillRect(x,y,70,55);ctx.fillStyle="#aab3a9";ctx.fillRect(x+15,y,40,10);
      }
    }
    for(let i=0;i<localNpcs.length;i++){
      const n=localNpcs[i],wx=-1900+(i%3)*1500,wy=-650+Math.floor(i/3)*1250,[x,y]=worldToScreen(wx,wy);
      if(x<-120||x>w+120||y<-120||y>h+120)continue;
      ctx.fillStyle="#efb47f";ctx.fillRect(x-7,y-25,14,14);ctx.fillStyle="#3e5368";ctx.fillRect(x-10,y-10,20,25);
      ctx.fillStyle="#eaf5ef";ctx.font="10px monospace";ctx.textAlign="center";ctx.fillText(n.name,x,y-32);
    }
    // Player sprite with a tiny walking animation.
    const bob=lastMove.current&&performance.now()-lastMove.current<220?Math.sin(performance.now()/55)*2:0,px=w/2,py=h/2+bob;
    ctx.fillStyle="rgba(0,0,0,.28)";ctx.fillRect(px-14,py+27,28,5);
    ctx.fillStyle="#17243b";ctx.fillRect(px-10,py+6,20,20);ctx.fillStyle="#3b9ac2";ctx.fillRect(px-12,py-10,24,18);ctx.fillStyle="#f0b583";ctx.fillRect(px-9,py-27,18,17);ctx.fillStyle="#252b3b";ctx.fillRect(px-10,py-30,20,7);ctx.fillStyle="#8be5ef";ctx.fillRect(px-14,py+27,28,3);
    ctx.fillStyle="rgba(0,0,0,.45)";ctx.font="bold 11px monospace";ctx.textAlign="center";ctx.fillText(player.name,px,py+43);
  };
  useEffect(()=>{let id,last=performance.now();const loop=t=>{const dt=Math.min(.05,(t-last)/1000);last=t;updateWorld(dt);drawCanvas();id=requestAnimationFrame(loop)};id=requestAnimationFrame(loop);return()=>cancelAnimationFrame(id)},[keys,paused,location?.id,player.name]);
  const travel=async id=>action(()=>api("/travel",{method:"POST",body:JSON.stringify({location:id})}),()=>{pos.current={x:0,y:0};setTab("world");setWorldMap(false);setMobileMenu(false)});
  const talk=(n,dialogue=0)=>action(()=>api("/npc/talk",{method:"POST",body:JSON.stringify({npc:n.id,dialogue})}),r=>setNpc(r));
  const buy=item=>action(()=>api("/shop/buy",{method:"POST",body:JSON.stringify({item,quantity:1})}),()=>setShop(null));
  const hatch=egg=>action(()=>api("/pet/hatch",{method:"POST",body:JSON.stringify({egg})}));
  const doAdventure=()=>{if(!canFight){setNotice("You can explore "+location.name+" freely, but battles unlock at level "+location.level+".");return}action(()=>api("/adventure",{method:"POST"}),r=>{if(r.result&&!r.result.error)setAdventure(r.result)})};
  const doDungeon=d=>{if(player.level<d.level){setNotice("Reach level "+d.level+" to enter this dungeon.");return}if(d.location!==location.id){setNotice("Walk to "+(world.locations.find(x=>x.id===d.location)?.name||"its entrance")+" first.");return}action(()=>api("/dungeon",{method:"POST",body:JSON.stringify({dungeon:d.id})}),r=>setDungeon(r))};
  const useItem=i=>action(()=>api("/item/use",{method:"POST",body:JSON.stringify({item:i.item_key,quantity:1})}));
  const equipItem=i=>action(()=>api("/item/equip",{method:"POST",body:JSON.stringify({item:i.item_key})}));
  const updateStick=(root,e)=>{if(!root||!e)return;const r=root.getBoundingClientRect(),dx=e.clientX-(r.left+r.width/2),dy=e.clientY-(r.top+r.height/2),limit=Math.max(1,(Math.min(r.width,r.height)/2)-24),m=Math.hypot(dx,dy)||1,s=Math.min(1,limit/m),nx=dx*s,ny=dy*s;touch.current.x=nx/limit;touch.current.y=ny/limit;const k=root.querySelector("span");if(k)k.style.transform="translate(calc(-50% + "+nx+"px),calc(-50% + "+ny+"px))"};
  const joystickStart=e=>{if(e.pointerType==="mouse"&&e.button!==0)return;e.preventDefault();e.stopPropagation();touch.current.id=e.pointerId;joyRef.current=e.currentTarget;try{e.currentTarget.setPointerCapture(e.pointerId)}catch{}updateStick(e.currentTarget,e)};
  const joystickMove=e=>{if(touch.current.id!==e.pointerId)return;e.preventDefault();updateStick(joyRef.current,e)};
  const stopTouch=e=>{if(touch.current.id!==null&&e.pointerId!==touch.current.id)return;e.preventDefault();touch.current.id=null;touch.current.x=0;touch.current.y=0;const k=joyRef.current?.querySelector("span");if(k)k.style.transform="translate(-50%,-50%)";joyRef.current=null};

  const mapNodes=world.locations.map((l,i)=>({...l,mx:70+(i%6)*17,my:16+Math.floor(i/6)*20}));
  if(!player)return null;
  return <div className="game">
    <canvas ref={canvas}/>
    <header className="gamebar"><div className="logo mini">HORIZON <span>FRONTIER</span></div><div className="location-name">{location?.name} · {location?.region}</div><div className="bar-actions"><button onClick={()=>setWorldMap(true)}>MAP</button><button onClick={()=>setPaused(!paused)}>{paused?"RESUME":"PAUSE"}</button><button onClick={onLogout}>LOG OUT</button></div></header>
    <aside className="hero-card"><div className="avatar">{player.name.slice(0,1).toUpperCase()}</div><div><b>{player.name}</b><small>{player.title||"Adventurer"} · Lv {player.level}</small></div><Bar label="HP" value={player.hp} max={player.max_hp}/><Bar label="MP" value={player.mp} max={player.max_mp} type="mana"/><div className="stats"><span>ATK <b>{player.atk}</b></span><span>SPD <b>{player.speed}</b></span><span>GOLD <b>{player.gold}</b></span></div></aside>
    <div className="area-banner"><b>{location?.name}</b><span>Lv {location?.level} zone · {canFight?"Combat available":"Exploration only — combat locked"}</span></div>
    <nav className="tabs">{[["world","WORLD"],["quests","QUESTS"],["inventory","INVENTORY"],["pets","PETS"],["titles","TITLES"],["dungeons","DUNGEONS"]].map(([k,v])=><button className={tab===k?"active":""} onClick={()=>setTab(k)} key={k}>{v}</button>)}</nav>
    <section className={"panel "+(mobileMenu?"mobile-open":"")}><div className="panel-head"><h2>{tab==="world"?location?.name:tab.toUpperCase()}</h2><button className="panel-close" onClick={()=>setMobileMenu(false)} aria-label="Close menu">×</button></div><div className="mobile-menu-nav">{[["world","WORLD"],["quests","QUESTS"],["inventory","INVENTORY"],["pets","PETS"],["titles","TITLES"],["dungeons","DUNGEONS"]].map(([k,v])=><button className={tab===k?"active":""} onClick={()=>setTab(k)} key={k}>{v}</button>)}</div>
      {tab==="world"&&<><p>{location?.description}</p><div className="world-status"><b>{canFight?"FULL ACCESS":"EXPLORATION MODE"}</b><span>Follow a road for about 1 minute to reach the next area. Reach it once to unlock teleport.</span></div><div className="npc-list"><h3>People here</h3>{localNpcs.map(n=><button disabled={!canFight} onClick={()=>talk(n)} className="list-card" key={n.id}><span className="npc-icon">{n.name[0]}</span><span><b>{n.name}</b><small>{n.role}</small></span><em>{canFight?"TALK":"LOCKED"}</em></button>)}</div><h3>Roads</h3><div className="location-grid">{exitDirections(location).map(e=>{const x=world.locations.find(z=>z.id===e.id);return x?<button className="location-card road-card" onClick={()=>setNotice("Follow the "+e.dir+" road — do not teleport yet. Walk there to unlock it.")} key={x.id}><b>{x.name}</b><small>{e.dir.toUpperCase()} · Lv {x.level} · ~1 min walk</small><em>{discovered.has(x.id)?"TELEPORT UNLOCKED":"WALK TO DISCOVER"}</em></button>:null})}</div><button className="map-open" onClick={()=>setWorldMap(true)}>OPEN WORLD MAP</button></>}
      {tab==="inventory"&&<><h2>Inventory</h2><div className="item-grid">{state.inventory?.map(i=>{const x=(world.items?.[i.item_key]||world.items?.find?.(z=>z.id===i.item_key))||{id:i.item_key,name:i.item_key,rarity:"Common",slot:"material"};const slot=x.slot||x.category;const consumable=slot==="consumable"||slot==="food";const equippable=["weapon","armor","offhand","accessory","ring","amulet","relic"].includes(slot);return <button className="item" onClick={()=>consumable?useItem(i):equippable?equipItem(i):setNotice("That item is a material and cannot be used directly.")} key={i.item_key}><b>{x.name}</b><small>{x.rarity} · ×{i.quantity}</small><em>{consumable?"USE":equippable?"EQUIP":"MATERIAL"}</em></button>})}</div><h3>Equipment</h3><p className="muted">Gear, upgrades and intrinsic properties persist with your hero.</p></>}
      {tab==="pets"&&<><h2>Pets & Eggs</h2><div className="pet-list">{state.pets?.map(p=><div className="pet item" key={p.pet_id}><b>{p.name}</b><small>{p.species} · Lv {p.level}{p.equipped?" · EQUIPPED":""}</small></div>)}</div><h3>Eggs</h3><div className="item-grid">{world.eggs.map(e=>state.inventory?.find(i=>i.item_key===e.id)?.quantity?<button className="item" onClick={()=>hatch(e.id)} key={e.id}><b>{e.name}</b><small>{e.rarity} · HATCH</small></button>:null)}</div></>}
      {tab==="titles"&&<><h2>Titles & Achievements</h2><div className="title-grid">{world.titles.map(t=><div className="title-card" key={t.id}><b>{t.name}</b><small>{t.condition}</small></div>)}</div></>}
      {tab==="dungeons"&&<><h2>Dungeons</h2><p className="muted">Dungeons are physical places in the world. You must reach their entrance before you can enter.</p>{world.dungeons.map(d=>{const atEntrance=d.location===location.id,levelOk=player.level>=d.level;return <button className="dungeon-card" disabled={!atEntrance||!levelOk} onClick={()=>doDungeon(d)} key={d.id}><span><b>{d.name}</b><small>Lv {d.level} · {d.floors} floors · Boss: {d.boss}</small></span><em>{!atEntrance?"TRAVEL TO ENTRANCE":!levelOk?"LOCKED":"ENTER"}</em></button>})}</>}
      {tab==="quests"&&<><h2>Adventure Board</h2><div className="quest-hero"><b>{canFight?"The wilds are calling.":"You are exploring beyond your level."}</b><p>{canFight?"Fight regional enemies, collect loot and push toward the next zone.":"You can walk, discover locations and unlock fast travel. Combat, NPCs and dungeons unlock when your level catches up."}</p><button className="primary" onClick={doAdventure}>{canFight?"START AN ADVENTURE":"EXPLORE THE AREA"}</button></div><h3>Frontier progression</h3><p className="muted">Discover new regions, unlock teleport points, collect gear, hatch pets, master skills and return to dangerous zones when you're ready.</p></>}
    </section>
    <div className="touch-zone" ref={joyRef} onPointerDown={joystickStart} onPointerMove={joystickMove} onPointerUp={stopTouch} onPointerCancel={stopTouch} onPointerLeave={joystickMove} onContextMenu={e=>e.preventDefault()}><span/></div>
    <div className="touch-actions"><button onClick={doAdventure} aria-label="Adventure">⚔</button><button onClick={()=>setWorldMap(true)} aria-label="Map">⌖</button><button onClick={()=>{setTab("inventory");setMobileMenu(true)}} aria-label="Inventory">▣</button><button onClick={()=>{setTab("world");setMobileMenu(v=>!v)}} aria-label="Menu">{mobileMenu?"×":"☰"}</button></div>
    {npc&&<div className="modal"><div className="dialog"><button className="close" onClick={()=>setNpc(null)}>×</button><div className="npc-big">{npc.npc.name[0]}</div><h2>{npc.npc.name}</h2><small>{npc.npc.role}</small><p className="dialogue">“{clean(npc.dialogue?.text||"The NPC looks at you, waiting for a moment before speaking.")}”</p><div className="dialogue-choices">{(npc.dialogue?.choices||["Goodbye."]).map((x,i)=><button onClick={()=>{const next=npc.dialogue?.next?.[i];if(next===-1||/goodbye|leave|bye/i.test(x)){setNpc(null);return}if(Number.isInteger(next)){talk(npc.npc,next);return}setNotice("The conversation pauses for now.")}} key={i}>{x}</button>)}</div></div></div>}
    {adventure&&<div className="modal"><div className="dialog"><button className="close" onClick={()=>setAdventure(null)}>×</button><h2>{adventure.win?"Adventure Complete":"Adventure Failed"}</h2><p className="muted">{adventure.enemy?.name||"Encounter"}</p><div className="run-log">{(adventure.log||[]).map((x,i)=><p key={i}>{clean(x)}</p>)}</div>{adventure.win?<div className="reward">Victory · +{adventure.xp||0} XP · +{adventure.gold||0} G · {adventure.drop||"loot"}</div>:<div className="reward">You survived and recovered. A Life Potion was added.</div>}</div></div>}
    {shop&&<div className="modal"><div className="dialog"><button className="close" onClick={()=>setShop(null)}>×</button><h2>{shop.name}</h2>{shop.products.map(i=><button className="shop-row" onClick={()=>buy(i.id)} key={i.id}><span><b>{i.name}</b><small>{i.rarity}</small></span><em>{i.price} G</em></button>)}</div></div>}
    {dungeon&&<div className="modal"><div className="dialog"><button className="close" onClick={()=>setDungeon(null)}>×</button><h2>{dungeon.result?.name||"Dungeon Run"}</h2><div className="run-log">{(dungeon.result?.log||[]).map((x,i)=><p key={i}>{clean(x)}</p>)}</div>{dungeon.result?.win&&<div className="reward">Victory · +{dungeon.result.xp} XP · +{dungeon.result.gold} G</div>}</div></div>}
    {worldMap&&<div className="modal world-map-modal"><div className="world-map-dialog"><button className="close" onClick={()=>setWorldMap(false)}>×</button><div className="map-title"><div><p className="eyebrow">THE FRONTIER</p><h2>World Map</h2><small>{discovered.size}/{world.locations.length} areas discovered · discovered areas are teleportable</small></div></div><div className="map-canvas">{mapNodes.map((n,i)=>{const isDiscovered=discovered.has(n.id),isCurrent=n.id===location.id;return <React.Fragment key={n.id}><div className={"map-node "+(isDiscovered?"discovered ":"")+" "+(isCurrent?"current":"")} style={{left:n.mx+"%",top:n.my+"%"}} onClick={()=>isDiscovered?travel(n.id):setNotice("Undiscovered. Walk there first.")}><span>{isCurrent?"★":isDiscovered?"◆":"?"}</span><b>{n.name}</b><small>Lv {n.level}</small></div></React.Fragment>})}</div><div className="map-legend"><span>◆ Discovered / teleportable</span><span>★ Current area</span><span>? Unknown — walk there</span></div></div></div>}
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
