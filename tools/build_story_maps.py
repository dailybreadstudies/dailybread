#!/usr/bin/env python3
"""Hand-drawn story maps for Genesis and Matthew (data/maps/<id>.json + index.json).

    python3 tools/build_story_maps.py && python3 tools/check_maps.py

Each map: movements (moves), symbols, named places with notes, and the passages it belongs to.
`anchor` is where the map button sits; `also` adds more passages (each with its own button and
verse range). Coordinates are OpenBible.info's where it has the site, otherwise standard
identifications (noted in the place note). Edit here and run again.
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAPS = os.path.join(ROOT, 'data', 'maps')
OB = 'https://www.openbible.info/geo/ancient/'


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


BOAT = [1.4, 1.1]          # dashed: by boat or uncertain
P = {  # shared coordinates
    'Ur': [46.1035, 30.9625], 'Haran': [39.03278, 36.86444], 'Shechem': [35.28194, 32.21361], 'Bethel': [35.24139, 31.92278],
    'Ai': [35.26111, 31.91694], 'Mamre': [35.10534, 31.55654], 'Hebron': [35.10222, 31.52509], 'Negev': [34.85, 31.08],
    'Egypt': [31.75, 30.82], 'Damascus': [36.30639, 33.51111], 'Dan': [35.652, 33.249], 'Salem': [35.2342, 31.7767],
    'Capernaum': [35.575, 32.88111], 'Nazareth': [35.29769, 32.70214], 'Bethsaida': [35.63096, 32.91038],
    'Gennesaret': [35.522, 32.858], 'Tyre': [35.19611, 33.27083], 'Sidon': [35.37194, 33.56099], 'Magadan': [35.5166, 32.8247],
    'Caesarea Philippi': [35.69333, 33.24611], 'Hermon': [35.857, 33.416],
}

MAPS_OUT = []

# ─────────────────────────── 1. Abram's journey (Genesis 11:31–13:18) ───────────────────────────
MAPS_OUT.append({
    'id': 'gen-12-abram', 'title': "Abram's Journey", 'ref': 'Genesis 11:31–13:18',
    'anchor': {'book': 'GEN', 'c': 12, 'v': 1}, 'range': [1, 20],
    'also': [{'c': 11, 'v': 31, 'range': [27, 32], 'links': ['Ur']}, {'c': 13, 'v': 1, 'range': [1, 18]}],
    'world': True, 'siteLabel': 'Site', 'placesName': 'Genesis',
    'bounds': [[30.6, 29.6], [47.2, 37.6]],
    'links': ['Haran', 'Shechem', 'Moreh', 'Bethel', 'Ai', 'Negev', 'Egypt', 'Sodom', 'Zoar', 'Mamre', 'Hebron'],
    'named': [
        named('Ur', P['Ur'], 'below', 'Tell el-Muqayyar, southern Iraq',
              'Ur "of the Chaldeans" (11:28, 31): the great Sumerian city by the Euphrates, excavated by Leonard Woolley in 1922–34, with its ziggurat to the moon-god Nanna and the royal tombs. Local tradition places Abraham\'s birthplace at Urfa (Şanlıurfa) near Haran instead, but the southern city is the usual identification.'),
        named('Haran', P['Haran'], 'right', 'Harran, south-east Turkey',
              'A city of the moon-god Sin on the Balikh river, on the main road between Mesopotamia and Syria. Terah settled and died here (11:31–32); Abram left from here at seventy-five (12:4). Rebekah\'s family and Laban lived in the region (24:10; 29:4).', 'a6d9af3/haran'),
        named('Shechem', P['Shechem'], 'right', 'Tell Balatah, Nablus',
              'In the pass between Mount Ebal and Mount Gerizim. At "the Oak of Moreh" here the LORD first promised the land to Abram\'s offspring, and Abram built his first altar in Canaan (12:6–7).', 'adf74d4/shechem'),
        named('Moreh', [35.29, 32.205], 'below', 'near Tell Balatah',
              '"The Oak of Moreh," probably "the teacher\'s oak," a sacred tree at Shechem (12:6; compare Deuteronomy 11:30).'),
        named('Bethel', P['Bethel'], 'left', 'Beitin',
              'Abram pitched his tent "with Bethel to the west and Ai to the east" and built an altar (12:8); he came back to the same place after Egypt (13:3–4). From these heights Lot looked down on the plain of the Jordan.', 'a64f355/bethel-1'),
        named('Ai', P['Ai'], 'right', 'et-Tell', 'East of Bethel. The city Joshua later took (Joshua 7–8).', 'a7e13e1/ai-1'),
        named('Negev', P['Negev'], 'below', 'the dry south, around Beersheba',
              'The arid south of Canaan, from Beersheba southward: grazing land in good years, the first to suffer in a drought.'),
        named('Egypt', P['Egypt'], 'below', 'the eastern Nile Delta',
              'In famine, people of Canaan went down to Egypt, where the Nile kept the land fed. A painting in the tomb of Khnumhotep II at Beni Hasan (about 1890 BC) shows a party of 37 "Asiatics" with their donkeys arriving in Egypt.'),
        named('Mamre', P['Mamre'], 'left', 'Ramat el-Khalil, north of Hebron',
              '"The Oaks of Mamre at Hebron," where Abram settled and built an altar (13:18). The enclosure built here by Herod and the church built by Constantine marked the traditional site.', 'aeb9e97/mamre'),
        named('Hebron', P['Hebron'], 'below', 'Tel Rumeida, Hebron', 'Hebron, near Mamre, where Abram settled (13:18) and where he later bought the cave of Machpelah (23:19).', 'a85151a/hebron'),
        named('Zoar', [35.48766, 31.0369], 'right', 'es-Safi?, south-east of the Dead Sea', 'The plain of the Jordan was well watered "all the way to Zoar" (13:10); Lot later fled there (19:22).', 'aacfcda/zoar'),
        named('Sodom', [35.449, 31.208], 'right', 'site disputed',
              'Lot "pitched his tent toward Sodom" (13:12). Its site is debated: many place the cities of the plain near the south end of the Dead Sea (Bab edh-Dhra and Numeira); others at Tall el-Hammam, north-east of the Dead Sea in the Jordan plain Lot looked down on from Bethel.', 'a0aa664/sodom'),
    ],
    'moves': [
        mv(1, 'other', '11:31', 'Terah takes Abram, Sarai and Lot from Ur toward Canaan, but they settle in Haran',
           [P['Ur'], [45.6, 31.42], [44.95, 32.05], [44.3, 32.62], [43.4, 33.45], [42.1, 34.3], [40.9, 34.55], [40.1, 35.2], [39.35, 35.95], P['Haran']], at=0.55),
        mv(2, 'israel', '12:4–6', 'At the LORD\'s call Abram leaves Haran for Canaan, as far as Shechem',
           [P['Haran'], [38.3, 36.6], [37.2, 36.2], [36.8, 35.4], [36.72, 34.74], [36.5, 34.0], P['Damascus'], [35.95, 33.05], [35.62, 32.75], [35.45, 32.45], P['Shechem']], at=0.45),
        mv(3, 'israel', '12:8–9', 'On to the hills between Bethel and Ai, then by stages toward the Negev',
           [P['Shechem'], [35.27, 32.08], [35.25, 31.93], [35.2, 31.7], [35.1, 31.48], [34.95, 31.25], P['Negev']], at=0.4),
        mv(4, 'israel', '12:10–20', 'Famine: down to Egypt, where Sarai is taken into Pharaoh\'s palace',
           [P['Negev'], [34.45, 31.18], [33.9, 31.1], [33.2, 31.05], [32.5, 30.95], P['Egypt']], at=0.5),
        mv(5, 'israel', '13:1–4', 'Sent away by Pharaoh: back through the Negev to the altar between Bethel and Ai',
           [P['Egypt'], [32.45, 30.72], [33.3, 30.74], [34.2, 30.9], [34.88, 31.12], [35.1, 31.42], [35.2, 31.72], [35.235, 31.9]], at=0.35, dash=[2, 1.4]),
        mv(6, 'other', '13:10–12', 'Lot chooses the well-watered plain of the Jordan and moves toward Sodom',
           [P['Bethel'], [35.35, 31.87], [35.46, 31.82], [35.55, 31.8]], at=0.6),
        mv(7, 'israel', '13:18', 'Abram moves his tent to the Oaks of Mamre at Hebron',
           [[35.245, 31.91], [35.22, 31.8], [35.17, 31.68], [35.13, 31.6], P['Mamre']], at=0.5),
    ],
    'symbols': [
        sym('altar', [35.30, 32.19], 'Altars Abram built: at Shechem, between Bethel and Ai, and at Mamre', '12:7–8; 13:4, 18', moves=[2], offset=[8, 6]),
        sym('altar', [35.255, 31.935], 'Altars Abram built: at Shechem, between Bethel and Ai, and at Mamre', '12:7–8; 13:4, 18', moves=[3]),
        sym('altar', [35.125, 31.565], 'Altars Abram built: at Shechem, between Bethel and Ai, and at Mamre', '12:7–8; 13:4, 18', moves=[7]),
    ],
    'notes': [
        {'h': 'The scale of the journey', 'p': [
            'From Ur to Haran along the Euphrates is about 1,000 km, and from Haran to Shechem about 700 km more: months of travel at the pace of flocks. '
            'The route follows the "Fertile Crescent," the arc of watered land between the desert and the mountains, avoiding the Syrian desert.']},
        {'h': 'Promise and land', 'p': [
            'At each stop Abram builds an altar and "calls on the name of the LORD," marking out the land he has been promised: Shechem in the north, Bethel in the centre, Hebron in the south. '
            'The same three places become centres of Israel\'s later history. Jewish tradition reads the journeys of the fathers as a sign for the children, <i>ma\'aseh avot siman la-banim</i> (Ramban on 12:6): the descent to Egypt in famine and the return with wealth foreshadow Israel\'s own story.']},
    ],
    'sources': 'Scripture: Berean Standard Bible (public domain). Places: OpenBible.info Bible Geocoding Data (CC BY 4.0) and standard identifications, as noted for each place. Seas, lakes and rivers: Natural Earth (public domain). Terrain: Terrain Tiles on AWS Open Data (Mapzen). Street map © OpenStreetMap contributors. Imagery © Esri. Routes are approximate. Map engine: MapLibre GL.',
})

# ─────────────────────────── 2. The war of the kings (Genesis 14) ───────────────────────────
MAPS_OUT.append({
    'id': 'gen-14-kings', 'title': 'The War of the Kings', 'ref': 'Genesis 14',
    'anchor': {'book': 'GEN', 'c': 14, 'v': 1}, 'range': [1, 24],
    'places': 'GEN', 'placesLabel': 'Places named in Genesis',
    'bounds': [[34.15, 29.4], [37.3, 34.35]],
    'links': ['Ashteroth-karnaim', 'Ham', 'Shaveh-kiriathaim', 'Mount Seir', 'El-paran', 'En-mishpat', 'Hazazon-tamar', 'Valley of Siddim',
              'Sodom', 'Gomorrah', 'Admah', 'Zeboiim', 'Zoar', 'Mamre', 'Dan', 'Hobah', 'Damascus', 'Valley of Shaveh', 'Salem'],
    'named': [
        named('Ashteroth-karnaim', [36.02, 32.82], 'right', 'Tell Ashtara and Sheikh Sa\'d, southern Syria',
              'Two neighbouring cities of Bashan; the Rephaites were remembered as giants (Deuteronomy 3:11). Og king of Bashan later reigned at Ashtaroth (Deuteronomy 1:4).'),
        named('Ham', [35.81238, 32.51421], 'right', 'Tell Ham, northern Jordan', 'Home of the Zuzites, perhaps the Zamzummites of Deuteronomy 2:20.', 'a7a5f29/ham-1'),
        named('Shaveh-kiriathaim', [35.75, 31.6], 'right', 'Khirbet el-Qureiyat?, Moab', '"The plain of Kiriathaim," in Moab (Numbers 32:37). The Emites were the earlier people of Moab (Deuteronomy 2:10–11).'),
        named('Mount Seir', [35.55, 30.55], 'right', 'the Edomite highlands', 'The hill country later held by Esau\'s descendants; the Horites lived here first (Genesis 36:20; Deuteronomy 2:12).'),
        named('El-paran', [35.0, 29.55], 'right', 'probably Elath, at the head of the Gulf of Aqaba', '"El-paran, which is near the desert": the southernmost point of the campaign, probably later Elath.'),
        named('En-mishpat', [34.42222, 30.64833], 'left', 'Ain el-Qudeirat (Kadesh-barnea)', '"En-mishpat (that is, Kadesh)," "the spring of judgment": the great oasis where Israel later camped for many years (Numbers 20:1; Deuteronomy 1:46).'),
        named('Hazazon-tamar', [35.39, 31.46], 'right', 'En-gedi (2 Chronicles 20:2), or Tamar further south',
              'The Amorites of Hazazon-tamar. 2 Chronicles 20:2 equates it with En-gedi on the Dead Sea; some prefer Tamar (Ein Hatzeva) in the Arabah.'),
        named('Valley of Siddim', [35.44, 31.12], 'right', 'the south end of the Dead Sea?',
              '"The Valley of Siddim (that is, the Salt Sea)," "full of tar pits" (14:3, 10): bitumen still rises from the Dead Sea. The text implies the valley later lay under the sea, which suggests its shallow southern basin.'),
        named('Mamre', P['Mamre'], 'below', 'Ramat el-Khalil, north of Hebron', 'Abram lived "near the Oaks of Mamre the Amorite," his ally (14:13).', 'aeb9e97/mamre'),
        named('Dan', P['Dan'], 'left', 'Tel Dan', 'The city was called Laish until the tribe of Dan took it (Judges 18:29); the narrator uses the later name. A mudbrick city gate of the Middle Bronze Age still stands here.', 'a513646/dan'),
        named('Hobah', [37.06667, 34.25], 'left', 'unknown; "north (literally "left") of Damascus"', 'Not identified. Facing east, "left" is north.', 'a6779cd/hobah'),
        named('Salem', P['Salem'], 'above', 'Jerusalem', 'Salem is Jerusalem (Psalm 76:2). Melchizedek, its priest-king, brings bread and wine and blesses Abram (14:18–20).'),
        named('Valley of Shaveh', [35.238, 31.765], 'left', 'the Kidron valley by Jerusalem?', '"The King\'s Valley" (14:17), where Absalom later set up his pillar (2 Samuel 18:18); Josephus places it near Jerusalem.'),
    ],
    'alternates': {'for': 'Hazazon-tamar', 'bounds': [[35.1, 30.65], [35.55, 31.6]],
                   'sites': [{'name': 'Tamar (Ein Hatzeva)', 'll': [35.247, 30.78]}]},
    'moves': [
        mv(1, 'enemy', 'v. 5', 'The four kings march south, defeating the Rephaites, Zuzites and Emites',
           [[36.32, 33.62], [36.2, 33.2], [36.02, 32.82], [35.81, 32.51], [35.86, 32.1], [35.8, 31.82], [35.75, 31.6]], at=0.3),
        mv(2, 'enemy', 'v. 6', '…and the Horites of Mount Seir, as far as El-paran',
           [[35.75, 31.6], [35.72, 31.3], [35.65, 31.0], [35.58, 30.7], [35.45, 30.25], [35.25, 29.85], [35.0, 29.55]], at=0.5),
        mv(3, 'enemy', 'v. 7', 'They turn back to En-mishpat (Kadesh), the Amalekites and Hazazon-tamar',
           [[35.0, 29.55], [34.82, 29.9], [34.6, 30.3], [34.42, 30.65], [34.75, 30.8], [35.05, 31.0], [35.28, 31.25], [35.39, 31.46]], at=0.3),
        mv(4, 'enemy', 'vv. 11–12', 'With the goods of Sodom and Gomorrah, and Lot, they head home to the north',
           [[35.4, 31.35], [35.42, 31.62], [35.5, 31.86], [35.55, 32.3], [35.58, 32.75], [35.61, 33.08], [35.652, 33.235]], at=0.45, dash=[2, 1.4]),
        mv(5, 'israel', 'vv. 13–14', 'Abram and his 318 trained men set out from Mamre in pursuit, as far as Dan',
           [P['Mamre'], [35.13, 31.65], [35.21, 31.78], [35.24, 31.95], [35.28, 32.2], [35.3, 32.5], [35.42, 32.78], [35.56, 33.02], [35.64, 33.22]], at=0.55),
        mv(6, 'israel', 'v. 15', 'A night attack at Dan; Abram routs them and pursues to Hobah, north of Damascus',
           [P['Dan'], [35.9, 33.38], [36.2, 33.48], [36.6, 33.8], [37.06, 34.25]], at=0.5),
        mv(7, 'israel', 'vv. 16–17', 'Abram brings back Lot and the goods; the king of Sodom and Melchizedek meet him at the Valley of Shaveh',
           [[37.0, 34.2], [36.3, 33.45], [35.9, 33.0], [35.6, 32.62], [35.55, 32.2], [35.5, 31.87], [35.42, 31.85], [35.3, 31.79], [35.245, 31.768]], at=0.6, dash=[2, 1.4]),
    ],
    'symbols': [
        sym('battle', [35.47, 31.2], 'Four kings against five in the Valley of Siddim; the kings of Sodom and Gomorrah fall into the tar pits', 'vv. 8–10', moves=[3, 4]),
        sym('captured', [35.5, 31.34], 'Lot is carried off from Sodom', 'v. 12', moves=[4], offset=[10, 0]),
        sym('battle', [35.7, 33.27], 'Abram divides his men and attacks by night', 'v. 15', moves=[6]),
        sym('altar', [35.255, 31.79], 'Melchizedek, priest of God Most High, brings bread and wine and blesses Abram; Abram gives him a tenth', 'vv. 18–20', moves=[7], offset=[10, -6]),
    ],
    'notes': [
        {'h': 'The four kings', 'p': [
            'Amraphel of Shinar (Babylonia), Arioch of Ellasar, Chedorlaomer of Elam and Tidal "king of Goiim" ("nations"). Older scholars identified Amraphel with Hammurabi; that is now generally given up. '
            'Chedorlaomer is a good Elamite name (<i>Kudur-</i>, "servant of," with the goddess Lagamar), Arioch resembles Arriwuk of the Mari texts, and Tidal the Hittite royal name Tudhaliya. Elam really did dominate southern Mesopotamia at times in the early second millennium.']},
        {'h': 'Melchizedek', 'p': [
            'The priest-king of Salem appears only here and in Psalm 110:4, "a priest forever in the order of Melchizedek," which Hebrews 5–7 applies to Jesus. '
            'The sages identified him with Shem son of Noah (Nedarim 32b; Targum Pseudo-Jonathan on 14:18). His blessing names God as <i>El Elyon</i>, "God Most High, Creator of heaven and earth," and Abram adopts the title as his own (14:22).']},
    ],
    'sources': 'Scripture: Berean Standard Bible (public domain). Places: OpenBible.info Bible Geocoding Data (CC BY 4.0) and standard identifications, as noted for each place. Ancient roads are approximations. Terrain: Terrain Tiles on AWS Open Data (Mapzen). Street map © OpenStreetMap contributors. Imagery © Esri. Map labels and streams: OpenFreeMap (OpenMapTiles, OpenStreetMap). Map engine: MapLibre GL.',
})

# ─────────────────────────── 3. Around the Sea of Galilee (Matthew 13–14) ───────────────────────────
FEED = [35.642, 32.884]
MAPS_OUT.append({
    'id': 'mat-13-galilee', 'title': 'Around the Sea of Galilee', 'ref': 'Matthew 13–14',
    'anchor': {'book': 'MAT', 'c': 13, 'v': 1}, 'range': [1, 58],
    'also': [{'c': 14, 'v': 1, 'range': [1, 36]}],
    'places': 'MAT', 'placesLabel': 'Places named in Matthew', 'placesName': 'Matthew',
    'bounds': [[35.27, 32.67], [35.71, 32.95]],
    'links': ['Gennesaret'],
    'named': [
        named('Capernaum', P['Capernaum'], 'above', 'Tell Hum (Kfar Nahum)',
              'Jesus\' base in Galilee, "His own town" (9:1). "The house" of 13:1 and 13:36 is probably Peter\'s (8:14): under the octagonal Byzantine church a first-century house, honoured by early believers, has been excavated. The white limestone synagogue seen today is later, built over the black basalt foundations of an earlier one.', 'af2161c/capernaum'),
        named('Nazareth', P['Nazareth'], 'below', 'Nazareth', 'His hometown (13:54; 2:23): in the first century a small village in the hills above the Jezreel Valley.', 'af5884f/nazareth'),
        named('Gennesaret', P['Gennesaret'], 'left', 'the plain of Ginosar',
              'The fertile plain on the north-west shore; Josephus praises its climate and fruit (<i>Jewish War</i> 3.516–521). The "Galilee boat," a fishing boat of the first century, was found in the mud here in 1986.'),
        named('Bethsaida', P['Bethsaida'], 'right', 'et-Tell, or el-Araj by the shore',
              'Luke places the feeding of the 5,000 near Bethsaida (Luke 9:10). Its site is debated: et-Tell, on a hill above the old shoreline, or el-Araj by the lake, where a Byzantine church was found in 2019.', 'a91b732/bethsaida-1'),
        named('Tabgha', [35.548, 32.873], 'below', 'Heptapegon, "seven springs"', 'The traditional site of the feeding of the 5,000 since the fourth century, with its mosaic of loaves and fishes.'),
    ],
    'alternates': {'for': 'Bethsaida', 'bounds': [[35.6, 32.875], [35.66, 32.925]], 'sites': [{'name': 'el-Araj', 'll': [35.6272, 32.8938]}]},
    'moves': [
        mv(1, 'israel', '13:53–54', 'After the parables Jesus leaves for His hometown, Nazareth, where they take offense at Him',
           [P['Capernaum'], [35.55, 32.862], [35.5, 32.83], [35.45, 32.785], [35.39, 32.75], [35.33, 32.72], P['Nazareth']], at=0.5),
        mv(2, 'israel', '14:13', 'Hearing of John\'s death, Jesus withdraws by boat to a solitary place', [[35.577, 32.876], [35.6, 32.872], [35.625, 32.876], FEED], at=0.5, dash=BOAT),
        mv(3, 'other', '14:13', 'The crowds follow on foot from the towns', [[35.578, 32.884], [35.6, 32.895], [35.63, 32.903], [35.643, 32.892]], at=0.55, dash=[0.1, 1.8], w=2.6),
        mv(4, 'israel', '14:22–34', 'The disciples row against the wind; Jesus comes to them walking on the sea; they land at Gennesaret',
           [FEED, [35.62, 32.872], [35.595, 32.86], [35.565, 32.853], [35.535, 32.854]], at=0.5, dash=BOAT),
    ],
    'symbols': [
        sym('boat', [35.578, 32.872], 'He teaches the crowds in parables from a boat', '13:1–3', label='Parables', offset=[10, 8]),
        sym('loaves', FEED, 'Five loaves and two fish: the 5,000 fed', '14:15–21', moves=[2, 3], label='5,000 fed'),
        sym('mount', [35.65, 32.898], 'He goes up on the mountain alone to pray', '14:23', moves=[4]),
        sym('boat', [35.585, 32.857], 'Jesus walks on the sea; Peter walks, sinks and is caught', '14:25–33', moves=[4], label='On the water'),
    ],
    'notes': [
        {'h': 'Herod and John', 'p': [
            'Herod Antipas ruled Galilee and Perea. Josephus says John was imprisoned and executed at Machaerus, Herod\'s fortress east of the Dead Sea (<i>Antiquities</i> 18.116–119), well beyond this map. The news sends Jesus to "a solitary place" (14:13).']},
        {'h': 'The lake', 'p': [
            'The Sea of Galilee (Kinneret) is about 21 km long and 12 km wide, some 210 m below sea level. Winds funnel down from the surrounding hills, so sudden storms are common, especially in the evening (14:24). '
            'The fourth watch (14:25) ran from about 3 to 6 a.m.']},
    ],
    'sources': 'Scripture: Berean Standard Bible (public domain). Places: OpenBible.info Bible Geocoding Data (CC BY 4.0) and standard identifications, as noted for each place. Terrain: Terrain Tiles on AWS Open Data (Mapzen). Street map © OpenStreetMap contributors. Imagery © Esri. Map labels and streams: OpenFreeMap (OpenMapTiles, OpenStreetMap). Routes are approximate. Map engine: MapLibre GL.',
})

# ─────────────────────────── 4. The northern journeys (Matthew 15–17) ───────────────────────────
EAST = [35.665, 32.815]
MAPS_OUT.append({
    'id': 'mat-15-north', 'title': 'The Northern Journeys', 'ref': 'Matthew 15:21–17:27',
    'anchor': {'book': 'MAT', 'c': 15, 'v': 21}, 'range': [21, 39],
    'also': [{'c': 16, 'v': 1, 'range': [1, 28]}, {'c': 17, 'v': 1, 'range': [1, 27]}],
    'places': 'MAT', 'placesLabel': 'Places named in Matthew', 'placesName': 'Matthew',
    'bounds': [[35.0, 32.62], [36.02, 33.62]],
    'links': ['Tyre', 'Sidon', 'Magadan', 'Caesarea Philippi', 'Capernaum'],
    'named': [
        named('Tyre', P['Tyre'], 'left', 'Sur, Lebanon', 'The great Phoenician port. "The district of Tyre and Sidon" was Gentile territory; there a Canaanite woman asks for "the crumbs" and is praised for her faith (15:21–28).', 'a160272/tyre'),
        named('Sidon', P['Sidon'], 'left', 'Saida, Lebanon', 'Mark 7:31 says Jesus went back "through Sidon" to the Sea of Galilee and the Decapolis.', 'a98e4d7/sidon'),
        named('Magadan', P['Magadan'], 'left', 'Magdala (Migdal), on the west shore',
              'Probably Magdala, home of Mary Magdalene ("Dalmanutha" in Mark 8:10). A first-century synagogue was excavated here in 2009, with the carved "Magdala stone" showing the Temple menorah.'),
        named('Caesarea Philippi', P['Caesarea Philippi'], 'right', 'Banias, at the foot of Mount Hermon',
              'At one of the springs of the Jordan, by a cave sacred to the god Pan; Herod the Great built a temple to Augustus here, and his son Philip refounded the town. Here Peter confesses, "You are the Christ, the Son of the living God" (16:16).', 'ab7bf48/caesarea-philippi'),
        named('Mount Hermon', P['Hermon'], 'right', '"a high mountain" (17:1)',
              'Matthew does not name the mountain of the Transfiguration. Hermon (2,814 m), above Caesarea Philippi "after six days," fits "a high mountain"; Mount Tabor has been the traditional site since the fourth century. Some suggest Mount Meron.'),
        named('Capernaum', P['Capernaum'], 'right', 'Tell Hum', 'Back in Capernaum, the collectors of the Temple tax come to Peter, and the coin is found in the fish\'s mouth (17:24–27).', 'af2161c/capernaum'),
        named('Decapolis', [35.75, 32.72], 'right', 'the Ten Cities, mostly east of the lake', 'A league of Greek cities (Hippos, Gadara, Scythopolis and others). Mark 7:31 places the return from Tyre "in the region of the Decapolis."'),
    ],
    'alternates': {'for': 'Mount Hermon', 'bounds': [[35.25, 32.62], [36.0, 33.5]],
                   'sites': [{'name': 'Mount Tabor', 'll': [35.3906, 32.687]}, {'name': 'Mount Meron', 'll': [35.41, 32.998]}]},
    'moves': [
        mv(1, 'israel', '15:21', 'Jesus withdraws to the district of Tyre and Sidon',
           [P['Gennesaret'], [35.49, 32.94], [35.42, 33.04], [35.33, 33.13], [35.25, 33.22]], at=0.5),
        mv(2, 'israel', '15:29', 'Back by way of Sidon and the Decapolis (Mark 7:31) to a mountain by the Sea of Galilee',
           [[35.22, 33.25], [35.27, 33.42], [35.36, 33.53], [35.52, 33.42], [35.64, 33.25], [35.7, 33.05], [35.69, 32.9], EAST], at=0.35),
        mv(3, 'israel', '15:39', 'By boat to the region of Magadan', [EAST, [35.62, 32.83], [35.57, 32.828], [35.525, 32.826]], at=0.5, dash=BOAT),
        mv(4, 'israel', '16:4–5', 'Leaving the Pharisees, they cross to the other side', [[35.525, 32.83], [35.57, 32.86], [35.61, 32.89], [35.628, 32.905]], at=0.5, dash=BOAT),
        mv(5, 'israel', '16:13', 'North to the region of Caesarea Philippi', [[35.63, 32.91], [35.64, 33.0], [35.62, 33.1], [35.65, 33.19], [35.685, 33.24]], at=0.5),
        mv(6, 'israel', '17:1', '"After six days": up a high mountain with Peter, James and John', [[35.7, 33.25], [35.76, 33.3], [35.81, 33.36], [35.845, 33.405]], at=0.5, dash=[2, 1.4]),
        mv(7, 'israel', '17:22–24', 'Through Galilee and back to Capernaum', [[35.69, 33.23], [35.63, 33.12], [35.6, 33.0], [35.58, 32.9]], at=0.5),
    ],
    'symbols': [
        sym('loaves', [EAST[0] + 0.012, EAST[1] - 0.012], 'Seven loaves and a few fish: the 4,000 fed', '15:32–38', moves=[2], label='4,000 fed'),
        sym('keys', [35.705, 33.255], 'Peter\'s confession: "the keys of the kingdom of heaven"', '16:16–19', moves=[5], offset=[10, -8]),
        sym('sun', [35.86, 33.42], 'Transfigured: "His face shone like the sun"', '17:2', moves=[6]),
    ],
    'notes': [
        {'h': 'Into Gentile country', 'p': [
            'These chapters take Jesus beyond Jewish Galilee: to the Phoenician coast, the Greek cities of the Decapolis, and the pagan shrine-town of Caesarea Philippi. '
            'The second feeding, of the 4,000 with seven loaves, probably took place on the eastern, Gentile shore, a sign alongside the first among the villages of Israel.']},
        {'h': 'At the gates of Hades', 'p': [
            'The cave at Banias was thought to lead down to the underworld. Against that backdrop Jesus says, "on this rock I will build My church, and the gates of Hades will not prevail against it" (16:18).']},
    ],
    'sources': 'Scripture: Berean Standard Bible (public domain). Places: OpenBible.info Bible Geocoding Data (CC BY 4.0) and standard identifications, as noted for each place. Terrain: Terrain Tiles on AWS Open Data (Mapzen). Street map © OpenStreetMap contributors. Imagery © Esri. Map labels and streams: OpenFreeMap (OpenMapTiles, OpenStreetMap). Routes are approximate. Map engine: MapLibre GL.',
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
        if m.get('also'):
            e['also'] = m['also']
        idx['maps'].append(e)
    order = ['GEN', 'EXO', 'JOS', 'JDG', 'MAT']
    idx['maps'].sort(key=lambda e: (order.index(e['book']) if e['book'] in order else 99, e['c'], e['v']))
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('%d maps written' % len(MAPS_OUT))


main()
