import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  ArrowRight, Bot, CalendarDays, ChevronDown, ChevronLeft, ChevronRight, Compass,
  Gamepad2, Heart, Menu, MessageCircle, Search, ShieldCheck, Sparkles, Star, Trophy, Users, X, Zap,
  Clock3, Crown, Medal, Plus, Filter, ExternalLink
} from 'lucide-react';
import './styles.css';

const scenes = [
  { type:'gate', eyebrow:'HORIZON GATE', title:'Opening the gate…', text:'Mapping a route beyond the familiar worlds.' },
  { type:'system', eyebrow:'SYSTEM BOOT', title:'Waking the world…', text:'Synchronizing community signals and preparing your interface.' },
  { type:'party', eyebrow:'PARTY SEARCH', title:'Finding your party…', text:'There is always room for one more traveler.' },
  { type:'stars', eyebrow:'STAR MAP', title:'Reading the horizon…', text:'Some destinations are easier to find than others.' },
  { type:'portal', eyebrow:'WORLD GATE', title:'Changing worlds…', text:'Hold on. The next destination is loading.' },
  { type:'archive', eyebrow:'HORIZON ARCHIVE', title:'Opening the records…', text:'Champions remembered. Community history preserved.' },
  { type:'signal', eyebrow:'COMMUNITY SIGNAL', title:'Gathering travelers…', text:'Every world starts with a few people.' },
  { type:'ai', eyebrow:'HORIZON AI', title:'Waking the guide…', text:'The guide is preparing a connection for a future release.' },
  { type:'anime', eyebrow:'ANIME ARCHIVE', title:'Opening the archive…', text:'Finding something worth adding to your watchlist.' }
];

const nav = [
  ['Home','home'], ['Community','community'], ['Anime','anime'], ['Events','events'], ['Horizon RPG','rpg'], ['Hall of Fame','hall']
];

const eventData = [
  {id:'fc-2026', title:'Fictional Character Tournament', category:'CREATIVE', sub:'Character Creation', date:'Thursday • 7:00 PM IST', status:'FEATURED', description:'Create an original fictional character and compete on creativity, presentation, concept and execution.', participants:'OPEN', rules:['Original character concept','Clear presentation','No changing your submitted character after the deadline','Judging criteria are published with the event']},
  {id:'anigame-pvp', title:'Anigame PvP Tournament', category:'TOURNAMENTS', sub:'Anigame', date:'Schedule announced in Discord', status:'UPCOMING', description:'Build your team, enter the arena and prove yourself in the game where the community began.', participants:'REGISTRATION SOON', rules:['Follow the tournament announcement','Submit verification screenshots when requested','Staff decisions are final']},
  {id:'game-night', title:'Community Game Night', category:'SOCIAL', sub:'Gaming', date:'Date announced in Discord', status:'UPCOMING', description:'Pick a game, bring your friends and spend an evening together.', participants:'OPEN', rules:['Be respectful','Join the voice/text channels for the selected game','Have fun']},
  {id:'anime-trivia', title:'Anime Trivia Night', category:'ANIME', sub:'Quiz', date:'Date announced in Discord', status:'UPCOMING', description:'How deep does your anime knowledge go? Bring your fastest answers.', participants:'COMING SOON', rules:['No answer sharing during rounds','Follow the host timer','Tie-breakers may be used']},
  {id:'character-challenge', title:'Character Creation Challenge', category:'CREATIVE', sub:'Anime', date:'Date announced in Discord', status:'UPCOMING', description:'Create a character from your imagination and show the community what you came up with.', participants:'COMING SOON', rules:['Original work preferred','Explain the concept','Respect other creators']},
  {id:'archive-01', title:'Anigame Community Tournament', category:'TOURNAMENTS', sub:'Archive', date:'Past event', status:'PAST', description:'A preserved record from the community archive.', participants:'ARCHIVED', rules:['Archived event record']}
];



const champions = [
  {tournament:'Fictional Character Tournament', winner:'Champion to be recorded', place:'1ST', date:'Awaiting results', icon:'crown'},
  {tournament:'Anigame PvP Tournament', winner:'Winner to be recorded', place:'1ST', date:'Awaiting results', icon:'medal'},
  {tournament:'Community Tournament Archive', winner:'Record to be added', place:'1ST', date:'Archived', icon:'trophy'}
];

function randomScene(preferred){
  const pool = preferred ? scenes.filter(s=>s.type===preferred) : scenes;
  return pool[Math.floor(Math.random()*pool.length)] || scenes[0];
}

