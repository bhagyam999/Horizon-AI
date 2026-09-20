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
  ['Home','home'], ['Community','community'], ['Anime','anime'], ['Events','events'], ['Games','games'], ['Hall of Fame','hall']
];

const eventData = [
  {id:'fc-2026', title:'Fictional Character Tournament', category:'CREATIVE', sub:'Character Creation', date:'Thursday • 7:00 PM IST', status:'FEATURED', description:'Create an original fictional character and compete on creativity, presentation, concept and execution.', participants:'OPEN', rules:['Original character concept','Clear presentation','No changing your submitted character after the deadline','Judging criteria are published with the event']},
  {id:'anigame-pvp', title:'Anigame PvP Tournament', category:'TOURNAMENTS', sub:'Anigame', date:'Schedule announced in Discord', status:'UPCOMING', description:'Build your team, enter the arena and prove yourself in the game where the community began.', participants:'REGISTRATION SOON', rules:['Follow the tournament announcement','Submit verification screenshots when requested','Staff decisions are final']},
  {id:'game-night', title:'Community Game Night', category:'SOCIAL', sub:'Gaming', date:'Date announced in Discord', status:'UPCOMING', description:'Pick a game, bring your friends and spend an evening together.', participants:'OPEN', rules:['Be respectful','Join the voice/text channels for the selected game','Have fun']},
  {id:'anime-trivia', title:'Anime Trivia Night', category:'ANIME', sub:'Quiz', date:'Date announced in Discord', status:'UPCOMING', description:'How deep does your anime knowledge go? Bring your fastest answers.', participants:'COMING SOON', rules:['No answer sharing during rounds','Follow the host timer','Tie-breakers may be used']},
  {id:'character-challenge', title:'Character Creation Challenge', category:'CREATIVE', sub:'Anime', date:'Date announced in Discord', status:'UPCOMING', description:'Create a character from your imagination and show the community what you came up with.', participants:'COMING SOON', rules:['Original work preferred','Explain the concept','Respect other creators']},
  {id:'archive-01', title:'Anigame Community Tournament', category:'TOURNAMENTS', sub:'Archive', date:'Past event', status:'PAST', description:'A preserved record from the community archive.', participants:'ARCHIVED', rules:['Archived event record']}
];

