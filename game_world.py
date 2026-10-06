from __future__ import annotations

LOCATIONS = [
 {"id":"horizon_village","name":"Horizon Village","region":"Frontier","level":1,"type":"town","description":"The first safe settlement beyond the Gate.","connections":["whispering_wilds","sunvale_fields","old_watchtower"],"shops":["Mira's General Store","Ironleaf Smithy"]},
 {"id":"whispering_wilds","name":"Whispering Wilds","region":"Frontier","level":2,"type":"wilds","description":"A dense forest where strange voices follow travelers.","connections":["horizon_village","moonlit_grove","thornwood","ashen_pass"],"shops":[]},
 {"id":"sunvale_fields","name":"Sunvale Fields","region":"Frontier","level":2,"type":"fields","description":"Golden farmland dotted with abandoned watch posts.","connections":["horizon_village","sunken_ruins","golden_steppe"],"shops":[]},
 {"id":"old_watchtower","name":"Old Watchtower","region":"Frontier","level":3,"type":"landmark","description":"A ruined tower overlooking the first frontier road.","connections":["horizon_village","ashen_pass"],"shops":[]},
 {"id":"moonlit_grove","name":"Moonlit Grove","region":"Wilds","level":4,"type":"forest","description":"An ancient grove where rare creatures appear after dusk.","connections":["whispering_wilds","fae_village","silverlake"],"shops":[]},
 {"id":"thornwood","name":"Thornwood","region":"Wilds","level":5,"type":"forest","description":"A dangerous forest filled with aggressive beasts.","connections":["whispering_wilds","beast_den","ashen_pass"],"shops":[]},
 {"id":"ashen_pass","name":"Ashen Pass","region":"Frontier","level":7,"type":"mountain","description":"A volcanic mountain road leading deeper into the continent.","connections":["old_watchtower","whispering_wilds","thornwood","emberfall"],"shops":["Ashen Supply Post"]},
 {"id":"sunken_ruins","name":"Sunken Ruins","region":"Ancient","level":6,"type":"ruins","description":"Flooded ruins from a civilization that vanished overnight.","connections":["sunvale_fields","silverlake","drowned_temple"],"shops":[]},
 {"id":"golden_steppe","name":"Golden Steppe","region":"Frontier","level":8,"type":"steppe","description":"A huge open grassland where roaming monsters and caravans cross.","connections":["sunvale_fields","caravan_crossroads","skyreach"],"shops":["Wanderer's Caravan"]},
 {"id":"silverlake","name":"Silverlake","region":"Ancient","level":7,"type":"lake","description":"A lakeside settlement famous for fishing and moon magic.","connections":["moonlit_grove","sunken_ruins","drowned_temple","caravan_crossroads"],"shops":["Silverlake Market"]},
 {"id":"fae_village","name":"Fae Village","region":"Mystic","level":9,"type":"town","description":"A hidden settlement protected by illusion magic.","connections":["moonlit_grove","crystal_caverns"],"shops":["Fae Curios"]},
 {"id":"beast_den","name":"Beast Den","region":"Wilds","level":10,"type":"dungeon_gate","description":"A massive cavern occupied by an ancient alpha.","connections":["thornwood"],"shops":[]},
 {"id":"emberfall","name":"Emberfall","region":"Volcanic","level":11,"type":"town","description":"A forge-town built around a dormant volcano.","connections":["ashen_pass","crimson_caldera"],"shops":["Emberforge"]},
 {"id":"drowned_temple","name":"Drowned Temple","region":"Ancient","level":12,"type":"dungeon_gate","description":"A half-submerged temple guarded by forgotten spirits.","connections":["sunken_ruins","silverlake"],"shops":[]},
 {"id":"caravan_crossroads","name":"Caravan Crossroads","region":"Frontier","level":10,"type":"hub","description":"Merchants from every region meet here.","connections":["golden_steppe","silverlake","skyreach","royal_capital"],"shops":["Grand Caravan","Black Market"]},
 {"id":"crystal_caverns","name":"Crystal Caverns","region":"Mystic","level":13,"type":"caves","description":"Crystal tunnels filled with monsters and rare ores.","connections":["fae_village","skyreach"],"shops":[]},
 {"id":"skyreach","name":"Skyreach","region":"Mystic","level":15,"type":"city","description":"A cliffside city overlooking the entire frontier.","connections":["golden_steppe","caravan_crossroads","crystal_caverns","royal_capital"],"shops":["Skyreach Bazaar"]},
 {"id":"crimson_caldera","name":"Crimson Caldera","region":"Volcanic","level":17,"type":"volcano","description":"The heart of the volcanic region and home to a legendary beast.","connections":["emberfall"],"shops":[]},
 {"id":"royal_capital","name":"Aurelia Capital","region":"Kingdom","level":18,"type":"capital","description":"The largest city in the known frontier.","connections":["caravan_crossroads","skyreach","frostbound_gate"],"shops":["Royal Armory","Grand Market"]},
 {"id":"frostbound_gate","name":"Frostbound Gate","region":"Endgame","level":22,"type":"frontier","description":"The final civilized outpost before the frozen north.","connections":["royal_capital","frostspire"],"shops":["Frostbound Provisioner"]},
 {"id":"frostspire","name":"Frostspire","region":"Endgame","level":25,"type":"endgame","description":"A frozen mountain where the oldest secrets of Horizon sleep.","connections":["frostbound_gate"],"shops":[]},
]