function LoadingScreen({scene,onDone}){
  useEffect(()=>{const t=setTimeout(onDone,760);return()=>clearTimeout(t)},[onDone]);
  return <div className={`loading-screen loading-${scene.type}`} role="status" aria-live="polite">
    <div className="loading-grid"/><div className="loading-stars"/><div className="loading-orbit orbit-one"/><div className="loading-orbit orbit-two"/>
    <div className="loading-core"><span>LH</span></div><div className="loading-scan"/>
    <div className="loading-copy"><span className="eyebrow">{scene.eyebrow}</span><h1>{scene.title}</h1><p>{scene.text}</p></div>
    <div className="loading-line"><span/></div><div className="loading-code">LH://{scene.type.toUpperCase()}_{String(Math.floor(Math.random()*9000+1000))}</div>
  </div>
}

function App(){
  const [loading,setLoading]=useState(true), [scene,setScene]=useState(()=>randomScene()), [view,setView]=useState('home');
  const [menu,setMenu]=useState(false), [modal,setModal]=useState(null), [notice,setNotice]=useState(''), [session,setSession]=useState(null);
  const [content,setContent]=useState({events:eventData,hall:champions,leaderboard:[{id:'community-leaderboard',name:'Community leaderboard',score:'—',status:'AWAITING DATA'},{id:'competitive-records',name:'Competitive records',score:'—',status:'AWAITING DATA'},{id:'event-achievements',name:'Event achievements',score:'—',status:'AWAITING DATA'}]});
  const [eventFilter,setEventFilter]=useState('ALL'), [query,setQuery]=useState(''); const [aiOpen,setAiOpen]=useState(false);

  const notify=useCallback((msg)=>{setNotice(msg);setTimeout(()=>setNotice(''),2200)},[]);
  const navigate=useCallback((next,preferred)=>{setMenu(false);setView(next);setScene(randomScene(preferred));setLoading(true);window.history.replaceState({},'',next==='home'?'/':`/#${next}`)},[]);

  useEffect(()=>{
    fetch('/api/site/auth-me', {credentials:'include'}).then(r=>r.ok?r.json():null).then(data=>setSession(data?.user ? {...data.user, admin:Boolean(data.admin)} : null)).catch(()=>{});
    fetch('/api/site/content', {credentials:'include',cache:'no-store'}).then(r=>r.ok?r.json():null).then(data=>{
      if(data) setContent({events:Array.isArray(data.events)&&data.events.length?data.events:eventData,hall:Array.isArray(data.hall)&&data.hall.length?data.hall:champions,leaderboard:Array.isArray(data.leaderboard)&&data.leaderboard.length?data.leaderboard:[]});
    }).catch(()=>{});
    const params=new URLSearchParams(window.location.search);
    const authResult=params.get('discord');
    if(authResult==='success') notify('Discord connected successfully.');
    else if(authResult==='not-member') notify('Your Discord account is not a member of Log Horizon.');
    else if(authResult==='error') notify('Discord login could not be completed. Check the OAuth settings.');
    if(authResult){ window.history.replaceState({},'',window.location.pathname+window.location.hash); }
    const h=()=>{const id=window.location.hash.replace('#',''); if(id && ['home','community','events','rpg','hall'].includes(id)) setView(id)};
    window.addEventListener('hashchange',h);h();return()=>window.removeEventListener('hashchange',h);
  },[notify]);

  const eventFilters=['ALL','GAMING','TOURNAMENTS','ANIME','CREATIVE','SOCIAL','COMMUNITY'];
  const visibleEvents=useMemo(()=>content.events.filter(e=>eventFilter==='ALL'||e.category===eventFilter||String(e.sub||'').toUpperCase()===eventFilter),[eventFilter,content.events]);
  const searchEvents=useMemo(()=>content.events.filter(e=>(e.title+' '+e.category+' '+e.sub).toLowerCase().includes(query.toLowerCase())),[query,content.events]);

  if(loading) return <LoadingScreen scene={scene} onDone={()=>setLoading(false)}/>;

  return <div className="app"><div className="ambient ambient-cyan"/><div className="ambient ambient-violet"/><div className="grid"/>
    <header className="header">
      <button className="brand" onClick={()=>navigate('home')}><span className="brand-mark">LH</span><span>LOG <b>HORIZON</b></span></button>
      <nav className={menu?'nav open':'nav'}>{nav.map(([label,id])=>id==='anime' ? <a key={id} href="/anime">{label}</a> : id==='rpg' ? <a key={id} className="rpg-nav-link" href="/rpg">{label}</a> : <button key={id} className={view===id?'active':''} onClick={()=>navigate(id,id==='events'?'portal':id==='hall'?'archive':undefined)}>{label}</button>)}{session?.admin&&<a className="admin-nav" href="/admin">Admin</a>}</nav>
      <div className="header-actions">
        <button className="horizon-ai-trigger" onClick={()=>setAiOpen(true)} aria-label="Open Horizon AI"><Bot size={15}/><span>HORIZON AI</span></button>
        {session ? <button className="profile-chip" onClick={()=>notify(`Connected as ${session.username}`)}><span className="profile-dot"/>{session.username}</button> : <button className="discord-login" onClick={()=>window.location.href='/api/site/auth-login'}><MessageCircle size={16}/> Continue with Discord</button>}
        <button className="menu-btn" onClick={()=>setMenu(!menu)} aria-label="Menu">{menu?<X/>:<Menu/>}</button>
      </div>
    </header>

    <main>
      {view==='home' && <Home navigate={navigate} openModal={setModal} openAI={()=>setAiOpen(true)}/>} 
      {view==='community' && <Community navigate={navigate} session={session}/>} 
      {view==='events' && <Events filters={eventFilters} filter={eventFilter} setFilter={setEventFilter} events={visibleEvents} allEvents={content.events} search={query} setSearch={setQuery} searchResults={searchEvents} openModal={setModal} navigate={navigate}/>} 
      {view==='hall' && <HallOfFame champions={content.hall} openModal={setModal} navigate={navigate}/>} 
    </main>

    <button className="floating-ai" onClick={()=>setAiOpen(true)} aria-label="Open Horizon AI"><span className="floating-ai-pulse"/><Bot size={17}/><span>ASK HORIZON</span></button>
    <footer><div className="brand-static"><span className="brand-mark">LH</span><span>LOG <b>HORIZON</b></span></div><span>A community beyond the game.</span><span>PHASE 1 • FOUNDATION COMPLETE</span></footer>
    {notice && <div className="toast"><span className="pulse-dot"/>{notice}</div>}
    {modal && <Modal item={modal} close={()=>setModal(null)} notify={notify} session={session}/>} {aiOpen && <HorizonAI onClose={()=>setAiOpen(false)} notify={notify}/>} 
  </div>
}