const gameData = [
  {id:'anigame', title:'Anigame', category:['CARD','COMPETITIVE'], status:'LIVE', text:'The game where the Log Horizon community began.', action:'Learn More'},
  {id:'quiz', title:'Horizon Quiz', category:['QUIZ','ANIME','CASUAL'], status:'PLAYABLE', text:'Test your knowledge against other members.', action:'Play'},
  {id:'anime-guess', title:'Anime Guess', category:['ANIME','CASUAL'], status:'COMING SOON', text:'Identify the anime before the timer runs out.', action:'Coming Soon'},
  {id:'forge', title:'Character Forge', category:['CREATIVE'], status:'COMING SOON', text:'Build your own fictional character and share it with the community.', action:'Coming Soon'},
  {id:'arena', title:'Horizon Arena', category:['COMPETITIVE'], status:'COMING SOON', text:'A small competitive arena built for Log Horizon members.', action:'Coming Soon'},
  {id:'browser', title:'Browser Game Hub', category:['CASUAL','COMMUNITY'], status:'COMING SOON', text:'A rotating collection of lightweight games for community nights.', action:'Coming Soon'}
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
  const [eventFilter,setEventFilter]=useState('ALL'), [gameFilter,setGameFilter]=useState('ALL'), [query,setQuery]=useState(''); const [aiOpen,setAiOpen]=useState(false);

  const notify=useCallback((msg)=>{setNotice(msg);setTimeout(()=>setNotice(''),2200)},[]);
  const navigate=useCallback((next,preferred)=>{setMenu(false);setView(next);setScene(randomScene(preferred));setLoading(true);window.history.replaceState({},'',next==='home'?'/':`/#${next}`)},[]);

  useEffect(()=>{
    fetch('/api/site/auth-me', {credentials:'include'}).then(r=>r.ok?r.json():null).then(data=>setSession(data?.user || null)).catch(()=>{});
    const h=()=>{const id=window.location.hash.replace('#',''); if(id && ['home','community','events','games','hall'].includes(id)) setView(id)};
    window.addEventListener('hashchange',h);h();return()=>window.removeEventListener('hashchange',h);
  },[]);

  const eventFilters=['ALL','GAMING','TOURNAMENTS','ANIME','CREATIVE','SOCIAL','COMMUNITY'];
  const gameFilters=['ALL','COMPETITIVE','CASUAL','ANIME','CARD','QUIZ','CREATIVE'];
  const visibleEvents=useMemo(()=>eventData.filter(e=>eventFilter==='ALL'||e.category===eventFilter||e.sub.toUpperCase()===eventFilter),[eventFilter]);
  const visibleGames=useMemo(()=>gameData.filter(g=>gameFilter==='ALL'||g.category.includes(gameFilter)),[gameFilter]);
  const searchEvents=useMemo(()=>eventData.filter(e=>(e.title+' '+e.category+' '+e.sub).toLowerCase().includes(query.toLowerCase())),[query]);

  if(loading) return <LoadingScreen scene={scene} onDone={()=>setLoading(false)}/>;

  return <div className="app"><div className="ambient ambient-cyan"/><div className="ambient ambient-violet"/><div className="grid"/>
    <header className="header">
      <button className="brand" onClick={()=>navigate('home')}><span className="brand-mark">LH</span><span>LOG <b>HORIZON</b></span></button>
      <nav className={menu?'nav open':'nav'}>{nav.map(([label,id])=>id==='anime' ? <a key={id} href="/anime">{label}</a> : <button key={id} className={view===id?'active':''} onClick={()=>navigate(id,id==='events'?'portal':id==='hall'?'archive':undefined)}>{label}</button>)}</nav>
      <div className="header-actions">
        <button className="horizon-ai-trigger" onClick={()=>setAiOpen(true)} aria-label="Open Horizon AI"><Bot size={15}/><span>HORIZON AI</span></button>
        {session ? <button className="profile-chip" onClick={()=>notify(`Connected as ${session.username}`)}><span className="profile-dot"/>{session.username}</button> : <button className="discord-login" onClick={()=>window.location.href='/api/site/auth-login'}><MessageCircle size={16}/> Continue with Discord</button>}
        <button className="menu-btn" onClick={()=>setMenu(!menu)} aria-label="Menu">{menu?<X/>:<Menu/>}</button>
      </div>
    </header>

    <main>
      {view==='home' && <Home navigate={navigate} openModal={setModal} openAI={()=>setAiOpen(true)}/>} 
      {view==='community' && <Community navigate={navigate} session={session}/>} 
      {view==='events' && <Events filters={eventFilters} filter={eventFilter} setFilter={setEventFilter} events={visibleEvents} search={query} setSearch={setQuery} searchResults={searchEvents} openModal={setModal} navigate={navigate}/>} 
      {view==='games' && <Games filters={gameFilters} filter={gameFilter} setFilter={setGameFilter} games={visibleGames} openModal={setModal}/>} 
      {view==='hall' && <HallOfFame openModal={setModal} navigate={navigate}/>} 
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
      setMessages([...next,{role:'model',content:data.answer}]);
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
  <section className="section showcase"><div className="portal-large"><div className="portal-ring"/><span>WORLD GATE</span><b>HORIZON</b><i>ANIGAME → MANY WORLDS</i></div><div><span className="eyebrow">03 / ALWAYS MOVING</span><h2>Something is always <em>on the horizon.</em></h2><p>Events give the community reasons to come back. Games give people something to do. The Hall of Fame makes the history worth keeping.</p><div className="quick-links"><button onClick={()=>navigate('events')}><CalendarDays/> Upcoming events <ArrowRight/></button><button onClick={()=>navigate('hall')}><Crown/> Hall of Fame <ArrowRight/></button></div></div></section>
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
  <div className="community-banner"><div><span className="eyebrow">THE FOUNDATION</span><h2>Built for growth, not just traffic.</h2><p>The site is structured so future systems—Discord roles, member profiles, event registration, games and Horizon AI—can plug into the same experience.</p></div><button className="btn primary" onClick={()=>navigate('events')}>See what’s happening <ArrowRight/></button></div>
</section>}

