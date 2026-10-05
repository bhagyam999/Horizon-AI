import React, {useMemo, useState} from "react";
import {createRoot} from "react-dom/client";
import {
  BookOpen, ChevronRight, Compass, Crown, Heart, Map,
  Menu, ScrollText, Shield, Sparkles, Swords, Users, X, Zap
} from "lucide-react";
import "./styles.css";

const LOCATIONS = [
  {id:"northreach", name:"Northreach", type:"CITY", state:"Stable", x:25, y:63, description:"A frontier city of merchants, travelers and old rumors.", color:"gold"},
  {id:"whispering", name:"Whispering Wilds", type:"WILDS", state:"Unstable", x:67, y:25, description:"The forest remembers every path taken through it.", color:"green"},
  {id:"sunken", name:"Sunken Ruins", type:"RUINS", state:"Unknown", x:78, y:70, description:"Half-buried structures from a civilization nobody understands.", color:"violet"},
  {id:"ashen", name:"Ashen Pass", type:"PASS", state:"Danger", x:48, y:17, description:"A mountain route where something enormous has been seen.", color:"red"},
  {id:"lake", name:"Mirror Lake", type:"LANDMARK", state:"Quiet", x:46, y:78, description:"Still water said to reflect places that are far away.", color:"blue"}
];

const TABS = [
  ["world","WORLD",Compass],
  ["character","CHARACTER",Shield],
  ["quests","QUESTS",ScrollText],
  ["codex","CODEX",BookOpen]
];

function App(){
  const [tab,setTab]=useState("world");
  const [selected,setSelected]=useState("northreach");
  const [menu,setMenu]=useState(false);
  const [messages,setMessages]=useState([
    "The world is waiting.",
    "No actions have been recorded yet."
  ]);

  const location=useMemo(
    ()=>LOCATIONS.find(x=>x.id===selected) || LOCATIONS[0],
    [selected]
  );

  const selectLocation=(id)=>{
    const next=LOCATIONS.find(x=>x.id===id);
    setSelected(id);
    if(next){
      setMessages(m=>[
        `You discovered ${next.name}.`,
        next.description,
        ...m
      ].slice(0,5));
    }
  };

  return <div className="rpg-app">
    <div className="ambient ambient-one"/>
    <div className="ambient ambient-two"/>

    <header className="topbar">
      <a className="brand" href="/">
        <span className="brand-mark">H</span>
        <span><b>HORIZON</b><small>RPG</small></span>
      </a>

      <button className="mobile-menu" onClick={()=>setMenu(v=>!v)} aria-label="Open menu">
        {menu?<X/>:<Menu/>}
      </button>

      <nav className={`main-nav ${menu?"open":""}`}>
        {TABS.map(([id,label,Icon])=>
          <button key={id} className={tab===id?"active":""} onClick={()=>{setTab(id);setMenu(false)}}>
            <Icon size={15}/>{label}
          </button>
        )}
      </nav>

      <div className="online"><span/> WORLD ONLINE</div>
    </header>

    <main className="game-layout">
      <section className="world-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">THE FRONTIER</span>
            <h1>{tab==="world" ? "A world that remembers." : tab==="character" ? "Your journey." : tab==="quests" ? "Threads waiting to be pulled." : "What the world has recorded."}</h1>
          </div>
          <div className="coordinates">REGION 01 <span>•</span> 42 / 18</div>
        </div>

        <div className="map-frame">
          <div className="map-sky"/>
          <div className="mountain mountain-a"/>
          <div className="mountain mountain-b"/>
          <div className="forest forest-a"/>
          <div className="forest forest-b"/>
          <div className="river"/>
          <div className="road road-a"/>
          <div className="road road-b"/>

          {LOCATIONS.map(point=>
            <button
              key={point.id}
              className={`map-point ${point.color} ${selected===point.id?"selected":""}`}
              style={{left:`${point.x}%`,top:`${point.y}%`}}
              onClick={()=>selectLocation(point.id)}
              title={point.name}
            >
              <span className="point-pulse"/>
              <i/>
              <b>{point.name}</b>
            </button>
          )}

          <div className="player-marker" style={{left:"38%",top:"52%"}}>
            <span className="player-glow"/>
            <div>YOU</div>
          </div>

          <div className="map-compass"><b>N</b><span>+</span><small>S</small></div>
          <div className="map-scale">NORTHREACH REGION <span>•</span> SCALE 1:1</div>
        </div>

        <div className="location-strip">
          <div>
            <span className="eyebrow">SELECTED LOCATION</span>
            <strong>{location.name}</strong>
            <small>{location.type} · {location.state}</small>
          </div>
          <p>{location.description}</p>
          <button onClick={()=>setMessages(m=>[`You inspect ${location.name}.`,"Nothing happens yet. The world system will grow here.",...m].slice(0,5))}>
            INTERACT <ChevronRight size={15}/>
          </button>
        </div>
      </section>

      <aside className="hud">
        <div className="character-card">
          <div className="portrait"><span>LV</span><b>01</b></div>
          <div><span className="eyebrow">ADVENTURER</span><h2>Wanderer</h2><small>Human · Novice</small></div>
          <Crown className="rank-icon" size={18}/>
        </div>

        <div className="bars">
          <div><span><Heart size={13}/> HP</span><b>100 / 100</b></div>
          <div className="bar"><i className="hp"/></div>
          <div><span><Zap size={13}/> MP</span><b>50 / 50</b></div>
          <div className="bar"><i className="mp"/></div>
        </div>

        <section className="hud-section">
          <div className="hud-title"><Map size={15}/> CURRENT OBJECTIVE</div>
          <h3>Find your first thread.</h3>
          <p>Explore Northreach and discover something the world can remember.</p>
          <div className="progress"><i/></div>
          <small>0 / 1 DISCOVERY</small>
        </section>

        <section className="hud-section">
          <div className="hud-title"><Sparkles size={15}/> WORLD SIGNAL</div>
          <div className="signal">
            <span className="signal-dot"/>
            <div><b>The frontier is quiet.</b><small>No major world events active.</small></div>
          </div>
        </section>

        <section className="hud-section event-log">
          <div className="hud-title"><ScrollText size={15}/> RECENT MEMORY</div>
          {messages.map((message,i)=><p key={i} className={i===0?"new":""}>{message}</p>)}
        </section>

        <div className="party-card">
          <Users size={16}/>
          <div><b>SOLO ADVENTURE</b><small>Party systems come later.</small></div>
        </div>
      </aside>
    </main>

    <footer className="actionbar">
      <div className="action-left">
        <span className="key">WASD</span><small>MOVE</small>
        <span className="key">E</span><small>INTERACT</small>
        <span className="key">I</span><small>INVENTORY</small>
      </div>
      <div className="world-state"><Swords size={14}/> PHASE 01 <span>PLAYABLE FOUNDATION</span></div>
    </footer>
  </div>
}

createRoot(document.getElementById("root")).render(<App/>);