function HorizonAI({onClose,notify}){
  const [messages,setMessages]=useState([
    {role:'model',content:'Hey — I’m Horizon. Ask me anything, or just start a conversation.'}
  ]);
  const [input,setInput]=useState('');
  const [busy,setBusy]=useState(false);
  const [status,setStatus]=useState('checking');
  const [statusText,setStatusText]=useState('Checking the Horizon signal…');
  const endRef=React.useRef(null);

  useEffect(()=>{endRef.current?.scrollIntoView({behavior:'smooth'});},[messages,busy]);

  useEffect(()=>{
    let alive=true;
    fetch('/api/site/horizon-ai',{credentials:'include'})
      .then(async r=>{const data=await r.json().catch(()=>({})); if(!alive)return; if(r.ok&&data.online){setStatus('online');setStatusText(`Online • ${data.model||'Horizon AI'}`);}else{setStatus('offline');setStatusText(data.error||'Horizon is not reachable right now.');}})
      .catch(()=>{if(alive){setStatus('offline');setStatusText('Horizon is not reachable right now.');}});
    return()=>{alive=false};
  },[]);

  async function send(){
    const message=input.trim();
    if(!message || busy) return;
    setInput('');
    const next=[...messages,{role:'user',content:message}];
    setMessages(next);
    setBusy(true);
    try{
      const response=await fetch('/api/site/horizon-ai',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        credentials:'include',
        body:JSON.stringify({
          message,
          history:messages.slice(-8)
        })
      });
      const data=await response.json().catch(()=>({}));
      if(!response.ok) throw new Error(data.error || 'Horizon AI is unavailable.');
      setMessages([...next,{role:'model',content:data.reply || data.answer || 'Horizon returned an empty response.'}]);
    }catch(error){
      setMessages([...next,{role:'model',content:`I couldn't reach Horizon AI right now. ${error.message}`}]);
      notify?.('Horizon AI request failed');
    }finally{
      setBusy(false);
    }
  }

  return <div className="ai-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}>
    <div className="ai-panel" role="dialog" aria-modal="true" aria-label="Horizon AI">
      <div className="ai-header">
        <div><span className="eyebrow">HORIZON AI</span><h2>Talk to <em>Horizon.</em></h2><div className={`ai-status ai-status-${status}`}><span/>{statusText}</div></div>
        <button className="icon-btn" onClick={onClose} aria-label="Close"><X/></button>
      </div>
      <div className="ai-messages">
        {messages.map((m,i)=><div key={i} className={`ai-message ${m.role==='user'?'ai-user':'ai-model'}`}>
          <span className="ai-role">{m.role==='user'?'YOU':'HORIZON'}</span>
          <p>{m.content}</p>
        </div>)}
        {busy&&<div className="ai-message ai-model"><span className="ai-role">HORIZON</span><p className="ai-thinking">Thinking…</p></div>}
        <div ref={endRef}/>
      </div>
      <div className="ai-input-row">
        <textarea value={input} onChange={e=>setInput(e.target.value)}
          onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}}}
          placeholder="Ask Horizon anything…" rows="1" maxLength="4000"/>
        <button className="btn primary ai-send" onClick={send} disabled={busy||!input.trim()}><ArrowRight/></button>
      </div>
      <div className="ai-footer">Powered securely through the Log Horizon server • API keys stay server-side</div>
    </div>
  </div>
}