function Events({filters,filter,setFilter,events,search,setSearch,searchResults,openModal,navigate}){return <section className="page-shell"><PageHero eyebrow="EVENTS" title={<>THE HORIZON<br/><em>AWAITS.</em></>} text="Tournaments, community challenges, game nights, creative competitions and more. Find your next event." actions={<><button className="btn primary" onClick={()=>document.getElementById('upcoming')?.scrollIntoView({behavior:'smooth'})}>View upcoming events <ArrowRight/></button><button className="btn secondary" onClick={()=>setFilter('ALL')}>Explore all</button></>}/>
  <section className="featured-event"><div className="featured-visual"><div className="event-sigil"><Trophy/></div><span>FEATURED EVENT</span><b>FC</b></div><div><span className="eyebrow">CREATIVE • THURSDAY • 7:00 PM IST</span><h2>Fictional Character Tournament</h2><p>Create an original fictional character and compete on creativity, presentation, concept and execution.</p><div className="event-meta"><span><Clock3/> Thursday • 7:00 PM IST</span><span><Users/> Registration system ready</span></div><button className="btn primary" onClick={()=>openModal(eventData[0])}>View event <ArrowRight/></button></div></section>
  <section className="section inner-section" id="upcoming"><div className="section-heading"><div><span className="eyebrow">UPCOMING EVENTS</span><h2>Choose your event.</h2></div><div className="search"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search events"/></div></div>
    <div className="filters">{filters.map(f=><button key={f} className={filter===f?'selected':''} onClick={()=>setFilter(f)}>{f}</button>)}</div>
    <div className="event-grid">{events.filter(e=>e.status!=='PAST').map(e=><EventCard key={e.id} event={e} onClick={()=>openModal(e)}/>)}</div>
    {events.filter(e=>e.status!=='PAST').length===0&&<Empty text="No events match that filter yet."/>}
  </section>
  <section className="section inner-section archive-section"><div className="section-heading"><div><span className="eyebrow">PAST EVENTS</span><h2>The archive.</h2></div><button className="text-link" onClick={()=>navigate('hall','archive')}>Open Hall of Fame <ArrowRight/></button></div><div className="archive-row">{eventData.filter(e=>e.status==='PAST').map(e=><EventCard key={e.id} event={e} compact onClick={()=>openModal(e)}/>)}</div></section>
  <section className="host-panel"><Plus/><div><span className="eyebrow">HAVE AN IDEA?</span><h3>Host or submit an event</h3><p>Phase 1 provides the interface. Registration and staff workflows can be connected to Discord in the next backend pass.</p></div><button className="btn secondary" onClick={()=>openModal({title:'Event submission',category:'COMMUNITY',description:'Tell the staff what you want to host. The full submission form will be connected after Discord authentication is live.',rules:['Event name','Proposed date/time','Game or activity','Rules and participant requirements']})}>Submit an idea</button></section>
</section>}

function Games({filters,filter,setFilter,games,openModal}){return <section className="page-shell"><PageHero eyebrow="GAMES" title={<>ENTER THE<br/><em>PLAYGROUND.</em></>} text="From competitive battles to casual games with friends, Log Horizon is expanding beyond a single world." actions={<button className="btn primary" onClick={()=>setFilter('ALL')}>Explore games <ArrowRight/></button>}/>
  <section className="featured-game"><div><span className="eyebrow">FEATURED • COMMUNITY GAME</span><h2>Horizon Arena</h2><p>A small competitive arena built for Log Horizon members. It is a placeholder for the community's future game systems.</p><span className="status-pill">COMING SOON</span></div><div className="arena-visual"><div className="arena-ring"/><span>LH://ARENA</span></div></section>
  <section className="section inner-section"><div className="section-heading"><div><span className="eyebrow">COMMUNITY GAMES</span><h2>Pick a world.</h2></div></div><div className="filters">{filters.map(f=><button key={f} className={filter===f?'selected':''} onClick={()=>setFilter(f)}>{f}</button>)}</div><div className="game-grid">{games.map(g=><GameCard key={g.id} game={g} onClick={()=>openModal(g)}/>)}</div></section>
  <section className="section leaderboard"><div className="section-heading"><div><span className="eyebrow">COMMUNITY LEADERBOARD</span><h2>Names worth remembering.</h2></div><span className="status-pill">SYSTEM COMING SOON</span></div><div className="leader-table"><div className="leader-head"><span>PLAYER</span><span>SCORE</span><span>STATUS</span></div>{['Community leaderboard','Competitive records','Event achievements','Game scores'].map((x,i)=><div className="leader-row" key={x}><span><span className="rank-box">0{i+1}</span>{x}</span><span>—</span><span>AWAITING DATA</span></div>)}</div></section>
</section>}