# ---------------------------------------------------------------------------
# Overworld metadata.  These values are consumed by the web client to make
# every region feel like a real place rather than a button in a menu.
# A normal road crossing is intentionally short: roughly 1 minute of
# uninterrupted walking at normal player speed. Level requirements are NOT
# movement requirements; they only gate combat, NPC interaction and dungeons.
# ---------------------------------------------------------------------------
_EXTRA_LOCATIONS = [
 {"id":"mistwood","name":"Mistwood","region":"Wilds","level":6,"type":"forest","description":"A huge silver-leaf forest where the road disappears beneath fog.","connections":["frostspire","moonlit_grove","verdant_basin"],"shops":[]},
 {"id":"verdant_basin","name":"Verdant Basin","region":"Wilds","level":8,"type":"fields","description":"A broad green basin crossed by streams, ruins and old caravan roads.","connections":["mistwood","ironroot_mines"],"shops":[]},
 {"id":"ironroot_mines","name":"Ironroot Mines","region":"Frontier","level":11,"type":"caves","description":"Deep mining roads beneath roots that have grown through ancient stone.","connections":["verdant_basin","shattered_coast"],"shops":["Ironroot Depot"]},
 {"id":"shattered_coast","name":"Shattered Coast","region":"Ancient","level":14,"type":"coast","description":"A vast broken coastline scattered with shipwrecks and sea caves.","connections":["ironroot_mines","aether_plains"],"shops":[]},
 {"id":"aether_plains","name":"Aether Plains","region":"Mystic","level":18,"type":"plains","description":"Wide floating-grass plains where fragments of old magic drift through the air.","connections":["shattered_coast","moonrise_plateau"],"shops":[]},
 {"id":"moonrise_plateau","name":"Moonrise Plateau","region":"Mystic","level":22,"type":"mountain","description":"A high plateau with an enormous view of the frontier below.","connections":["aether_plains","celestial_ruins"],"shops":[]},
 {"id":"celestial_ruins","name":"Celestial Ruins","region":"Astral","level":27,"type":"ruins","description":"Broken observatories built around stones that fell from the stars.","connections":["moonrise_plateau","dragonbone_expanse"],"shops":[]},
 {"id":"dragonbone_expanse","name":"Dragonbone Expanse","region":"Ancient","level":32,"type":"graveyard","description":"A continent-sized graveyard of colossal dragon bones.","connections":["celestial_ruins","eclipse_valley"],"shops":[]},
 {"id":"eclipse_valley","name":"Eclipse Valley","region":"Cursed","level":38,"type":"cursed","description":"A valley caught beneath a permanent eclipse and strange red auroras.","connections":["dragonbone_expanse","void_marsh"],"shops":[]},
 {"id":"void_marsh","name":"Void Marsh","region":"Void","level":45,"type":"void","description":"A black wetland where paths shift when nobody is looking.","connections":["eclipse_valley","astral_gate"],"shops":[]},
 {"id":"astral_gate","name":"Astral Gate","region":"Astral","level":52,"type":"sky","description":"A colossal gate hanging in open air above the world.","connections":["void_marsh","worldroot_hollow"],"shops":[]},
 {"id":"worldroot_hollow","name":"Worldroot Hollow","region":"Mythic","level":60,"type":"mythic","description":"A forest-sized hollow inside roots older than recorded history.","connections":["astral_gate","horizon_expanse"],"shops":[]},
 {"id":"horizon_expanse","name":"Horizon Expanse","region":"Endgame","level":70,"type":"endgame","description":"A massive frontier where the horizon itself bends into impossible shapes.","connections":["worldroot_hollow","edge_of_reality"],"shops":[]},
 {"id":"edge_of_reality","name":"Edge of Reality","region":"Endgame","level":82,"type":"void","description":"The final overland frontier before the world gives way to the unknown.","connections":["horizon_expanse","origin_sanctum"],"shops":[]},
 {"id":"sunscorch_desert","name":"Sunscorch Desert","region":"Frontier","level":9,"type":"desert","description":"A blazing desert crossed by buried roads, nomad camps and ancient stone gates.","connections":["golden_steppe","caravan_crossroads"],"shops":["Sunscorch Caravan"]},

]
LOCATIONS.extend(_EXTRA_LOCATIONS)