function Home({navigate,openModal,openAI}){return <>
  <section className="hero"><div className="hero-horizon"><div className="horizon-ring"/><div className="horizon-ring inner"/><div className="horizon-floor"/></div>
    <div className="hero-copy"><div className="eyebrow"><span className="pulse-dot"/> COMMUNITY SERVER • ANIGAME ROOTS • MANY WORLDS</div><h1>LOG<br/><span>HORIZON</span></h1><p className="hero-sub">A community beyond the game.</p><p className="hero-text">Born around Anigame. Growing into a home for gamers, anime fans, creators, events, and people who simply want somewhere fun to hang out.</p>
      <div className="hero-actions"><a className="btn primary" href="https://discord.gg/D5aNgKg7Kx" target="_blank" rel="noreferrer">Join the Community <ArrowRight size={18}/></a><button className="btn secondary" onClick={()=>navigate('community')}>Explore Log Horizon</button></div>
    </div><div className="scroll-cue"><ChevronDown size={16}/> SCROLL TO ENTER</div>
  </section>
  <section className="section intro"><div><span className="eyebrow">01 / THE COMMUNITY</span><h2>One community.<br/><em>Many worlds.</em></h2></div><div className="intro-copy"><p>Log Horizon started with Anigame, but the destination is bigger than one game. Different games, anime interests, events, creativity, and conversations can share the same home.</p><LiveCommunityStats/><div className="stat-row"><Stat n="∞" t="Things to build"/><Stat n="1" t="Shared community world"/><Stat n="24/7" t="Horizon can be present"/></div></div></section>
  <section className="section ai-spotlight" id="horizon-ai"><div className="ai-spotlight-art"><div className="ai-spotlight-ring"/><div className="ai-spotlight-core"><Bot size={34}/><span>HORIZON</span></div><span className="ai-signal">SERVER SIGNAL • ONLINE WHEN CONNECTED</span></div><div className="ai-spotlight-copy"><span className="eyebrow">02 / HORIZON AI</span><h2>Talk to the guide<br/><em>behind the horizon.</em></h2><p>The website uses the Railway-hosted Horizon service instead of keeping a separate Gemini connection in the browser. Your conversation travels through the secure server bridge, then Horizon responds using its existing AI system.</p><div className="ai-spotlight-actions"><button className="btn primary" onClick={openAI}><Bot size={17}/> Talk to Horizon <ArrowRight size={17}/></button><span className="ai-security-note">Gemini key stays on Railway • browser never receives it</span></div></div></section>
  <section className="section section-dark"><div className="section-heading"><div><span className="eyebrow">03 / THE WORLD</span><h2>Find your world.</h2></div><p>Four doors into the community. More can be added without changing the foundation.</p></div><div className="feature-grid">
    <Feature icon={<Gamepad2/>} tag="GAMES" title="Play together" text="Competitive battles, casual sessions and community challenges." onClick={()=>navigate('games')}/>
    <Feature icon={<Trophy/>} tag="EVENTS" title="Make it an event" text="Tournaments, creative competitions, game nights and more." onClick={()=>navigate('events','portal')}/>
    <Feature icon={<Sparkles/>} tag="ANIME" title="For the anime people" text="A working archive with search, genres, details and a personal watchlist." onClick={()=>{window.location.href='/anime'}}/>
    <Feature icon={<Bot/>} tag="HORIZON AI" title="Meet the guide" text="Horizon AI runs through the Log Horizon server. Ask the same Horizon intelligence that powers the community bot." special onClick={openAI}/>
  </div></section>
  <section className="section showcase"><div className="portal-large"><div className="portal-ring"/><span>WORLD GATE</span><b>HORIZON</b><i>ANIGAME → MANY WORLDS</i></div><div><span className="eyebrow">03 / ALWAYS MOVING</span><h2>Something is always <em>on the horizon.</em></h2><p>Events give the community reasons to come back. The Hall of Fame makes the history worth keeping.</p><div className="quick-links"><button onClick={()=>navigate('events')}><CalendarDays/> Upcoming events <ArrowRight/></button><button onClick={()=>navigate('hall')}><Crown/> Hall of Fame <ArrowRight/></button></div></div></section>
  <section className="section cta"><span className="eyebrow">04 / YOUR INVITATION</span><h2>There's more beyond<br/><em>the horizon.</em></h2><p>Come for Anigame. Stay for the community.</p><a className="btn primary" href="https://discord.gg/D5aNgKg7Kx" target="_blank" rel="noreferrer">Join Log Horizon <ArrowRight size={18}/></a></section>
</>}

