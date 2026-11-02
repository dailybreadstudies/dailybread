#!/usr/bin/env python3
"""Hand-drawn story maps for Judges (data/maps/<id>.json + index.json).

    python3 tools/build_judges_maps.py && python3 tools/check_maps.py

Eight maps: the judges and the oppressors (overview), Ehud, Deborah and Barak, Gideon, Jephthah, Samson,
Dan's move north, and the war against Benjamin. Same format as tools/build_story_maps.py: movements,
symbols, named places with notes, and the passages each map belongs to (`anchor` + `also`).
Coordinates are OpenBible.info's where it has the site (data/maps/places/JDG.json), otherwise standard
identifications, noted in each place. The book map (tools/build_judges_land.py) links every name these
maps leave out. Edit here and run again.
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAPS = os.path.join(ROOT, 'data', 'maps')


def named(name, ll, label, site, note, ob=None):
    d = {'name': name, 'll': ll, 'label': label, 'site': site, 'note': note}
    if ob:
        d['ob'] = ob
    return d


def mv(n, side, vv, text, coords, at=0.5, dash=None, w=None):
    d = {'n': n, 'side': side, 'vv': vv, 'at': at, 'text': text, 'coords': coords}
    if dash:
        d['dash'] = dash
    if w:
        d['w'] = w
    return d


def sym(t, at, key, vv, moves=(), label=None, offset=None):
    d = {'type': t, 'at': at, 'key': key, 'vv': vv}
    if moves:
        d['moves'] = list(moves)
    if label:
        d['label'] = label
    if offset:
        d['offset'] = offset
    return d


DASH = [2, 1.4]            # dashed: route uncertain, or a message / a flight
SOURCES = ('Scripture: Berean Standard Bible (public domain). Places: OpenBible.info Bible Geocoding Data (CC BY 4.0) and standard identifications, '
           'as noted for each place. Ancient Dead Sea outline from OpenBible.info (CC BY 4.0). Ancient roads are approximations. '
           'Terrain: Terrain Tiles on AWS Open Data (Mapzen). Street map © OpenStreetMap contributors. Imagery © Esri. '
           'Map labels and streams: OpenFreeMap (OpenMapTiles, OpenStreetMap). Routes are approximate. Map engine: MapLibre GL.')

P = {  # shared coordinates (OpenBible.info unless noted)
    'Debir': [35.0149, 31.4321], 'Jericho': [35.4446, 31.8717], 'Gilgal': [35.46, 31.8819], 'Bethel': [35.2414, 31.9228],
    'Ramah': [35.2316, 31.8543], 'Palm': [35.236, 31.889], 'Hazor': [35.5692, 33.0183], 'Harosheth': [35.105, 32.712],
    'Kedesh': [35.5555, 32.735], 'Tabor': [35.3929, 32.6863], 'Megiddo': [35.1844, 32.5853], 'Taanach': [35.2191, 32.5215],
    'Zaanannim': [35.4106, 32.7211], 'Ophrah': [35.29, 32.6057], 'Harod': [35.3925, 32.5508], 'Moreh': [35.3487, 32.6176],
    'Beth-shittah': [35.4072, 32.5392], 'Abel-meholah': [35.5609, 32.3743], 'Tabbath': [35.6189, 32.2868],
    'Beth-barah': [35.52, 32.1], 'Succoth': [35.6212, 32.1966], 'Penuel': [35.6921, 32.187], 'Jogbehah': [35.8558, 32.0135],
    'Karkor': [37.5428, 31.3631], 'Mizpah-G': [35.777, 32.1185], 'Tob': [36.2439, 32.5633], 'Rabbah': [35.9339, 31.9539],
    'Aroer': [35.8194, 31.4708], 'Aroer-R': [35.8713, 31.9702], 'Minnith': [35.8747, 31.8202], 'Abel-keramim': [36.0049, 31.8756],
    'Heshbon': [35.8091, 31.8008], 'Jahaz': [35.9079, 31.5883], 'Zaphon': [35.5772, 32.2677], 'Zorah': [34.9853, 31.774],
    'Eshtaol': [34.986, 31.7977], 'Timnah': [34.9103, 31.7848], 'Ashkelon': [34.5458, 31.6639], 'Etam': [35.0258, 31.7637],
    'Lehi': [35.001, 31.7488], 'Gaza': [34.4644, 31.504], 'Hebron': [35.1022, 31.5251], 'Mahaneh-dan': [35.03, 31.79],
    'Kiriath-jearim': [35.1038, 31.809], 'Dan': [35.652, 33.249], 'Beth-rehob': [36.1453, 34.0089], 'Bethlehem': [35.2076, 31.7043],
    'Jerusalem': [35.2342, 31.7767], 'Gibeah': [35.2307, 31.8231], 'Mizpah': [35.2164, 31.8851], 'Baal-tamar': [35.2413, 31.8315],
    'Rimmon': [35.2967, 31.9333], 'Jabesh-gilead': [35.6823, 32.4024], 'Shiloh': [35.2895, 32.0557], 'Lebonah': [35.2498, 32.0591],
    'Pirathon': [35.1658, 32.1906], 'Kamon': [35.7256, 32.5876], 'Aijalon-Z': [35.309, 32.8141], 'Beth-anath': [35.4331, 33.2003],
    'Bethlehem-Z': [35.1903, 32.7358], 'Shamir': [35.193, 32.276], 'Fords-Jericho': [35.548, 31.838],
}

MAPS_OUT = []

# ─────────────────────────── 1. The judges and the oppressors (overview) ───────────────────────────
J_RED, J_BLUE = '#a0443a', '#24577a'
MAPS_OUT.append({
    'id': 'jdg-2-judges', 'title': 'The Judges and the Oppressors', 'ref': 'Judges 2:11–16:31',
    'anchor': {'book': 'JDG', 'c': 2, 'v': 11}, 'range': [11, 23],
    'also': [{'c': 3, 'v': 7, 'range': [7, 11]}, {'c': 10, 'v': 1, 'range': [1, 5]}, {'c': 12, 'v': 8, 'range': [8, 15]}],
    'placesName': 'Judges', 'siteLabel': 'Home', 'groupsLabel': 'Judges', 'groupLabelZoom': 6,
    'bounds': [[34.3, 31.15], [36.55, 33.35]],
    'links': [],
    'named': [],
    'groups': [
        {'id': 'told', 'name': 'Judges whose deeds are told', 'color': J_RED, 'places': [
            {'n': 'Othniel', 'll': P['Debir'], 'c': 2, 'm': 'Debir (Khirbet Rabud), Judah', 'f': '3:9',
             'note': 'Caleb\'s nephew, of Judah, who took Debir (1:12–13). He delivered Israel from Cushan-rishathaim king of Aram-naharaim after eight years; the land had rest forty years (3:7–11).'},
            {'n': 'Ehud', 'll': [35.3, 31.84], 'c': 1, 'm': 'Benjamin', 'f': '3:15',
             'note': 'A left-handed Benjamite. He killed Eglon king of Moab, who held the City of Palms, and Israel took the fords of the Jordan; the land had rest eighty years (3:12–30).'},
            {'n': 'Deborah', 'll': P['Palm'], 'c': 1, 'm': 'the Palm of Deborah, between Ramah and Bethel', 'f': '4:4',
             'note': 'A prophetess who judged Israel under her palm tree in the hill country of Ephraim. She called Barak to fight Sisera, and sang the victory song of Judges 5 (4:4–5:31).'},
            {'n': 'Barak', 'll': P['Kedesh'], 'c': 1, 'm': 'Kedesh in Naphtali', 'f': '4:6',
             'note': 'Of Kedesh in Naphtali. With Deborah he led Zebulun and Naphtali from Mount Tabor against the chariots of Sisera; the land had rest forty years (4:6–5:31; Hebrews 11:32).'},
            {'n': 'Gideon', 'll': P['Ophrah'], 'c': 1, 'm': 'Ophrah of the Abiezrites, Manasseh', 'f': '6:11',
             'note': 'Of the clan of Abiezer in Manasseh. With three hundred men he routed the Midianites in the Valley of Jezreel and pursued them across the Jordan; the land had rest forty years (6–8).'},
            {'n': 'Jephthah', 'll': P['Mizpah-G'], 'c': 0, 'm': 'Mizpah of Gilead', 'f': '11:1',
             'note': 'A Gileadite, driven out to the land of Tob and called back to lead Gilead against the Ammonites. He judged six years and was buried in one of the cities of Gilead (10:17–12:7).'},
            {'n': 'Samson', 'll': P['Zorah'], 'c': 2, 'm': 'Zorah (Tel Tzora), Dan', 'f': '13:24',
             'note': 'A Nazirite from birth, of the tribe of Dan. He "began to save Israel from the hand of the Philistines" and judged twenty years; he was buried between Zorah and Eshtaol (13–16).'},
        ]},
        {'id': 'minor', 'name': 'Judges named briefly', 'color': J_BLUE, 'places': [
            {'n': 'Shamgar', 'll': P['Beth-anath'], 'c': 0, 'm': 'unknown; "son of Anath" may point to Beth-anath', 'f': '3:31',
             'note': 'He struck down six hundred Philistines with an oxgoad (3:31). In his days the roads were deserted (5:6). Where he lived is not said; Beth-anath in Galilee is one guess.'},
            {'n': 'Tola', 'll': P['Shamir'], 'c': 0, 'm': 'Shamir in the hill country of Ephraim (site unknown)', 'f': '10:1',
             'note': 'A man of Issachar who lived in Shamir in the hill country of Ephraim, judged twenty-three years and was buried there (10:1–2). Some suggest Shamir is Samaria (Shomron); the dot shows that guess.'},
            {'n': 'Jair', 'll': P['Kamon'], 'c': 0, 'm': 'Gilead; buried at Kamon', 'f': '10:3',
             'note': 'A Gileadite who judged twenty-two years. His thirty sons rode thirty donkeys and had thirty towns, Havvoth-jair (10:3–5).'},
            {'n': 'Ibzan', 'll': P['Bethlehem-Z'], 'c': 1, 'm': 'Bethlehem, probably the one in Zebulun', 'f': '12:8',
             'note': 'He judged seven years and was buried at Bethlehem (12:8–10). Since Bethlehem of Judah is usually named with "Judah" in Judges, many take this to be Bethlehem of Zebulun (Joshua 19:15), near Elon\'s home.'},
            {'n': 'Elon', 'll': P['Aijalon-Z'], 'c': 0, 'm': 'Aijalon in the land of Zebulun', 'f': '12:11',
             'note': 'A Zebulunite who judged ten years and was buried in Aijalon in the land of Zebulun (12:11–12).'},
            {'n': 'Abdon', 'll': P['Pirathon'], 'c': 2, 'm': 'Pirathon (Farata), Ephraim', 'f': '12:13',
             'note': 'He judged eight years; his forty sons and thirty grandsons rode seventy donkeys. He was buried at Pirathon in Ephraim (12:13–15).'},
        ]},
    ],
    'moves': [
        mv(1, 'enemy', '3:8–10', 'Cushan-rishathaim of Aram-naharaim oppresses Israel eight years (from far to the north-east)',
           [[36.55, 33.55], [36.2, 33.2], [35.95, 32.95], [35.75, 32.7]], at=0.4, dash=DASH),
        mv(2, 'enemy', '3:12–14', 'Eglon of Moab, with Ammon and Amalek, crosses the Jordan and takes the City of Palms',
           [[35.78, 31.45], [35.72, 31.62], [35.62, 31.78], P['Fords-Jericho'], [35.46, 31.87]], at=0.45),
        mv(3, 'enemy', '4:2–3', 'Jabin of Hazor oppresses the north twenty years; Sisera\'s chariots hold the Jezreel Valley',
           [P['Hazor'], [35.52, 32.92], [35.42, 32.8], [35.3, 32.7], [35.2, 32.64]], at=0.4),
        mv(4, 'enemy', '6:1–6, 33', 'Midianites, Amalekites and the people of the east cross the Jordan into the Jezreel Valley…',
           [[36.45, 32.45], [36.0, 32.45], [35.6, 32.48], [35.42, 32.58], [35.3, 32.6]], at=0.35),
        mv(5, 'enemy', '6:4', '…and raid the land as far as Gaza',
           [[35.3, 32.6], [35.1, 32.45], [34.95, 32.15], [34.8, 31.85], [34.62, 31.65], [34.48, 31.52]], at=0.55, dash=DASH, w=2.4),
        mv(6, 'enemy', '10:7–9', 'The Ammonites oppress Gilead eighteen years and cross the Jordan against Judah, Benjamin and Ephraim',
           [P['Rabbah'], [35.85, 32.08], [35.7, 32.1], [35.55, 32.05], [35.4, 31.98]], at=0.35),
        mv(7, 'enemy', '10:7; 13:1', 'The Philistines rule Israel forty years',
           [[34.52, 31.6], [34.7, 31.72], [34.88, 31.78]], at=0.5),
    ],
    'symbols': [],
    'notes': [
        {'h': 'A cycle, told in the regions', 'p': [
            'Judges 2:11–19 gives the pattern of the book: Israel does evil and serves the Baals; the LORD gives them into the hand of an oppressor; they cry out; the LORD raises up a judge who saves them; '
            'the land has rest; and when the judge dies they turn back, "more corruptly than their fathers." Each judge comes from a different tribe and region, from Othniel of Judah in the south to Barak of Naphtali in the north and Jephthah of Gilead in the east, and each faces the neighbour pressing on that part of the land.']},
        {'h': 'How long was the time of the judges?', 'p': [
            'Added together, the years of oppression and rest in Judges come to about 410. 1 Kings 6:1 gives 480 years from the Exodus to Solomon\'s fourth year, and Jephthah speaks of 300 years in Heshbon (11:26). '
            'Since the judges were regional, many scholars think some of their times overlapped; the Philistine oppression of Samson\'s days (13:1) may run alongside the Ammonite oppression in Gilead (10:7).']},
        {'h': 'How to use this map', 'p': [
            'The red dots are the judges whose deeds are told, at their homes; the blue dots are the judges named only briefly. The red arrows show where each oppressor came from. '
            'Tap a judge in the key to show or hide the group, and a dot for the story. Each story has its own map at its chapter.']},
    ],
    'sources': SOURCES,
})

# ─────────────────────────── 2. Ehud (3:12–30) ───────────────────────────
MAPS_OUT.append({
    'id': 'jdg-3-ehud', 'title': 'Ehud and Eglon King of Moab', 'ref': 'Judges 3:12–30',
    'anchor': {'book': 'JDG', 'c': 3, 'v': 12}, 'range': [12, 30],
    'places': 'JDG', 'placesLabel': 'Places named in Judges', 'placesName': 'Judges',
    'bounds': [[35.12, 31.55], [35.95, 32.08]],
    'links': ['Moab', 'City of Palms', 'Gilgal', 'Seirah', 'Jordan'],
    'aliases': {'Jordan': 'Fords of the Jordan'},
    'named': [
        named('Moab', [35.78, 31.62], 'right', 'the plateau east of the Salt Sea',
              'Eglon king of Moab, with the Ammonites and Amalekites, defeated Israel and ruled them eighteen years (3:12–14). The Moabite plateau lies across the Jordan from Jericho; the plains of Moab face the city directly.'),
        named('City of Palms', P['Jericho'], 'left', 'Jericho (Tell es-Sultan)',
              'Eglon took "the City of Palms," Jericho by its spring (3:13; Deuteronomy 34:3), a foothold west of the Jordan. Joshua had cursed the rebuilding of its walls, so this was probably a settlement or residence by the oasis rather than a walled city. Eglon\'s "cool upper room" was probably here.', 'a231f80/jericho-1'),
        named('Gilgal', P['Gilgal'], 'right', 'Khirbet el-Mefjir?',
              'Ehud turned back "at the idols near Gilgal" (3:19) and escaped past them (3:26). The Hebrew <i>pesilim</i> means carved images or carved stones; some think of the twelve stones Joshua set up at Gilgal (Joshua 4:20), here perhaps as a boundary marker.', 'ab94aea/gilgal-1'),
        named('Seirah', [35.33, 31.97], 'right', 'unknown, in the hill country of Ephraim',
              'Ehud escaped to Seirah and blew the shofar in the hill country of Ephraim (3:26–27). The site is unknown; the dot only shows the region.'),
        named('Fords of the Jordan', P['Fords-Jericho'], 'right', 'the fords opposite Jericho',
              'Israel "seized the fords of the Jordan leading to Moab" and let no one cross, cutting off the Moabites west of the river; about ten thousand fell (3:28–29). The main fords near Jericho lie by the traditional site of the baptism of Jesus.'),
    ],
    'moves': [
        mv(1, 'enemy', '3:12–13', 'Eglon of Moab, with Ammonites and Amalekites, crosses the Jordan and takes the City of Palms',
           [[35.78, 31.66], [35.7, 31.74], [35.62, 31.8], P['Fords-Jericho'], [35.5, 31.855], [35.452, 31.868]], at=0.35),
        mv(2, 'israel', '3:15–18', 'Ehud brings the tribute down from the hill country to Eglon',
           [[35.27, 31.85], [35.32, 31.86], [35.38, 31.865], [35.437, 31.87]], at=0.5),
        mv(3, 'israel', '3:26', 'After killing Eglon, Ehud escapes past the idols to Seirah',
           [[35.45, 31.877], [35.4, 31.9], [35.36, 31.94], [35.335, 31.965]], at=0.5, dash=DASH),
        mv(4, 'israel', '3:27–28', 'Ehud blows the shofar; Israel comes down with him and seizes the fords of the Jordan',
           [[35.34, 31.97], [35.42, 31.95], [35.5, 31.9], [35.545, 31.845]], at=0.5),
    ],
    'symbols': [
        sym('captured', [35.447, 31.871], 'Ehud kills Eglon in his upper room with a short double-edged sword', '3:20–25', moves=[2], offset=[-12, 8]),
        sym('stones', [35.465, 31.888], 'The idols (carved stones) near Gilgal', '3:19, 26', moves=[3], offset=[10, -6]),
        sym('battle', [35.565, 31.835], 'About ten thousand Moabites are struck down at the fords; the land has rest eighty years', '3:29–30', moves=[4]),
    ],
    'notes': [
        {'h': 'A left-handed deliverer', 'p': [
            'Ehud was a Benjamite, "a man restricted in his right hand" (3:15). Benjamin, "son of the right hand," was known for its left-handed men (20:16). '
            'He hid a short double-edged sword on his right thigh, where a guard checking a right-handed man would not look, and asked to see the king alone with "a secret message" and then "a word from God" (3:19–20).']},
        {'h': 'Holding the fords', 'p': [
            'The Jordan can be crossed easily in only a few places. By taking the fords opposite Jericho, Israel trapped the Moabite force on the west bank. '
            'Gideon (7:24) and the Gileadites under Jephthah (12:5–6) later used the same tactic.']},
    ],
    'sources': SOURCES,
})

# ─────────────────────────── 3. Deborah and Barak (4–5) ───────────────────────────
MAPS_OUT.append({
    'id': 'jdg-4-deborah', 'title': 'Deborah and Barak at the Kishon', 'ref': 'Judges 4–5',
    'anchor': {'book': 'JDG', 'c': 4, 'v': 1}, 'range': [1, 24],
    'also': [{'c': 5, 'v': 1, 'range': [1, 31]}],
    'places': 'JDG', 'placesLabel': 'Places named in Judges', 'placesName': 'Judges',
    'bounds': [[34.9, 32.42], [35.75, 33.1]],
    'links': ['Hazor', 'Harosheth-hagoyim', 'Palm of Deborah', 'Kedesh', 'Mount Tabor', 'Tabor', 'Kishon', 'Zaanannim', 'Megiddo', 'Taanach'],
    'aliases': {'Tabor': 'Mount Tabor'},
    'named': [
        named('Hazor', P['Hazor'], 'right', 'Tel Hazor',
              'Jabin "king of Canaan" reigned in Hazor (4:2), the greatest city of Canaan, burned by Joshua (Joshua 11:10–13) and evidently rebuilt as a power again. The excavations show a great fire at the end of the Late Bronze Age; how the layers fit Joshua and Judges is debated.', 'a6f33c5/hazor-1'),
        named('Harosheth-hagoyim', P['Harosheth'], 'left', 'unknown; perhaps in the Kishon gorge below Carmel',
              '"Harosheth of the nations," Sisera\'s home and base. His 900 iron chariots came from here to the Kishon, and Barak pursued them back to it (4:2, 13, 16). Some read the name as "the forested land of the nations," a region rather than a town.'),
        named('Palm of Deborah', P['Palm'], 'right', 'between Ramah and Bethel, hill country of Ephraim',
              'Deborah judged Israel under her palm tree between Ramah and Bethel (4:4–5). From here she summoned Barak, more than 100 km to the north, and went with him to Kedesh (4:6–9).'),
        named('Kedesh', P['Kedesh'], 'right', 'Khirbet Qedish, above the Sea of Galilee',
              'Barak\'s home, "Kedesh in Naphtali" (4:6), where he called out Zebulun and Naphtali (4:10). This Kedesh, near Tabor and the tent of Heber, fits the story better than the great Kedesh in upper Galilee (Tel Kedesh).', 'a48191b/kedesh-naphtali'),
        named('Mount Tabor', P['Tabor'], 'above', 'Jebel et-Tur (575 m)',
              'The rounded mountain at the north-east corner of the Jezreel Valley. Barak gathered ten thousand men on it, safe from chariots, and charged down at Deborah\'s word: "Arise! For this is the day the LORD has given Sisera into your hand" (4:14).', 'acd63ee/mount-tabor'),
        named('Kishon', [35.17, 32.645], 'below', 'Nahal Kishon, the stream of the Jezreel Valley',
              '"The torrent Kishon swept them away" (5:21). The song tells of rain from heaven (5:4, 20): a cloudburst would turn the valley floor into deep mud, where chariots were useless.'),
        named('Megiddo', P['Megiddo'], 'left', 'Tel Megiddo',
              '"The kings of Canaan fought at Taanach by the waters of Megiddo" (5:19): the battle was fought in the valley below these two cities.', 'a8554e3/megiddo'),
        named('Taanach', P['Taanach'], 'right', 'Tell Ta\'anakh', 'Eight km south-east of Megiddo, also on the edge of the valley (5:19).', 'a6f05f6/taanach'),
        named('Zaanannim', P['Zaanannim'], 'right', 'unknown; near Kedesh',
              'Heber the Kenite had separated from the other Kenites and pitched his tent "by the great tree of Zaanannim, near Kedesh" (4:11). Sisera fled here on foot, and Jael killed him with a tent peg (4:17–21).', 'a0c4f5e/zaanannim'),
    ],
    'moves': [
        mv(1, 'israel', '4:6–10', 'Barak calls up Zebulun and Naphtali at Kedesh and goes up to Mount Tabor with ten thousand men; Deborah goes with him',
           [P['Kedesh'], [35.5, 32.73], [35.45, 32.71], [35.405, 32.692]], at=0.45),
        mv(2, 'enemy', '4:12–13', 'Sisera brings his 900 iron chariots from Harosheth-hagoyim to the Kishon',
           [P['Harosheth'], [35.13, 32.69], [35.17, 32.66], [35.22, 32.63], [35.27, 32.62]], at=0.45),
        mv(3, 'israel', '4:14–15', 'Barak charges down from Tabor; the LORD routs Sisera and his chariots',
           [[35.39, 32.68], [35.36, 32.665], [35.33, 32.645], [35.29, 32.63]], at=0.5, w=3.8),
        mv(4, 'israel', '4:16', 'Barak pursues the chariots to Harosheth-hagoyim; not a man is left',
           [[35.25, 32.635], [35.2, 32.66], [35.15, 32.69], [35.11, 32.708]], at=0.5, dash=DASH),
        mv(5, 'enemy', '4:15, 17', 'Sisera flees on foot to the tent of Jael, near Kedesh',
           [[35.28, 32.625], [35.31, 32.66], [35.35, 32.69], [35.385, 32.71], [35.405, 32.72]], at=0.55, dash=DASH),
    ],
    'symbols': [
        sym('battle', [35.25, 32.6], '"The kings of Canaan fought at Taanach by the waters of Megiddo… the torrent Kishon swept them away"', '5:19–21', moves=[2, 3]),
        sym('camp', [35.4106, 32.7211], 'Jael kills Sisera in her tent', '4:17–22; 5:24–27', moves=[5], offset=[0, -10]),
    ],
    'notes': [
        {'h': 'Chariots and the rain', 'p': [
            'Sisera\'s strength was his nine hundred iron-fitted chariots (4:3), which ruled the flat Jezreel Valley. Barak waited on Mount Tabor, where chariots could not reach him. '
            'Deborah\'s song tells what turned the battle: "the clouds poured down water… the stars fought from the heavens… the torrent Kishon swept them away" (5:4, 20–21). In the mud of the valley floor the chariots became a trap.']},
        {'h': 'Who came, and who stayed', 'p': [
            'The song names the tribes that came, Ephraim, Benjamin, Machir (Manasseh), Zebulun, Issachar and Naphtali, and those that stayed home: Reuben "among the sheepfolds," Gilead beyond the Jordan, Dan by the ships and Asher by the coast (5:14–18). '
            'Meroz is cursed "for they did not come to help the LORD" (5:23). The victory is the LORD\'s, and the honour goes to a woman, as Deborah said: Jael, "most blessed of women in tents" (4:9; 5:24).']},
    ],
    'sources': SOURCES,
})

# ─────────────────────────── 4. Gideon (6–8) ───────────────────────────
MAPS_OUT.append({
    'id': 'jdg-6-gideon', 'title': 'Gideon\'s Three Hundred', 'ref': 'Judges 6–8',
    'anchor': {'book': 'JDG', 'c': 6, 'v': 1}, 'range': [1, 40],
    'also': [{'c': 7, 'v': 1, 'range': [1, 25]}, {'c': 8, 'v': 1, 'range': [1, 35]}],
    'places': 'JDG', 'placesLabel': 'Places named in Judges', 'placesName': 'Judges',
    'bounds': [[35.15, 32.0], [35.95, 32.7]],
    'links': ['Valley of Jezreel', 'Ophrah', 'Harod', 'Moreh', 'Beth-shittah', 'Abel-meholah', 'Tabbath', 'Beth-barah', 'Succoth', 'Penuel', 'Jogbehah', 'Karkor'],
    'named': [
        named('Valley of Jezreel', [35.33, 32.585], 'below', 'the eastern Jezreel Valley, between Moreh and Gilboa',
              'The Midianites, Amalekites and people of the east crossed the Jordan and camped here "as thick as locusts," with camels past counting (6:33; 7:12). The valley leads straight up from the Jordan at Beth-shean.'),
        named('Ophrah', P['Ophrah'], 'left', 'unknown; Afula is one proposal',
              'Ophrah of the Abiezrites, Gideon\'s town. The angel of the LORD found him threshing wheat in a winepress to hide it from Midian; Gideon built an altar, "The LORD Is Peace," and tore down his father\'s altar of Baal (6:11–32). He later set up a gold ephod here (8:27).', 'abd637f/ophrah-2'),
        named('Harod', P['Harod'], 'below', 'the spring of Harod: Ein Harod, at the foot of Gilboa',
              'Gideon camped "beside the spring of Harod" (7:1). Here 22,000 fearful men went home, and the LORD chose the 300 who lapped the water with their hands to their mouths (7:2–7).'),
        named('Moreh', P['Moreh'], 'above', 'Givat HaMoreh (Jebel Dahi), 515 m',
              'The camp of Midian was "in the valley near the hill of Moreh," north of Gideon (7:1). Gideon crept down at night and heard a man tell his dream of a barley loaf tumbling into the camp (7:9–15).', 'a772880/moreh-2'),
        named('Beth-shittah', P['Beth-shittah'], 'right', 'unknown; toward the Jordan', 'The Midianites fled toward Beth-shittah and Zererah (7:22).', 'a83d789/beth-shittah'),
        named('Abel-meholah', P['Abel-meholah'], 'right', 'Tell Abu Sus?',
              '"As far as the border of Abel-meholah near Tabbath" (7:22): the rout ran down the Jordan valley. Later the home of Elisha (1 Kings 19:16).', 'a5a1bdd/abel-meholah'),
        named('Tabbath', P['Tabbath'], 'right', 'Ras Abu Tabat?, east of the Jordan', 'Near Abel-meholah (7:22).', 'ab5c435/tabbath'),
        named('Beth-barah', P['Beth-barah'], 'left', 'unknown; by the Jordan fords below the Wadi Far\'a',
              'Gideon sent to Ephraim to "seize the waters of the Jordan as far as Beth-barah." They did, and caught the princes Oreb and Zeeb at the rock of Oreb and the winepress of Zeeb (7:24–25).', 'a0d1977/beth-barah'),
        named('Succoth', P['Succoth'], 'left', 'Tell Deir Alla',
              'The leaders of Succoth refused bread to Gideon\'s exhausted men: "Are the hands of Zebah and Zalmunna now in your possession?" Gideon punished them on his return (8:5–7, 14–16). A plaster text found at Tell Deir Alla tells of "Balaam son of Beor."', 'a0905b5/succoth-1'),
        named('Penuel', P['Penuel'], 'right', 'Tell edh-Dhahab esh-Sherqiyeh, on the Jabbok',
              'Penuel also refused; on his return Gideon tore down its tower (8:8–9, 17). Here Jacob had wrestled with God (Genesis 32:30–31).', 'a8a9ff9/penuel'),
        named('Jogbehah', P['Jogbehah'], 'right', 'Khirbet Jubeiha',
              'Gideon went up "by way of the caravan route east of Nobah and Jogbehah" and fell on the Midianite army (8:11).', 'acf6e00/jogbehah'),
        named('Karkor', P['Karkor'], 'left', 'unknown; Qarqar in Wadi Sirhan is one proposal, far to the east',
              'Zebah and Zalmunna rested at Karkor with 15,000 men, far out on the desert route and thinking themselves safe (8:10). The site is uncertain; the dot shows one proposal, over 150 km east of the Jordan. Zoom out to see it.', 'a0415e8/karkor'),
    ],
    'moves': [
        mv(1, 'enemy', '6:33', 'Midianites, Amalekites and the people of the east cross the Jordan and camp in the Valley of Jezreel',
           [[36.25, 32.48], [35.9, 32.5], [35.6, 32.5], [35.48, 32.55], [35.4, 32.6], [35.36, 32.605]], at=0.35),
        mv(2, 'israel', '6:34–35; 7:1', 'Gideon calls out Abiezer, Manasseh, Asher, Zebulun and Naphtali and camps at the spring of Harod',
           [P['Ophrah'], [35.32, 32.585], [35.36, 32.565], [35.39, 32.552]], at=0.5),
        mv(3, 'israel', '7:16–21', 'At night the 300 surround the camp with trumpets, jars and torches',
           [[35.39, 32.556], [35.375, 32.575], [35.36, 32.592]], at=0.5, w=3.8),
        mv(4, 'enemy', '7:22', 'The Midianites flee toward Beth-shittah and down the Jordan valley to Abel-meholah near Tabbath',
           [[35.37, 32.6], [35.39, 32.555], P['Beth-shittah'], [35.48, 32.48], [35.53, 32.42], P['Abel-meholah'], [35.59, 32.33], P['Tabbath']], at=0.45, dash=DASH),
        mv(5, 'ambush', '7:24–25', 'Ephraim seizes the waters of the Jordan as far as Beth-barah and captures Oreb and Zeeb',
           [[35.3, 32.13], [35.38, 32.12], [35.45, 32.11], [35.51, 32.1]], at=0.5),
        mv(6, 'israel', '8:4–9', 'Gideon and the 300 cross the Jordan, exhausted but pursuing; Succoth and Penuel refuse them bread',
           [[35.6, 32.3], [35.6, 32.24], P['Succoth'], [35.66, 32.19], P['Penuel']], at=0.4),
        mv(7, 'israel', '8:10–12', 'Up the caravan route east of Nobah and Jogbehah, to the camp at Karkor',
           [P['Penuel'], [35.78, 32.1], P['Jogbehah'], [36.1, 31.9], [36.6, 31.7], [37.1, 31.52], P['Karkor']], at=0.25, dash=DASH),
        mv(8, 'israel', '8:13–17', 'Returning by the Ascent of Heres, Gideon punishes Succoth and tears down the tower of Penuel',
           [[37.45, 31.42], [36.9, 31.68], [36.3, 31.93], [35.9, 32.08], [35.72, 32.16], [35.65, 32.19]], at=0.8, dash=[0.4, 1.6], w=2.4),
    ],
    'symbols': [
        sym('altar', [35.283, 32.612], '"The LORD Is Peace": Gideon\'s altar at Ophrah', '6:24–27', moves=[2], offset=[-10, -8]),
        sym('camp', [35.3925, 32.5508], 'Gideon\'s camp at the spring of Harod; the 300 who lapped', '7:1–8', moves=[2, 3], offset=[0, 10]),
        sym('battle', [35.36, 32.598], '"A sword for the LORD and for Gideon!" The Midianites turn on one another', '7:19–22', moves=[3]),
        sym('captured', [35.5, 32.105], 'Oreb and Zeeb, the princes of Midian, are captured and killed', '7:25', moves=[5], offset=[-12, 6]),
        sym('captured', [37.5, 31.38], 'Gideon takes the camp by surprise and captures Zebah and Zalmunna', '8:11–12', moves=[7]),
    ],
    'notes': [
        {'h': 'Raiders on camels', 'p': [
            'The Midianites came every harvest "like a swarm of locusts," with their livestock and tents, and stripped the land "as far as Gaza" (6:3–5). '
            'This is among the earliest pictures of large-scale camel-riding raids in the Bible; the domesticated camel let desert peoples cross great distances quickly. Israel hid in caves and strongholds, and Gideon threshed wheat in a winepress.']},
        {'h': 'Three hundred', 'p': [
            'The LORD cut Gideon\'s army from 32,000 to 300, "lest Israel glorify themselves over Me, saying, \'My own hand has saved me\'" (7:2). '
            'At the change of the night watch the 300 broke their jars, raised their torches and blew their shofars around the camp, and the LORD set the Midianites against one another (7:19–22). '
            'The pursuit then ran down the Jordan and far out into the desert. Isaiah remembers "the day of Midian" as a picture of the Messiah\'s victory (Isaiah 9:4).']},
    ],
    'sources': SOURCES,
})

# ─────────────────────────── 5. Jephthah (10:17–12:7) ───────────────────────────
MAPS_OUT.append({
    'id': 'jdg-11-jephthah', 'title': 'Jephthah of Gilead', 'ref': 'Judges 10:17–12:7',
    'anchor': {'book': 'JDG', 'c': 10, 'v': 17}, 'range': [17, 18],
    'also': [{'c': 11, 'v': 1, 'range': [1, 40]}, {'c': 12, 'v': 1, 'range': [1, 7]}],
    'places': 'JDG', 'placesLabel': 'Places named in Judges', 'placesName': 'Judges',
    'bounds': [[35.35, 31.35], [36.4, 32.65]],
    'links': ['Gilead', 'Mizpah of Gilead', 'Mizpah', 'Tob', 'Arnon', 'Jabbok', 'Heshbon', 'Jahaz', 'Aroer', 'Minnith', 'Abel-keramim', 'Zaphon', 'Jordan'],
    'aliases': {'Mizpah': 'Mizpah of Gilead', 'Jordan': 'Fords of the Jordan'},
    'except': {'Gilead': ['11:1-2'], 'Aroer': ['11:33']},
    'named': [
        named('Gilead', [35.75, 32.36], 'right', 'the hill country east of the Jordan',
              'The wooded highlands between the Yarmuk and the Arnon, settled by Gad and the half-tribe of Manasseh. The Ammonites oppressed "all the Israelites on the other side of the Jordan in Gilead" for eighteen years (10:8).'),
        named('Mizpah of Gilead', P['Mizpah-G'], 'right', 'unknown; Jel\'ad is one proposal',
              'Israel camped at Mizpah facing the Ammonites (10:17). Jephthah was made leader here "before the LORD" (11:11), and here his daughter came out to meet him with tambourines (11:34). Probably the Mizpah or "watchtower" where Jacob and Laban made their covenant (Genesis 31:49).', 'a0f8af9/mizpah-1'),
        named('Tob', P['Tob'], 'right', 'et-Tayibeh?',
              'Driven out by his half-brothers, Jephthah fled to the land of Tob, an Aramean region east of Gilead, where worthless men gathered around him (11:3). Tob later sent men to help the Ammonites against David (2 Samuel 10:6).', 'aaff3e1/tob'),
        named('Rabbah', P['Rabbah'], 'right', 'the citadel of Amman',
              'The capital of the Ammonites, not named in Judges. Today\'s Amman takes its name from Ammon.'),
        named('Arnon', [35.7, 31.46], 'below', 'Wadi Mujib',
              'The deep gorge into the Salt Sea, the border of Moab. The Ammonite king claimed "from the Arnon to the Jabbok"; Jephthah answered that Israel took that land from Sihon king of the Amorites, not from Ammon or Moab (11:13, 18–22).'),
        named('Jabbok', [35.62, 32.15], 'below', 'the Zarqa river', 'The northern limit of the land the Ammonite king claimed (11:13, 22).'),
        named('Heshbon', P['Heshbon'], 'left', 'Tell Hesban',
              'The city of Sihon. "Israel lived in Heshbon… for three hundred years. Why did you not take them back during that time?" (11:26).', 'abf2fc1/heshbon'),
        named('Jahaz', P['Jahaz'], 'right', 'Khirbet el-Medeiyineh?', 'Sihon fought Israel at Jahaz and was defeated (11:20–21; Numbers 21:23).', 'ad9b1cd/jahaz'),
        named('Aroer', P['Aroer'], 'right', 'Arair, on the edge of the Arnon gorge',
              'Aroer on the Arnon, one of the towns Israel had held for three hundred years (11:26). The Aroer of 11:33 is probably another town of that name near Rabbah (Joshua 13:25), shown as "Aroer near Rabbah."', 'ae46f2e/aroer-1'),
        named('Aroer near Rabbah', P['Aroer-R'], 'left', 'unknown; Khirbet Udena is one proposal',
              'Jephthah struck the Ammonites "from Aroer to the vicinity of Minnith, as far as Abel-keramim," twenty cities (11:33). This Aroer is "near Rabbah" (Joshua 13:25).'),
        named('Minnith', P['Minnith'], 'right', 'unknown; Umm el-Hanafish?', 'Known later for its wheat, traded at Tyre (Ezekiel 27:17).', 'a222545/minnith'),
        named('Abel-keramim', P['Abel-keramim'], 'right', 'Sahab?', '"Meadow of vineyards," the limit of the victory (11:33).', 'a957c5b/abel-keramim'),
        named('Zaphon', P['Zaphon'], 'left', 'Tell es-Sa\'idiyeh?',
              'The men of Ephraim crossed the Jordan to Zaphon to threaten Jephthah: "We will burn your house down on you" (12:1).', 'ab49753/zaphon-1'),
        named('Fords of the Jordan', [35.55, 32.12], 'left', 'the fords below the Jabbok',
              'The Gileadites held the fords. Each fugitive was told to say "Shibboleth"; an Ephraimite said "Sibboleth," and was killed. 42,000 of Ephraim fell (12:5–6).'),
    ],
    'moves': [
        mv(1, 'enemy', '10:17', 'The Ammonites are called to arms and camp in Gilead',
           [P['Rabbah'], [35.88, 32.0], [35.83, 32.06], [35.8, 32.1]], at=0.5),
        mv(2, 'other', '11:3', 'Driven out, Jephthah flees to the land of Tob',
           [P['Mizpah-G'], [35.9, 32.25], [36.05, 32.4], P['Tob']], at=0.5, dash=DASH),
        mv(3, 'israel', '11:5–11', 'The elders of Gilead bring Jephthah back to Mizpah as their leader',
           [[36.22, 32.54], [36.0, 32.36], [35.85, 32.2], [35.79, 32.13]], at=0.5),
        mv(4, 'israel', '11:32–33', 'Jephthah strikes twenty cities, from Aroer to Minnith and Abel-keramim',
           [P['Mizpah-G'], [35.84, 32.02], P['Aroer-R'], [35.88, 31.9], P['Minnith'], [35.94, 31.85], P['Abel-keramim']], at=0.3, w=3.8),
        mv(5, 'other', '11:18–22', 'Israel\'s route long before, in Jephthah\'s answer: around Edom and Moab, then north across the Arnon to Jahaz and Heshbon',
           [[36.1, 31.36], [36.08, 31.43], [35.98, 31.5], P['Jahaz'], [35.85, 31.7], P['Heshbon']], at=0.3, dash=[0.4, 1.6], w=2.4),
        mv(6, 'enemy', '12:1', 'The men of Ephraim cross the Jordan to Zaphon',
           [[35.38, 32.2], [35.45, 32.24], [35.52, 32.26], [35.57, 32.266]], at=0.5),
        mv(7, 'israel', '12:4–5', 'The men of Gilead strike Ephraim and seize the fords of the Jordan',
           [P['Mizpah-G'], [35.7, 32.14], [35.62, 32.13], [35.56, 32.12]], at=0.5),
    ],
    'symbols': [
        sym('battle', [35.92, 31.88], 'The Ammonites are subdued before Israel', '11:33', moves=[4]),
        sym('battle', [35.545, 32.15], '"Shibboleth": 42,000 men of Ephraim fall at the fords', '12:5–6', moves=[7]),
    ],
    'notes': [
        {'h': 'Jephthah\'s answer to Ammon', 'p': [
            'Before fighting, Jephthah sent the Ammonite king a history lesson (11:12–28): Israel came from Egypt to Kadesh, asked passage from Edom and Moab and was refused, went around their lands, '
            'and took the land "from the Arnon to the Jabbok" from Sihon king of the Amorites, who attacked them. It was not Ammon\'s land, and Israel had lived there three hundred years. "Let the LORD, the Judge, decide today."']},
        {'h': 'Shibboleth', 'p': [
            'The word means an ear of grain, or a flowing stream. Ephraimites west of the Jordan seem to have pronounced the <i>sh</i> as <i>s</i>, and could not hide their speech. '
            'The quarrel recalls Ephraim\'s complaint to Gideon (8:1–3); this time it ended in civil war, a first sign of the division that runs through the end of the book.']},
    ],
    'sources': SOURCES,
})

# ─────────────────────────── 6. Samson (13–16) ───────────────────────────
MAPS_OUT.append({
    'id': 'jdg-13-samson', 'title': 'Samson among the Philistines', 'ref': 'Judges 13–16',
    'anchor': {'book': 'JDG', 'c': 13, 'v': 1}, 'range': [1, 25],
    'also': [{'c': 14, 'v': 1, 'range': [1, 20]}, {'c': 15, 'v': 1, 'range': [1, 20]}, {'c': 16, 'v': 1, 'range': [1, 31]}],
    'places': 'JDG', 'placesLabel': 'Places named in Judges', 'placesName': 'Judges',
    'bounds': [[34.38, 31.45], [35.2, 31.88]],
    'links': ['Zorah', 'Eshtaol', 'Mahaneh-dan', 'Timnah', 'Ashkelon', 'Etam', 'Lehi', 'Ramath-lehi', 'En-hakkore', 'Gaza', 'Hebron', 'Valley of Sorek'],
    'aliases': {'Ramath-lehi': 'Lehi', 'En-hakkore': 'Lehi'},
    'named': [
        named('Zorah', P['Zorah'], 'above', 'Tel Tzora, above the Sorek Valley',
              'The home of Manoah and his wife, where the angel of the LORD announced Samson\'s birth (13:2–24). Samson was buried "between Zorah and Eshtaol in the tomb of his father Manoah" (16:31).', 'a08174b/zorah'),
        named('Eshtaol', P['Eshtaol'], 'right', 'Khirbet Deir Shubeib?', 'With Zorah, on the edge of the hill country facing the Philistine plain (13:25; 16:31).', 'a355b6e/eshtaol'),
        named('Mahaneh-dan', P['Mahaneh-dan'], 'right', 'unknown; between Zorah and Eshtaol',
              '"The camp of Dan," where the Spirit of the LORD began to stir Samson (13:25).'),
        named('Timnah', P['Timnah'], 'below', 'Tel Batash, in the Sorek Valley',
              'Samson "went down to Timnah" and saw a Philistine woman he wanted as his wife; on the way he tore apart a lion, and later found honey in its carcass (14:1–9). Tel Batash shows a town on the border between Israelite hills and Philistine plain.', 'a21f909/timnah-1'),
        named('Valley of Sorek', [34.93, 31.765], 'below', 'Nahal Sorek',
              'The valley running from the hills past Beth-shemesh and Timnah toward the coast. Here Samson loved Delilah, and the Philistine lords paid her to learn the secret of his strength (16:4–21).'),
        named('Ashkelon', P['Ashkelon'], 'left', 'Tel Ashkelon',
              'To pay the thirty sets of clothes for his riddle, Samson went down to Ashkelon and struck down thirty men (14:19), about 40 km away.', 'ac87d4c/ashkelon'),
        named('Etam', P['Etam'], 'right', 'unknown; a cave near Zorah ("Arak Isma\'in") is one proposal',
              'Samson stayed in the cave at the rock of Etam, and three thousand men of Judah came down and bound him with two new ropes to hand him over (15:8–13).', 'ae05348/etam-1'),
        named('Lehi', P['Lehi'], 'below', 'unknown; in Judah near the Philistine border',
              '"Jawbone." The ropes melted from Samson\'s arms, and with a donkey\'s jawbone he struck down a thousand men. He named the place Ramath-lehi, and God split open a hollow for water: En-hakkore, "the spring of the one who called" (15:14–19).', 'aeeaca0/lehi'),
        named('Gaza', P['Gaza'], 'left', 'Tell Harube, Gaza',
              'The southernmost Philistine city. Samson carried off its gates at midnight (16:1–3). Later, blinded, he ground grain in its prison, and died pulling down the temple of Dagon on the lords of the Philistines (16:21–30).', 'aa8edd2/gaza'),
        named('Hebron', P['Hebron'], 'right', 'Tel Rumeida, Hebron',
              'Samson carried the doors and posts of Gaza\'s gate "to the top of the mountain overlooking Hebron" (16:3), some 60 km away and 900 m higher. Some read it as a hill near Gaza facing toward Hebron.', 'a85151a/hebron'),
    ],
    'moves': [
        mv(1, 'israel', '14:1–5', 'Samson goes down to Timnah with his parents; on the way he kills a lion',
           [P['Zorah'], [34.96, 31.775], [34.93, 31.78], [34.912, 31.784]], at=0.5),
        mv(2, 'israel', '14:19', 'He goes down to Ashkelon and strikes thirty men to pay for his riddle',
           [P['Timnah'], [34.82, 31.74], [34.7, 31.69], [34.56, 31.666]], at=0.45, dash=DASH),
        mv(3, 'israel', '15:8', 'After the foxes and the slaughter, Samson goes to the cave at the rock of Etam',
           [P['Timnah'], [34.96, 31.77], [35.0, 31.765], [35.024, 31.764]], at=0.5),
        mv(4, 'enemy', '15:9', 'The Philistines camp in Judah and spread out near Lehi',
           [[34.72, 31.68], [34.82, 31.71], [34.92, 31.74], [34.995, 31.748]], at=0.5),
        mv(5, 'other', '15:11–13', 'Three thousand men of Judah bind Samson and bring him to Lehi',
           [P['Etam'], [35.016, 31.757], [35.004, 31.75]], at=0.5, dash=DASH),
        mv(6, 'israel', '16:1–3', 'Samson at Gaza: at midnight he carries off the city gate toward Hebron',
           [P['Gaza'], [34.68, 31.48], [34.88, 31.48], [35.0, 31.5], [35.09, 31.522]], at=0.4, dash=DASH),
        mv(7, 'enemy', '16:21', 'Seized in the Valley of Sorek, blinded and taken down to Gaza',
           [[34.92, 31.76], [34.8, 31.7], [34.66, 31.6], [34.54, 31.54], [34.47, 31.507]], at=0.5),
    ],
    'symbols': [
        sym('fire', [34.84, 31.74], 'Three hundred foxes with torches set the Philistine grain, vineyards and olive groves on fire', '15:4–5', offset=[0, -6]),
        sym('battle', [35.001, 31.742], 'With a donkey\'s jawbone Samson strikes down a thousand men', '15:14–17', moves=[4, 5], offset=[0, 10]),
        sym('captured', [34.93, 31.76], 'Delilah: Samson\'s hair is cut and the Philistines seize him', '16:19–21', moves=[7], offset=[0, 10]),
        sym('battle', [34.4644, 31.504], 'Samson pulls down the temple of Dagon on the lords of the Philistines', '16:23–30', moves=[7], offset=[-12, 0]),
        sym('tomb', [34.985, 31.786], 'Buried between Zorah and Eshtaol, in the tomb of his father Manoah', '16:31', offset=[10, 0]),
    ],
    'notes': [
        {'h': 'On the border', 'p': [
            'Samson\'s stories happen in a small area: the Danite towns of Zorah and Eshtaol on the hill country\'s edge, and the Philistine towns a short walk down the Sorek Valley. '
            'The Philistines had come from the Aegean world in the 12th century BC and settled the coast; their pottery, temples and diet (including pork) set their towns apart from the villages of the hills. '
            'By Samson\'s day they ruled Israel, and the men of Judah would rather hand him over than fight (15:11).']},
        {'h': 'Two pillars', 'p': [
            'The Philistine temple excavated at Tell Qasile (Tel Aviv) had its roof resting on two central wooden pillars on stone bases, set about two metres apart. '
            'It helps picture the house of Dagon at Gaza, where Samson braced himself against the two middle pillars and prayed, "Remember me, Lord GOD" (16:26–30). Hebrews 11:32 counts him among the heroes of faith.']},
    ],
    'sources': SOURCES,
})

# ─────────────────────────── 7. The Danites move north (18) ───────────────────────────
MAPS_OUT.append({
    'id': 'jdg-18-dan', 'title': 'The Danites Move North', 'ref': 'Judges 18',
    'anchor': {'book': 'JDG', 'c': 18, 'v': 1}, 'range': [1, 31],
    'places': 'JDG', 'placesLabel': 'Places named in Judges', 'placesName': 'Judges',
    'bounds': [[34.85, 31.68], [35.95, 33.32]],
    'links': ['Zorah', 'Eshtaol', 'Mahaneh-dan', 'Kiriath-jearim', 'Laish', 'Dan', 'Beth-rehob', 'Shiloh'],
    'aliases': {'Laish': 'Dan'},
    'except': {'Dan': ['18:29-30']},
    'named': [
        named('Zorah', P['Zorah'], 'below', 'Tel Tzora', 'The Danites sent five spies from Zorah and Eshtaol, and six hundred armed men set out from there (18:2, 11). The tribe had not been able to hold its allotment in the Shephelah against the Amorites (1:34).', 'a08174b/zorah'),
        named('Eshtaol', P['Eshtaol'], 'left', 'Khirbet Deir Shubeib?', 'With Zorah, the home of the Danites (18:2, 8, 11).', 'a355b6e/eshtaol'),
        named('Mahaneh-dan', P['Mahaneh-dan'], 'right', 'unknown; west of Kiriath-jearim',
              'The six hundred camped at Kiriath-jearim in Judah, "which is why the place west of Kiriath-jearim is called Mahaneh-dan to this day" (18:12).'),
        named('Kiriath-jearim', P['Kiriath-jearim'], 'right', 'Deir el-Azar', 'The Danites camped west of it (18:12). The ark later stayed here twenty years (1 Samuel 7:1–2).', 'a9bba61/kiriath-jearim'),
        named('Dan', P['Dan'], 'right', 'Tel Dan, by the springs of the Jordan',
              'Laish was a quiet and secure town "far from Sidon," with no ally. The Danites burned it, rebuilt it and named it Dan, and set up Micah\'s carved image with Jonathan son of Gershom, son of Moses, as priest (18:7–31). Tel Dan still has a great Middle Bronze Age gate of mudbrick from the city\'s Canaanite days.', 'a513646/dan'),
        named('Beth-rehob', P['Beth-rehob'], 'left', 'unknown; in the valley north of Laish',
              'Laish lay "in a valley near Beth-rehob" (18:28), the upper Jordan and Hula valley running north toward the Beqaa.', 'ad44b24/beth-rehob'),
        named('Shiloh', P['Shiloh'], 'left', 'Khirbet Seilun',
              'Micah\'s image stood at Dan "all the time the house of God was in Shiloh" (18:31).', 'aa4680a/shiloh'),
    ],
    'moves': [
        mv(1, 'other', '18:2–10', 'Five Danite spies go north by way of Micah\'s house to Laish, and report back',
           [P['Eshtaol'], [35.06, 31.87], [35.17, 31.97], [35.21, 32.06], [35.22, 32.3], [35.27, 32.6], [35.39, 32.86], [35.53, 33.07], [35.638, 33.243]], at=0.3, dash=DASH, w=2.4),
        mv(2, 'israel', '18:11–27', 'Six hundred Danites camp at Mahaneh-dan, take Micah\'s image and priest, and fall on Laish',
           [P['Zorah'], P['Mahaneh-dan'], [35.1, 31.83], [35.19, 31.93], [35.235, 32.0], [35.29, 32.12], [35.34, 32.4], [35.43, 32.68], [35.55, 32.92], [35.63, 33.12], [35.65, 33.235]], at=0.55),
    ],
    'symbols': [
        sym('captured', [35.235, 32.0], 'Micah\'s house in the hill country of Ephraim (site unknown): the Danites take his carved image, ephod and priest', '18:13–20', moves=[2], offset=[-14, 0]),
        sym('camp', [35.03, 31.79], 'The six hundred camp at Mahaneh-dan', '18:12', moves=[2], offset=[0, -10]),
        sym('fire', [35.652, 33.249], 'The Danites strike Laish and burn the city; they rebuild it and name it Dan', '18:27–29', moves=[2], offset=[12, -6]),
    ],
    'notes': [
        {'h': 'No king in Israel', 'p': [
            'The last chapters of Judges are not in time order; they show what Israel had become. Twice the narrator says, "In those days there was no king in Israel; everyone did what was right in his own eyes" (17:6; 21:25). '
            'A Levite descended from Moses serves a household idol for pay, and a tribe gives up its allotment to take a peaceful town far from help. '
            'The priest is Jonathan son of Gershom, son of Moses (18:30), so these events took place within a few generations of the conquest.']},
        {'h': 'From the coast to the springs of the Jordan', 'p': [
            'Dan\'s allotment lay in the Shephelah and on the coast (Joshua 19:40–46), but the Amorites, and later the Philistines, pressed them into the hills (1:34). '
            'About 150 km north, Laish sat by one of the great springs of the Jordan, well watered and open. From then on Dan was Israel\'s northern end, "from Dan to Beersheba" (20:1), and later Jeroboam set a golden calf there (1 Kings 12:29).']},
    ],
    'sources': SOURCES,
})

# ─────────────────────────── 8. The war against Benjamin (19–21) ───────────────────────────
MAPS_OUT.append({
    'id': 'jdg-19-benjamin', 'title': 'The War against Benjamin', 'ref': 'Judges 19–21',
    'anchor': {'book': 'JDG', 'c': 19, 'v': 1}, 'range': [1, 30],
    'also': [{'c': 20, 'v': 1, 'range': [1, 48]}, {'c': 21, 'v': 1, 'range': [1, 25]}],
    'places': 'JDG', 'placesLabel': 'Places named in Judges', 'placesName': 'Judges',
    'bounds': [[35.08, 31.68], [35.76, 32.44]],
    'links': ['Bethlehem', 'Jebus', 'Jerusalem', 'Gibeah', 'Ramah', 'Mizpah', 'Bethel', 'Baal-tamar', 'Rimmon', 'Jabesh-gilead', 'Shiloh', 'Lebonah'],
    'aliases': {'Jebus': 'Jerusalem'},
    'named': [
        named('Bethlehem', P['Bethlehem'], 'right', 'Bethlehem',
              'The Levite\'s concubine went home to her father in Bethlehem in Judah. He followed, and after five days of hospitality they left late in the day (19:1–10).', 'a112427/bethlehem-1'),
        named('Jerusalem', P['Jerusalem'], 'right', 'the City of David',
              'Jebus, still a Jebusite city. The Levite would not stay "in a city of foreigners" and went on to Gibeah (19:10–12).', 'a15257a/jerusalem'),
        named('Gibeah', P['Gibeah'], 'left', 'Tell el-Ful',
              'Gibeah of Benjamin, where no one took the travellers in except an old man from Ephraim, and where the men of the city abused the Levite\'s concubine until she died (19:14–28). When Benjamin refused to hand over the guilty men, all Israel went to war against it (20).', 'ac24f5f/gibeah-1'),
        named('Ramah', P['Ramah'], 'right', 'er-Ram', '"Let us try to reach… Gibeah or Ramah" (19:13).', 'a6d57ed/ramah-1'),
        named('Mizpah', P['Mizpah'], 'left', 'Tell en-Nasbeh',
              'All Israel, "from Dan to Beersheba and from the land of Gilead," assembled before the LORD at Mizpah and swore not to give their daughters to Benjamin (20:1; 21:1).', 'a736f6c/mizpah-3'),
        named('Bethel', P['Bethel'], 'right', 'Beitin',
              'Israel went up to inquire of God at Bethel, where the ark of the covenant was in those days with Phinehas son of Eleazar (20:18, 26–28), and wept there over Benjamin (21:2).', 'a64f355/bethel-1'),
        named('Baal-tamar', P['Baal-tamar'], 'right', 'unknown; Ras et-Tawil?', 'On the third day Israel drew up at Baal-tamar while the ambush rushed out west of Gibeah (20:33).', 'a66136c/baal-tamar'),
        named('Rimmon', P['Rimmon'], 'right', 'the rock of Rimmon: Rammun',
              'Six hundred Benjamites fled to the rock of Rimmon in the wilderness and held out four months, until Israel offered them peace (20:47; 21:13).'),
        named('Jabesh-gilead', P['Jabesh-gilead'], 'right', 'Tell el-Maqlub?',
              'No one from Jabesh-gilead came to Mizpah. Twelve thousand men struck the town and brought back four hundred young women for Benjamin (21:8–14). Saul\'s first victory later rescued it, and its men buried him (1 Samuel 11; 31:11–13).', 'af92088/jabesh-gilead'),
        named('Shiloh', P['Shiloh'], 'left', 'Khirbet Seilun',
              'At the yearly feast of the LORD at Shiloh the remaining Benjamites caught wives from the girls who came out to dance (21:19–23).', 'aa4680a/shiloh'),
        named('Lebonah', P['Lebonah'], 'right', 'Khan el-Lubban',
              'Shiloh is "north of Bethel, east of the road that goes up from Bethel to Shechem, and south of Lebonah" (21:19), directions that still lead to the site.', 'ab6bb68/lebonah'),
    ],
    'moves': [
        mv(1, 'other', '19:9–15', 'The Levite and his concubine leave Bethlehem late, pass Jebus, and reach Gibeah at sunset',
           [P['Bethlehem'], [35.215, 31.74], [35.236, 31.79], [35.231, 31.818]], at=0.5, dash=DASH),
        mv(2, 'israel', '20:18–25', 'Israel goes up to inquire at Bethel, then attacks Gibeah, and is beaten back twice',
           [P['Bethel'], [35.238, 31.89], [35.235, 31.86], [35.232, 31.835]], at=0.5),
        mv(3, 'enemy', '20:45–47', 'Six hundred Benjamites flee to the rock of Rimmon',
           [[35.24, 31.83], [35.265, 31.87], [35.282, 31.9], [35.294, 31.927]], at=0.5, dash=DASH),
        mv(4, 'israel', '21:10–12', 'Twelve thousand men strike Jabesh-gilead and bring four hundred young women to the camp at Shiloh',
           [[35.3, 32.06], [35.4, 32.15], [35.55, 32.3], [35.675, 32.398], [35.56, 32.33], [35.42, 32.2], [35.305, 32.065]], at=0.3),
    ],
    'symbols': [
        sym('camp', [35.2164, 31.8851], 'All Israel assembles before the LORD at Mizpah', '20:1–11', offset=[-12, 0]),
        sym('ambush', [35.205, 31.82], 'The ambush rushes out west of Gibeah and sets the city on fire', '20:29–40', moves=[2], offset=[-10, 6]),
        sym('battle', [35.2307, 31.8231], 'Benjamin is drawn out from the city and defeated; 25,000 fall', '20:31–46', moves=[2, 3], offset=[10, 4]),
        sym('tabernacle', [35.2895, 32.0557], 'The yearly feast of the LORD at Shiloh', '21:19–23', moves=[4], offset=[10, -6]),
    ],
    'notes': [
        {'h': 'A crime and a civil war', 'p': [
            'The story runs along the old ridge road north from Bethlehem through Jebus to Gibeah, Ramah and Bethel. The outrage at Gibeah recalls Sodom (Genesis 19), but in a town of Israel. '
            'All the tribes gather at Mizpah; Benjamin defends Gibeah and wins twice before Israel takes the city with an ambush, as Joshua took Ai (Joshua 8). Benjamin is left with six hundred men at the rock of Rimmon, and Israel grieves that "one tribe is cut off" (21:6).']},
        {'h': 'Gibeah and what followed', 'p': [
            'Each of these places returns in 1 Samuel: Shiloh with Eli and Samuel, Mizpah with Samuel\'s assemblies, and Gibeah as the home of Saul of Benjamin, the first king, whose first deed is to rescue Jabesh-gilead (1 Samuel 11). '
            'The book ends where it began its warning: "In those days there was no king in Israel; everyone did what was right in his own eyes" (21:25).']},
    ],
    'sources': SOURCES,
})


def main():
    idx_path = os.path.join(MAPS, 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8'))
    ours = {m['id'] for m in MAPS_OUT}
    idx['maps'] = [e for e in idx['maps'] if e['id'] not in ours]
    for m in MAPS_OUT:
        with open(os.path.join(MAPS, m['id'] + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(m, fh, ensure_ascii=False, indent=1)
        e = {'id': m['id'], 'title': m['title'], 'ref': m['ref'], 'book': m['anchor']['book'], 'c': m['anchor']['c'], 'v': m['anchor']['v'],
             'links': m['links'], 'range': m['range']}
        for k in ('also', 'aliases', 'except'):
            if m.get(k):
                e[k] = m[k]
        idx['maps'].append(e)
    order = ['GEN', 'EXO', 'JOS', 'JDG', 'MAT']
    idx['maps'].sort(key=lambda e: (order.index(e['book']) if e['book'] in order else 99, e['c'], e['v']))
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('%d maps written' % len(MAPS_OUT))


if __name__ == '__main__':
    main()