# Stable global coordinates for the overworld. The web client derives the
# actual road direction from these coordinates instead of assuming connection
# order is north/east/south/west.
_WORLD_COORDS = {
 "horizon_village":(0,0),"whispering_wilds":(-1,-1),"sunvale_fields":(-1,1),"old_watchtower":(-2,0),
 "moonlit_grove":(-2,-1),"thornwood":(-2,-2),"ashen_pass":(-2,1),"sunken_ruins":(-2,2),
 "golden_steppe":(-3,2),"silverlake":(-3,0),"fae_village":(-3,-1),"beast_den":(-3,-2),
 "emberfall":(-3,1),"drowned_temple":(-4,0),"caravan_crossroads":(-4,1),"crystal_caverns":(-4,-1),
 "skyreach":(-5,-1),"crimson_caldera":(-4,2),"royal_capital":(-5,1),"frostbound_gate":(-6,1),"frostspire":(-7,1),
 "mistwood":(-4,-2),"verdant_basin":(-5,-2),"ironroot_mines":(-6,-2),"shattered_coast":(-7,-2),
 "aether_plains":(-7,-1),"moonrise_plateau":(-8,-1),"celestial_ruins":(-8,0),"dragonbone_expanse":(-9,0),
 "eclipse_valley":(-9,1),"void_marsh":(-10,1),"astral_gate":(-11,1),"worldroot_hollow":(-12,1),
 "horizon_expanse":(-13,1),"edge_of_reality":(-14,1),"sunscorch_desert":(-3,3),
}
for _i,_loc in enumerate(LOCATIONS):
    _loc.setdefault("map_x", _WORLD_COORDS.get(_loc["id"], (_i*80, 0))[0])
    _loc.setdefault("map_y", _WORLD_COORDS.get(_loc["id"], (_i*80, 0))[1])

# Repair one-way roads introduced by world expansion. Every road is
# intentionally traversable in both directions.
_by_id = {x["id"]:x for x in LOCATIONS}
for _loc in LOCATIONS:
    for _target in list(_loc.get("connections", [])):
        if _target in _by_id and _loc["id"] not in _by_id[_target].setdefault("connections", []):
            _by_id[_target]["connections"].append(_loc["id"])