function LiveCommunityStats(){
  const [data,setData]=useState(null);
  useEffect(()=>{
    let live=true;
    fetch('/api/site/horizon-server?view=overview',{credentials:'include',cache:'no-store'})
      .then(r=>r.ok?r.json():null)
      .then(x=>{if(live&&x?.online!==false)setData(x)})
      .catch(()=>{});
    return()=>{live=false};
  },[]);
  const online=Boolean(data);
  return <div className="live-stats"><div className="live-status"><span className={`live-dot ${online?'':'idle'}`}/><div><strong>{online?'COMMUNITY SIGNAL ONLINE':'COMMUNITY DATA AWAITING'}</strong><span>{online?'Live data from the Horizon server bridge':'The site will show live server data when the bridge is connected.'}</span></div></div><div className="live-metrics"><div><strong>{data?.member_count ?? '—'}</strong><span>MEMBERS</span></div><div><strong>{data?.tracked_players ?? '—'}</strong><span>TRACKED</span></div><div><strong>{data?.event_count ?? '—'}</strong><span>EVENTS</span></div></div></div>;
}

function Community({navigate,session}){return <section className="page-shell"><PageHero eyebrow="COMMUNITY" title={<>One server.<br/><em>Many worlds.</em></>} text="Log Horizon is being built as a place to play, talk, create, compete and discover people with shared interests."/>
  <div className="community-grid"><InfoCard icon={<Users/>} title="Meet people" text="Find conversations and activities beyond a single game."/><InfoCard icon={<Trophy/>} title="Compete" text="Join tournaments and leave a record in the community archive."/><InfoCard icon={<Sparkles/>} title="Create" text="Character contests, creative challenges and community projects."/><InfoCard icon={<ShieldCheck/>} title="Connected" text={session?`Discord connected as ${session.username}.`:'Connect Discord when you are ready for member-only features.'}/></div>
  <div className="community-banner"><div><span className="eyebrow">THE FOUNDATION</span><h2>Built for growth, not just traffic.</h2><p>The site is structured so future systems—Discord roles, member profiles, event registration and Horizon AI—can plug into the same experience.</p></div><button className="btn primary" onClick={()=>navigate('events')}>See what’s happening <ArrowRight/></button></div>
</section>}

