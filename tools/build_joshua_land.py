#!/usr/bin/env python3
"""Joshua's general map (book map), so every place in Joshua can be tapped in the text.

    python3 tools/build_joshua_land.py && python3 tools/check_maps.py

- josh-land  "The Land in the Days of Joshua": the land west and east of the Jordan, with the tribes,
             every place named in Joshua (red) and a few other places of the time for context (black).

It is a book map ("bookwide"): its names are tappable in every chapter of Joshua that has no map of its own
for them. The places named in Joshua come from data/maps/places/JOS.json (OpenBible.info, CC BY 4.0), with
the BSB spelling where OpenBible uses another, plus the springs, valleys and regions OpenBible ties to Joshua.
The tribe names are labels only: their areas are approximate, and the tribal maps (Joshua 13–19) draw them.
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

# OpenBible's name → the BSB spelling in Joshua
RENAME = {'Timnath-heres': 'Timnath-serah', 'Beth-shan': 'Beth-shean', 'Baal-meon': 'Beth-baal-meon', 'Shaalbim': 'Shaalabbin',
          'Lahmam': 'Lahmas', 'Dilean': 'Dilan', 'En-dor': 'Endor', 'Mareal': 'Maralah', 'Yiron': 'Iron', 'Zela': 'Zelah'}
# other forms used in the text (the first place of that name gets them)
AKA = {'Jerusalem': ['Jebus'], 'Hebron': ['Kiriath-arba'], 'Bethel': ['Luz'], 'Debir': ['Kiriath-sepher'],
       'Kiriath-jearim': ['Kiriath-baal', 'Baalah'], 'Lower Beth-horon': ['Beth-horon'], 'Mount Hermon': ['Hermon'],
       'Mount Tabor': ['Tabor'], 'Gebal': ['Gebalites'], 'Dor': ['Naphoth-dor'], 'Madmannah': ['Beth-marcaboth']}
SITE = {'Jerusalem': 'Jerusalem (the City of David)', 'Mount Ebal': 'Jebel Eslamiyeh', 'Mount Gerizim': 'Jebel et-Tor',
        'Mount Hermon': 'Jebel esh-Sheikh', 'Tyre': 'Sur, Lebanon', 'Sidon': 'Saida, Lebanon'}

NOTES = {
    'Jericho': 'The oasis city by its spring, 250 m below sea level, the first city taken west of the Jordan (2; 6). Excavations at Tell es-Sultan have found a long history of walls and destruction; how they fit Joshua 6 is debated, mainly over the date of the conquest.',
    'Gilgal': 'Israel\'s first camp west of the Jordan, where the twelve stones were set up, the men circumcised and the Passover kept (4:19–5:12). The base of the campaigns until the land was divided at Shiloh.',
    'Ai': '"The ruin," east of Bethel. Defeated at first because of Achan\'s sin, then taken by ambush (7–8). Et-Tell is the usual identification; Khirbet el-Maqatir nearby is another proposal.',
    'Bethel': 'Next to Ai (7:2; 8:9), formerly Luz (18:13). Its king is among the defeated (12:16); on the border of Benjamin and Ephraim.',
    'Gibeon': 'The great Hivite city whose people tricked Israel into a treaty (9). When five Amorite kings attacked it, Joshua marched all night from Gilgal; "Sun, stand still over Gibeon" (10:12).',
    'Jerusalem': 'Jebus, the city of Adoni-zedek, who led the five kings against Gibeon (10:1–5). Its king was defeated, but Judah could not drive out the Jebusites (15:63).',
    'Hebron': 'Also Kiriath-arba, the city of the Anakim. Caleb asked for this hill country at 85 and took it (14:6–15; 15:13–14). A city of refuge (20:7).',
    'Debir': 'Also Kiriath-sepher, "town of the scroll." Othniel took it and won Caleb\'s daughter Achsah (15:15–17).',
    'Lachish': 'A great city of the Shephelah, taken in two days in the southern campaign (10:31–32). In the Amarna letters its king wrote to Pharaoh.',
    'Hazor': '"The head of all those kingdoms" (11:10). Jabin of Hazor led the northern alliance; Joshua burned the city. The huge mound has a destruction layer with signs of a great fire in the Late Bronze Age.',
    'Shechem': 'In the pass between Ebal and Gerizim, a city of refuge (20:7). Here Joshua gathered all the tribes to renew the covenant: "As for me and my house, we will serve the LORD" (24:1, 15); Joseph\'s bones were buried here (24:32).',
    'Mount Ebal': 'Joshua built an altar on Mount Ebal, wrote a copy of the Law on stones, and read the blessings and curses to all Israel (8:30–35). An early Iron Age stone structure on the mountain has been interpreted as this altar.',
    'Mount Gerizim': 'The mount of blessing, facing Ebal across the valley of Shechem (8:33).',
    'Shiloh': 'The Tabernacle was set up here, and the rest of the land was divided by lot before the LORD (18:1–10). The centre of Israel\'s worship until the days of Eli and Samuel.',
    'Timnath-serah': 'Joshua\'s own inheritance in the hill country of Ephraim, where he was buried (19:50; 24:30).',
    'Kadesh-barnea': 'The oasis from which Moses sent the twelve spies; Caleb recalls it at 85 (14:6–7). The southern limit of Joshua\'s campaigns (10:41).',
    'Beersheba': 'The southern end of the land; one of the towns of Simeon within Judah (19:2).',
    'Gaza': 'The south-west limit of Joshua\'s campaign (10:41); one of the five Philistine cities left unconquered (13:3).',
    'Ashdod': 'One of the five cities of the Philistines; some Anakim remained here, at Gaza and Gath (11:22; 13:3).',
    'Ashkelon': 'One of the five cities of the Philistines (13:3).',
    'Gath': 'One of the five cities of the Philistines, where Anakim remained (11:22), later the home of Goliath.',
    'Ekron': 'One of the five cities of the Philistines (13:3), on Judah\'s northern border (15:11).',
    'Gezer': 'Its king Horam came to help Lachish and was defeated (10:33), but the Canaanites of Gezer were not driven out (16:10).',
    'Makkedah': 'The five Amorite kings hid in the cave here and were brought out and killed (10:16–27).',
    'Azekah': 'On the road down from Beth-horon. The LORD threw down hailstones on the fleeing Amorites "as far as Azekah" (10:10–11).',
    'Lower Beth-horon': 'The pass of Beth-horon, the road down from the hill country to the Valley of Aijalon, where the Amorites fled from Gibeon (10:10–11).',
    'Upper Beth-horon': 'The upper town of the Beth-horon pass, on the border of Ephraim (16:5).',
    'Aijalon': '"O moon, over the Valley of Aijalon" (10:12). The valley opens west of the Beth-horon pass.',
    'Megiddo': 'Guarding the pass into the Jezreel Valley; its king was defeated (12:21), but the Canaanites stayed there (17:11–12).',
    'Beth-shean': 'At the junction of the Jezreel and Jordan valleys. In Joshua\'s age an Egyptian garrison town; its Canaanites had iron chariots (17:11, 16).',
    'Adam': '"The city of Adam, near Zarethan": the waters of the Jordan stood up in a heap here while Israel crossed opposite Jericho (3:16).',
    'Kedesh': 'Kedesh in Galilee, in the hill country of Naphtali, a city of refuge (20:7).',
    'Golan': 'In Bashan, the northern city of refuge east of the Jordan (20:8).',
    'Bezer': 'In the wilderness on the plateau, the city of refuge of Reuben (20:8).',
    'Ramoth': 'Ramoth in Gilead, the city of refuge of Gad (20:8).',
    'Heshbon': 'The capital of Sihon king of the Amorites, defeated by Moses (12:2; 13:10).',
    'Ashtaroth': 'With Edrei, a royal city of Og king of Bashan (12:4; 13:12).',
    'Edrei': 'With Ashtaroth, a royal city of Og king of Bashan (12:4).',
    'Mount Hermon': 'The northern limit of the conquest, "from Baal-gad in the Valley of Lebanon below Mount Hermon" (11:17); about 2,800 m.',
    'Dan': 'Leshem, taken by the tribe of Dan when its land in the south proved too small, and renamed Dan (19:47).',
    'Shittim': 'Abel-shittim, Israel\'s last camp east of the Jordan; from here Joshua sent the two spies to Jericho (2:1; 3:1). Often identified with Tall el-Hammam.',
    'Valley of Achor': '"The Valley of Trouble," where Achan was stoned and a heap of stones raised (7:24–26). Hosea 2:15 promises it will become "a door of hope."',
    'Merom': 'By "the waters of Merom" the northern kings camped together, and there Joshua fell on them suddenly (11:5–7).',
    'Madon': 'Jobab king of Madon joined Jabin\'s northern alliance (11:1).',
    'Baal-gad': 'In the Valley of Lebanon below Mount Hermon: the northern limit of Joshua\'s conquests (11:17; 12:7).',
    'Mahanaim': 'On the border of Gad and the half-tribe of Manasseh (13:26, 30); a Levitical city (21:38).',
    'Succoth': 'In the Jordan Valley, given to Gad (13:27).',
    'Hormah': 'Its king is among the 31 kings defeated (12:14); a town of Simeon (19:4).',
    'Arad': 'Its king is among the 31 kings defeated (12:14).',
    'Ziklag': 'A town of Simeon in the Negev (19:5), later David\'s base.',
    'Beth-shemesh': 'On Judah\'s northern border (15:10), a Levitical city (21:16).',
    'Kiriath-jearim': 'One of the four Gibeonite cities (9:17), on the border of Judah and Benjamin (15:9).',
    'Joppa': 'The port at the edge of Dan\'s territory (19:46).',
    'Sidon': '"Greater Sidon" was the limit of the pursuit after the battle at the waters of Merom (11:8).',
    'Tyre': '"The fortified city of Tyre" on Asher\'s border (19:29).',
    'Mount Carmel': 'The ridge on Asher\'s south-western border (19:26); "Jokneam in Carmel" lay at its foot (12:22). (The Carmel of 15:55 is a town in Judah.)',
    'Pisgah': 'The slopes of Pisgah, from which Moses saw the land (12:3; 13:20; Deuteronomy 34:1).',
    'Libnah': 'Taken in the southern campaign (10:29–30); later a Levitical city (21:13).',
    'Eglon': 'Its king Debir joined the five kings against Gibeon (10:3); taken in the southern campaign (10:34–35).',
    'Jarmuth': 'Its king Piram joined the five kings against Gibeon (10:3).',
}

# springs, valleys and places OpenBible ties to Joshua that the places layer leaves out
EXTRA = [
    {'n': 'Shittim', 'll': [35.67368, 31.84018], 'c': 1, 'm': 'Tall el-Hammam?', 'u': 'af64fb3/shittim', 'f': '2:1'},
    {'n': 'Valley of Achor', 'll': [35.38333, 31.71667], 'c': 1, 'm': 'el-Buqei\'a', 'u': 'a31492f/valley-of-achor', 'f': '7:24'},
    {'n': 'Ramoth', 'll': [36.01499, 32.49985], 'c': 1, 'm': 'Tell er-Rumeith', 'u': 'a95147f/ramoth-3', 'f': '20:8'},
    {'n': 'Merom', 'll': [35.43778, 32.97889], 'c': 1, 'm': 'the waters of Merom: Ein Meron?', 'u': 'a6ee047/waters-of-merom', 'f': '11:5'},
    {'n': 'Madon', 'll': [35.43235, 33.07678], 'c': 0, 'm': 'near Meron?', 'u': 'a6c2936/madon', 'f': '11:1'},
    {'n': 'Baal-gad', 'll': [35.85, 33.4], 'c': 0, 'm': 'below Mount Hermon', 'u': 'ae12e43/baal-gad', 'f': '11:17'},
    {'n': 'En-rogel', 'll': [35.23599, 31.7672], 'c': 2, 'm': 'Bir Ayyub, Jerusalem', 'u': 'af9cfc9/en-rogel', 'f': '15:7'},
    {'n': 'En-shemesh', 'll': [35.27013, 31.77406], 'c': 1, 'm': 'Ein Haud', 'u': 'a34e870/en-shemesh', 'f': '15:7'},
    {'n': 'Nephtoah', 'll': [35.19661, 31.79439], 'c': 1, 'm': 'Lifta', 'u': 'ac1fef1/nephtoah', 'f': '15:9'},
    {'n': 'En-gedi', 'll': [35.38333, 31.45], 'c': 2, 'm': 'Ein Gedi', 'u': 'a51df0e/engedi', 'f': '15:62'},
    {'n': 'Adummim', 'll': [35.36151, 31.8175], 'c': 1, 'm': 'Ma\'ale Adummim', 'u': 'acf8790/adummim', 'f': '15:7',
     'note': 'The "Ascent of Adummim," the red road climbing from the Jordan Valley toward Jerusalem, on Judah\'s border (15:7).'},
    {'n': 'Akrabbim', 'll': [35.13126, 30.9066], 'c': 1, 'm': 'Ma\'ale Akrabbim', 'u': 'a39267b/akrabbim', 'f': '15:3',
     'note': 'The "Ascent of Scorpions" on Judah\'s southern border (15:3).'},
]

CONTEXT = [
    {'n': 'Mount Nebo', 'll': [35.7253, 31.7678], 'c': 2, 'm': 'Jebel Siyagha', 'k': 'mount',
     'note': 'Where Moses saw the land and died before Joshua led Israel across (Deuteronomy 34:1–9; Joshua 1:1–2).'},
    {'n': 'Pella', 'll': [35.6156, 32.4497], 'c': 2, 'm': 'Tabaqat Fahl',
     'note': 'A Canaanite city east of the Jordan, Pihilu in the Amarna letters of the 14th century BC.'},
    {'n': 'Damascus', 'll': [36.30639, 33.51111], 'c': 2, 'm': 'Damascus',
     'note': 'The great city of Syria (Upi in Egyptian texts) beyond Mount Hermon, not part of the land allotted.'},
    {'n': 'Kumidi', 'll': [35.8222, 33.6219], 'c': 2, 'm': 'Kamid el-Loz, Lebanon',
     'note': 'An Egyptian administrative centre in the Valley of Lebanon, known from the Amarna letters.'},
    {'n': 'Bethlehem', 'll': [35.20764, 31.70431], 'c': 2, 'm': 'Bethlehem',
     'note': 'Bethlehem of Judah is not in the Hebrew list of Judah\'s towns; the Greek Septuagint includes it with Tekoa (15:59). The Bethlehem of Joshua 19:15 is in Zebulun.'},
]

REGIONS = [
    # the tribes (labels only)
    {'n': 'Asher', 'll': [35.2, 32.98], 'r': 1, 'link': False, 'note': 'The coast and hills from Carmel north toward Sidon (19:24–31).'},
    {'n': 'Naphtali', 'll': [35.5, 33.17], 'r': 1, 'link': False, 'note': 'Upper Galilee, west of the Sea of Chinnereth and the upper Jordan (19:32–39).'},
    {'n': 'Zebulun', 'll': [35.27, 32.78], 'r': 1, 'link': False, 'note': 'Lower Galilee, north of the Jezreel Valley (19:10–16).'},
    {'n': 'Issachar', 'll': [35.45, 32.6], 'r': 1, 'link': False, 'note': 'The eastern Jezreel Valley and the hills toward the Jordan (19:17–23).'},
    {'n': 'Manasseh', 'll': [35.15, 32.4], 'r': 1, 'link': False, 'note': 'The half-tribe west of the Jordan: the hill country around Shechem north to the Jezreel Valley (17:7–11).'},
    {'n': 'Ephraim', 'll': [35.2, 32.1], 'r': 1, 'link': False, 'note': 'The central hill country from Bethel to Shechem, with Shiloh and Timnath-serah (16:5–10).'},
    {'n': 'Benjamin', 'll': [35.31, 31.84], 'r': 1, 'link': False, 'note': 'The small territory between Judah and Ephraim, from Jericho to Jerusalem, with Gibeon, Ramah and Bethel (18:11–28).'},
    {'n': 'Tribe of Dan', 'label': 'Dan', 'll': [34.85, 31.93], 'r': 1, 'link': False, 'note': 'First allotted the Shephelah and coast west of Benjamin, with Zorah, Eshtaol and Aijalon (19:40–46); later the tribe moved north to Leshem (19:47).'},
    {'n': 'Judah', 'll': [35.13, 31.42], 'r': 1, 'link': False, 'note': 'The largest tribe: the hill country around Hebron, the Shephelah, the Negev and the wilderness by the Salt Sea (15).'},
    {'n': 'Simeon', 'll': [34.78, 31.17], 'r': 1, 'link': False, 'note': 'Towns within Judah\'s inheritance in the Negev, around Beersheba (19:1–9).'},
    {'n': 'Reuben', 'll': [35.8, 31.62], 'r': 1, 'link': False, 'note': 'The plateau east of the Salt Sea, from the Arnon north to Heshbon (13:15–23).'},
    {'n': 'Gad', 'll': [35.7, 32.0], 'r': 1, 'link': False, 'note': 'Gilead east of the Jordan, from Heshbon north toward the Sea of Chinnereth (13:24–28).'},
    {'n': 'East Manasseh', 'label': 'Manasseh', 'll': [35.95, 32.62], 'r': 1, 'link': False, 'note': 'The half-tribe east of the Jordan: Bashan and half of Gilead, given by Moses (13:29–31).'},
    # lands and regions
    {'n': 'Negev', 'll': [34.95, 30.85], 'r': 2, 'aka': ['Negeb'], 'note': 'The dry south, from Beersheba toward Kadesh-barnea (10:40; 15:21).'},
    {'n': 'Lebanon', 'll': [35.65, 33.6], 'r': 2, 'note': 'The mountains and land north of Israel, part of the land promised (1:4; 13:5–6) but not taken.'},
    {'n': 'Bashan', 'll': [36.25, 32.95], 'r': 2, 'note': 'The fertile plateau of Og, east of the Sea of Chinnereth, given to the half-tribe of Manasseh (12:4–5; 13:30).'},
    {'n': 'Gilead', 'll': [35.85, 32.3], 'r': 2, 'note': 'The wooded hill country east of the Jordan, divided between Gad and the half-tribe of Manasseh (13:25, 31).'},
    {'n': 'Edom', 'll': [35.55, 30.55], 'r': 2, 'aka': ['Seir'], 'note': 'Seir, the hill country south-east of the Salt Sea given to Esau (24:4). Judah\'s southern border ran along Edom (15:1, 21).'},
    {'n': 'Moab', 'll': [35.85, 31.25], 'r': 2, 'note': 'The plateau east of the Salt Sea, south of the Arnon. Balak king of Moab hired Balaam (24:9).'},
    {'n': 'Ammon', 'll': [36.12, 31.95], 'r': 2, 'aka': ['Ammonites'], 'note': 'The land of the Ammonites, beyond Gad\'s eastern border (13:10, 25).'},
    {'n': 'Land of the Philistines', 'label': 'Land of the\nPhilistines', 'll': [34.48, 31.45], 'r': 2, 'aka': ['Philistines'], 'note': 'The coast of the five Philistine cities, Gaza, Ashdod, Ashkelon, Gath and Ekron, one of the lands "still to be possessed" (13:2–3).'},
    {'n': 'Arabah', 'll': [35.38, 30.85], 'r': 3, 'note': 'The rift valley of the Jordan and the Salt Sea and south toward the Red Sea (11:2, 16; 12:1–3).'},
    {'n': 'Shephelah', 'label': 'Shephelah', 'll': [34.86, 31.68], 'r': 3, 'link': False, 'note': 'The "foothills" (lowland) between the hill country of Judah and the coast (10:40; 15:33).'},
    {'n': 'Geshur', 'll': [35.72, 32.9], 'r': 3, 'aka': ['Geshurites'], 'note': 'A small Aramean kingdom east of the Sea of Chinnereth that Israel did not drive out (13:13).'},
    {'n': 'Maacah', 'll': [35.7, 33.2], 'r': 3, 'aka': ['Maacathites'], 'note': 'A small Aramean kingdom below Mount Hermon, not driven out (13:13).'},
    {'n': 'Galilee', 'll': [35.38, 33.0], 'r': 3, 'hide': True, 'z': 8.5, 'note': 'The hill country of Naphtali, where Kedesh was set apart as a city of refuge (20:7).'},
    {'n': 'Valley of Jezreel', 'll': [35.3, 32.6], 'r': 3, 'hide': True, 'z': 9, 'note': 'The broad valley between Galilee and the hill country of Manasseh, where the Canaanites had iron chariots (17:16).'},
    {'n': 'Valley of Aijalon', 'll': [34.96, 31.87], 'r': 3, 'hide': True, 'z': 9.5, 'note': '"O moon, over the Valley of Aijalon" (10:12).'},
    {'n': 'Jordan', 'll': [35.56, 32.15], 'hide': True, 'z': 8, 'note': 'Israel crossed it on dry ground opposite Jericho while it overflowed its banks at harvest (3–4). It was the eastern border of the land west of the river.'},
    {'n': 'Salt Sea', 'll': [35.49, 31.5], 'hide': True, 'z': 8.5, 'note': 'The Dead Sea, also "the Sea of the Arabah" (3:16), 430 m below sea level.'},
    {'n': 'Sea of Chinnereth', 'll': [35.59, 32.82], 'hide': True, 'z': 9.5, 'note': 'The Sea of Galilee (12:3; 13:27).'},
    {'n': 'Arnon', 'll': [35.65, 31.46], 'hide': True, 'z': 9, 'aka': ['Valley of the Arnon'], 'note': 'The deep gorge into the Salt Sea, the southern border of the land east of the Jordan (12:1–2; 13:9).'},
    {'n': 'Jabbok', 'll': [35.65, 32.17], 'hide': True, 'z': 9.5, 'note': 'The river (Zarqa) bounding Sihon\'s kingdom (12:2).'},
]
WATER = [
    {'n': 'The Great Sea', 's': '(Mediterranean)', 'll': [34.25, 32.45]},
    {'n': 'Sea of Chinnereth', 's': '(Galilee)', 'll': [35.59, 32.83]},
    {'n': 'Salt Sea', 's': '(Dead Sea)', 'll': [35.49, 31.5]},
    {'n': 'Jordan', 's': '', 'll': [35.555, 32.2]},
]

# verses where a linked name means a person (or another place), not the place on the map
EXCEPT = {'Shechem': ['17:2'], 'Gilead': ['17:3'], 'Hepher': ['17:2-3'], 'Tirzah': ['17:3'], 'Japhia': ['10:3'], 'Debir': ['10:3'],
          'Rekem': ['13:21'], 'Dan': ['19:40', '19:48', '21:5', '21:23'], 'Carmel': ['12:22', '19:26'], 'Gilgal': ['12:23'],
          'Baalah': ['15:29'], 'Mount Seir': ['24:4'], 'Rimmon': ['15:32'], 'Jezreel': ['15:56']}
# where two places share a name, the one first named at this verse takes the name's links
PRIMARY = {'Gibeah': '24:33'}


def build():
    verses = book_verses('JOS')
    layer = []
    for f in json.load(open(os.path.join(MAPS, 'places', 'JOS.json'), encoding='utf-8'))['features']:
        p = f['properties']
        n = RENAME.get(p['n'], p['n'])
        q = {'n': n, 'll': f['geometry']['coordinates'], 'c': p['c'], 'm': SITE.get(n, p.get('m') or ''), 'f': p.get('f', '')}
        if p.get('k') == 'mount':
            q['k'] = 'mount'
        if p.get('u'):
            q['u'] = p['u']
        layer.append(q)
    named = layer + [dict(x) for x in EXTRA]
    # where a name is shared, the best-known place comes first and takes the name's links
    named.sort(key=lambda q: (q['n'], PRIMARY.get(q['n']) != q['f'], -q['c'], q['f'] and [int(x) for x in q['f'].split(':')]))
    seen = set()
    for q in named:
        if q['n'] not in seen:
            if q['n'] in AKA:
                q['aka'] = AKA[q['n']]
            if q['n'] in NOTES and 'note' not in q:
                q['note'] = NOTES[q['n']]
        seen.add(q['n'])

    all_names = sorted({x for p in named + REGIONS for x in [p['n']] + p.get('aka', [])}, key=len, reverse=True)

    def occurs(f):
        for c, v, t in verses:
            tt = t
            for longer in all_names:
                if len(longer) > len(f) and f in longer:
                    tt = tt.replace(longer, '')
            if re.search(r'(?<![A-Za-z\-])' + re.escape(f) + r'(?![A-Za-z]|-[a-z])', tt):
                return True
        return False

    links, aliases, taken = [], {}, set()

    def link(n, aka):
        for f in [n] + (aka or []):
            if f not in taken and occurs(f):
                links.append(f); taken.add(f)
                if f != n:
                    aliases[f] = n

    places = []
    for q in named:
        if q['n'] not in taken:
            link(q['n'], q.get('aka'))
        places.append({k: q[k] for k in ('n', 'll', 'c', 'm', 'u', 'k', 'f', 'note') if q.get(k) or k == 'c'})
    regs = []
    for r in REGIONS:
        regs.append({k: r[k] for k in ('n', 'label', 'll', 'r', 'hide', 'z', 'note') if k in r})
        if r.get('link', True):
            link(r['n'], r.get('aka'))
    missing = [q['n'] for q in named if q['n'] not in taken and not any(a in taken for a in q.get('aka', []))]
    if missing:
        print('not found in the text:', ', '.join(sorted(set(missing))))

    return {
        'id': 'josh-land', 'title': 'The Land in the Days of Joshua', 'ref': 'Joshua', 'anchor': {'book': 'JOS', 'c': 1, 'v': 1},
        'bookwide': True, 'placesName': 'Joshua', 'siteLabel': 'Site', 'groupsLabel': 'Places',
        'bounds': [[34.25, 30.5], [36.6, 33.7]], 'groupLabelZoom': 8.2, 'waterNames': WATER,
        'regions': regs, 'links': links, 'aliases': aliases, 'except': {k: v for k, v in EXCEPT.items() if k in links},
        'groups': [{'id': 'book', 'name': 'Named in Joshua', 'color': RED, 'places': places, 'firstNamed': True},
                   {'id': 'other', 'name': 'Other places of the time', 'color': BLACK, 'places': CONTEXT}],
        'notes': [
            {'h': 'The land in Joshua\'s day', 'p': [
                'Joshua is set at the end of the Late Bronze Age. Canaan was a patchwork of small city-states, each ruled by its own king, such as the 31 kings listed in Joshua 12, '
                'and Egypt held the land loosely through garrisons like Beth-shean. In the Amarna letters (about 1350 BC) the kings of Jerusalem, Shechem, Hazor, Lachish and Gezer write to Pharaoh, '
                'complaining of one another and of raiders called Habiru.',
                'The date of the conquest is debated: 1 Kings 6:1 points to the 15th century BC, while other scholars prefer the 13th. By about 1208 BC the Merneptah Stele names "Israel" as a people in Canaan.']},
            {'h': 'How to use this map', 'p': [
                'This map opens from any place named in Joshua, in chapters that have no map of their own. The red dots are places named in Joshua; the black dots are other places of the time, for context. '
                'The tribe names show roughly where each tribe\'s inheritance lay; the maps of Joshua 13–19 draw the allotments.']},
        ],
        'sources': 'Scripture: Berean Standard Bible (public domain). Places: OpenBible.info Bible Geocoding Data (CC BY 4.0) and standard identifications, as noted for each place. '
                   'Ancient Dead Sea outline from OpenBible.info (CC BY 4.0). Ancient roads are approximations. Terrain: Terrain Tiles on AWS Open Data (Mapzen). '
                   'Street map © OpenStreetMap contributors. Imagery © Esri. Map engine: MapLibre GL.',
    }


def main():
    m = build()
    with open(os.path.join(MAPS, m['id'] + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(m, fh, ensure_ascii=False, indent=1)
    idx_path = os.path.join(MAPS, 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8'))
    idx['maps'] = [e for e in idx['maps'] if e['id'] != m['id']]
    idx['maps'].append({'id': m['id'], 'title': m['title'], 'ref': m['ref'], 'book': 'JOS', 'c': 1, 'v': 1,
                        'bookwide': True, 'links': m['links'], 'aliases': m['aliases'], 'except': m['except']})
    order = ['GEN', 'EXO', 'JOS', 'JDG', 'MAT']
    idx['maps'].sort(key=lambda e: (order.index(e['book']) if e['book'] in order else 99, e['c'], e['v']))
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    n = sum(len(g['places']) for g in m['groups'])
    print('%s: %d places, %d regions, %d tappable names' % (m['id'], n, len(m['regions']), len(m['links'])))


if __name__ == '__main__':
    main()
