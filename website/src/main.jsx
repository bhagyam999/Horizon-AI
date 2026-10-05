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
  if(!r.ok){let msg="Something went wrong.";try{msg=(await r.json()).error||await r.text()||msg}catch{};throw new Error(msg)}
  return r.json();
}

const fallbackWorld={locations:[],npcs:[],dungeons:[],titles:[],eggs:[],items:[],shops:[],races:{},classes:{}};

function Auth({onLogin}){
  const [register,setRegister]=useState(false),[email,setEmail]=useState(""),[password,setPassword]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const submit=async e=>{e.preventDefault();setBusy(true);setError("");try{const r=await api(register?"/auth/register":"/auth/login",{method:"POST",body:JSON.stringify({email,password})});localStorage.setItem(tokenKey,r.token);onLogin()}catch(e){setError(e.message)}finally{setBusy(false)}};
  return <div className="auth"><div className="auth-card"><div className="logo">HORIZON <span>FRONTIER</span></div><p className="eyebrow">A persistent open-world RPG</p><h1>{register?"Create your adventurer account":"Enter the frontier"}</h1><p className="muted">Your hero, inventory, pets, titles and progress are saved to your account.</p><form onSubmit={submit}><label>Email<input type="email" value={email} onChange={e=>setEmail(e.target.value)} required placeholder="you@example.com"/></label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required minLength={8} placeholder="At least 8 characters"/></label>{error&&<div className="error">{error}</div>}<button className="primary wide" disabled={busy}>{busy?"Connecting…":register?"CREATE ACCOUNT":"LOGIN"}</button></form><button className="link" onClick={()=>{setRegister(!register);setError("")}}>{register?"Already have an account? Login":"New here? Create an account"}</button></div></div>
}

function CharacterCreate({world,onDone}){
  const [name,setName]=useState(""),[race,setRace]=useState("human"),[cls,setCls]=useState("warrior"),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  const submit=async()=>{setBusy(true);setError("");try{await api("/character",{method:"POST",body:JSON.stringify({name,race,class_name:cls})});onDone()}catch(e){setError(e.message)}finally{setBusy(false)}};
  return <div className="auth"><div className="create-card"><div className="logo">HORIZON <span>FRONTIER</span></div><p className="eyebrow">Create your hero</p><h1>Who enters the Gate?</h1><label>Hero name<input value={name} onChange={e=>setName(e.target.value)} maxLength={24} placeholder="Choose your own name"/></label><div className="choice-grid"><div><h3>Race</h3>{Object.entries(world.races||{}).map(([k,v])=><button className={race===k?"choice active":"choice"} onClick={()=>setRace(k)} key={k}><b>{k}</b><small>{v.desc}</small></button>)}</div><div><h3>Class</h3>{Object.entries(world.classes||{}).map(([k,v])=><button className={cls===k?"choice active":"choice"} onClick={()=>setCls(k)} key={k}><b>{k}</b><small>{v.desc}</small></button>)}</div></div>{error&&<div className="error">{error}</div>}<button className="primary wide" disabled={busy||name.trim().length<2} onClick={submit}>{busy?"Creating…":"ENTER HORIZON"}</button></div></div>
}

function Bar({label,value,max,type}){return <div className="bar-row"><span>{label} {value}/{max}</span><div><i className={type||""} style={{width:`${Math.max(0,Math.min(100,value/max*100))}%`}}/></div></div>}