function Events({filters,filter,setFilter,events,allEvents,search,setSearch,searchResults,openModal,navigate}){return <section className="page-shell"><PageHero eyebrow="EVENTS" title={<>THE HORIZON<br/><em>AWAITS.</em></>} text="Tournaments, community challenges, game nights, creative competitions and more. Find your next event." actions={<><button className="btn primary" onClick={()=>document.getElementById('upcoming')?.scrollIntoView({behavior:'smooth'})}>View upcoming events <ArrowRight/></button><button className="btn secondary" onClick={()=>setFilter('ALL')}>Explore all</button></>}/>
  <section className="featured-event"><div className="featured-visual"><div className="event-sigil"><Trophy/></div><span>FEATURED EVENT</span><b>{(allEvents[0]?.title||'LH').slice(0,2).toUpperCase()}</b></div><div><span className="eyebrow">{allEvents[0]?.category||'COMMUNITY'} • {allEvents[0]?.date||'DATE TO BE ANNOUNCED'}</span><h2>{allEvents[0]?.title||'No featured event yet'}</h2><p>{allEvents[0]?.description||'Add a featured event from the admin control center.'}</p><div className="event-meta"><span><Clock3/> {allEvents[0]?.date||'TBA'}</span><span><Users/> {allEvents[0]?.participants||'OPEN'}</span></div>{allEvents[0]&&<button className="btn primary" onClick={()=>openModal(allEvents[0])}>View event <ArrowRight/></button>}</div></section>
  <section className="section inner-section" id="upcoming"><div className="section-heading"><div><span className="eyebrow">UPCOMING EVENTS</span><h2>Choose your event.</h2></div><div className="search"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search events"/></div></div>
    <div className="filters">{filters.map(f=><button key={f} className={filter===f?'selected':''} onClick={()=>setFilter(f)}>{f}</button>)}</div>
    <div className="event-grid">{events.filter(e=>e.status!=='PAST').map(e=><EventCard key={e.id} event={e} onClick={()=>openModal(e)}/>)}</div>
    {events.filter(e=>e.status!=='PAST').length===0&&<Empty text="No events match that filter yet."/>}
  </section>
  <section className="section inner-section archive-section"><div className="section-heading"><div><span className="eyebrow">PAST EVENTS</span><h2>The archive.</h2></div><button className="text-link" onClick={()=>navigate('hall','archive')}>Open Hall of Fame <ArrowRight/></button></div><div className="archive-row">{allEvents.filter(e=>e.status==='PAST').map(e=><EventCard key={e.id} event={e} compact onClick={()=>openModal(e)}/>)}</div></section>
  <section className="host-panel"><Plus/><div><span className="eyebrow">HAVE AN IDEA?</span><h3>Host or submit an event</h3><p>Phase 1 provides the interface. Registration and staff workflows can be connected to Discord in the next backend pass.</p></div><button className="btn secondary" onClick={()=>openModal({title:'Event submission',category:'COMMUNITY',description:'Tell the staff what you want to host. The full submission form will be connected after Discord authentication is live.',rules:['Event name','Proposed date/time','Game or activity','Rules and participant requirements']})}>Submit an idea</button></section>
</section>}

function Modal({item,close,notify,session}){return <div className="modal-backdrop" onMouseDown={e=>e.target===e.currentTarget&&close()}><div className="modal"><button className="modal-close" onClick={close}><X/></button><span className="eyebrow">{item.category||'LOG HORIZON'}</span><h2>{item.title}</h2><p>{item.description||item.text}</p>{item.date&&<div className="modal-meta"><span><CalendarDays/>{item.date}</span><span><Users/>{item.participants}</span></div>}<h3>Details</h3><ul>{(item.rules||['This feature is ready for the next integration step.']).map((r,i)=><li key={i}>{r}</li>)}</ul><div className="modal-actions">{item.status!=='PAST'&&<button className="btn primary" onClick={()=>notify(session?'Registration flow ready for backend.':'Connect Discord to register for member events.')}>{session?'Register interest':'Continue with Discord'} <ArrowRight/></button>}<button className="btn secondary" onClick={close}>Close</button></div></div></div>}

