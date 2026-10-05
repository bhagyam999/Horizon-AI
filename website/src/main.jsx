import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const locations = [
  {id:'northreach',name:'Northreach',type:'Settlement',desc:'A frontier town built around an old crystal gate.',x:25,y:35},
  {id:'wilds',name:'Whispering Wilds',type:'Wilderness',desc:'A forest where paths shift after sunset.',x:63,y:24},
  {id:'ruins',name:'Sunken Ruins',type:'Ancient Site',desc:'Broken towers beneath a flooded valley.',x:70,y:69},
  {id:'pass',name:'Ashen Pass',type:'Mountain Route',desc:'A dangerous crossing watched by something unseen.',x:33,y:74},
];

function App(){
  const [tab,setTab]=useState('world');
  const [selected,setSelected]=useState(locations[0]);
  const [events,setEvents]=useState([
    'You arrived at the Northreach crossroads.',
    'The world registered your first step into Horizon.',
    'Mira noticed you and remembered your name.'
  ]);
  const act=(text)=>setEvents(e=>[text,...e].slice(0,5));
  return <div className="app">
    <header className="topbar">
      <div className="brand"><div className="mark">H</div><div><b>HORIZON RPG</b><small>A WORLD THAT REMEMBERS</small></div></div>
      <div className="online"><i/> WORLD ONLINE <span/> DAY 01 <span/> 18:00</div>
      <button className="player-btn" onClick={()=>setTab('character')}>PLAYER</button>
    </header>
    <div className="layout">
      <aside className="nav">
        <small>HORIZON</small>
        {[['world','01','WORLD'],['character','02','CHARACTER'],['quests','03','QUESTS'],['codex','04','CODEX']].map(x=>
          <button key={x[0]} className={'nav-item '+(tab===x[0]?'active':'')} onClick={()=>setTab(x[0])}><em>{x[1]}</em>{x[2]}</button>
        )}
        <div className="build"><small>FOUNDATION BUILD</small><strong>0.1</strong><p>The shell is live. Systems will be added one layer at a time.</p></div>
      </aside>
      <main className="main">
        {tab==='world' && <World selected={selected} setSelected={setSelected} events={events} act={act}/>}
        {tab==='character' && <Character act={act}/>}
        {tab==='quests' && <Quests act={act}/>}
        {tab==='codex' && <Codex/>}
      </main>
      <aside className="rail">
        <div className="card player-card">
          <small>CURRENT HERO</small><div className="avatar">A</div><h2>Aeris</h2><label>ADVENTURER • LEVEL 1</label>
          <div className="xp"><span>XP</span><span>120 / 500</span></div><div className="bar"><i/></div>
          <div className="stats"><b>10<small>VIT</small></b><b>10<small>STR</small></b><b>10<small>AGI</small></b><b>10<small>INT</small></b></div>
        </div>
        <div className="card"><small>ACTIVE THREAD</small><h3>The First Footstep</h3><p>Explore Northreach and learn what the frontier remembers.</p><div className="bar"><i style={{width:'25%'}}/></div><footer><span>1 / 4</span><span>MAIN</span></footer></div>
        <div className="card muted"><small>WORLD CLOCK</small><strong>18:00</strong><p>Weather: clear<br/>Moon: waxing crescent</p></div>
      </aside>
    </div>
  </div>
}