_TERRAIN_BY_TYPE = {
 "town":"village","wilds":"forest","fields":"meadow","landmark":"ruins","forest":"forest",
 "mountain":"mountain","ruins":"ruins","steppe":"steppe","lake":"lake","dungeon_gate":"cave",
 "hub":"road","caves":"cave","city":"city","volcano":"volcano","capital":"city","frontier":"mountain",
 "endgame":"void","plains":"meadow","coast":"coast","graveyard":"bones","cursed":"eclipse","void":"void","sky":"sky","mythic":"worldroot"
}
for _i,_loc in enumerate(LOCATIONS):
    _loc.setdefault("walk_minutes", 1)
    _loc.setdefault("terrain", _TERRAIN_BY_TYPE.get(_loc.get("type"),"wild"))
    _loc.setdefault("travel_note","Discovered by walking")
    _loc.setdefault("teleport_note","Teleport unlocked after discovery")

# Location-specific visual identity consumed by the web client.
WORLD_SCENES = {
 "horizon_village":{"biome":"village","weather":["clear","rain","fog"],"structures":["houses","inn","smithy","guild"],"landmarks":["village_square","windmill"],"road":"stone"},
 "whispering_wilds":{"biome":"forest","weather":["fog","rain","clear"],"structures":["forest_shrine"],"landmarks":["ancient_trees","mossy_stones"],"road":"dirt"},
 "sunvale_fields":{"biome":"farmland","weather":["clear","rain","fog"],"structures":["farmhouses","barn"],"landmarks":["windmill","haystacks"],"road":"dirt"},
 "old_watchtower":{"biome":"watchtower","weather":["clear","fog","rain"],"structures":["watchtower","ruined_wall"],"landmarks":["signal_fire"],"road":"stone"},
 "moonlit_grove":{"biome":"enchanted_forest","weather":["fog","clear","rain"],"structures":["fae_shrine"],"landmarks":["giant_moon_tree","fireflies"],"road":"root"},
 "thornwood":{"biome":"thorn_forest","weather":["fog","rain"],"structures":["hunter_camp"],"landmarks":["thorn_brambles","fallen_logs"],"road":"dirt"},
 "ashen_pass":{"biome":"mountain","weather":["fog","rain","clear"],"structures":["road_fort"],"landmarks":["cliffs","ash_pines"],"road":"stone"},
 "sunken_ruins":{"biome":"ruins","weather":["rain","fog"],"structures":["sunken_arch"],"landmarks":["broken_columns","flooded_streets"],"road":"stone"},
 "golden_steppe":{"biome":"steppe","weather":["clear","wind","rain"],"structures":["caravan_camp"],"landmarks":["grass_sea","stone_markers"],"road":"dirt"},
 "silverlake":{"biome":"lake","weather":["fog","clear","rain"],"structures":["lake_houses","docks"],"landmarks":["lighthouse","fishing_boats"],"road":"stone"},
 "fae_village":{"biome":"fae","weather":["fog","clear"],"structures":["fae_houses","glowing_gates"],"landmarks":["mushroom_rings","lantern_trees"],"road":"glow"},
 "beast_den":{"biome":"cavern","weather":["fog"],"structures":["cave_gate"],"landmarks":["bones","claw_marks"],"road":"rock"},
 "emberfall":{"biome":"volcanic_town","weather":["ash","clear"],"structures":["forge","lava_houses"],"landmarks":["lava_channel","smokestacks"],"road":"basalt"},
 "drowned_temple":{"biome":"underwater_ruins","weather":["rain","fog"],"structures":["temple_gate"],"landmarks":["waterfall","statues"],"road":"stone"},
 "caravan_crossroads":{"biome":"crossroads","weather":["clear","rain","wind"],"structures":["caravan_stalls","inn"],"landmarks":["road_marker","campfires"],"road":"cobble"},
 "crystal_caverns":{"biome":"crystal_cave","weather":["fog"],"structures":["crystal_entrance"],"landmarks":["giant_crystals","ore_veins"],"road":"crystal"},
 "skyreach":{"biome":"cliff_city","weather":["clear","fog","wind"],"structures":["cliff_houses","sky_docks"],"landmarks":["great_bridge","airships"],"road":"stone"},
 "crimson_caldera":{"biome":"volcano","weather":["ash","clear"],"structures":["volcanic_gate"],"landmarks":["lava_lake","dragon_roost"],"road":"basalt"},
 "royal_capital":{"biome":"kingdom","weather":["clear","rain","fog"],"structures":["castle","market","guildhall","residences"],"landmarks":["royal_palace","city_gate"],"road":"cobble"},
 "frostbound_gate":{"biome":"snow_outpost","weather":["snow","fog"],"structures":["fortress_gate","inn"],"landmarks":["ice_barricades","beacon"],"road":"ice"},
 "frostspire":{"biome":"frost_mountains","weather":["snow","fog"],"structures":["ice_fort"],"landmarks":["frozen_peaks","ancient_statues"],"road":"ice"},
 "mistwood":{"biome":"mist_forest","weather":["fog","rain"],"structures":["ranger_camp"],"landmarks":["silver_trees","mist_pool"],"road":"root"},
 "verdant_basin":{"biome":"verdant","weather":["clear","rain"],"structures":["ruined_bridge"],"landmarks":["waterfalls","giant_ferns"],"road":"dirt"},
 "ironroot_mines":{"biome":"mine","weather":["fog"],"structures":["mine_entrance","ore_lifts"],"landmarks":["ironroot_tree","ore_veins"],"road":"rail"},
 "shattered_coast":{"biome":"coast","weather":["rain","wind","clear"],"structures":["fishing_village","lighthouse"],"landmarks":["shipwrecks","sea_cliffs"],"road":"sand"},
 "aether_plains":{"biome":"aether","weather":["clear","wind"],"structures":["sky_shrine"],"landmarks":["floating_islands","aether_rifts"],"road":"light"},
 "moonrise_plateau":{"biome":"highlands","weather":["fog","clear","snow"],"structures":["mountain_camp"],"landmarks":["moonstone","cliffs"],"road":"stone"},
 "celestial_ruins":{"biome":"celestial","weather":["fog","clear"],"structures":["observatory"],"landmarks":["fallen_stars","astral_arch"],"road":"marble"},
 "dragonbone_expanse":{"biome":"dragon_graveyard","weather":["wind","fog"],"structures":["bone_camp"],"landmarks":["colossal_skulls","dragon_ribs"],"road":"bone"},
 "eclipse_valley":{"biome":"eclipse","weather":["fog","ash"],"structures":["eclipse_shrine"],"landmarks":["black_sun","red_crystals"],"road":"dark"},
 "void_marsh":{"biome":"void_marsh","weather":["fog","rain"],"structures":["marsh_camp"],"landmarks":["black_water","void_lilies"],"road":"wood"},
 "astral_gate":{"biome":"astral","weather":["clear","fog"],"structures":["gate_platform"],"landmarks":["giant_portal","floating_stones"],"road":"light"},
 "worldroot_hollow":{"biome":"worldroot","weather":["fog","rain"],"structures":["root_village"],"landmarks":["colossal_roots","glowing_sap"],"road":"root"},
 "horizon_expanse":{"biome":"endgame","weather":["clear","fog","ash"],"structures":["frontier_camp"],"landmarks":["broken_horizon","monoliths"],"road":"stone"},
 "edge_of_reality":{"biome":"reality_edge","weather":["fog","clear"],"structures":["last_outpost"],"landmarks":["reality_rift","floating_rocks"],"road":"void"},
 "sunscorch_desert":{"biome":"desert","weather":["clear","wind","ash"],"structures":["nomad_camp","desert_gate"],"landmarks":["giant_dunes","buried_ruins","oasis"],"road":"sand"}
}