function HorizonRPGPage(){
  const [tab,setTab]=useState('WORLD');
  const [selected,setSelected]=useState('Northreach');

  const locations=[
    {name:'Northreach',type:'CITY',text:'A frontier city where travelers, merchants and rumors meet.',state:'STABLE'},
    {name:'Whispering Wilds',type:'WILDS',text:'A forest that changes when people disturb what sleeps beneath it.',state:'UNSTABLE'},
    {name:'Sunken Ruins',type:'RUINS',text:'An old civilization left behind doors nobody fully understands.',state:'UNKNOWN'},
    {name:'Ashen Pass',type:'PASS',text:'A dangerous mountain route watched by something enormous.',state:'DANGER'}
  ];

  return <div className="rpg-shell-v2">
    <div className="rpg-v2-bg"/><div className="rpg-v2-grid"/>
    <header className="rpg-v2-header">
      <a className="rpg-v2-brand" href="/"><span>LH</span><div><b>HORIZON RPG</b><small>A WORLD THAT REMEMBERS</small></div></a>
      <nav>
        {['WORLD','CHARACTER','QUESTS','CODEX'].map(x=><button key={x} className={tab===x?'active':''} onClick={()=>setTab(x)}>{x}</button>)}
      </nav>
      <a className="rpg-v2-exit" href="/">EXIT RPG</a>
    </header>

    <main className="rpg-v2-main">
      <section className="rpg-v2-hero">
        <div className="rpg-v2-copy">
          <span className="eyebrow">HORIZON RPG • WEBSITE WORLD</span>
          <h1>A world that<br/><em>remembers.</em></h1>
          <p>This is its own Horizon RPG experience — separate from the community website, while still belonging to the same universe. The shell comes first; the living systems will be added one at a time.</p>
          <div className="rpg-v2-actions"><button onClick={()=>setTab('WORLD')}>ENTER THE WORLD <ArrowRight size={16}/></button><span>PHASE 1 • WORLD SHELL</span></div>
        </div>
        <div className="rpg-v2-map">
          <div className="rpg-v2-moon"/><div className="rpg-v2-mountain m1"/><div className="rpg-v2-mountain m2"/>
          <div className="rpg-v2-river"/><div className="rpg-v2-road road1"/><div className="rpg-v2-road road2"/>
          <div className="rpg-v2-town"><b>NORTHREACH</b><small>SAFE HAVEN</small></div>
          <div className="rpg-v2-player"><span>YOU</span></div>
          <i className="rpg-v2-location l1"/><i className="rpg-v2-location l2"/><i className="rpg-v2-location l3"/>
          <div className="rpg-v2-compass">N<br/><b>+</b><br/>S</div>
          <div className="rpg-v2-map-label a">WHISPERING WILDS</div><div className="rpg-v2-map-label b">ASHEN PASS</div>
        </div>
      </section>

      <section className="rpg-v2-section">
        <div className="rpg-v2-heading"><div><span className="eyebrow">FOUNDATION</span><h2>Build the world<br/><em>before the systems.</em></h2></div><p>The first version is intentionally a shell. Nothing here needs to be final before we add movement, combat, NPC memory, quests and persistent consequences.</p></div>
        <div className="rpg-v2-cards">
          <button onClick={()=>setTab('WORLD')}><Compass/><span>01</span><b>WORLD</b><small>Map, locations, regions and a persistent world state.</small></button>
          <button onClick={()=>setTab('CHARACTER')}><Users/><span>02</span><b>CHARACTER</b><small>Identity, stats, equipment and progression.</small></button>
          <button onClick={()=>setTab('QUESTS')}><Sparkles/><span>03</span><b>QUESTS</b><small>Choices that can eventually change what happens around you.</small></button>
          <button onClick={()=>setTab('CODEX')}><Trophy/><span>04</span><b>CODEX</b><small>People, creatures, discoveries and history worth remembering.</small></button>
        </div>
      </section>

      <section className="rpg-v2-living">
        <div><span className="eyebrow">THE LIVING WORLD</span><h2>Small actions should<br/><em>leave footprints.</em></h2><p>Help a merchant today. That merchant remembers. Return later and the conversation, price, quest or rumor can be different. The goal is a world where even small choices have somewhere to go.</p></div>
        <div className="rpg-v2-chain"><article><span>PLAYER ACTION</span><b>You help a traveler reach Northreach.</b></article><i>↓</i><article><span>MEMORY</span><b>The traveler remembers your name.</b></article><i>↓</i><article><span>CONSEQUENCE</span><b>A future route or opportunity opens.</b></article></div>
      </section>

      <section className="rpg-v2-section">
        <div className="rpg-v2-heading compact"><div><span className="eyebrow">WORLD PREVIEW</span><h2>There is already<br/><em>somewhere to go.</em></h2></div></div>
        <div className="rpg-v2-location-grid">{locations.map(x=><button key={x.name} className={selected===x.name?'selected':''} onClick={()=>setSelected(x.name)}><span>{x.type}</span><b>{x.name}</b><small>{x.text}</small><em>{x.state}</em></button>)}</div>
        <div className="rpg-v2-selected"><span>SELECTED LOCATION</span><b>{selected}</b><small>The location system is ready for the next layer of world-state logic.</small></div>
      </section>

      <section className="rpg-v2-roadmap">
        <span className="eyebrow">ROADMAP</span>
        <div><b>01</b><span>Playable foundation</span><small>World, movement, collision, save/load and basic interaction.</small></div>
        <div><b>02</b><span>RPG depth</span><small>Combat, classes, skills, equipment, enemies and dungeons.</small></div>
        <div><b>03</b><span>Living world</span><small>NPC schedules, memory, relationships, factions and consequences.</small></div>
        <div><b>04</b><span>Shared world</span><small>Parties, trading, guilds, world events and multiplayer systems.</small></div>
        <div><b>05</b><span>Endgame</span><small>Raids, seasons, legendary content and world-changing events.</small></div>
      </section>
    </main>
  </div>
}