function HallOfFame({openModal,navigate}){return <section className="page-shell"><PageHero eyebrow="HORIZON ARCHIVE" title={<>HALL OF<br/><em>FAME.</em></>} text="Those who made their mark on Log Horizon. Tournament records, champions and achievements preserved for the community." actions={<button className="btn primary" onClick={()=>document.getElementById('archive')?.scrollIntoView({behavior:'smooth'})}>Open the archive <ArrowRight/></button>}/>
  <section className="champion-feature"><div className="crown-stage"><div className="archive-ring"/><Crown size={56}/><span>1ST PLACE</span></div><div><span className="eyebrow">CURRENT CHAMPION RECORD</span><h2>Champion to be recorded.</h2><p>The Hall of Fame is live, but names are intentionally left blank until official tournament results are entered.</p><div className="achievement-row"><span><Crown/> TOURNAMENT WINNER</span><span><Medal/> HALL OF FAME MEMBER</span></div></div></section>
  <section className="section inner-section" id="archive"><div className="section-heading"><div><span className="eyebrow">TOURNAMENT ARCHIVE</span><h2>Champions remembered.</h2></div><button className="text-link" onClick={()=>navigate('events')}>View events <ArrowRight/></button></div><div className="hof-table"><div className="hof-head"><span>TOURNAMENT</span><span>WINNER</span><span>PLACE</span><span>DATE</span></div>{champions.map(c=><div className="hof-row" key={c.tournament}><span>{c.tournament}</span><span>{c.winner}</span><span className="place"><Crown size={15}/>{c.place}</span><span>{c.date}</span></div>)}</div></section>
  <section className="section achievements"><div className="section-heading"><div><span className="eyebrow">ACHIEVEMENTS</span><h2>Earned, not assigned.</h2></div></div><div className="achievement-grid"><InfoCard icon={<Crown/>} title="First Champion" text="Awarded to the first official tournament winner."/><InfoCard icon={<Trophy/>} title="Tournament Winner" text="A permanent achievement for an official win."/><InfoCard icon={<Medal/>} title="2× Champion" text="Unlocked after two recorded tournament victories."/><InfoCard icon={<Sparkles/>} title="Event Legend" text="A future community achievement for standout participation."/></div></section>
</section>}