NPCS = [
 {"id":"mira","name":"Mira","location":"horizon_village","role":"Shopkeeper","portrait":"merchant","dialogues":[
  {"text":"New face? Welcome to Horizon Village. The frontier rewards curiosity, but it punishes carelessness.","choices":["Show me your wares.","Tell me about the village.","Goodbye."],"next":[2,1,-1]},
  {"text":"The Gate opened three weeks ago. Since then, monsters have appeared where there used to be nothing.","choices":["What is behind the Gate?","I will investigate.","Goodbye."],"next":[3,3,-1]},
  {"text":"I keep potions, supplies and a few things travelers don't usually find in the wild. If you have the gold, I have the gear.","choices":["I'll look around.","Thanks, Mira.","Goodbye."],"next":[2,0,-1]},
  {"text":"Beyond the Gate are the Whispering Wilds and the old roads. Something has been changing the creatures there.","choices":["I'll be careful.","What should I watch for?","Goodbye."],"next":[0,3,-1]}]},
 {"id":"kael","name":"Kael","location":"horizon_village","role":"Guild Scout","portrait":"scout","dialogues":[
  {"text":"The Adventurer's Guild posts contracts every morning. If you want to grow stronger, take more than the safe jobs.","choices":["Give me a contract.","What lies beyond the village?","Goodbye."],"next":[1,2,-1]},
  {"text":"A scouting contract: reach the edge of the village and return safely. Easy enough for a new adventurer, but the wilds have teeth.","choices":["I'll take it.","Tell me about the wilds.","Goodbye."],"next":[2,3,-1]},
  {"text":"The frontier opens into forests, fields and ruins. Each road gets more dangerous, but better rewards wait farther out.","choices":["Which route should I take?","I'll get stronger first.","Goodbye."],"next":[3,1,-1]},
  {"text":"Start with the Whispering Wilds. Watch for wolves, keep your potions ready, and don't wander too far from the road.","choices":["Got it.","Any other advice?","Goodbye."],"next":[0,2,-1]}]},
 {"id":"selene","name":"Selene","location":"sunvale_fields","role":"Wandering Mage","portrait":"mage","dialogues":[
  {"text":"Magic behaves strangely near the ruins. Something below the water is answering spells.","choices":["Can I help?","What are you searching for?","Goodbye."]}]},
 {"id":"orin","name":"Orin","location":"old_watchtower","role":"Watch Captain","portrait":"guard","dialogues":[
  {"text":"Keep your eyes on the road. The beasts have started moving south.","choices":["Why?","I'll keep watch.","Goodbye."]}]},
 {"id":"luma","name":"Luma","location":"moonlit_grove","role":"Fae Guide","portrait":"fae","dialogues":[
  {"text":"You carry the scent of the Gate. The forest remembers every traveler who passes through it.","choices":["Can you guide me?","What is the Gate?","Goodbye."]}]},
 {"id":"brann","name":"Brann","location":"emberfall","role":"Blacksmith","portrait":"blacksmith","dialogues":[
  {"text":"If you bring me ore from the caverns, I can turn it into something worth carrying.","choices":["Show me the forge.","What should I mine?","Goodbye."]}]},
 {"id":"nox","name":"Nox","location":"caravan_crossroads","role":"Caravan Broker","portrait":"merchant","dialogues":[
  {"text":"Every road meets here eventually. I can get you supplies, rumors, or trouble. Sometimes all three.","choices":["Show me rare goods.","Any rumors?","Goodbye."]}]},
 {"id":"aria","name":"Aria","location":"fae_village","role":"Egg Keeper","portrait":"keeper","dialogues":[
  {"text":"Creatures hatch from more than eggs here. Some are born from memories, moonlight, or the dreams of their owners.","choices":["Show me the eggs.","How do eggs work?","Goodbye."]}]},
 {"id":"voss","name":"Voss","location":"royal_capital","role":"Royal Archivist","portrait":"scholar","dialogues":[
  {"text":"The oldest records mention twenty-one settlements before the Gate appeared. Only a handful remain.","choices":["Tell me about the Gate.","Can I read the archives?","Goodbye."]}]},
 {"id":"yuri","name":"Yuri","location":"silverlake","role":"Fisher","portrait":"villager","dialogues":[
  {"text":"Something enormous moved under the lake last night. I didn't sleep after that.","choices":["What did you see?","Need any help?","Goodbye."]}]},
 {"id":"sera","name":"Sera","location":"skyreach","role":"Arena Master","portrait":"warrior","dialogues":[
  {"text":"Strength isn't enough up here. Build a style that can survive when everything goes wrong.","choices":["Enter the arena.","Teach me.","Goodbye."]}]},
 {"id":"tarek","name":"Tarek","location":"sunscorch_desert","role":"Desert Guide","portrait":"scout","dialogues":[{"text":"Follow the stone markers. The dunes move, but the old road does not.","choices":["Guide me.","Where is the oasis?","Goodbye."}] ]},
 {"id":"vesa","name":"Vesa","location":"crystal_caverns","role":"Crystal Miner","portrait":"miner","dialogues":[{"text":"Every color of crystal has a different resonance. Blue ones hum when monsters are near.","choices":["Show me the mine.","What should I collect?","Goodbye."}] ]},
 {"id":"rowan","name":"Rowan","location":"old_watchtower","role":"Ranger","portrait":"scout","dialogues":[{"text":"This tower used to guard three kingdoms. Now I mostly watch monsters cross the valley.","choices":["What kingdoms?","Need help?","Goodbye."}] ]},
 {"id":"maris","name":"Maris","location":"royal_capital","role":"Royal Guard","portrait":"guard","dialogues":[{"text":"Aurelia is more than a capital. It is the last city where every road still has a name.","choices":["Tell me about the kingdom.","Where is the royal district?","Goodbye."}] ]},
 {"id":"dorin","name":"Dorin","location":"ironroot_mines","role":"Mine Foreman","portrait":"miner","dialogues":[{"text":"The roots down here are older than the mine. Don't cut anything that glows.","choices":["What can I mine?","Why are the roots moving?","Goodbye."}] ]},
 {"id":"lyra","name":"Lyra","location":"shattered_coast","role":"Harbor Master","portrait":"villager","dialogues":[{"text":"The tide has been carrying strange crystals onto the shore. Somebody is waking up beneath the sea.","choices":["What did you find?","Show me the harbor.","Goodbye."}] ]},
 {"id":"kaia","name":"Kaia","location":"frostspire","role":"Ice Oracle","portrait":"mage","dialogues":[{"text":"The mountain does not want visitors. The mountain remembers them.","choices":["What is at the summit?","Can I survive the climb?","Goodbye."}] ]},
 {"id":"eldra","name":"Eldra","location":"frostbound_gate","role":"Gatekeeper","portrait":"guard","dialogues":[
  {"text":"Few travelers return from Frostspire. Those who do never describe what they found the same way twice.","choices":["I'm going north.","What is in Frostspire?","Goodbye."]}]},
]