function World({selected,setSelected,events,act}){
 return <><section className="hero"><div><small>THE FRONTIER • NORTHREACH REGION</small><h1>A world that <i>remembers.</i></h1><p>Every journey starts small. Your choices will eventually change places, people, factions and stories.</p></div><div className="actions"><button className="primary" onClick={()=>act('You set out toward '+selected.name+'.')}>SET OUT</button><button onClick={()=>act('Time advanced. The world continued without you.')}>ADVANCE TIME</button></div></section>
 <section className="panel"><header><div><small>LIVE WORLD MAP</small><h2>Northreach Frontier</h2></div><label>● PERSISTENT STATE</label></header>
 <div className="map"><div className="grid"/><div className="river"/><div className="mountain m1"/><div className="mountain m2"/>
 {locations.map(l=><button key={l.id} className={'loc '+(selected.id===l.id?'selected':'')} style={{left:l.x+'%',top:l.y+'%'}} onClick={()=>{setSelected(l);act('You focused on '+l.name+'.')}}><b/><span>{l.name}</span></button>)}
 <div className="you">YOU</div><div className="north">N</div><div className="scale">10 KM</div></div>
 <div className="detail"><div><small>SELECTED LOCATION</small><h3>{selected.name}</h3><label>{selected.type}</label><p>{selected.desc}</p></div><div className="actions"><button onClick={()=>act('You inspected '+selected.name+'.')}>INSPECT</button><button className="primary" onClick={()=>act('You entered '+selected.name+'.')}>ENTER</button></div></div></section>
 <section className="cards"><Info n="01" tag="NPC MEMORY" title="Mira remembers you." text="You helped carry a crate on your first visit. She may treat you differently next time."/><Info n="02" tag="WORLD STATE" title="Small actions matter." text="A locked gate, a missed meeting or a kind word can become part of the world's history."/><Info n="03" tag="NEXT LAYER" title="Living world systems." text="Schedules, factions, consequences and hidden interactions will be built on this foundation."/></section>
 <section className="panel activity"><header><div><small>WORLD ACTIVITY</small><h2>Recent changes</h2></div><label>LIVE</label></header>{events.map((e,i)=><div className="event" key={i}><time>{i?'Earlier':'Just now'}</time><p>{e}</p></div>)}</section></>
}
function Info({n,tag,title,text}){return <article className="info"><small>{n} • {tag}</small><h3>{title}</h3><p>{text}</p></article>}
function Character({act}){return <Page title="Your character is more than stats." eyebrow="CHARACTER SYSTEM • FOUNDATION" lead="This page will hold progression, equipment, skills, traits and choices that shape how the world reacts to you."><div className="sheet"><div className="big-avatar">A</div><div><small>ADVENTURER</small><h2>Aeris</h2><p>Level 1 • Northreach</p></div></div><div className="systems">{['Attributes','Skills','Equipment','Traits'].map((x,i)=><article key={x}><small>0{i+1}</small><h3>{x}</h3><p>Foundation ready. The real system will be added here.</p></article>)}</div><button className="primary" onClick={()=>act('You reviewed your character sheet.')}>REVIEW CHARACTER</button></Page>}
function Quests({act}){return <Page title="Not every quest starts with a marker." eyebrow="QUESTS • CONSEQUENCES" lead="Some objectives will emerge from what you do, who remembers you and what changes in the world."><div className="quests">{[['The First Footstep','Explore Northreach and learn the frontier.','1 / 4','MAIN'],['A Familiar Face','Speak with Mira again after helping her.','0 / 1','MEMORY'],['Unknown Road','Discover a route beyond the Ashen Pass.','LOCKED','HIDDEN']].map(q=><button key={q[0]} onClick={()=>act('You inspected the quest: '+q[0]+'.')}><div><small>{q[3]}</small><h3>{q[0]}</h3><p>{q[1]}</p></div><b>{q[2]}</b></button>)}</div></Page>}
function Codex(){return <Page title="Things the world has learned." eyebrow="CODEX • WORLD MEMORY" lead="The Codex will become the persistent record of people, places, creatures, items, factions and events discovered by the player."><div className="systems codex">{['People','Places','Creatures','Factions','Items','Events'].map((x,i)=><article key={x}><small>0{i+1}</small><h3>{x}</h3><p>0 discoveries</p></article>)}</div></Page>}
function Page({title,eyebrow,lead,children}){return <section className="page"><small>{eyebrow}</small><h1>{title}</h1><p className="lead">{lead}</p>{children}</section>}

createRoot(document.getElementById('root')).render(<App/>);
