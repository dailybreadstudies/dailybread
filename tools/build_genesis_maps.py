#!/usr/bin/env python3
"""Genesis's two general maps (book maps), so every place in Genesis can be tapped in the text.

    python3 tools/build_genesis_maps.py && python3 tools/check_maps.py

- gen-world  "The World of Genesis": the ancient Near East from Egypt to Elam, with the places of Genesis
             outside Canaan (Ur, Haran, Babel, Nineveh, Egypt…) and the great cities of the age for context.
- gen-land   "Canaan in the Time of the Patriarchs": the land the patriarchs walked, with the places named
             in Genesis and the main Middle Bronze Age cities for context.

Both are book maps ("bookwide"): their names are tappable in every chapter of Genesis that has no map of its
own for them. A name is linked to one map only: the land map takes the places in Canaan, the world map the rest.
Coordinates: OpenBible.info where it has the site, otherwise standard identifications (noted in each place).
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_book_maps import book_verses  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAPS = os.path.join(ROOT, 'data', 'maps')
RED, BLACK = '#a0443a', 'var(--dbm-city)'


# OpenBible.info pages checked against data/maps/places/GEN.json (other links are left out rather than guessed)
OB_OK = {'af82614/adullam', 'a7e13e1/ai-1', 'a64f355/bethel-1', 'a112427/bethlehem-1', 'a871210/bozrah-1', 'ae1f807/calah',
         'a69c1d4/damascus', 'a513646/dan', 'ab635e4/dothan', 'a5db1a6/erech', 'aa8edd2/gaza', 'a3f5814/gerar', 'a6d9af3/haran',
         'a85151a/hebron', 'acd9137/heliopolis', 'ac2cef0/kadesh-barnea', 'ae5bfe9/mahanaim', 'aeb9e97/mamre', 'a70fd5d/nineveh',
         'a8a9ff9/penuel', 'a079b21/rameses', 'adf74d4/shechem', 'a98e4d7/sidon', 'a0905b5/succoth-1', 'a70ac98/abel-mizraim',
         'aa572e2/gomorrah', 'a7a5f29/ham-1', 'ae00861/machpelah', 'acdbce0/shur', 'a0aa664/sodom', 'aacfcda/zoar',
         'a8b7a6b/accad', 'ab80fa1/eder-1', 'a6779cd/hobah', 'a15257a/jerusalem', 'aa3ff18/bered'}


def P(n, ll, c, m, note, u=None, aka=None, k=None, link=True):
    d = {'n': n, 'll': ll, 'c': c, 'm': m, 'note': note}
    if u and u in OB_OK: d['u'] = u
    if aka: d['aka'] = aka
    if k: d['k'] = k
    if not link: d['nolink'] = True
    return d


# ─────────────────────────── The land of Canaan ───────────────────────────
LAND_NAMED = [
    P('Shechem', [35.28194, 32.21361], 2, 'Tell Balatah, Nablus', 'In the pass between Ebal and Gerizim. Abram\'s first altar in Canaan (12:6–7); Jacob bought land here (33:18–20); Simeon and Levi\'s revenge (34). Its Middle Bronze Age walls and gate still stand.', 'adf74d4/shechem'),
    P('Bethel', [35.24139, 31.92278], 2, 'Beitin', 'Abram\'s altar "with Bethel to the west and Ai to the east" (12:8). Here Jacob dreamed of the ladder and renamed Luz "Bethel", house of God (28:19; 35:6–15).', 'a64f355/bethel-1', aka=['Luz']),
    P('Ai', [35.26111, 31.91694], 2, 'et-Tell', 'East of Bethel (12:8; 13:3).', 'a7e13e1/ai-1'),
    P('Hebron', [35.10222, 31.52509], 2, 'Tel Rumeida', 'Also Kiriath-arba (23:2). Abraham, Isaac and Jacob lived here, and Sarah died here. A Middle Bronze Age city wall has been excavated on the tell.', 'a85151a/hebron', aka=['Kiriath-arba']),
    P('Mamre', [35.10534, 31.55654], 2, 'Ramat el-Khalil', '"The Oaks of Mamre at Hebron," where Abram settled (13:18) and received the three visitors (18:1). Herod later enclosed the traditional site.', 'aeb9e97/mamre'),
    P('Machpelah', [35.11076, 31.52467], 1, 'Cave of the Patriarchs, Hebron', 'The cave Abraham bought from Ephron the Hittite (23), where Sarah, Abraham, Isaac, Rebekah, Leah and Jacob were buried (49:29–33; 50:13). Herod built the great enclosure that still stands over it.', 'ae00861/machpelah'),
    P('Beersheba', [34.84083, 31.24472], 2, 'Tel Beer Sheva', '"Well of the oath" or "of seven": Abraham\'s covenant with Abimelech (21:31), Isaac\'s well (26:33), and Jacob\'s last stop before Egypt (46:1). The southern limit of the land, "from Dan to Beersheba".', 'ad2f6c2/beersheba-2'),
    P('Gerar', [34.6065, 31.3821], 2, 'Tel Haror', 'Where Abraham and later Isaac lived among the Philistines of Abimelech (20; 26). Tel Haror was a large fortified city in the Middle Bronze Age.', 'a3f5814/gerar'),
    P('Esek', [34.6062, 31.4245], 0, 'near Gerar', '"Contention": the first of Isaac\'s disputed wells (26:20).', 'ae6c1b1/esek'),
    P('Rehoboth', [34.56583, 31.03111], 1, 'Ruheibeh', '"Room": Isaac\'s third well, not disputed. "Now the LORD has made room for us" (26:22).', 'a984753/rehoboth-1'),
    P('Beer-lahai-roi', [34.33333, 30.6875], 0, 'Ain Muweileh?', '"The well of the Living One who sees me," where the angel found Hagar (16:13–14). Isaac later lived nearby (24:62; 25:11).', 'a0bf7f2/beer-lahai-roi'),
    P('Kadesh', [34.42222, 30.64833], 2, 'Ain el-Qudeirat', 'Kadesh, also En-mishpat (14:7): the great oasis of the south, near Beer-lahai-roi (16:14) and on the road toward Shur (20:1).', 'ac2cef0/kadesh-barnea', aka=['En-mishpat']),
    P('Bered', [34.652, 31.097], 0, 'Haluza?', 'Beer-lahai-roi lies "between Kadesh and Bered" (16:14). The site is not known.', 'aa3ff18/bered'),
    P('Salem', [35.2342, 31.7767], 2, 'Jerusalem', 'Melchizedek\'s city (14:18); Psalm 76:2 identifies Salem with Jerusalem (Zion).', 'a15257a/jerusalem'),
    P('Moriah', [35.2355, 31.7778], 1, 'the Temple Mount, Jerusalem', 'Abraham was sent to "the land of Moriah" to offer Isaac (22:2). 2 Chronicles 3:1 places Mount Moriah where Solomon built the Temple.', 'aac1fcf/moriah', k='mount'),
    P('Bethlehem', [35.20764, 31.70431], 2, 'Bethlehem', 'Also Ephrath. Rachel died giving birth to Benjamin "on the way to Ephrath (that is, Bethlehem)" (35:19; 48:7).', 'a112427/bethlehem-1', aka=['Ephrath']),
    P('Migdal-eder', [35.23011, 31.70731], 0, 'near Bethlehem?', '"The tower of the flock," where Jacob camped after Rachel\'s death (35:21). Micah 4:8 links it to the coming king.', 'ab80fa1/eder-1', aka=['Eder']),
    P('Dothan', [35.23986, 32.41353], 2, 'Tel Dotan', 'Where Joseph found his brothers with the flocks and was sold to the Ishmaelite caravan, on the road down to Egypt (37:17–28).', 'ab635e4/dothan'),
    P('Adullam', [35.00167, 31.65167], 2, 'Khirbet esh-Sheikh Madhkur', 'Judah stayed with Hirah the Adullamite (38:1); later David\'s cave refuge (1 Samuel 22:1).', 'af82614/adullam'),
    P('Timnah', [35.13384, 31.40945], 0, 'in the hill country of Judah', 'Judah went up to his sheepshearers at Timnah (38:12–13).', 'ae3f164/timnah-3'),
    P('Enaim', [35.01237, 31.68768], 1, 'near Adullam', 'Where Tamar sat by the road to Timnah (38:14, 21).', 'a26921e/enaim'),
    P('Chezib', [34.95302, 31.64207], 1, 'Achzib of Judah', 'Where Shelah, Judah\'s third son, was born (38:5).', 'a2270e4/chezib'),
    P('Gaza', [34.4644, 31.504], 2, 'Tell Harube', 'The south-west corner of Canaan\'s border (10:19).', 'aa8edd2/gaza'),
    P('Sidon', [35.37194, 33.56099], 2, 'Saida, Lebanon', 'Canaan\'s firstborn (10:15) and the northern limit of his land (10:19); Zebulun\'s border reaches toward it (49:13).', 'a98e4d7/sidon'),
    P('Dan', [35.652, 33.249], 2, 'Tel Dan', 'Abram pursued the four kings "as far as Dan" (14:14), the city then called Laish. Its mudbrick Middle Bronze Age gate, with its arch, still stands.', 'a513646/dan', link=False),   # elsewhere Dan is Jacob's son
    P('Damascus', [36.30639, 33.51111], 2, 'Damascus', 'Home of Eliezer, Abram\'s steward (15:2); Abram\'s pursuit ended past it at Hobah (14:15).', 'a69c1d4/damascus'),
    P('Succoth', [35.62118, 32.1966], 2, 'Tell Deir Alla', '"Booths": Jacob built shelters for his livestock here after meeting Esau (33:17).', 'a0905b5/succoth-1'),
    P('Penuel', [35.69211, 32.18702], 2, 'Tell edh-Dhahab esh-Sherqiyeh', 'Also Peniel, "the face of God", where Jacob wrestled through the night by the Jabbok and was named Israel (32:24–31).', 'a8a9ff9/penuel', aka=['Peniel']),
    P('Mahanaim', [35.68667, 32.18575], 2, 'Tell edh-Dhahab el-Gharbi', '"Two camps": angels of God met Jacob on his way home (32:1–2).', 'ae5bfe9/mahanaim'),
    P('Mizpah', [35.77702, 32.11851], 1, 'in Gilead', 'The heap of witness Jacob and Laban raised, "The LORD watch between you and me" (31:45–49); also Galeed.', 'a8cb9fa/mizpah-1', aka=['Galeed']),
    P('Abel-mizraim', [35.53045, 31.91489], 1, 'near the mouth of the Jordan?', '"The mourning of Egypt," at the threshing floor of Atad, where Joseph and the Egyptians mourned Jacob for seven days (50:10–11).', 'a70ac98/abel-mizraim', aka=['Atad']),
    P('Sodom', [35.535, 31.252], 0, 'Bab edh-Dhra? (site disputed)', 'The city of the plain where Lot settled, destroyed in Genesis 19. Bab edh-Dhra by the south of the Dead Sea and Tall el-Hammam north of it are the main proposals.', 'a0aa664/sodom'),
    P('Gomorrah', [35.565, 31.135], 0, 'Numeira? (site disputed)', 'Destroyed with Sodom (19:24–28). Numeira, south of Bab edh-Dhra, is one proposal.', 'aa572e2/gomorrah'),
    P('Zoar', [35.48766, 31.0369], 1, 'es-Safi?', 'Once Bela (14:2); the small town Lot fled to (19:20–23).', 'aacfcda/zoar'),
    P('Ashteroth-karnaim', [36.01583, 32.80417], 1, 'Tell Ashtara and Sheikh Sa\'d', 'Where the four kings defeated the Rephaites (14:5).', 'a6fea11/ashteroth-karnaim'),
    P('Ham', [35.81238, 32.51421], 1, 'Tell Ham', 'Home of the Zuzites, defeated by the four kings (14:5).', 'a7a5f29/ham-1', link=False),   # elsewhere Ham is Noah's son
    P('Shaveh-kiriathaim', [35.68611, 31.54056], 0, 'near Khirbet el-Qureiyat?', 'Where the Emites were defeated (14:5).', 'ad54201/shaveh-kiriathaim'),
    P('Hazazon-tamar', [35.39, 31.46], 1, 'En-gedi (2 Chronicles 20:2)?', 'Home of the Amorites defeated by the four kings (14:7).', 'a51df0e/hazazon-tamar-2'),
    P('Bozrah', [35.60392, 30.74584], 2, 'Buseira', 'A city of the early kings of Edom (36:33).', 'a871210/bozrah-1'),
]
LAND_CONTEXT = [
    P('Hazor', [35.5681, 33.0172], 2, 'Tel Hazor', 'The greatest city of Canaan in the Middle Bronze Age, about 80 hectares; it appears in the Mari letters of the 18th century BC.', link=False),
    P('Megiddo', [35.1844, 32.5853], 2, 'Tel Megiddo', 'The fortress guarding the pass of the Way of the Sea into the Jezreel Valley.', link=False),
    P('Jericho', [35.4436, 31.8711], 2, 'Tell es-Sultan', 'The oasis city by its spring; walled long before Abraham.', link=False),
    P('Gezer', [34.9206, 31.8592], 2, 'Tel Gezer', 'A Middle Bronze Age city with massive gates and a row of standing stones.', link=False),
    P('Lachish', [34.8486, 31.5647], 2, 'Tel Lachish', 'A great city of the Shephelah.', link=False),
    P('Ashkelon', [34.5506, 31.6644], 2, 'Tel Ashkelon', 'A port city whose Middle Bronze Age arched mudbrick gate is one of the oldest of its kind.', link=False),
    P('Joppa', [34.75304, 32.05448], 2, 'Jaffa', 'The port of the central coast.', link=False),
    P('Shiloh', [35.2895, 32.0557], 2, 'Khirbet Seilun', 'A walled site of the Middle Bronze Age, later home of the Tabernacle. (In 49:10 "Shiloh" is read by most as a title, not this town.)', link=False),
    P('Acco', [35.0692, 32.9214], 2, 'Tel Akko', 'The northern port, with a Middle Bronze Age rampart.', link=False),
    P('Tyre', [35.19611, 33.27083], 2, 'Sur, Lebanon', 'The island port of the Phoenician coast.', link=False),
    P('Beth-shean', [35.5025, 32.5045], 2, 'Tel Beth-shean', 'Guarding the junction of the Jezreel and Jordan valleys.', link=False),
    P('Arad', [35.1267, 31.2803], 2, 'Tel Arad', 'A great walled town of the Early Bronze Age, already in ruins in Abraham\'s day.', link=False),
    P('Tall el-Hammam', [35.6733, 31.8403], 1, 'Tall el-Hammam', 'A large Middle Bronze Age city on the plain north-east of the Dead Sea; its excavators identify it with Sodom.', link=False),
]
LAND_REGIONS = [
    {'n': 'Canaan', 'll': [35.12, 32.05], 'r': 1, 'note': 'The land promised to Abraham and his offspring (12:5–7; 17:8), from Sidon to Gaza and toward Sodom (10:19). In the Middle Bronze Age it was a land of walled city-states, with Egypt as the great power to the south.'},
    {'n': 'Negev', 'll': [34.85, 30.95], 'r': 1, 'note': 'The dry south, where Abraham and Isaac moved between wells and grazing (12:9; 13:1; 20:1; 24:62).'},
    {'n': 'Gilead', 'll': [35.78, 32.32], 'r': 1, 'note': 'The wooded hills east of the Jordan: Laban caught up with Jacob here (31:21–25), and the Ishmaelite caravan came from Gilead with balm (37:25).'},
    {'n': 'Edom', 'll': [35.5, 30.45], 'r': 1, 'aka': ['Seir', 'Mount Seir'], 'note': 'Seir, the hill country south-east of the Dead Sea, where Esau settled: "Esau (that is, Edom) settled in the hill country of Seir" (36:8). The Horites lived there first (36:20).'},
    {'n': 'Moab', 'll': [35.78, 31.38], 'r': 2, 'note': 'The plateau east of the Dead Sea, named for Moab, son of Lot\'s elder daughter (19:37).'},
    {'n': 'Ammon', 'll': [35.98, 31.95], 'r': 2, 'aka': ['Ammonites'], 'note': 'The land of the Ammonites, descended from Ben-ammi, son of Lot\'s younger daughter (19:38).'},
    {'n': 'Bashan', 'll': [36.05, 32.95], 'r': 2, 'note': 'The fertile plateau east of the Sea of Galilee; Ashteroth-karnaim was its city (14:5).', 'link': False},
    {'n': 'Land of the Philistines', 'label': 'Land of the\nPhilistines', 'll': [34.5, 31.3], 'r': 2, 'note': 'The coast around Gerar where Abimelech ruled (21:32, 34; 26:1). The name is the one Israel later used for this coast.'},
    {'n': 'Wilderness of Paran', 'label': 'Wilderness\nof Paran', 'll': [34.75, 30.45], 'r': 2, 'note': 'The desert south of Beersheba where Ishmael grew up with Hagar (21:21).'},
    {'n': 'Plain of the Jordan', 'label': 'Plain of\nthe Jordan', 'll': [35.6, 31.88], 'r': 3, 'note': 'The well-watered "circle of the Jordan" that Lot chose (13:10–12).'},
    {'n': 'Valley of Siddim', 'll': [35.48, 31.2], 'r': 3, 'hide': True, 'z': 9, 'note': '"The Valley of Siddim (that is, the Salt Sea)," full of tar pits, where the five kings fought the four (14:3, 10).'},
    {'n': 'Salt Sea', 'll': [35.49, 31.5], 'r': 2, 'hide': True, 'z': 8.5, 'note': 'The Dead Sea (14:3), 430 m below sea level, the lowest place on earth.'},
    {'n': 'Jordan', 'll': [35.56, 32.15], 'hide': True, 'z': 8, 'note': 'The river of the land (13:10–11; 32:10; 50:10–11). Jacob crossed it "with only my staff" (32:10).'},
    {'n': 'Jabbok', 'll': [35.6, 32.17], 'hide': True, 'z': 9.5, 'note': 'The river (Zarqa) where Jacob wrestled at the ford (32:22).'},
]

# ─────────────────────────── The ancient Near East ───────────────────────────
WORLD_NAMED = [
    P('Ur', [46.10444, 30.96222], 2, 'Tell el-Muqayyar, southern Iraq', 'Ur of the Chaldeans, Abram\'s home (11:28–31): a great Sumerian city of the moon-god Nanna, with its ziggurat and royal tombs (excavated by Leonard Woolley, 1922–34).', 'aa01373/ur-1'),
    P('Haran', [39.03278, 36.86444], 2, 'Harran, south-east Turkey', 'Where Terah settled and died (11:31–32), and the home of Rebekah\'s family and of Laban (24; 29–31). A city of the moon-god Sin on the road from Mesopotamia to Syria.', 'a6d9af3/haran'),
    P('Babel', [44.42222, 32.54333], 2, 'Babylon, Iraq', 'Nimrod\'s first city (10:10) and the tower of Genesis 11. Babylon rose under Hammurabi in the 18th century BC.', 'a217d18/babylon-1', aka=['Babylon']),
    P('Erech', [45.63611, 31.32222], 2, 'Uruk (Warka), Iraq', 'One of the world\'s first true cities, home of the Gilgamesh legend (10:10).', 'a5db1a6/erech'),
    P('Accad', [44.39194, 33.02556], 0, 'unknown, near Babylon?', 'Akkad, capital of Sargon\'s empire about 2300 BC; its site has not been found (10:10).', 'a8b7a6b/accad'),
    P('Nineveh', [43.1528, 36.3594], 2, 'Mosul, Iraq', 'Built by Nimrod (10:11); later the capital of Assyria.', 'a70fd5d/nineveh'),
    P('Calah', [43.32889, 36.09806], 2, 'Nimrud, Iraq', 'Another of Nimrod\'s Assyrian cities (10:11–12).', 'ae1f807/calah'),
    P('Hobah', [37.06667, 34.25], 0, 'north of Damascus', 'Where Abram\'s pursuit of the four kings ended (14:15).', 'a6779cd/hobah'),
    P('On', [31.3075, 30.12944], 2, 'Heliopolis (Ain Shams), Cairo', 'Joseph married Asenath, daughter of Potiphera, priest of On (41:45, 50; 46:20): the city of the sun-god Ra.', 'acd9137/heliopolis', link=False),
    P('Rameses', [31.83422, 30.79937], 2, 'Qantir, the eastern Delta', '"The land of Rameses," the best of Egypt, given to Jacob\'s family (47:11). The name is the one the region bore later; under the Hyksos the city here was Avaris.', 'a079b21/rameses'),
    P('Shur', [32.95667, 30.49333], 1, 'the desert east of Egypt', 'The "wilderness of Shur", on the way to Egypt (16:7; 20:1; 25:18).', 'acdbce0/shur'),
]
WORLD_CONTEXT = [
    P('Mari', [40.8886, 34.5497], 2, 'Tell Hariri, Syria', 'A great Euphrates city whose archive of 20,000 tablets (18th century BC) mentions Hazor, Laish and names like those of the patriarchs.', link=False),
    P('Ebla', [36.798, 35.798], 2, 'Tell Mardikh, Syria', 'A Syrian kingdom of the third millennium BC with a royal archive of some 17,000 tablets.', link=False),
    P('Ugarit', [35.7856, 35.6019], 2, 'Ras Shamra, Syria', 'A port whose later tablets (14th–13th centuries BC) are the main source for Canaanite religion and language.', link=False),
    P('Byblos', [35.6481, 34.1208], 2, 'Jbeil, Lebanon', 'The old port of the cedar trade with Egypt.', link=False),
    P('Carchemish', [38.0153, 36.8297], 2, 'Karkamış, on the Euphrates', 'The great crossing of the Euphrates on the road from Mesopotamia to Syria.', link=False),
    P('Aleppo', [37.1625, 36.1997], 2, 'Aleppo, Syria', 'Capital of the kingdom of Yamhad in the 18th century BC.', link=False),
    P('Ashur', [43.2625, 35.4567], 2, 'Qal\'at Sherqat, Iraq', 'The old capital of Assyria, whose merchants traded tin and cloth as far as Anatolia in the patriarchs\' age.', link=False),
    P('Susa', [48.2575, 32.1894], 2, 'Shush, Iran', 'Capital of Elam, the land of Chedorlaomer (14:1).', link=False),
    P('Nippur', [45.2308, 32.1261], 2, 'Nippur, Iraq', 'The religious centre of Sumer. Some identify it with Calneh (10:10).', link=False),
    P('Hattusa', [34.615, 40.0197], 2, 'Boğazkale, Turkey', 'Capital of the Hittite kingdom from the 17th century BC.', link=False),
    P('Kanesh', [35.6339, 38.8506], 2, 'Kültepe, Turkey', 'An Assyrian trading colony whose 23,000 letters (20th–18th centuries BC) show caravans like those of Genesis.', link=False),
    P('Memphis', [31.2547, 29.8447], 2, 'Mit Rahina, Egypt', 'The old capital of Egypt at the head of the Delta.', link=False),
    P('Giza', [31.1342, 29.9792], 2, 'the pyramids of Giza', 'The great pyramids were already some 500 years old in Abraham\'s day.', link=False, k='mount'),
    P('Beni Hasan', [30.8833, 27.9333], 2, 'Beni Hasan, Egypt', 'The tomb of Khnumhotep II (about 1890 BC) shows a party of 37 "Asiatics" with donkeys and coloured cloaks arriving in Egypt.', link=False),
]
WORLD_REGIONS = [
    {'n': 'Shinar', 'll': [45.0, 32.1], 'r': 1, 'note': 'Babylonia, southern Mesopotamia: the plain where Babel was built (10:10; 11:2; 14:1).'},
    {'n': 'Assyria', 'll': [43.3, 35.9], 'r': 1, 'note': 'Northern Mesopotamia on the Tigris (2:14; 10:11).'},
    {'n': 'Elam', 'll': [48.2, 32.7], 'r': 1, 'note': 'South-west Iran, the kingdom of Chedorlaomer (14:1, 9).'},
    {'n': 'Paddan-aram', 'll': [39.6, 36.3], 'r': 1, 'aka': ['Aram-naharaim', 'Mesopotamia'], 'note': '"The field of Aram" around Haran in upper Mesopotamia, home of Rebekah and of Laban (25:20; 28:2; 24:10).'},
    {'n': 'Canaan', 'll': [35.15, 31.9], 'r': 1, 'link': False, 'note': 'The land promised to Abraham. See the map of Canaan in the time of the patriarchs.'},
    {'n': 'Egypt', 'll': [31.0, 28.6], 'r': 1, 'z': 6, 'note': 'Abram went down in famine (12:10); Joseph was sold there and rose to rule it (37–41); Jacob\'s family settled in Goshen (46–47). In the Middle Kingdom and Hyksos periods Semites from Canaan lived in the eastern Delta in large numbers.'},
    {'n': 'Goshen', 'll': [31.75, 30.65], 'r': 2, 'z': 8, 'note': 'The pasture land of the eastern Delta given to Jacob\'s family (45:10; 47:6). Excavations at Tell el-Dab\'a (Avaris) found a large Canaanite population there.'},
    {'n': 'Ararat', 'll': [44.3, 39.4], 'r': 1, 'aka': ['mountains of Ararat'], 'note': 'Urartu, the highlands of eastern Turkey and Armenia, where the ark came to rest "on the mountains of Ararat" (8:4).'},
    {'n': 'Aram', 'll': [37.4, 34.6], 'r': 2, 'link': False, 'note': 'Syria, the land of the Arameans.'},
    {'n': 'Hittites', 'label': 'Land of Hatti', 'll': [34.9, 39.3], 'r': 2, 'link': False, 'note': 'Central Anatolia, the kingdom of the Hittites. The "sons of Heth" at Hebron (23) were a smaller people of Canaan.'},
    {'n': 'Midian', 'll': [35.4, 28.2], 'r': 2, 'link': False, 'note': 'North-west Arabia, home of the Midianites descended from Abraham and Keturah (25:2–4), who bought Joseph (37:28, 36).'},
    {'n': 'Arabia', 'll': [41.5, 28.5], 'r': 2, 'link': False, 'note': 'The great desert peninsula; Ishmael\'s sons lived from Havilah to Shur (25:18).'},
    {'n': 'Euphrates', 'll': [41.2, 34.6], 'hide': True, 'z': 6, 'note': 'The great river, the eastern limit of the land promised to Abraham (15:18); one of the four rivers of Eden (2:14).'},
    {'n': 'Tigris', 'll': [44.4, 34.2], 'hide': True, 'z': 6, 'note': 'The second great river of Mesopotamia, "the Tigris, which runs east of Assyria" (2:14).'},
]
WORLD_WATER = [
    {'n': 'The Great Sea', 's': '(Mediterranean)', 'll': [28.5, 34.0]},
    {'n': 'Red Sea', 's': '', 'll': [35.6, 26.0]},
    {'n': 'Persian Gulf', 's': '', 'll': [50.2, 27.8]},
    {'n': 'Euphrates', 's': '', 'll': [40.6, 35.0]},
    {'n': 'Tigris', 's': '', 'll': [43.9, 34.6]},
    {'n': 'Nile', 's': '', 'll': [31.3, 27.6]},
    {'n': 'Black Sea', 's': '', 'll': [35.0, 42.6]},
    {'n': 'Caspian Sea', 's': '', 'll': [50.5, 41.0]},
]


# verses where a linked name means a person, not the place
EXCEPT = {'Haran': ['11:26-31'], 'Moab': ['19:37'], 'Seir': ['36:20-21'], 'Edom': ['25:30', '36:1', '36:8', '36:19', '36:43'],
          'Rehoboth': ['10:11', '36:37'], 'Elam': ['10:22'], 'Canaan': ['9:18-27', '10:6', '10:15'], 'Sidon': ['10:15']}


def build():
    verses = book_verses('GEN')
    all_names = sorted({x for p in LAND_NAMED + LAND_CONTEXT + LAND_REGIONS + WORLD_NAMED + WORLD_CONTEXT + WORLD_REGIONS
                        for x in [p['n']] + p.get('aka', [])}, key=len, reverse=True)

    def first(forms):
        for c, v, t in verses:
            for f in forms:
                tt = t
                for longer in all_names:
                    if len(longer) > len(f) and f in longer:
                        tt = tt.replace(longer, '')
                if re.search(r'(?<![A-Za-z\-])' + re.escape(f) + r'(?![A-Za-z]|-[a-z])', tt):
                    return '%d:%d' % (c, v)
        return None

    taken = set()

    def make(mid, title, ref, anchor, named, context, regions, extra):
        links, aliases = [], {}
        book_places, other = [], []

        def link(n, aka):
            if n in taken:
                return False
            hit = False
            for f in [n] + (aka or []):
                if first([f]) and f not in taken:
                    links.append(f); taken.add(f); hit = True
                    if f != n:
                        aliases[f] = n
            return hit

        for p in named:
            q = {k: p[k] for k in ('n', 'll', 'c', 'm', 'u', 'k', 'note') if k in p}
            ref1 = first([p['n']] + p.get('aka', []))
            if ref1:
                q['f'] = ref1
            if not p.get('nolink'):
                link(p['n'], p.get('aka'))
            book_places.append(q)
        for p in context:
            other.append({k: p[k] for k in ('n', 'll', 'c', 'm', 'u', 'k', 'note') if k in p})
        regs = []
        for r in regions:
            d = {k: r[k] for k in ('n', 'label', 'll', 'r', 'hide', 'z', 'note') if k in r}
            if r.get('link', True):
                link(r['n'], r.get('aka'))
            regs.append(d)
        m = {'id': mid, 'title': title, 'ref': ref, 'anchor': anchor, 'bookwide': True, 'placesName': 'Genesis', 'siteLabel': 'Site',
             'regions': regs, 'links': links, 'aliases': aliases, 'groupsLabel': 'Places',
             'except': {k: v for k, v in EXCEPT.items() if k in links},
             'groups': [{'id': 'book', 'name': 'Named in Genesis', 'color': RED, 'places': book_places, 'firstNamed': True},
                        {'id': 'other', 'name': extra['otherName'], 'color': BLACK, 'places': other}]}
        m.update(extra['spec'])
        return m

    land = make('gen-land', 'Canaan in the Time of the Patriarchs', 'Genesis', {'book': 'GEN', 'c': 12, 'v': 1},
                LAND_NAMED, LAND_CONTEXT, LAND_REGIONS, {
        'otherName': 'Other cities of the time (Middle Bronze Age)',
        'spec': {
            'bounds': [[34.0, 30.35], [36.55, 33.6]], 'groupLabelZoom': 7.2,
            'alternates': {'for': 'Sodom', 'bounds': [[35.3, 31.0], [35.85, 31.95]], 'sites': [{'name': 'Tall el-Hammam', 'll': [35.6733, 31.8403]}]},
            'notes': [
                {'h': 'The land in the patriarchs\' day', 'p': [
                    'Most scholars place Abraham, Isaac and Jacob in the Middle Bronze Age (about 2000–1550 BC), though the Bible gives no outside date. '
                    'Canaan was then a land of walled city-states such as Hazor, Shechem, Megiddo and Gezer, with great earth ramparts and gates, while herdsmen like the patriarchs moved between the towns, '
                    'from Shechem through Bethel and Hebron to Beersheba and the Negev. Egypt was the power to the south, and in famine people went down to it for grain.']},
                {'h': 'How to use this map', 'p': [
                    'This map opens from any place in Canaan named in Genesis, in chapters that have no map of their own. The red dots are places named in Genesis; '
                    'the black dots are other cities of the time, for context. Places farther away (Ur, Haran, Babel, Egypt) are on the map of the world of Genesis.']},
            ],
            'sources': 'Scripture: Berean Standard Bible (public domain). Places: OpenBible.info Bible Geocoding Data (CC BY 4.0) and standard identifications, as noted for each place. '
                       'Ancient Dead Sea outline from OpenBible.info (CC BY 4.0). Ancient roads are approximations. Terrain: Terrain Tiles on AWS Open Data (Mapzen). '
                       'Street map © OpenStreetMap contributors. Imagery © Esri. Map engine: MapLibre GL.'}})
    world = make('gen-world', 'The World of Genesis', 'Genesis', {'book': 'GEN', 'c': 1, 'v': 1},
                 WORLD_NAMED, WORLD_CONTEXT, WORLD_REGIONS, {
        'otherName': 'Other cities of the age',
        'spec': {
            'world': True, 'bounds': [[25.5, 24.5], [50.5, 41.0]], 'regionZoom': 4.6, 'waterNames': WORLD_WATER,
            'notes': [
                {'h': 'The world of Genesis', 'p': [
                    'Genesis moves across the whole Fertile Crescent: from Ur and Babel in Mesopotamia, up the Euphrates to Haran, down into Canaan, and on to Egypt. '
                    'In the patriarchs\' age these were linked by trade routes, caravans and letters; Mari, Ebla and Kanesh have left tens of thousands of tablets from these centuries.']},
                {'h': 'How to use this map', 'p': [
                    'This map opens from places outside Canaan named in Genesis. Red dots are places named in Genesis; black dots are other great cities of the age. '
                    'The land of Canaan itself is on its own map, Canaan in the time of the patriarchs.']},
            ],
            'sources': 'Scripture: Berean Standard Bible (public domain). Places: OpenBible.info Bible Geocoding Data (CC BY 4.0) and standard identifications. '
                       'Seas, lakes and rivers: Natural Earth (public domain). Terrain: Terrain Tiles on AWS Open Data (Mapzen). Map engine: MapLibre GL.'}})
    return [land, world]


def main():
    idx_path = os.path.join(MAPS, 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8'))
    for m in build():
        with open(os.path.join(MAPS, m['id'] + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(m, fh, ensure_ascii=False, indent=1)
        idx['maps'] = [e for e in idx['maps'] if e['id'] != m['id']]
        idx['maps'].append({'id': m['id'], 'title': m['title'], 'ref': m['ref'], 'book': 'GEN', 'c': m['anchor']['c'], 'v': m['anchor']['v'],
                            'bookwide': True, 'links': m['links'], 'aliases': m['aliases'], 'except': m['except']})
        n = sum(len(g['places']) for g in m['groups'])
        print('%s: %d places, %d regions, %d tappable names' % (m['id'], n, len(m['regions']), len(m['links'])))
        print('   ', ', '.join(m['links']))
    order = ['GEN', 'EXO', 'JOS', 'JDG', 'MAT']
    idx['maps'].sort(key=lambda e: (order.index(e['book']) if e['book'] in order else 99, e['c'], e['v']))
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