DUNGEONS = [
 {"id":"forgotten_mine","name":"Forgotten Mine","location":"old_watchtower","level":3,"floors":5,"boss":"Cave Tyrant","rewards":["Iron Ore","Arcane Shard","Minekeeper Title"]},
 {"id":"thornwood_hollow","name":"Thornwood Hollow","location":"thornwood","level":6,"floors":7,"boss":"Ancient Treant","rewards":["Moonleaf","Forest Egg","Wildwood Title"]},
 {"id":"drowned_temple","name":"Drowned Temple","location":"drowned_temple","level":12,"floors":9,"boss":"Abyssal Priest","rewards":["Pearl Core","Aqua Egg","Sunken Relic"]},
 {"id":"crystal_labyrinth","name":"Crystal Labyrinth","location":"crystal_caverns","level":15,"floors":10,"boss":"Prism Wyrm","rewards":["Crystal Core","Prism Egg","Labyrinth Title"]},
 {"id":"crimson_caldera","name":"Crimson Caldera","location":"crimson_caldera","level":17,"floors":12,"boss":"Caldera Dragon","rewards":["Dragon Scale","Ember Egg","Dragon Slayer Title"]},
 {"id":"frostspire","name":"Frostspire","location":"frostspire","level":25,"floors":15,"boss":"The Frozen King","rewards":["Frost Crown","Legendary Egg","Frostbound Title"]},
]