function Game({world,initial,onLogout}){
  const [state,setState]=useState(initial),[tab,setTab]=useState("world"),[notice,setNotice]=useState("Explore the frontier."),[npc,setNpc]=useState(null),[shop,setShop]=useState(null),[dungeon,setDungeon]=useState(null),[paused,setPaused]=useState(false),[pos,setPos]=useState({x:0,y:0}),[keys,setKeys]=useState({});
  const canvas=useRef(null), touch=useRef({x:0,y:0}), player=state.character;
  const location=world.locations.find(x=>x.id===player?.area_key)||world.locations[0];
  const localNpcs=world.npcs.filter(x=>x.location===player?.area_key);
  const nearbyDungeons=world.dungeons.filter(x=>x.location===player?.area_key);
  const refresh=async()=>setState(await api("/state"));
  const action=async(fn,success)=>{try{const r=await fn();if(r.message||r.result?.message)setNotice(r.message||r.result.message);if(r.state)setState(r.state);else await refresh();if(success)success(r)}catch(e){setNotice(e.message)}};
  useEffect(()=>{const down=e=>{if(["INPUT","TEXTAREA"].includes(e.target.tagName))return;setKeys(k=>({...k,[e.key.toLowerCase()]:true}))},up=e=>setKeys(k=>({...k,[e.key.toLowerCase()]:false}));addEventListener("keydown",down);addEventListener("keyup",up);return()=>{removeEventListener("keydown",down);removeEventListener("keyup",up)}},[]);
  useEffect(()=>{let id,last=performance.now();const loop=t=>{const dt=Math.min(.04,(t-last)/1000);last=t;if(!paused){let x=(keys.d||keys.arrowright?1:0)-(keys.a||keys.arrowleft?1:0)+touch.current.x,y=(keys.s||keys.arrowdown?1:0)-(keys.w||keys.arrowup?1:0)+touch.current.y;const m=Math.hypot(x,y)||1;setPos(p=>({x:Math.max(-360,Math.min(360,p.x+x/m*145*dt)),y:Math.max(-220,Math.min(220,p.y+y/m*145*dt))}))}draw();id=requestAnimationFrame(loop)};id=requestAnimationFrame(loop);return()=>cancelAnimationFrame(id)},[keys,paused,location]);
  const draw=()=>{const c=canvas.current;if(!c)return;const dpr=Math.min(2,devicePixelRatio||1),w=c.clientWidth,h=c.clientHeight;if(c.width!==w*dpr||c.height!==h*dpr){c.width=w*dpr;c.height=h*dpr}const ctx=c.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.imageSmoothingEnabled=false;ctx.fillStyle=location?.type==="lake"||location?.type==="ruins"?"#356f7c":"#5f8f55";ctx.fillRect(0,0,w,h);const camX=pos.x,camY=pos.y;for(let y=-480;y<480;y+=32)for(let x=-640;x<640;x+=32){const px=w/2+x-camX,py=h/2+y-camY;const n=(x*13+y*7)%17;ctx.fillStyle=n<4?"#67985c":"#62925a";ctx.fillRect(px,py,32,32);if(n===3){ctx.fillStyle="#d2c07b";ctx.fillRect(px+9,py+16,11,3)}}if(location?.type!=="wilds"&&location?.type!=="forest"&&location?.type!=="mountain"){for(let x=-420;x<420;x+=140){const px=w/2+x-camX,py=h/2+100-camY;ctx.fillStyle="#c6ae78";ctx.fillRect(px,py,120,38)}}localNpcs.forEach((n,i)=>{const x=w/2+(i-1.5)*115-camX*.15,y=h/2-70+(i%2)*120-camY*.15;ctx.fillStyle="#e6b27f";ctx.fillRect(x-7,y-20,14,14);ctx.fillStyle="#334c68";ctx.fillRect(x-9,y-5,18,25);ctx.fillStyle="#fff";ctx.font="11px monospace";ctx.textAlign="center";ctx.fillText(n.name,x,y-27)});const px=w/2,py=h/2;ctx.fillStyle="#1b2942";ctx.fillRect(px-9,py+6,18,20);ctx.fillStyle="#4ea7d8";ctx.fillRect(px-10,py-10,20,17);ctx.fillStyle="#efb47f";ctx.fillRect(px-8,py-25,16,15);ctx.fillStyle="#273047";ctx.fillRect(px-9,py-28,18,6);ctx.fillStyle="#82e8ff";ctx.fillRect(px-14,py+30,28,3)};
  const travel=async id=>action(()=>api("/travel",{method:"POST",body:JSON.stringify({location:id})}),()=>{setPos({x:0,y:0});setTab("world")});
  const talk=n=>action(()=>api("/npc/talk",{method:"POST",body:JSON.stringify({npc:n.id})}),r=>setNpc(r));
  const buy=item=>action(()=>api("/shop/buy",{method:"POST",body:JSON.stringify({item,quantity:1})}),()=>setShop(null));
  const hatch=egg=>action(()=>api("/pet/hatch",{method:"POST",body:JSON.stringify({egg})}));
  const doAdventure=()=>action(()=>api("/adventure",{method:"POST"}));
  const doDungeon=d=>action(()=>api("/dungeon",{method:"POST",body:JSON.stringify({dungeon:d.id})}),r=>setDungeon(r));
  const joystick=e=>{const r=e.currentTarget.getBoundingClientRect(),dx=e.clientX-(r.left+r.width/2),dy=e.clientY-(r.top+r.height/2),m=Math.max(1,Math.hypot(dx,dy));touch.current.x=Math.max(-1,Math.min(1,dx/(r.width*.4)));touch.current.y=Math.max(-1,Math.min(1,dy/(r.height*.4)));const k=e.currentTarget.querySelector("span");if(k)k.style.transform=`translate(calc(-50% + ${touch.current.x*35}px),calc(-50% + ${touch.current.y*35}px))`};
  const stopTouch=e=>{touch.current.x=0;touch.current.y=0;const k=e.currentTarget.querySelector("span");if(k)k.style.transform="translate(-50%,-50%)"};
  if(!player)return null;
  return <div className="game"><canvas ref={canvas}/><header className="gamebar"><div className="logo mini">HORIZON <span>FRONTIER</span></div><div className="location-name">{location?.name}</div><div className="bar-actions"><button onClick={()=>setPaused(!paused)}>{paused?"RESUME":"PAUSE"}</button><button onClick={onLogout}>LOG OUT</button></div></header>
  <aside className="hero-card"><div className="avatar">{player.name.slice(0,1).toUpperCase()}</div><div><b>{player.name}</b><small>{player.title||"Adventurer"} · Lv {player.level}</small></div><Bar label="HP" value={player.hp} max={player.max_hp}/><Bar label="MP" value={player.mp} max={player.max_mp} type="mana"/><div className="stats"><span>ATK <b>{player.atk}</b></span><span>SPD <b>{player.speed}</b></span><span>GOLD <b>{player.gold}</b></span></div></aside>
  <div className="quick-actions"><button onClick={doAdventure}>ADVENTURE</button><button onClick={()=>setTab("inventory")}>BAG</button><button onClick={()=>setTab("world")}>WORLD</button></div>
  <nav className="tabs">{[["world","WORLD"],["quests","QUESTS"],["inventory","INVENTORY"],["pets","PETS"],["titles","TITLES"],["dungeons","DUNGEONS"]].map(([k,v])=><button className={tab===k?"active":""} onClick={()=>setTab(k)} key={k}>{v}</button>)}</nav>
  <section className="panel">{tab==="world"&&<><h2>{location?.name}</h2><p>{location?.description}</p><div className="npc-list"><h3>People here</h3>{localNpcs.map(n=><button onClick={()=>talk(n)} className="list-card" key={n.id}><span className="npc-icon">{n.name[0]}</span><span><b>{n.name}</b><small>{n.role}</small></span><em>TALK</em></button>)}</div><h3>Travel</h3><div className="location-grid">{(location?.connections||[]).map(id=>{const x=world.locations.find(z=>z.id===id);return x?<button className="location-card" onClick={()=>travel(x.id)} key={x.id}><b>{x.name}</b><small>Lv {x.level} · {x.region}</small></button>:null})}</div></>}
  {tab==="inventory"&&<><h2>Inventory</h2><div className="item-grid">{state.inventory?.map(i=>{const x=world.items.find(z=>z.id===i.item_key)||{name:i.item_key,rarity:"Common"};return <div className="item"><b>{x.name}</b><small>{x.rarity} · ×{i.quantity}</small></div>})}</div><h3>Equipment</h3><p className="muted">Your equipment, upgrades and loadouts persist with your hero.</p></>}
  {tab==="pets"&&<><h2>Pets & Eggs</h2><div className="pet-list">{state.pets?.map(p=><div className="pet item" key={p.pet_id}><b>{p.name}</b><small>{p.species} · Lv {p.level}{p.equipped?" · EQUIPPED":""}</small></div>)}</div><h3>Eggs</h3><div className="item-grid">{world.eggs.map(e=>state.inventory?.find(i=>i.item_key===e.id)?.quantity?<button className="item" onClick={()=>hatch(e.id)} key={e.id}><b>{e.name}</b><small>{e.rarity} · HATCH</small></button>:null)}</div></>}
  {tab==="titles"&&<><h2>Titles & Achievements</h2><div className="title-grid">{world.titles.map(t=><div className="title-card"><b>{t.name}</b><small>{t.condition}</small></div>)}</div></>}
  {tab==="dungeons"&&<><h2>Dungeons</h2><p className="muted">Multi-floor expeditions with bosses and unique rewards.</p>{world.dungeons.map(d=><button className="dungeon-card" disabled={player.level<d.level} onClick={()=>doDungeon(d)} key={d.id}><span><b>{d.name}</b><small>Lv {d.level} · {d.floors} floors · Boss: {d.boss}</small></span><em>{player.level>=d.level?"ENTER":"LOCKED"}</em></button>)}</>}
  {tab==="quests"&&<><h2>Adventure Board</h2><div className="quest-hero"><b>Explore. Fight. Discover.</b><p>Take normal adventures whenever you want. Dungeons offer longer multi-floor runs.</p><button className="primary" onClick={doAdventure}>START AN ADVENTURE</button></div><h3>Active systems</h3><p className="muted">Main quests, daily objectives, achievements, crafting, guilds and more are connected to the same persistent RPG profile.</p></>}
  </section>
  <div className="touch-zone" onPointerDown={joystick} onPointerMove={e=>e.buttons&&joystick(e)} onPointerUp={stopTouch} onPointerCancel={stopTouch}><span/></div><div className="touch-actions"><button onClick={doAdventure}>⚔</button><button onClick={()=>setTab("inventory")}>▣</button><button onClick={()=>setTab("world")}>◎</button></div>
  {npc&&<div className="modal"><div className="dialog"><button className="close" onClick={()=>setNpc(null)}>×</button><div className="npc-big">{npc.npc.name[0]}</div><h2>{npc.npc.name}</h2><small>{npc.npc.role}</small><p className="dialogue">“{npc.dialogue.text}”</p><div className="dialogue-choices">{npc.dialogue.choices.map((x,i)=><button onClick={()=>{setNotice(x);setNpc(null)}} key={i}>{x}</button>)}</div></div></div>}
  {shop&&<div className="modal"><div className="dialog"><button className="close" onClick={()=>setShop(null)}>×</button><h2>{shop.name}</h2>{shop.products.map(i=><button className="shop-row" onClick={()=>buy(i.id)} key={i.id}><span><b>{i.name}</b><small>{i.rarity}</small></span><em>{i.price} G</em></button>)}</div></div>}
  {dungeon&&<div className="modal"><div className="dialog"><button className="close" onClick={()=>setDungeon(null)}>×</button><h2>{dungeon.result?.name||"Dungeon Run"}</h2><div className="run-log">{(dungeon.result?.log||[]).map((x,i)=><p key={i}>{x}</p>)}</div>{dungeon.result?.win&&<div className="reward">Victory · +{dungeon.result.xp} XP · +{dungeon.result.gold} G</div>}</div></div>}
  <div className="notice">{notice}</div>{paused&&<div className="pause-screen"><h1>PAUSED</h1><button className="primary" onClick={()=>setPaused(false)}>CONTINUE</button></div>}</div>
}

function App(){
  const [auth,setAuth]=useState(!!getToken()),[world,setWorld]=useState(fallbackWorld),[state,setState]=useState(null),[loading,setLoading]=useState(true);
  const load=async()=>{try{const w=await api("/world");setWorld(w);if(getToken()){const s=await api("/state");setState(s)}}catch(e){localStorage.removeItem(tokenKey);setAuth(false)}finally{setLoading(false)}};
  useEffect(()=>{load()},[auth]);
  if(loading)return <div className="loading"><div className="logo">HORIZON <span>FRONTIER</span></div><p>Loading the frontier…</p></div>;
  if(!auth)return <Auth onLogin={()=>setAuth(true)}/>;
  if(!state?.character)return <CharacterCreate world={world} onDone={async()=>setState(await api("/state"))}/>;
  return <Game world={world} initial={state} onLogout={async()=>{await api("/auth/logout",{method:"POST"});localStorage.removeItem(tokenKey);setAuth(false);setState(null)}}/>;
}
createRoot(document.getElementById("root")).render(<App/>);
