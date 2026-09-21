import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

import aiohttp
from aiohttp import web

log = logging.getLogger("horizon.dashboard")


class Dashboard:
    """Railway web service: health/API + the complete Log Horizon website."""
    def __init__(self, bot):
        self.bot = bot
        self.runner = None
        self.port = None
        self.base_dir = Path(__file__).resolve().parent
        self.site_dir = self.base_dir / "website"
        self.dist_dir = self.site_dir / "dist"
        self.rpg_art_cache = self.base_dir / "data" / "rpg_art_cache"
        self.rpg_art_tasks = {}
        self._rpg_style_reference_b64 = None

    async def start(self):
        app = web.Application(client_max_size=5 * 1024 * 1024)
        app.add_routes([
            web.get("/", self.website),
            web.get("/anime", self.website),
            web.get("/health", self.health),
            web.get("/api/overview", self.api_overview),
            web.get("/api/member", self.api_member),
            web.post("/api/ai", self.api_ai),
            web.get("/api/site/auth-login", self.site_auth_login),
            web.get("/api/site/auth-callback", self.site_auth_callback),
            web.get("/api/site/auth-callback/", self.site_auth_callback),
            web.get("/api/site/auth/callback", self.site_auth_callback),
            # Compatibility with the old Netlify callback path, so a stale Discord
            # OAuth redirect does not dead-end in a 404 after moving to Railway.
            web.get("/.netlify/functions/auth-callback", self.site_auth_callback),
            web.get("/.netlify/functions/auth-callback/", self.site_auth_callback),
            web.get("/auth/callback", self.site_auth_callback),
            web.get("/api/site/auth-me", self.site_auth_me),
            web.get("/api/site/auth-logout", self.site_auth_logout),
            web.route("*", "/api/site/horizon-ai", self.site_horizon_ai),
            web.get("/api/site/horizon-server", self.site_horizon_server),
            web.get("/api/rpg/art", self.rpg_art),
            web.get("/assets/{path:.*}", self.asset),
        ])

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        # Railway routes public traffic to the exact value of $PORT. Never
        # silently move to another port: doing so makes the service appear
        # healthy internally while Railway returns 502 externally.
        port_raw = os.getenv("PORT", "").strip()
        if not port_raw:
            port_raw = os.getenv("DASHBOARD_PORT", "8765").strip()
            print("WARNING: PORT is not set; using DASHBOARD_PORT/fallback. Public Railway networking requires PORT.")
        requested_port = int(port_raw)
        try:
            site = web.TCPSite(self.runner, "0.0.0.0", requested_port)
            await site.start()
            self.port = requested_port
            print(f"Dashboard listening on 0.0.0.0:{requested_port}; website={self.dist_dir}")
        except OSError as exc:
            self.port = None
            print(f"Dashboard failed to bind required port {requested_port}: {exc}")
            raise

    def _authorized(self, request):
        expected = os.getenv("HORIZON_API_TOKEN", "").strip()
        if not expected:
            return False
        return hmac.compare_digest(request.headers.get("X-Horizon-API-Key", ""), expected)

    def _base_url(self, request):
        configured = os.getenv("SITE_URL", "").strip().rstrip("/")
        if configured:
            return configured
        proto = request.headers.get("X-Forwarded-Proto", request.url.scheme)
        host = request.headers.get("X-Forwarded-Host", request.host)
        return f"{proto}://{host}"

    def _redirect_uri(self, request):
        configured = os.getenv("DISCORD_REDIRECT_URI", "").strip()
        return configured or f"{self._base_url(request)}/api/site/auth-callback"

    def _secret(self):
        return os.getenv("SESSION_SECRET", "").strip()

    def _sign(self, value):
        return hmac.new(self._secret().encode(), value.encode(), hashlib.sha256).digest()

    def _make_token(self, payload):
        body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
        sig = base64.urlsafe_b64encode(self._sign(body)).decode().rstrip("=")
        return f"{body}.{sig}"

    def _verify_token(self, token):
        if not token or not self._secret():
            return None
        try:
            body, signature = token.split(".", 1)
            expected = base64.urlsafe_b64encode(self._sign(body)).decode().rstrip("=")
            if not hmac.compare_digest(signature, expected):
                return None
            padded = body + "=" * (-len(body) % 4)
            return json.loads(base64.urlsafe_b64decode(padded).decode())
        except Exception:
            return None

    def _cookies(self, request):
        return {part.split("=", 1)[0].strip(): part.split("=", 1)[1].strip() for part in request.headers.get("Cookie", "").split("; ") if "=" in part}

    def _set_cookie(self, response, name, value, max_age, http_only=True):
        response.set_cookie(name, value, max_age=max_age, path="/", secure=True, httponly=http_only, samesite="Lax")

    def _session(self, request):
        return self._verify_token(self._cookies(request).get("lh_session", ""))

    async def _discord(self, path, **kwargs):
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request("GET", f"https://discord.com/api/v10{path}", **kwargs) as response:
                data = await response.json(content_type=None)
                if response.status >= 400:
                    raise RuntimeError(f"Discord API {response.status}")
                return data

    async def website(self, request):
        index = self.dist_dir / "index.html"
        if index.exists():
            return web.FileResponse(index)
        # The source is kept in the ZIP; Railway's build phase creates dist.
        return web.Response(status=503, text="Log Horizon website is still building. Please refresh shortly.", content_type="text/plain")

    async def asset(self, request):
        path = (self.dist_dir / "assets" / request.match_info["path"]).resolve()
        assets_root = (self.dist_dir / "assets").resolve()
        if not str(path).startswith(str(assets_root)) or not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path)

    async def _rpg_art_fallback(self, request):
        """Render deterministic, high-detail RPG art as PNG for Discord embeds.

        This is deliberately generated from the identity seed instead of using a
        random avatar service: the same hero/pet/mob/item always keeps the same
        visual identity while race/class/species/gear words change the design.
        """
        import hashlib
        import io
        import math
        import random
        from PIL import Image, ImageDraw, ImageFont, ImageFilter

        kind=request.query.get("kind","character").lower()
        seed=request.query.get("seed","unknown")
        bits=[x.strip().lower().replace("_"," ") for x in seed.split("|") if x.strip()]
        digest=hashlib.sha256(seed.encode()).digest()
        rng=random.Random(int.from_bytes(digest[:16],"big"))
        def pick(values,offset=0): return values[digest[offset % len(digest)] % len(values)]
        def clamp(v): return max(0,min(255,int(v)))
        def mix(a,b,t): return tuple(clamp(a[i]*(1-t)+b[i]*t) for i in range(3))

        W=1024; H=1024
        bg1=pick([(8,13,28),(18,10,32),(8,24,34),(32,18,10),(12,29,22)],0)
        bg2=pick([(20,39,68),(55,20,72),(11,64,74),(77,39,16),(20,66,46)],1)
        accent=pick([(80,210,255),(192,120,255),(255,170,54),(255,75,105),(61,225,171),(230,235,255)],2)
        accent2=pick([(124,90,255),(255,95,150),(62,230,220),(255,215,90),(110,255,140)],5)
        skin=pick([(246,205,180),(224,175,140),(188,122,88),(239,211,193),(139,90,68)],4)
        hair=pick([(12,18,30),(55,29,20),(125,40,17),(242,205,95),(225,229,238),(101,30,170),(178,35,65)],6)
        dark=(9,13,24); ink=(4,8,16); white=(245,247,252); muted=(178,190,212)

        # Gradient + subtle parchment/noise texture makes the art feel like a game card.
        im=Image.new("RGB",(W,H))
        px=im.load()
        for y in range(H):
            t=y/(H-1)
            base=mix(bg1,bg2,t)
            for x in range(W):
                radial=1.0-math.hypot(x-W*.5,y-H*.43)/(W*.72)
                c=tuple(clamp(base[i]+max(0,radial)*accent[i]*.08) for i in range(3))
                n=rng.randint(-3,3)
                px[x,y]=tuple(clamp(v+n) for v in c)
        im=im.convert("RGBA")
        glow=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow)
        for r,a in [(430,14),(330,22),(220,34),(120,45)]:
            gd.ellipse((W//2-r,455-r,W//2+r,455+r),fill=(*accent,a))
        glow=glow.filter(ImageFilter.GaussianBlur(32)); im=Image.alpha_composite(im,glow)
        d=ImageDraw.Draw(im)
        try:
            font=ImageFont.truetype("DejaVuSans-Bold.ttf",34)
            subfont=ImageFont.truetype("DejaVuSans.ttf",19)
            tiny=ImageFont.truetype("DejaVuSans.ttf",15)
            statfont=ImageFont.truetype("DejaVuSans-Bold.ttf",16)
        except Exception:
            font=subfont=tiny=statfont=None
        def txt(xy,text,f=font,fill=white,anchor=None): d.text(xy,text,font=f,fill=fill,anchor=anchor)
        def rounded(box,r,fill,outline=None,width=1): d.rounded_rectangle(box,r,fill=fill,outline=outline,width=width)
        def glow_line(points,fill,width=8,blur=14):
            layer=Image.new("RGBA",(W,H),(0,0,0,0)); ld=ImageDraw.Draw(layer); ld.line(points,fill=(*fill,120),width=width+16,joint="curve"); layer=layer.filter(ImageFilter.GaussianBlur(blur)); im.alpha_composite(layer); ImageDraw.Draw(im).line(points,fill=fill,width=width,joint="curve")
        def particle_field(count=90):
            for _ in range(count):
                x=rng.randint(30,W-30); y=rng.randint(100,H-120); r=rng.choice([1,1,2,2,3])
                col=accent if rng.random()<.7 else accent2
                d.ellipse((x-r,y-r,x+r,y+r),fill=(*col,rng.randint(70,190)))
        def frame(title,subtitle):
            rounded((24,24,W-24,H-24),28,fill=(3,7,15,65),outline=(*accent,120),width=2)
            rounded((42,42,W-42,118),18,fill=(4,8,17,175),outline=(*accent2,65),width=1)
            txt((66,62),title,font); txt((66,101),subtitle,subfont,muted)
            particle_field(70)
            # bottom stat plate
            rounded((42,H-112,W-42,H-42),18,fill=(4,8,17,190),outline=(*accent,75),width=1)

        if kind=="character":
            race=bits[0] if bits else "human"; cls=bits[2] if len(bits)>2 else "warrior"; sub=bits[3] if len(bits)>3 else ""; evo=bits[4] if len(bits)>4 else ""
            frame(f"{race.title()} {cls.title()}",f"{sub.title() or 'Adventurer'}  •  {evo.title() or 'Base Evolution'}  •  HERO IDENTITY")
            # Backplate sigil / magic circle.
            for rad in (275,250,225): d.ellipse((512-rad,555-rad,512+rad,555+rad),outline=(*accent,50),width=2)
            for ang in range(0,360,30):
                a=math.radians(ang); x1=512+250*math.cos(a); y1=555+250*math.sin(a); x2=512+275*math.cos(a); y2=555+275*math.sin(a); d.line((x1,y1,x2,y2),fill=(*accent2,80),width=3)
            # Silhouette / cloak.
            d.polygon([(350,475),(674,475),(760,800),(640,870),(384,870),(264,800)],fill=(8,14,27,230),outline=(*accent,170))
            # Race traits.
            if race in {"fae"}:
                d.polygon([(365,430),(145,250),(220,555),(395,500)],fill=(*accent,55),outline=(*accent,120))
                d.polygon([(659,430),(879,250),(804,555),(629,500)],fill=(*accent,55),outline=(*accent,120))
            if race in {"beastfolk","kitsune"}:
                pts=[(635,610),(820,675),(755,760),(670,725)]
                d.line(pts,fill=hair,width=42,joint="curve"); d.line(pts,fill=(*accent,130),width=5,joint="curve")
            if race=="dragonkin":
                d.polygon([(360,430),(285,285),(410,360)],fill=(skin),outline=(*accent,180)); d.polygon([(664,430),(739,285),(614,360)],fill=skin,outline=(*accent,180))
            if race in {"tiefling","vampire","dragonkin"}:
                d.polygon([(412,330),(375,235),(438,300)],fill=(213,205,199),outline=dark)
                d.polygon([(612,330),(649,235),(586,300)],fill=(213,205,199),outline=dark)
            # Legs + boots with highlights.
            d.polygon([(400,735),(500,735),(490,890),(420,890)],fill=(31,41,58),outline=(*accent2,160))
            d.polygon([(520,735),(620,735),(625,890),(555,890)],fill=(25,34,50),outline=(*accent2,160))
            d.rounded_rectangle((370,875,485,925),18,fill=(5,9,17),outline=(*accent,160),width=3)
            d.rounded_rectangle((545,875,660,925),18,fill=(5,9,17),outline=(*accent,160),width=3)
            # Torso armor with layered plates.
            torso=[(380,465),(644,465),(690,720),(512,775),(334,720)]
            d.polygon(torso,fill=(35,45,64),outline=(*accent,210),width=4)
            d.polygon([(392,490),(632,490),(653,615),(512,675),(371,615)],fill=(51,61,82),outline=(*accent2,140),width=3)
            d.polygon([(410,500),(512,470),(614,500),(585,570),(512,600),(439,570)],fill=(66,75,96),outline=(*accent,120))
            d.line((512,505,512,735),fill=(*accent,120),width=5)
            for x in (405,619): d.line((x,535,x+(-28 if x<500 else 28),690),fill=(*accent2,100),width=5)
            # Shoulder guards.
            d.pieslice((285,470,410,600),180,355,fill=(54,65,86),outline=(*accent,170),width=4)
            d.pieslice((614,470,739,600),185,360,fill=(54,65,86),outline=(*accent,170),width=4)
            # Neck.
            d.rectangle((470,380,554,480),fill=skin,outline=dark)
            # Head, jaw, hair.
            d.ellipse((372,215,652,485),fill=skin,outline=(*accent,180),width=4)
            d.pieslice((370,195,654,470),180,355,fill=hair)
            d.polygon([(390,290),(320,220),(365,375),(408,340)],fill=hair,outline=dark)
            d.polygon([(634,290),(704,220),(659,375),(616,340)],fill=hair,outline=dark)
            # Hair strands.
            for i in range(9):
                x=405+i*27; endx=x+rng.randint(-35,35); endy=rng.randint(170,250)
                d.line((x,280,endx,endy),fill=mix(hair,white,.18),width=rng.randint(4,8))
            # Eyes, brows, nose, mouth, facial highlight.
            eye_col=accent2 if race not in {"human","dwarf","golem"} else pick([(60,120,255),(80,220,190),(255,190,70),(235,90,120)],8)
            d.polygon([(425,332),(470,316),(480,335),(430,350)],fill=white)
            d.polygon([(545,335),(555,316),(600,332),(595,350)],fill=white)
            d.ellipse((443,323,467,346),fill=eye_col); d.ellipse((557,323,581,346),fill=eye_col)
            d.ellipse((450,328,461,339),fill=ink); d.ellipse((564,328,575,339),fill=ink)
            d.line((420,305,475,298),fill=dark,width=10); d.line((549,298,604,305),fill=dark,width=10)
            d.line((512,345,498,385,518,391),fill=(130,80,65),width=4)
            d.arc((475,390,550,430),0,180,fill=(105,35,50),width=5)
            d.ellipse((405,260,445,295),fill=(255,255,255,35)); d.ellipse((585,260,625,295),fill=(255,255,255,35))
            # Class weapon + class-specific magic.
            if any(x in cls for x in ("mage","cleric","druid","summoner","warlock","necromancer","bard")):
                d.line((720,810,785,245),fill=(197,162,115),width=18); d.ellipse((755,195,815,255),fill=accent,outline=white,width=3); glow_line([(785,195),(810,145),(770,105)],accent,width=5)
            elif "lancer" in cls:
                d.line((725,830,835,190),fill=(198,171,128),width=17); d.polygon([(835,145),(806,225),(864,225)],fill=accent,outline=white); d.line((760,620,820,555),fill=accent2,width=7)
            elif "ranger" in cls:
                d.arc((675,245,905,700),65,300,fill=(205,170,110),width=15); d.line((790,245,790,700),fill=white,width=5); glow_line([(790,360),(880,300)],accent,width=4)
            elif "engineer" in cls:
                rounded((690,390,900,475),18,fill=(83,95,112),outline=accent,width=4); d.ellipse((835,405,875,445),fill=accent); d.rectangle((760,475,825,585),fill=(52,61,75),outline=accent2,width=3); glow_line([(875,430),(935,360)],accent,width=4)
            elif "rogue" in cls or "assassin" in cls:
                d.polygon([(720,470),(930,350),(912,405),(730,500)],fill=(226,235,250),outline=accent,width=3); d.polygon([(700,560),(885,450),(868,500),(710,590)],fill=(226,235,250),outline=accent2,width=3)
            else:
                d.polygon([(750,190),(825,430),(770,690),(700,430)],fill=(225,232,244),outline=accent,width=4); d.rectangle((715,410,830,450),fill=(177,120,70),outline=dark,width=3)
            # Magical motes / sparks around weapon.
            for _ in range(28):
                x=rng.randint(170,900); y=rng.randint(170,860); rr=rng.choice([2,3,4]); d.ellipse((x-rr,y-rr,x+rr,y+rr),fill=(*accent,rng.randint(80,220)))
            txt((66,H-91),f"RACE  {race.upper()}",statfont,accent)
            txt((300,H-91),f"CLASS  {cls.upper()}",statfont,accent2)
            txt((560,H-91),f"PATH  {(sub or 'ADVENTURER').upper()}",statfont,white)
            txt((66,H-62),"Stable visual identity • generated from character progression",tiny,muted)

        elif kind=="pet":
            species=bits[0] if bits else "companion"; ability=bits[2] if len(bits)>2 else "companion"; level=bits[1] if len(bits)>1 else "1"
            frame(f"{species.title()} Companion",f"Level {level}  •  {ability.title()}  •  COMPANION IDENTITY")
            # Ground shadow and aura.
            d.ellipse((220,790,804,900),fill=(0,0,0,110))
            d.ellipse((235,250,789,800),outline=(*accent,90),width=5)
            archetype=species
            if any(x in species for x in ("dragon","drake")): archetype="dragon"
            elif any(x in species for x in ("wolf","hound")): archetype="wolf"
            elif any(x in species for x in ("fox","kitsune")): archetype="fox"
            elif "cat" in species: archetype="feline"
            elif any(x in species for x in ("hawk","bird","falcon")): archetype="avian"
            elif any(x in species for x in ("bear",)): archetype="bear"
            elif any(x in species for x in ("spirit","slime","wraith")): archetype="spirit"
            body=pick([(80,100,130),(112,75,90),(58,105,94),(125,95,55),(90,78,135)],11)
            hi=mix(body,white,.28)
            if archetype=="dragon":
                d.ellipse((300,330,720,690),fill=body,outline=accent,width=6); d.polygon([(340,390),(220,220),(390,300)],fill=body,outline=accent); d.polygon([(680,390),(800,220),(630,300)],fill=body,outline=accent)
                d.polygon([(355,560),(220,700),(405,650)],fill=hi,outline=accent2); d.polygon([(669,560),(804,700),(619,650)],fill=hi,outline=accent2)
                d.polygon([(375,650),(280,825),(430,760),(512,835),(594,760),(744,825),(649,650)],fill=body,outline=accent,width=5)
                d.polygon([(400,610),(512,690),(624,610),(575,720),(512,750),(449,720)],fill=skin,outline=accent2)
                d.polygon([(380,420),(430,360),(475,420)],fill=accent); d.polygon([(549,420),(594,360),(644,420)],fill=accent)
            elif archetype in {"wolf","fox","feline","bear"}:
                d.ellipse((295,330,730,690),fill=body,outline=accent,width=6)
                earfill=body
                d.polygon([(350,405),(260,210),(430,320)],fill=earfill,outline=accent,width=5); d.polygon([(674,405),(764,210),(594,320)],fill=earfill,outline=accent,width=5)
                if archetype=="fox": d.polygon([(330,270),(390,320),(350,390)],fill=(255,170,90)); d.polygon([(694,270),(634,320),(674,390)],fill=(255,170,90))
                d.ellipse((365,455,430,520),fill=accent2); d.ellipse((595,455,660,520),fill=accent2); d.ellipse((390,478,416,504),fill=ink); d.ellipse((610,478,636,504),fill=ink)
                d.polygon([(445,565),(512,610),(579,565),(560,655),(512,690),(464,655)],fill=skin,outline=accent2,width=4)
                d.arc((430,600,594,730),0,180,fill=ink,width=12)
                # paws/claws
                for x in (345,610):
                    d.ellipse((x,650,x+85,815),fill=body,outline=accent,width=5)
                    for j in range(3): d.line((x+20+j*22,770,x+8+j*22,805),fill=white,width=4)
                d.line((680,650,850,790),fill=body,width=48); d.line((690,650,850,790),fill=accent2,width=5)
            elif archetype=="avian":
                d.ellipse((330,350,690,700),fill=body,outline=accent,width=6); d.polygon([(360,470),(120,300),(300,610)],fill=body,outline=accent); d.polygon([(664,470),(904,300),(724,610)],fill=body,outline=accent)
                d.polygon([(480,500),(512,545),(544,500),(530,570),(494,570)],fill=(255,195,70),outline=dark)
                d.ellipse((420,440,455,475),fill=white); d.ellipse((569,440,604,475),fill=white); d.ellipse((430,450,448,468),fill=ink); d.ellipse((576,450,594,468),fill=ink)
                for i in range(6): d.polygon([(390+i*45,610),(410+i*45,780),(430+i*45,610)],fill=hi,outline=accent2)
            else: # spirit / unusual
                d.ellipse((290,290,735,800),fill=(*accent,45),outline=accent,width=7)
                for i in range(7):
                    x=350+i*48; y=420+int(math.sin(i)*35); d.ellipse((x,y,x+70,y+70),fill=(*accent2,130))
                d.ellipse((405,445,455,495),fill=white); d.ellipse((570,445,620,495),fill=white); d.ellipse((423,462,440,479),fill=ink); d.ellipse((587,462,604,479),fill=ink)
            # Ability rune and companion badge.
            rounded((70,730,330,840),18,fill=(4,8,17,190),outline=(*accent,100),width=2)
            txt((92,755),"ABILITY",statfont,accent); txt((92,782),ability.title()[:22],subfont,white)
            txt((66,H-91),f"SPECIES  {species.upper()}",statfont,accent)
            txt((370,H-91),f"LEVEL  {str(level).upper()}",statfont,accent2)
            txt((66,H-62),"Stable companion identity • species, ability and level shape the render",tiny,muted)

        elif kind=="mob":
            name=bits[0] if bits else "monster"; level=bits[1] if len(bits)>1 else "?"; region=bits[2] if len(bits)>2 else "wild"; element=bits[3] if len(bits)>3 else "arcane"; role=bits[4] if len(bits)>4 else "beast"
            frame(name.title(),f"Lv {level}  •  {region.title()}  •  {element.title()}  •  {role.title()} MOB")
            archetype=pick(["beast","undead","construct","elemental","demon","insect","humanoid"],14)
            body=pick([(88,42,52),(50,70,95),(54,92,72),(90,76,45),(73,49,101),(102,53,35)],15)
            eye=pick([(255,72,72),(255,190,60),(180,90,255),(40,225,235),(145,235,80)],16)
            d.ellipse((200,250,824,860),fill=(0,0,0,90))
            d.ellipse((210,200,814,820),outline=(*eye,75),width=8)
            # Main monster body with asymmetry for a more creature-like silhouette.
            d.polygon([(330,760),(235,550),(270,320),(390,220),(640,240),(755,365),(790,600),(690,785),(560,850),(420,840)],fill=body,outline=(*accent,210),width=7)
            if archetype in {"beast","demon","insect"}:
                d.polygon([(330,360),(170,185),(305,260)],fill=body,outline=accent,width=6); d.polygon([(694,360),(854,185),(719,260)],fill=body,outline=accent,width=6)
            if archetype=="undead":
                for i in range(7):
                    x=310+i*62; d.line((x,380,x+(-20 if i%2 else 20),720),fill=(210,215,225),width=5)
            if archetype=="construct":
                for x,y in [(330,390),(650,420),(370,610),(620,640)]: d.rectangle((x,y,x+80,y+70),fill=(100,110,125),outline=accent2,width=4)
            if archetype=="elemental":
                for i in range(16):
                    x=rng.randint(280,740); y=rng.randint(300,780); rr=rng.randint(8,24); d.ellipse((x-rr,y-rr,x+rr,y+rr),fill=(*accent,rng.randint(90,190)))
            # Face.
            d.polygon([(335,470),(430,425),(470,470),(430,515)],fill=eye); d.polygon([(554,470),(594,425),(689,470),(594,515)],fill=eye)
            d.ellipse((390,455,430,495),fill=ink); d.ellipse((594,455,634,495),fill=ink)
            d.polygon([(425,590),(512,650),(600,590),(570,700),(512,750),(455,700)],fill=(25,16,24),outline=accent2,width=4)
            for x in range(460,570,22): d.polygon([(x,650),(x+10,690),(x+20,650)],fill=white)
            # Element core + weapon-like appendage depending on role.
            d.ellipse((455,530,569,644),fill=(*accent,80),outline=accent2,width=5)
            if role in {"champion","guardian","knight"}:
                d.line((690,750,900,250),fill=(190,165,120),width=22); d.polygon([(900,205),(872,300),(928,300)],fill=eye,outline=white)
            elif role in {"caster","mage","support"}:
                glow_line([(690,720),(830,330),(760,250)],accent,width=7); d.ellipse((735,220,800,285),fill=accent2,outline=white,width=3)
            else:
                d.line((690,650,875,800),fill=body,width=58); d.line((700,650,875,800),fill=accent,width=5)
            txt((66,H-91),f"TYPE  {archetype.upper()}",statfont,accent)
            txt((300,H-91),f"ELEMENT  {element.upper()}",statfont,accent2)
            txt((570,H-91),f"ROLE  {role.upper()}",statfont,white)
            txt((66,H-62),"Persistent enemy identity • region, role and element shape the design",tiny,muted)

        else:  # item / gear art
            key=" ".join(bits) if bits else "mystery item"
            lower=key.lower()
            rarity=pick(["common","uncommon","rare","epic","legendary","mythic"],17)
            rarity_colors={"common":(180,190,205),"uncommon":(90,220,150),"rare":(90,170,255),"epic":(190,105,255),"legendary":(255,170,55),"mythic":(255,90,130)}
            rc=rarity_colors[rarity]
            frame(key.title(),f"{rarity.title()}  •  crafted relic render  •  ITEM IDENTITY")
            d.ellipse((210,190,814,800),fill=(*rc,18),outline=(*rc,130),width=5)
            # Detect broad equipment family from generated item names.
            if any(x in lower for x in ("armor","robe","cloak","mail","plate","leather","scale","garb")):
                # Chest armor / robe.
                d.polygon([(390,260),(512,205),(634,260),(690,430),(620,730),(404,730),(334,430)],fill=(48,56,76),outline=rc,width=7)
                d.polygon([(405,290),(512,245),(619,290),(590,390),(512,440),(434,390)],fill=mix((48,56,76),white,.15),outline=(*rc,160))
                for y in range(390,680,52): d.line((390,y,634,y),fill=(*rc,70),width=4)
                d.line((512,255,512,710),fill=(*rc,150),width=6)
                for x in (410,614): d.ellipse((x,300,x+50,350),fill=(*accent,90),outline=rc,width=3)
            elif any(x in lower for x in ("shield",)):
                d.polygon([(512,210),(760,315),(710,640),(512,820),(314,640),(264,315)],fill=(48,58,78),outline=rc,width=8)
                d.polygon([(512,270),(685,345),(648,590),(512,735),(376,590),(339,345)],fill=(65,77,99),outline=accent,width=5)
                d.ellipse((460,430,564,534),fill=(*accent,85),outline=rc,width=5); d.line((512,330,512,635),fill=rc,width=7); d.line((410,480,614,480),fill=rc,width=7)
            elif any(x in lower for x in ("bow",)):
                d.arc((260,180,780,840),70,290,fill=(190,145,95),width=24); d.line((512,230,512,790),fill=white,width=5); glow_line([(512,300),(720,420)],rc,width=5)
            elif any(x in lower for x in ("staff","wand")):
                d.line((512,820,512,260),fill=(188,140,85),width=24); d.ellipse((448,170,576,298),fill=rc,outline=white,width=5); d.ellipse((475,197,549,271),fill=(*accent2,150))
            elif any(x in lower for x in ("ring","amulet","necklace")):
                d.ellipse((300,280,724,704),outline=rc,width=44); d.ellipse((365,345,659,639),outline=accent,width=12); d.polygon([(512,265),(585,405),(512,535),(439,405)],fill=rc,outline=white)
            else:
                # Blade / relic silhouette for weapons and unknown gear.
                d.polygon([(512,160),(650,500),(565,720),(512,820),(459,720),(374,500)],fill=(222,229,240),outline=rc,width=7)
                d.line((512,190,512,735),fill=accent,width=7)
                d.rectangle((450,710,574,770),fill=(160,104,60),outline=rc,width=4)
                d.ellipse((430,740,594,900),fill=(72,50,36),outline=accent,width=5)
            # Rarity shards.
            for i in range({"common":1,"uncommon":2,"rare":3,"epic":4,"legendary":5,"mythic":6}[rarity]):
                a=math.radians(210+i*25); x=512+340*math.cos(a); y=520+340*math.sin(a); d.polygon([(x,y-16),(x+12,y),(x,y+16),(x-12,y)],fill=rc)
            txt((66,H-91),f"RARITY  {rarity.upper()}",statfont,rc)
            txt((360,H-91),"TRADEABLE GEAR",statfont,accent)
            txt((66,H-62),"Stable item identity • generated from the item's name and type",tiny,muted)

        out=io.BytesIO(); im.convert("RGB").save(out,format="PNG",optimize=True)
        return web.Response(body=out.getvalue(),content_type="image/png",headers={"Cache-Control":"public, max-age=86400"})

    def _rpg_art_cache_key(self, kind, seed):
        return hashlib.sha256(f"v5|{kind}|{seed}".encode("utf-8")).hexdigest()

    def _rpg_art_labels(self, kind, seed):
        bits=[x.strip().replace("_", " ") for x in seed.split("|") if x.strip()]
        if kind == "character":
            return {
                "name": bits[0].title() if bits else "Horizon Hero",
                "race": bits[0].title() if bits else "Human",
                "class_name": bits[2].title() if len(bits)>2 else "Warrior",
                "path": bits[3].title() if len(bits)>3 else "Adventurer",
                "evolution": bits[4].title() if len(bits)>4 else "Base Evolution",
            }
        if kind == "pet":
            return {"name": bits[0].title() if bits else "Companion", "level": bits[1] if len(bits)>1 else "1", "ability": bits[2].title() if len(bits)>2 else "Companion Bond", "rarity": bits[3].title() if len(bits)>3 else "Rare"}
        if kind == "mob":
            return {"name": bits[0].title() if bits else "World Enemy", "level": bits[1] if len(bits)>1 else "?", "region": bits[2].title() if len(bits)>2 else "Wilds", "element": bits[3].title() if len(bits)>3 else "Arcane", "role": bits[4].title() if len(bits)>4 else "Beast", "type": bits[5].title() if len(bits)>5 else "Monster"}
        return {"name": " ".join(bits).title() if bits else "Mystery Relic", "rarity": "Legendary"}

    def _rpg_art_prompt(self, kind, labels):
        # The supplied reference is used only for broad visual presentation.
        # The generated subject, pose, setting and details are always original.
        style=(
            "dark fantasy MMORPG gameplay key art, cinematic painterly digital illustration, "
            "semi-realistic anime-fantasy character design, extremely detailed materials and textures, "
            "dramatic rim lighting, volumetric fog, atmospheric depth, rich environment storytelling, "
            "dynamic composition, realistic anatomy, detailed face and eyes, detailed hair/fur, layered "
            "armor and cloth, glowing magic particles, subtle film grain, high-end game concept art, "
            "16:9 widescreen composition, premium RPG promotional artwork."
        )
        avoid=(
            "No text, no title, no logo, no watermark, no UI, no game menu, no random avatar, no flat vector art, "
            "no simple geometric shapes, no chibi style, no blank background, no close-up floating head."
        )
        if kind == "character":
            return (
                f"Create original {style} Show a full-body hero in a dramatic gameplay scene. "
                f"Identity: race {labels['race']}, class {labels['class_name']}, path/subclass {labels['path']}, "
                f"evolution {labels['evolution']}. Give the race unmistakable physical traits, the class a distinctive "
                "signature weapon, believable layered equipment, class-specific magic, and a visually coherent silhouette. "
                "Place the hero in a location that matches the class and race, with foreground particles and a deep "
                "background containing ruins, terrain, enemies, structures or magical phenomena. The hero must be the "
                "clear focal point and occupy roughly the center-right of the frame, posed as if actively adventuring. "
                f"{avoid}"
            )
        if kind == "pet":
            return (
                f"Create original {style} Show a full-body fantasy companion in a living environment. "
                f"Species {labels['name']}, level {labels['level']}, ability theme {labels['ability']}, rarity {labels['rarity']}. "
                "Give the creature distinctive anatomy, expressive eyes, believable fur/scales/feathers/skin, unique "
                "markings, small equipment or magical accessories where appropriate, and an environment that reinforces "
                "its species and ability. It should look like a real collectible MMORPG companion rather than a generic "
                f"animal avatar. {avoid}"
            )
        if kind == "mob":
            return (
                f"Create original {style} Show a full-body enemy encounter, not a portrait. "
                f"Enemy: {labels['name']}; level {labels['level']}; region {labels['region']}; element {labels['element']}; "
                f"combat role {labels['role']}; creature type {labels['type']}. Design a memorable monster with a strong "
                "silhouette, anatomy suited to its role, visible scars/armor/horns/claws/ritual markings as appropriate, "
                "elemental effects, and a dangerous environment. Add scale cues such as ruins, smaller creatures, weapons, "
                "or terrain. The creature should feel like a named RPG enemy/boss from a large fantasy world. "
                f"{avoid}"
            )
        return (
            f"Create original {style} as a premium MMORPG inventory item showcase. "
            f"Item: {labels['name']}; rarity {labels['rarity']}. Render the complete object with believable materials, "
            "fine engravings, wear, gemstones, magical energy and construction details. Put it on a dramatic fantasy "
            "altar/armory/background with depth and lighting that matches its rarity. Make the object immediately readable "
            f"as a specific piece of gear rather than an abstract icon. {avoid}"
        )

    def _rpg_style_reference(self):
        if self._rpg_style_reference_b64 is not None:
            return self._rpg_style_reference_b64
        path=self.base_dir / "assets" / "rpg_art_style_reference.jpg"
        try:
            self._rpg_style_reference_b64=base64.b64encode(path.read_bytes()).decode("ascii")
        except Exception:
            self._rpg_style_reference_b64=""
        return self._rpg_style_reference_b64

    async def _generate_rpg_ai_art(self, kind, seed, cache_path):
        api_key=os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return False
        model=os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image").strip() or "gemini-3.1-flash-image"
        labels=self._rpg_art_labels(kind, seed)
        prompt=self._rpg_art_prompt(kind, labels)
        parts=[{"text":prompt}]
        ref=self._rpg_style_reference()
        if ref:
            parts.append({"inline_data":{"mime_type":"image/jpeg","data":ref}})
            parts[0]["text"] += (
                " Use the supplied reference only as a broad visual presentation reference: cinematic dark-fantasy "
                "MMORPG composition, painterly rendering, dramatic lighting and dense environmental detail. Do not copy "
                "its characters, text, logo, UI, exact layout or exact artwork."
            )
        payload={
            "contents":[{"parts":parts}],
            "generationConfig":{
                "responseModalities":["IMAGE"],
                "responseFormat":{"image":{"aspectRatio":"16:9","imageSize":"1K"}},
            },
        }
        url=f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent"
        timeout=aiohttp.ClientTimeout(total=float(os.getenv("RPG_ART_AI_TIMEOUT", "35")))
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url,headers={"x-goog-api-key":api_key,"Content-Type":"application/json"},json=payload) as resp:
                    raw=await resp.read()
                    if resp.status >= 400:
                        log.warning("RPG AI art request failed: HTTP %s: %s",resp.status,raw[:500])
                        return False
                    data=json.loads(raw.decode("utf-8"))
            image_b64=None
            for cand in data.get("candidates",[]):
                for part in cand.get("content",{}).get("parts",[]):
                    inline=part.get("inlineData") or part.get("inline_data")
                    if inline and inline.get("data"):
                        image_b64=inline["data"]
                        break
                if image_b64: break
            if not image_b64:
                log.warning("RPG AI art response contained no image data for %s",seed)
                return False
            from PIL import Image, ImageOps
            import io
            image=Image.open(io.BytesIO(base64.b64decode(image_b64))).convert("RGB")
            image=ImageOps.fit(image,(1536,864),method=Image.Resampling.LANCZOS,centering=(0.5,0.48))
            image.save(cache_path,"PNG",optimize=True)
            return True
        except Exception:
            log.exception("RPG AI art generation failed for %s",seed)
            return False

    async def _rpg_art_ai_background(self, kind, seed, cache_path):
        key=f"{kind}|{seed}"
        try:
            await self._generate_rpg_ai_art(kind,seed,cache_path)
        finally:
            self.rpg_art_tasks.pop(key,None)

    def _rpg_hud(self, image, kind, labels):
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        W,H=image.size
        im=image.convert("RGBA")
        overlay=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(overlay)
        try:
            title=ImageFont.truetype("DejaVuSans-Bold.ttf",30)
            sub=ImageFont.truetype("DejaVuSans.ttf",17)
            small=ImageFont.truetype("DejaVuSans.ttf",14)
        except Exception:
            title=sub=small=None
        accent=(74,220,255,225); panel=(5,10,19,190); white=(245,248,255,240); muted=(188,199,220,220)
        # Subtle cinematic vignette, then restrained HUD inspired by modern MMORPG combat screens.
        vignette=Image.new("RGBA",(W,H),(0,0,0,0)); vd=ImageDraw.Draw(vignette)
        for i in range(9):
            pad=i*28
            vd.rectangle((pad,pad,W-pad,H-pad),outline=(0,0,0,12+i*8),width=28)
        vignette=vignette.filter(ImageFilter.GaussianBlur(16)); im=Image.alpha_composite(im,vignette)
        d=ImageDraw.Draw(im)
        d.rounded_rectangle((26,22,610,104),18,fill=panel,outline=(80,220,255,95),width=2)
        d.text((48,38),labels.get("name","Horizon"),font=title,fill=white)
        if kind=="character":
            subtxt=f"{labels.get('race','Human')}  •  {labels.get('class_name','Warrior')}  •  {labels.get('path','Adventurer')}"
        elif kind=="mob":
            subtxt=f"Lv {labels.get('level','?')}  •  {labels.get('element','Arcane')}  •  {labels.get('role','Beast')}"
        elif kind=="pet":
            subtxt=f"Lv {labels.get('level','1')}  •  {labels.get('rarity','Rare')}  •  {labels.get('ability','Companion Bond')}"
        else:
            subtxt=f"{labels.get('rarity','Legendary')}  •  HORIZON INVENTORY"
        d.text((50,76),subtxt,font=sub,fill=muted)
        # Bottom combat strip; intentionally transparent so the generated artwork remains dominant.
        d.rounded_rectangle((26,H-112,1510,H-24),20,fill=(4,8,16,155),outline=(74,220,255,75),width=2)
        if kind=="character":
            d.text((50,H-92),"HP",font=small,fill=(255,255,255,220)); d.rounded_rectangle((84,H-88,390,H-68),8,fill=(65,25,35,210)); d.rounded_rectangle((84,H-88,382,H-68),8,fill=(210,48,56,230))
            d.text((420,H-92),"MP",font=small,fill=(255,255,255,220)); d.rounded_rectangle((454,H-88,760,H-68),8,fill=(26,47,72,210)); d.rounded_rectangle((454,H-88,690,H-68),8,fill=(62,150,235,230))
            for i in range(5):
                x=870+i*112; d.rounded_rectangle((x,H-98,x+82,H-36),14,fill=(10,18,31,205),outline=(74,220,255,95),width=2); d.ellipse((x+25,H-86,x+57,H-54),fill=(74,220,255,110))
        elif kind=="mob":
            d.text((50,H-92),"THREAT",font=small,fill=(255,255,255,220)); d.rounded_rectangle((120,H-88,650,H-68),8,fill=(62,24,30,220)); d.rounded_rectangle((120,H-88,580,H-68),8,fill=(220,55,70,230)); d.text((700,H-92),"ENCOUNTER",font=small,fill=(255,190,110,220))
        elif kind=="pet":
            d.text((50,H-92),"COMPANION",font=small,fill=(255,255,255,220)); d.text((180,H-92),labels.get("ability","Companion Bond"),font=sub,fill=(120,235,190,230))
        else:
            d.text((50,H-92),"RARITY",font=small,fill=(255,255,255,220)); d.text((120,H-92),labels.get("rarity","Legendary"),font=sub,fill=(255,196,95,240)); d.text((390,H-92),"TRADEABLE",font=small,fill=(120,235,190,230))
        return im.convert("RGB")

    async def rpg_art(self, request):
        """Serve cinematic AI-generated RPG artwork, with deterministic fallback/cache."""
        kind=request.query.get("kind","character").lower().strip()
        seed=request.query.get("seed","unknown").strip()[:500]
        if kind not in {"character","pet","mob","item"}:
            kind="character"
        self.rpg_art_cache.mkdir(parents=True,exist_ok=True)
        cache_key=self._rpg_art_cache_key(kind,seed)
        cache_path=self.rpg_art_cache / f"{cache_key}.png"
        labels=self._rpg_art_labels(kind,seed)
        if cache_path.exists():
            return web.FileResponse(cache_path,headers={"Cache-Control":"public, max-age=604800"})

        ai_enabled=os.getenv("RPG_ART_AI", "1").strip().lower() not in {"0","false","off","no"}
        task_key=f"{kind}|{seed}"
        if ai_enabled and os.getenv("GEMINI_API_KEY","").strip() and task_key not in self.rpg_art_tasks:
            task=asyncio.create_task(self._rpg_art_ai_background(kind,seed,cache_path))
            self.rpg_art_tasks[task_key]=task
            # Give the first request a short chance to receive the premium render.
            try:
                await asyncio.wait_for(asyncio.shield(task),timeout=float(os.getenv("RPG_ART_FIRST_WAIT", "20")))
            except (asyncio.TimeoutError,Exception):
                pass
            if cache_path.exists():
                return web.FileResponse(cache_path,headers={"Cache-Control":"public, max-age=604800"})

        # AI generation may still be running. The deterministic renderer is returned
        # immediately rather than making Discord wait; future requests reuse the AI cache.
        fallback=await self._rpg_art_fallback(request)
        body=fallback.body or b""
        from PIL import Image
        import io
        image=Image.open(io.BytesIO(body)).convert("RGB")
        image=self._rpg_hud(image,kind,labels)
        out=io.BytesIO(); image.save(out,"PNG",optimize=True)
        return web.Response(body=out.getvalue(),content_type="image/png",headers={"Cache-Control":"public, max-age=300"})

    async def health(self, request):
        return web.json_response({
            "online": True,
            "guilds": len(self.bot.guilds),
            "provider": self.bot.ai.provider_name,
            "model": self.bot.ai.model,
            "ai_configured": self.bot.ai.enabled,
            "website": self.dist_dir.exists(),
            "discord_oauth_configured": bool(os.getenv("DISCORD_CLIENT_ID", "").strip() and os.getenv("DISCORD_CLIENT_SECRET", "").strip()),
            "session_configured": bool(self._secret()),
            "redirect_uri_configured": bool(os.getenv("DISCORD_REDIRECT_URI", "").strip()),
            "site_url_configured": bool(os.getenv("SITE_URL", "").strip()),
        })

    async def api_overview(self, request):
        if not self._authorized(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        guild_id = request.query.get("guild_id", "")
        if not guild_id.isdigit():
            return web.json_response({"error": "guild_id is required"}, status=400)
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return web.json_response({"error": "Guild not found"}, status=404)
        rows = await self.bot.db.leaderboard(int(guild_id), 10000)
        events = await self.bot.db.events(int(guild_id))
        return web.json_response({
            "guild_id": guild.id, "guild_name": guild.name, "member_count": guild.member_count,
            "tracked_players": len(rows), "total_xp": sum(r[1] for r in rows),
            "total_coins": sum(r[2] for r in rows), "event_count": len(events),
            "latency_ms": round(self.bot.latency * 1000), "ai_online": bool(self.bot.ai.enabled),
            "ai_model": self.bot.ai.model,
        })

    async def api_member(self, request):
        if not self._authorized(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        guild_id, user_id = request.query.get("guild_id", ""), request.query.get("user_id", "")
        if not guild_id.isdigit() or not user_id.isdigit():
            return web.json_response({"error": "guild_id and user_id are required"}, status=400)
        guild = self.bot.get_guild(int(guild_id))
        member = guild.get_member(int(user_id)) if guild else None
        if not member:
            return web.json_response({"error": "Member not found"}, status=404)
        profile = await self.bot.db.profile(int(guild_id), int(user_id))
        return web.json_response({"user_id": member.id, "username": member.display_name, "avatar": str(member.display_avatar.url), "roles": [r.name for r in member.roles if r.name != "@everyone"], "level": profile["xp"] // 100 + 1, "xp": profile["xp"], "coins": profile["coins"], "warnings": profile["warnings"]})

    async def api_ai(self, request):
        if not self._authorized(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)
        message = body.get("message", "") if isinstance(body, dict) else ""
        if not isinstance(message, str) or not message.strip():
            return web.json_response({"error": "Please enter a message."}, status=400)
        guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()
        if not guild_id.isdigit():
            return web.json_response({"error": "Horizon guild is not configured."}, status=503)
        return await self._ai_response(request, int(guild_id), message.strip())

    async def _ai_response(self, request, guild_id, message):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return web.json_response({"error": "Horizon is not connected to the configured guild."}, status=503)
        session = self._session(request)
        if session and str(session.get("id", "")).isdigit():
            scope_id = f"discord:{session['id']}"
            name = session.get("global_name") or session.get("username") or "Discord member"
            profile = await self.bot.db.profile(guild_id, int(session["id"]))
            profile_text = f"nickname={profile['nickname'] or 'none'}; preferences={profile['preferences'] or 'none'}"
        else:
            cookies = self._cookies(request)
            visitor = self._verify_token(cookies.get("lh_visitor", ""))
            response_cookie = None
            if visitor and visitor.get("id"):
                visitor_id = visitor["id"]
            else:
                visitor_id = secrets.token_urlsafe(18)
                response_cookie = visitor_id
            scope_id = f"web:{visitor_id}"
            name = "Website visitor"
            profile_text = "(none)"

        settings = await self.bot.db.settings(guild_id)
        memories = await self.bot.db.memories(guild_id, 30)
        rows = await self.bot.db.ai_conversation(guild_id, scope_id, 120)
        context = self.bot.ai_context_from_rows(rows, message)
        memory_text = "\n".join(f"- {row[1]}" for row in memories)
        system = self.bot.build_ai_system(guild.name, name, memory_text, settings["personality"], profile_text, context)
        system += "\n\nMemory rule: use private conversation memory only when it clearly helps the current request. Never bring up unrelated old topics and never reveal another member's conversation."
        await self.bot.db.add_ai_message(guild_id, scope_id, "user", message)
        try:
            answer = await self.bot.ai.generate(system, message)
        except Exception as exc:
            await self.bot.db.remove_last_ai_message(guild_id, scope_id, "user")
            log.exception("Website Horizon AI request failed")
            return web.json_response({"error": "Horizon AI is temporarily unavailable."}, status=502)
        await self.bot.db.add_ai_message(guild_id, scope_id, "model", answer)
        response = web.json_response({"reply": answer, "model": self.bot.ai.model})
        if not session and response_cookie:
            token=self._make_token({"id":response_cookie,"createdAt":int(time.time())})
            self._set_cookie(response,"lh_visitor",token,60*60*24*365,http_only=True)
        return response

    async def site_horizon_ai(self, request):
        if request.method == "GET":
            try:
                online, detail = await self.bot.ai.status()
                return web.json_response({
                    "online": bool(online),
                    "serviceOnline": True,
                    "aiConfigured": bool(self.bot.ai.enabled),
                    "model": self.bot.ai.model,
                    "provider": self.bot.ai.provider_name,
                    "detail": detail,
                })
            except Exception as exc:
                log.exception("Website Horizon AI status check failed")
                return web.json_response({
                    "online": False,
                    "serviceOnline": True,
                    "aiConfigured": bool(self.bot.ai.enabled),
                    "model": self.bot.ai.model,
                    "provider": self.bot.ai.provider_name,
                    "error": "Horizon AI status check failed.",
                }, status=503)
        if request.method != "POST":
            return web.json_response({"error":"Method not allowed."}, status=405)
        try:
            body=await request.json()
        except Exception:
            return web.json_response({"error":"Invalid JSON body"}, status=400)
        message=body.get("message","") if isinstance(body,dict) else ""
        if not isinstance(message,str) or not message.strip():
            return web.json_response({"error":"Please enter a message."},status=400)
        if len(message)>4000:
            return web.json_response({"error":"Message is too long."},status=400)
        guild_id=os.getenv("DISCORD_GUILD_ID","").strip()
        if not guild_id.isdigit(): return web.json_response({"error":"Horizon guild is not configured."},status=503)
        return await self._ai_response(request,int(guild_id),message.strip())

    async def site_horizon_server(self, request):
        guild_id=os.getenv("DISCORD_GUILD_ID","").strip()
        if not guild_id.isdigit(): return web.json_response({"error":"Horizon guild is not configured."},status=503)
        guild=self.bot.get_guild(int(guild_id))
        if not guild: return web.json_response({"error":"Horizon community data is temporarily unavailable."},status=503)
        rows=await self.bot.db.leaderboard(int(guild_id),10000)
        events=await self.bot.db.events(int(guild_id))
        return web.json_response({"online":True,"guild_name":guild.name,"member_count":guild.member_count,"tracked_players":len(rows),"event_count":len(events),"latency_ms":round(self.bot.latency*1000),"ai_online":bool(self.bot.ai.enabled),"ai_model":self.bot.ai.model})

    async def site_auth_login(self, request):
        if not self._secret(): return web.Response(status=503,text="SESSION_SECRET is not configured.")
        client_id=os.getenv("DISCORD_CLIENT_ID","").strip()
        if not client_id: return web.Response(status=503,text="DISCORD_CLIENT_ID is not configured.")
        state=secrets.token_urlsafe(32)
        params=urlencode({"client_id":client_id,"response_type":"code","redirect_uri":self._redirect_uri(request),"scope":"identify guilds","state":state})
        response=web.HTTPFound(f"https://discord.com/oauth2/authorize?{params}")
        self._set_cookie(response,"lh_oauth_state",state,600,http_only=True)
        return response

    async def site_auth_callback(self, request):
        site=self._base_url(request)
        try:
            q=request.rel_url.query
            code,state=q.get("code"),q.get("state")
            if not code or not state or state!=self._cookies(request).get("lh_oauth_state"):
                return web.HTTPFound(f"{site}/?discord=error")
            data={"client_id":os.getenv("DISCORD_CLIENT_ID",""),"client_secret":os.getenv("DISCORD_CLIENT_SECRET",""),"grant_type":"authorization_code","code":code,"redirect_uri":self._redirect_uri(request)}
            timeout=aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post("https://discord.com/api/v10/oauth2/token",data=data) as token_response:
                    token=await token_response.json(content_type=None)
                    if token_response.status>=400: raise RuntimeError("Discord OAuth token exchange failed")
                headers={"Authorization":f"Bearer {token['access_token']}"}
                async with session.get("https://discord.com/api/v10/users/@me",headers=headers) as user_response:
                    user=await user_response.json(content_type=None)
                    if user_response.status>=400: raise RuntimeError("Discord user lookup failed")
                async with session.get("https://discord.com/api/v10/users/@me/guilds",headers=headers) as guild_response:
                    guilds=await guild_response.json(content_type=None)
                    if guild_response.status>=400: raise RuntimeError("Discord guild lookup failed")
            guild_id=os.getenv("DISCORD_GUILD_ID","").strip()
            if not any(str(g.get("id"))==guild_id for g in guilds if isinstance(g,dict)):
                response=web.HTTPFound(f"{site}/?discord=not-member")
            else:
                payload={"id":str(user["id"]),"username":user.get("username"),"global_name":user.get("global_name") or user.get("username"),"avatar":user.get("avatar"),"loggedInAt":int(time.time()*1000)}
                response=web.HTTPFound(f"{site}/?discord=success")
                self._set_cookie(response,"lh_session",self._make_token(payload),60*60*24*7,http_only=True)
            self._set_cookie(response,"lh_oauth_state","",0,http_only=True)
            return response
        except Exception as exc:
            log.exception("Discord OAuth callback failed")
            # Never expose Discord tokens or client secrets in the browser. The user
            # gets a stable redirect back to the SPA while the detailed exception
            # remains in Railway logs for diagnosis.
            return web.HTTPFound(f"{site}/?discord=error")

    async def site_auth_me(self, request):
        return web.json_response({"user":self._session(request)},headers={"Cache-Control":"no-store"})

    async def site_auth_logout(self, request):
        response=web.json_response({"ok":True})
        self._set_cookie(response,"lh_session","",0,http_only=True)
        return response