TITLES = [
 {"id":"adventurer","name":"Adventurer","condition":"Create your first hero"},
 {"id":"first_blood","name":"First Blood","condition":"Defeat your first enemy"},
 {"id":"explorer","name":"Pathfinder","condition":"Discover 10 locations"},
 {"id":"deep_delver","name":"Deep Delver","condition":"Reach floor 5 of a dungeon"},
 {"id":"beast_friend","name":"Beast Friend","condition":"Hatch your first pet"},
 {"id":"merchant","name":"Merchant","condition":"Buy and sell 25 items"},
 {"id":"dragon_slayer","name":"Dragon Slayer","condition":"Defeat a dragon boss"},
 {"id":"gatewalker","name":"Gatewalker","condition":"Complete the first main story arc"},
 {"id":"champion","name":"Champion","condition":"Win 25 adventures"},
 {"id":"horizon_legend","name":"Horizon Legend","condition":"Reach level 50"},
]

EGGS = [
 {"id":"forest_egg","name":"Forest Egg","rarity":"Rare","hatch_time":900,"pool":["Wolf Pup","Fox Spirit","Moon Cat"]},
 {"id":"aqua_egg","name":"Aqua Egg","rarity":"Epic","hatch_time":1800,"pool":["Tide Otter","Aqua Fox","Moon Cat"]},
 {"id":"prism_egg","name":"Prism Egg","rarity":"Epic","hatch_time":3600,"pool":["Crystal Lynx","Prism Fox","Star Hare"]},
 {"id":"ember_egg","name":"Ember Egg","rarity":"Legendary","hatch_time":5400,"pool":["Ember Wolf","Flame Drake","Cinder Cat"]},
 {"id":"legendary_egg","name":"Legendary Egg","rarity":"Mythic","hatch_time":10800,"pool":["Sky Dragon","Frost Dragon","Astral Fox"]},
]