function shuffle(list){return [...list].sort(()=>Math.random()-0.5)}

const QUIZ_QUESTIONS=[
  ['Which anime features Monkey D. Luffy?',['One Piece','Bleach','Naruto','Demon Slayer'],0],
  ['Which Pokémon is known as the Electric Mouse?',['Eevee','Pikachu','Mew','Lucario'],1],
  ['Who uses the breathing style called Hinokami Kagura?',['Tanjiro Kamado','Gojo Satoru','Ichigo Kurosaki','Saitama'],0],
  ['Which series is set around the Hidden Leaf Village?',['Naruto','One Piece','Jujutsu Kaisen','Bleach'],0],
  ['What is the name of Ichigo’s sword?',['Zangetsu','Enma','Samehada','Nichirin'],0],
  ['Which anime has the character Satoru Gojo?',['Jujutsu Kaisen','Black Clover','One Punch Man','Fairy Tail'],0],
  ['Who is the captain of the Straw Hat Pirates?',['Zoro','Sanji','Luffy','Usopp'],2],
  ['Which series features the Survey Corps?',['Attack on Titan','Bleach','Demon Slayer','Blue Lock'],0],
  ['What is the name of Tanjiro’s sister?',['Nezuko','Mikasa','Nami','Shinobu'],0],
  ['Which anime is centered around a hero named Izuku Midoriya?',['My Hero Academia','Hunter x Hunter','Haikyuu!!','Tokyo Ghoul'],0],
  ['Which character is known for saying “Plus Ultra” in hero training?',['All Might','Kakashi','Levi','Gon'],0],
  ['Which series features the Soul Reapers?',['Bleach','Naruto','One Piece','Chainsaw Man'],0]
];

const ANIME_GUESSES=[
  ['Pirates, Devil Fruits and a rubber-bodied captain are central to this adventure.',['One Piece','Naruto','Bleach','Fairy Tail'],0],
  ['A boy and his sister travel while fighting demons with Nichirin blades.',['Demon Slayer','Jujutsu Kaisen','Blue Exorcist','Noragami'],0],
  ['Ninja villages, chakra and the Uchiha clan are key parts of this story.',['Naruto','One Piece','Black Clover','Bleach'],0],
  ['Cursed energy and sorcerers face supernatural curses in modern Japan.',['Jujutsu Kaisen','Mob Psycho 100','Tokyo Ghoul','Fire Force'],0],
  ['Humanity fights enormous humanoid threats behind massive walls.',['Attack on Titan','Dr. Stone','86','Vinland Saga'],0],
  ['A young hero enters a school where students train to become professional heroes.',['My Hero Academia','Blue Lock','Assassination Classroom','Soul Eater'],0],
  ['A volleyball team works toward the national stage under a passionate first-year player.',['Haikyuu!!','Kuroko’s Basketball','Free!','Blue Lock'],0],
  ['A swordsman hunts monsters while mastering several powerful breathing techniques.',['Demon Slayer','Bleach','Rurouni Kenshin','Samurai Champloo'],0],
  ['A quiet genius and a group of classmates become involved with a mysterious notebook.',['Death Note','Code Geass','Monster','Erased'],0],
  ['A young alchemist travels with his brother while searching for a way to restore their bodies.',['Fullmetal Alchemist','Hunter x Hunter','Soul Eater','Fire Force'],0]
];



createRoot(document.getElementById('root')).render(
  window.location.pathname.replace(/\/$/, '') === '/anime' ? <AnimePage /> :
  window.location.pathname.replace(/\/$/, '') === '/admin' ? <AdminPage /> :
  window.location.pathname.replace(/\/$/, '') === '/rpg' ? <HorizonRPGPage /> : <App />
);