const fallbackAnimeData = [
  { title: 'One Piece', genres: ['Adventure', 'Action', 'Fantasy'], episodes: '1000+', year: '1999–', description: 'A huge pirate adventure built around friendship, exploration, freedom and an ever-expanding world.', tag: 'MASTERPIECE' },
  { title: 'Frieren', genres: ['Fantasy', 'Adventure', 'Drama'], episodes: '28+', year: '2023–', description: 'A quiet fantasy journey about time, friendship and what remains after the great adventure.', tag: 'MASTERPIECE' },
  { title: 'Fullmetal Alchemist: Brotherhood', genres: ['Action', 'Fantasy', 'Drama'], episodes: '64', year: '2009', description: 'Two brothers search for a way to restore what they lost after a forbidden alchemical experiment.', tag: 'MASTERPIECE' },
  { title: 'Hunter × Hunter (2011)', genres: ['Adventure', 'Action', 'Fantasy'], episodes: '148', year: '2011', description: 'A young hunter enters a dangerous world of exams, friendships, strategy and extraordinary abilities.', tag: 'ADVENTURE' },
  { title: 'Steins;Gate', genres: ['Sci-Fi', 'Thriller', 'Drama'], episodes: '24', year: '2011', description: 'A small group of friends discovers that experiments with time can have consequences far beyond their plans.', tag: 'SCI-FI' },
  { title: 'Code Geass', genres: ['Action', 'Strategy', 'Drama'], episodes: '50', year: '2006', description: 'Rebellion, strategy and supernatural power collide in a story of choices and consequences.', tag: 'STRATEGY' },
  { title: 'Vinland Saga', genres: ['Action', 'Historical', 'Drama'], episodes: '48+', year: '2019–', description: 'A character-driven historical saga exploring revenge, violence, purpose and the meaning of strength.', tag: 'DRAMA' },
  { title: 'Attack on Titan', genres: ['Action', 'Dark Fantasy', 'Mystery'], episodes: '89', year: '2013–2023', description: 'Humanity fights for survival while the truth behind its world slowly comes into focus.', tag: 'MYSTERY' },
  { title: 'Death Note', genres: ['Thriller', 'Mystery', 'Supernatural'], episodes: '37', year: '2006', description: 'A supernatural notebook turns a battle of ideals into a tense game of strategy and deduction.', tag: 'THRILLER' },
  { title: 'Mob Psycho 100', genres: ['Action', 'Comedy', 'Supernatural'], episodes: '37', year: '2016–2022', description: 'A powerful psychic tries to grow as a person while navigating spirits, school and absurd situations.', tag: 'ACTION' },
  { title: 'Re:Zero', genres: ['Fantasy', 'Isekai', 'Drama'], episodes: '50+', year: '2016–', description: 'A fantasy journey where returning from death forces its protagonist to confront impossible situations.', tag: 'ISEKAI' },
  { title: 'That Time I Got Reincarnated as a Slime', genres: ['Fantasy', 'Isekai', 'Adventure'], episodes: '70+', year: '2018–', description: 'A reincarnated slime builds a community and a growing nation in a fantasy world.', tag: 'ISEKAI' },
  { title: 'Mushoku Tensei', genres: ['Fantasy', 'Isekai', 'Adventure'], episodes: '48+', year: '2021–', description: 'A second chance at life becomes a long-form fantasy adventure focused on growth and world-building.', tag: 'ISEKAI' },
  { title: 'Made in Abyss', genres: ['Adventure', 'Fantasy', 'Mystery'], episodes: '25+', year: '2017–', description: 'An expedition into a mysterious abyss reveals beautiful places and increasingly dangerous secrets.', tag: 'MYSTERY' },
  { title: 'Kingdom', genres: ['Historical', 'Strategy', 'Action'], episodes: '150+', year: '2012–', description: 'Large-scale warfare and political strategy follow a young soldier during China’s Warring States period.', tag: 'STRATEGY' },
  { title: 'Violet Evergarden', genres: ['Drama', 'Romance'], episodes: '13+', year: '2018', description: 'A former soldier learns to understand emotions while helping others put their feelings into words.', tag: 'DRAMA' },
  { title: 'Summertime Rendering', genres: ['Mystery', 'Thriller', 'Supernatural'], episodes: '25', year: '2022', description: 'A return to a childhood island turns into a tightly constructed mystery involving loops and strange doubles.', tag: 'MYSTERY' },
  { title: 'Gintama', genres: ['Comedy', 'Action', 'Sci-Fi'], episodes: '350+', year: '2006–2018', description: 'Chaotic comedy, heartfelt character arcs and surprisingly serious battles share the same universe.', tag: 'COMEDY' },
  { title: 'The Apothecary Diaries', genres: ['Mystery', 'Drama', 'Historical'], episodes: '48+', year: '2023–', description: 'A sharp-minded apothecary investigates mysteries inside an imperial court.', tag: 'MYSTERY' },
  { title: 'Kaguya-sama: Love is War', genres: ['Romance', 'Comedy', 'School'], episodes: '37+', year: '2019–2022', description: 'Two brilliant students turn romance into an elaborate battle of pride, schemes and ridiculous mind games.', tag: 'ROMANCE' },
  { title: 'Konosuba', genres: ['Comedy', 'Fantasy', 'Isekai'], episodes: '30+', year: '2016–', description: 'An intentionally chaotic fantasy party tries to survive quests, monsters and each other.', tag: 'COMEDY' },
  { title: 'Haikyuu!!', genres: ['Sports', 'Drama', 'Comedy'], episodes: '85', year: '2014–2020', description: 'A determined volleyball player works with teammates and rivals to reach the top of the sport.', tag: 'SPORTS' },
  { title: '86', genres: ['Sci-Fi', 'Action', 'Drama'], episodes: '23', year: '2021', description: 'A military science-fiction story about discrimination, war and the people fighting beyond the supposedly safe zone.', tag: 'SCI-FI' },
  { title: 'Your Name', genres: ['Romance', 'Fantasy', 'Drama'], episodes: 'Movie', year: '2016', description: 'Two teenagers find their lives unexpectedly connected across distance, time and memory.', tag: 'MOVIE' },
  { title: 'A Silent Voice', genres: ['Drama', 'Romance'], episodes: 'Movie', year: '2016', description: 'A story of bullying, regret, communication and the difficult work of making amends.', tag: 'MOVIE' }
];


const ANILIST_ENDPOINT = 'https://graphql.anilist.co';
const ANILIST_QUERY = `
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { hasNextPage currentPage perPage }
    media(
      type: ANIME
      isAdult: false
      sort: [POPULARITY_DESC]
    ) {
      id
      title { romaji english native }
      description(asHtml: false)
      episodes
      status
      averageScore
      genres
      format
      coverImage { large extraLarge }
      bannerImage
      startDate { year month day }
    }
  }
}`;

async function fetchAniListPage(page, perPage = 50) {
  const response = await fetch(ANILIST_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ query: ANILIST_QUERY, variables: { page, perPage } })
  });
  if (!response.ok) throw new Error(`AniList request failed: ${response.status}`);
  const payload = await response.json();
  if (payload.errors?.length) throw new Error(payload.errors[0].message || 'AniList error');
  return payload.data.Page;
}