ITEMS = [
 {"id":"life_potion","name":"Life Potion","category":"consumable","price":35,"rarity":"Common"},
 {"id":"mana_potion","name":"Mana Potion","category":"consumable","price":40,"rarity":"Common"},
 {"id":"hearty_stew","name":"Hearty Stew","category":"food","price":55,"rarity":"Common"},
 {"id":"iron_sword","name":"Iron Sword","category":"weapon","price":180,"rarity":"Common"},
 {"id":"iron_armor","name":"Iron Armor","category":"armor","price":220,"rarity":"Common"},
 {"id":"moonleaf","name":"Moonleaf","category":"material","price":75,"rarity":"Uncommon"},
 {"id":"arcane_shard","name":"Arcane Shard","category":"material","price":160,"rarity":"Rare"},
 {"id":"dragon_scale","name":"Dragon Scale","category":"material","price":500,"rarity":"Legendary"},
]

SHOPS = [
 {"id":"general","name":"Mira's General Store","location":"horizon_village","items":["life_potion","mana_potion","hearty_stew","iron_sword"]},
 {"id":"smith","name":"Ironleaf Smithy","location":"horizon_village","items":["iron_sword","iron_armor"]},
 {"id":"fae","name":"Fae Curios","location":"fae_village","items":["moonleaf","arcane_shard"]},
 {"id":"ember","name":"Emberforge","location":"emberfall","items":["dragon_scale","iron_armor"]},
 {"id":"royal","name":"Grand Market","location":"royal_capital","items":["life_potion","mana_potion","arcane_shard","dragon_scale"]},
]