function mapAniListAnime(item) {
  const title = item.title?.english || item.title?.romaji || item.title?.native || 'Unknown Anime';
  const year = item.startDate?.year ? String(item.startDate.year) : 'TBA';
  const description = (item.description || 'No community description available yet.')
    .replace(/<[^>]*>/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  return {
    id: item.id,
    title,
    genres: item.genres || [],
    episodes: item.episodes || item.format || '—',
    year,
    description: description || 'No description available yet.',
    tag: item.format || 'ANIME',
    score: item.averageScore || null,
    status: item.status || '',
    cover: item.coverImage?.extraLarge || item.coverImage?.large || '',
    banner: item.bannerImage || ''
  };
}


function AnimePage() {
  const [loading, setLoading] = useState(true);
  const [scene] = useState(() => randomScene('anime'));
  const [notice, setNotice] = useState('');
  const [animeData, setAnimeData] = useState(fallbackAnimeData);
  const [animeLoading, setAnimeLoading] = useState(true);
  const [animeSource, setAnimeSource] = useState('community fallback');
  const [visibleAnimeCount, setVisibleAnimeCount] = useState(40);
  const [animeSearch, setAnimeSearch] = useState('');
  const [animeGenre, setAnimeGenre] = useState('ALL');
  const [selectedAnime, setSelectedAnime] = useState(null);
  const [watchlist, setWatchlist] = useState(() => {
    try { return JSON.parse(localStorage.getItem('lh-anime-watchlist') || '[]'); } catch { return []; }
  });

  useEffect(() => { const t = setTimeout(() => setLoading(false), 850); return () => clearTimeout(t); }, []);
  useEffect(() => { localStorage.setItem('lh-anime-watchlist', JSON.stringify(watchlist)); }, [watchlist]);
  useEffect(() => {
    let cancelled = false;
    const cacheKey = 'lh-anilist-popular-v1';
    const cacheTTL = 12 * 60 * 60 * 1000;
    try {
      const cached = JSON.parse(localStorage.getItem(cacheKey) || 'null');
      if (cached?.savedAt && Date.now() - cached.savedAt < cacheTTL && Array.isArray(cached.items) && cached.items.length >= 100) {
        setAnimeData(cached.items); setAnimeSource('AniList live archive • cached'); setAnimeLoading(false);
        return () => { cancelled = true; };
      }
    } catch {}
    (async () => {
      try {
        const pages = [];
        for (let page = 1; page <= 10; page += 1) {
          const result = await fetchAniListPage(page, 50);
          pages.push(...result.media.map(mapAniListAnime));
          if (!result.pageInfo.hasNextPage) break;
          await new Promise(resolve => setTimeout(resolve, 120));
        }
        const unique = Array.from(new Map(pages.map(item => [item.id, item])).values());
        if (!cancelled && unique.length) {
          setAnimeData(unique); setAnimeSource(`AniList live archive • ${unique.length}+ indexed`);
          try { localStorage.setItem(cacheKey, JSON.stringify({ savedAt: Date.now(), items: unique })); } catch {}
        }
      } catch (error) { console.warn('AniList archive unavailable; using bundled fallback.', error); if (!cancelled) setAnimeSource('Bundled community archive'); }
      finally { if (!cancelled) setAnimeLoading(false); }
    })();
    return () => { cancelled = true; };
  }, []);

  const animeGenres = useMemo(() => ['ALL', ...Array.from(new Set(animeData.flatMap(a => a.genres || []))).filter(Boolean).sort((a,b) => a.localeCompare(b))], [animeData]);
  const filteredAnime = useMemo(() => {
    const q = animeSearch.trim().toLowerCase();
    return animeData.filter(a => {
      const matchesSearch = !q || [a.title, ...a.genres, a.tag].join(' ').toLowerCase().includes(q);
      const matchesGenre = animeGenre === 'ALL' || a.genres.some(g => g.toUpperCase() === animeGenre);
      return matchesSearch && matchesGenre;
    });
  }, [animeSearch, animeGenre, animeData]);
  useEffect(() => { setVisibleAnimeCount(40); }, [animeSearch, animeGenre]);
  const toggleWatchlist = (title) => {
    setWatchlist(current => current.includes(title) ? current.filter(x => x !== title) : [...current, title]);
    setNotice(watchlist.includes(title) ? `${title} removed from your watchlist.` : `${title} added to your watchlist.`);
  };

  if (loading) return <LoadingScreen scene={scene} onDone={() => setLoading(false)} />;
  return <div className="app">
    <div className="ambient ambient-cyan" /><div className="ambient ambient-violet" /><div className="grid" />
    <header className="header">
      <a className="brand" href="/" aria-label="Go to Log Horizon home"><span className="brand-mark">LH</span><span>LOG <b>HORIZON</b></span></a>
      <nav className="nav open" aria-label="Main navigation">
        <a href="/">Home</a><a href="/#community">Community</a><a className="active" href="/anime">Anime</a><a href="/#events">Events</a><a href="/#games">Games</a><a href="/#horizon-ai">Horizon AI</a>
      </nav>
      <a className="discord-login" href="/api/site/auth-login"><MessageCircle size={17} /> Continue with Discord</a>
    </header>
    <main>
      <section className="section anime-section anime-page-section" id="anime">
        <div className="anime-hero-copy"><span className="eyebrow">ANIME ARCHIVE / LOG HORIZON</span><h1>Find your next<br /><em>world to enter.</em></h1><p>A searchable community archive with hundreds of anime titles, genre filters, details, and a personal watchlist.</p><div className="page-back"><a className="text-link" href="/"><ArrowRight size={17} style={{transform:'rotate(180deg)'}} /> Return to Log Horizon</a></div></div>
        <div className="anime-console"><div className="console-top"><span><i /> ARCHIVE ONLINE</span><small>{animeLoading ? 'SYNCING ANIME INDEX…' : `${animeData.length}+ TITLES INDEXED`}</small></div><div className="console-stats"><div><strong>{watchlist.length}</strong><span>MY WATCHLIST</span></div><div><strong>{animeGenres.length - 1}</strong><span>GENRE FILTERS</span></div><div><strong>500+</strong><span>POPULAR TITLES</span></div></div></div>
        <div className="anime-library" id="anime-library">
          <div className="library-toolbar"><div className="search-box"><Search size={17} /><input value={animeSearch} onChange={e => setAnimeSearch(e.target.value)} placeholder="Search anime, genre or tag…" aria-label="Search anime" /></div><div className="genre-strip">{animeGenres.map(g => <button key={g} className={animeGenre === g ? 'selected' : ''} onClick={() => setAnimeGenre(g)}>{g}</button>)}</div></div>
          <div className="library-meta"><span>{filteredAnime.length} result{filteredAnime.length === 1 ? '' : 's'} • {animeSource}</span>{watchlist.length > 0 && <button onClick={() => { setAnimeSearch(''); setAnimeGenre('ALL'); }}>Showing {watchlist.length} saved title{watchlist.length === 1 ? '' : 's'}</button>}</div>
          <div className="anime-grid">{filteredAnime.slice(0, visibleAnimeCount).map(anime => <AnimeCard key={anime.id || anime.title} anime={anime} saved={watchlist.includes(anime.title)} onSave={() => toggleWatchlist(anime.title)} onOpen={() => setSelectedAnime(anime)} />)}</div>
          {filteredAnime.length > visibleAnimeCount && <div className="archive-more"><button className="btn secondary" onClick={() => setVisibleAnimeCount(count => count + 40)}>Load 40 more anime <ArrowRight size={17}/></button><span>Showing {Math.min(visibleAnimeCount, filteredAnime.length)} of {filteredAnime.length}</span></div>}
          {filteredAnime.length === 0 && <div className="empty-state"><Sparkles size={22} /><h3>Nothing found in this sector.</h3><p>Try another title or clear the genre filter.</p><button className="text-link" onClick={() => {setAnimeSearch('');setAnimeGenre('ALL');}}>Reset archive <ArrowRight size={16}/></button></div>}
        </div>
      </section>
    </main>
    <footer><div className="brand-static"><span className="brand-mark">LH</span><span>LOG <b>HORIZON</b></span></div><span>A community beyond the game.</span><span>ANIME ARCHIVE ONLINE</span></footer>
    {notice && <div className="toast"><span className="pulse-dot" />{notice}</div>}
    {selectedAnime && <AnimeModal anime={selectedAnime} saved={watchlist.includes(selectedAnime.title)} onSave={() => toggleWatchlist(selectedAnime.title)} onClose={() => setSelectedAnime(null)} />}
  </div>;
}


function AnimeCard({ anime, saved, onSave, onOpen }) {
  const initials = anime.title.replace(/[^A-Za-z0-9 ]/g, '').split(' ').filter(Boolean).slice(0,2).map(x => x[0]).join('');
  return <article className="anime-card"><button className="anime-art" onClick={onOpen} aria-label={`Open ${anime.title}`} style={anime.cover ? { backgroundImage: `linear-gradient(180deg, rgba(5,6,10,.02), rgba(5,6,10,.82)), url(\"${anime.cover}\")` } : undefined}><span>{!anime.cover && initials}</span><small>{anime.tag}</small></button><div className="anime-card-body"><div className="anime-title-row"><button className="anime-title" onClick={onOpen}>{anime.title}</button><button className={`save-btn ${saved ? 'saved' : ''}`} onClick={onSave} aria-label={saved ? `Remove ${anime.title} from watchlist` : `Save ${anime.title}`}><Heart size={16} fill={saved ? 'currentColor' : 'none'} /></button></div><div className="anime-tags">{anime.genres.slice(0,3).map(g => <span key={g}>{g}</span>)}</div><p>{anime.episodes} episodes • {anime.year}{anime.score ? ` • ${anime.score}%` : ''}</p><button className="card-link" onClick={onOpen}>View details <ArrowRight size={15}/></button></div></article>;
}


function AnimeModal({ anime, saved, onSave, onClose }) {
  return <div className="modal-backdrop" onClick={onClose}><div className="anime-modal" onClick={e => e.stopPropagation()} role="dialog" aria-modal="true" aria-label={`${anime.title} details`}><button className="modal-close" onClick={onClose} aria-label="Close"><X size={19}/></button><div className="modal-art" style={anime.cover ? { backgroundImage: `linear-gradient(180deg, rgba(5,6,10,.05), rgba(5,6,10,.82)), url(\"${anime.cover}\")` } : undefined}><span>{!anime.cover && anime.title.split(' ').slice(0,2).map(x => x[0]).join('')}</span><small>{anime.tag}</small></div><div className="modal-content"><span className="eyebrow">ARCHIVE ENTRY</span><h2>{anime.title}</h2><div className="modal-meta"><span><Star size={14}/> {anime.episodes}</span><span>{anime.year}</span>{anime.score && <span>Score {anime.score}%</span>}{anime.status && <span>{anime.status}</span>}{anime.genres.map(g => <span key={g}>{g}</span>)}</div><p>{anime.description}</p><div className="modal-actions"><button className={`btn ${saved ? 'secondary' : 'primary'}`} onClick={onSave}>{saved ? 'Remove from watchlist' : 'Add to watchlist'} <Heart size={16} fill={saved ? 'currentColor' : 'none'}/></button><button className="btn secondary" onClick={onClose}>Close archive</button></div><small className="modal-note">Community archive entry. This V1 does not host or stream copyrighted episodes.</small></div></div></div>;
}


function PageHero({eyebrow,title,text,actions}){return <section className="page-hero"><div className="page-hero-art"><div className="hero-orbit"/><div className="hero-orbit second"/></div><div className="page-hero-copy"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{text}</p>{actions&&<div className="hero-actions">{actions}</div>}</div></section>}
function Stat({n,t}){return <div><strong>{n}</strong><span>{t}</span></div>}
function Feature({icon,tag,title,text,special,onClick}){return <button className={`feature ${special?'special':''}`} onClick={onClick}><div className="feature-icon">{icon}</div><span className="eyebrow">{tag}</span><h3>{title}</h3><p>{text}</p><ArrowRight className="feature-arrow" size={19}/></button>}
function InfoCard({icon,title,text}){return <article className="info-card"><div className="info-icon">{icon}</div><h3>{title}</h3><p>{text}</p></article>}
function EventCard({event,onClick,compact}){return <article className={`event-card ${compact?'compact':''}`} onClick={onClick}><div className="card-top"><span className="eyebrow">{event.category}</span><span className="status-pill">{event.status}</span></div><div className="event-card-icon"><CalendarDays/></div><h3>{event.title}</h3><span className="card-sub">{event.sub} • {event.date}</span><p>{event.description}</p><button className="text-link">View event <ArrowRight size={15}/></button></article>}
function GameCard({game,onClick}){return <article className="game-card" onClick={onClick}><div className="game-art"><Gamepad2/><span>{game.status}</span></div><div className="card-top"><span className="eyebrow">{game.category.join(' • ')}</span></div><h3>{game.title}</h3><p>{game.text}</p><button className="text-link">{game.action} <ArrowRight size={15}/></button></article>}
function Empty({text}){return <div className="empty"><Filter size={18}/>{text}</div>}
function Modal({item,close,notify,session}){return <div className="modal-backdrop" onMouseDown={e=>e.target===e.currentTarget&&close()}><div className="modal"><button className="modal-close" onClick={close}><X/></button><span className="eyebrow">{item.category||'LOG HORIZON'}</span><h2>{item.title}</h2><p>{item.description||item.text}</p>{item.date&&<div className="modal-meta"><span><CalendarDays/>{item.date}</span><span><Users/>{item.participants}</span></div>}<h3>Details</h3><ul>{(item.rules||['This feature is ready for the next integration step.']).map((r,i)=><li key={i}>{r}</li>)}</ul><div className="modal-actions">{item.status!=='PAST'&&<button className="btn primary" onClick={()=>notify(session?'Registration flow ready for backend.':'Connect Discord to register for member events.')}>{session?'Register interest':'Continue with Discord'} <ArrowRight/></button>}<button className="btn secondary" onClick={close}>Close</button></div></div></div>}


createRoot(document.getElementById('root')).render(window.location.pathname.replace(/\/$/, '') === '/anime' ? <AnimePage /> : <App />);
