#!/usr/bin/env python3
"""Judges' general map (book map), so every place in Judges can be tapped in the text.

    python3 tools/build_judges_land.py && python3 tools/check_maps.py

- jdg-land  "The Land in the Days of the Judges": the land west and east of the Jordan, with the tribes,
            every place named in Judges (red) and a few other places of the time for context (black).

It is a book map ("bookwide"): its names are tappable in every chapter of Judges that has no map of its own
for them. The places named in Judges come from data/maps/places/JDG.json (OpenBible.info, CC BY 4.0), with
the BSB spelling where OpenBible uses another, plus the springs, hills and rocks it leaves out (standard
identifications, noted in each place). Built on the same pattern as tools/build_joshua_land.py.
The tribe names are labels only: their areas are approximate.
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

# OpenBible's name → the BSB spelling in Judges
RENAME = {'Beth-shan': 'Beth-shean', 'Kedesh-naphtali': 'Kedesh', 'Nahalal': 'Nahalol'}
# OpenBible places left out: Maon (10:12 has only "Maonites", a people), and the second Aroer (11:33, very uncertain;
# the note on Aroer covers it)
DROP = {'a6845b1/maon', 'af74969/aroer-2', 'a0f8af9/mizpah-1'}   # Mizpah of Gilead is added below under that name
# other forms used in the text (the first place of that name gets them)
AKA = {'Jerusalem': ['Jebus'], 'Hebron': ['Kiriath-arba'], 'Bethel': ['Luz'], 'Debir': ['Kiriath-sepher'], 'Hormah': ['Zephath'],
       'Jericho': ['City of Palms'], 'Dan': ['Laish'], 'Mount Tabor': ['Tabor'], 'Lehi': ['Ramath-lehi', 'En-hakkore'],
       'Kadesh-barnea': ['Kadesh'], 'Mount Sinai': ['Sinai']}
SITE = {'Jerusalem': 'Jerusalem (the City of David)', 'Mount Gerizim': 'Jebel et-Tor', 'Bethlehem': 'Bethlehem',
        'Sidon': 'Saida, Lebanon', 'Moreh': 'Givat HaMoreh (Jebel Dahi)'}

NOTES = {
    'Bezek': 'Judah and Simeon defeated Adoni-bezek here and cut off his thumbs and big toes, as he had done to seventy kings (1:4–7). Khirbet Ibziq in the north is the usual identification; some look for a Bezek nearer Judah.',
    'Jerusalem': 'Jebus. Judah attacked it and set it on fire (1:8), but the Jebusites stayed (1:21). The Levite would not lodge in this "city of foreigners" and went on to Gibeah (19:10–12). David took it later (2 Samuel 5).',
    'Hebron': 'Formerly Kiriath-arba. Judah defeated the three sons of Anak here, and it was given to Caleb (1:10, 20). Samson carried the gates of Gaza "to the top of the mountain overlooking Hebron" (16:3), about 60 km uphill.',
    'Debir': 'Formerly Kiriath-sepher. Othniel took it and won Caleb\'s daughter Achsah, who asked her father for the springs of water (1:11–15). Othniel became the first judge (3:9–11).',
    'Hormah': 'Formerly Zephath. Judah and Simeon devoted it to destruction, and it was renamed Hormah, "devoted" (1:17).',
    'Arad': 'The Kenites, Moses\' in-laws, went up from the City of Palms to the wilderness of Judah near Arad (1:16).',
    'Jericho': 'The City of Palms. The Kenites set out from here (1:16); Eglon king of Moab took it (3:13). Joshua had cursed the rebuilding of its walls (Joshua 6:26; 1 Kings 16:34).',
    'Bethel': 'Formerly Luz. The house of Joseph took it through a man who showed them the way in (1:22–26). Deborah judged between Ramah and Bethel (4:5); the tribes inquired of the LORD here, where the ark was in those days (20:18, 26–27).',
    'Luz': 'The man of Bethel who showed the spies the way in went to the land of the Hittites and built a new Luz (1:26). Its site is unknown; Luweizeh in Lebanon is one guess.',
    'Gaza': 'The southernmost Philistine city. Samson carried off its gates (16:1–3), and was later blinded and set to grind grain in its prison (16:21) before pulling down the temple of Dagon (16:23–30).',
    'Ashkelon': 'Taken by Judah (1:18), later Philistine again. Samson killed thirty men of Ashkelon to pay his wedding riddle (14:19).',
    'Ekron': 'The northernmost of the five Philistine cities, taken by Judah (1:18). Excavated at Tel Miqne.',
    'Gezer': 'Ephraim did not drive out the Canaanites who lived in Gezer (1:29); Pharaoh later gave it to Solomon (1 Kings 9:16).',
    'Beth-shean': 'At the junction of the Jezreel and Jordan valleys. Manasseh did not drive out its people (1:27). An Egyptian garrison stood here into the 12th century BC.',
    'Megiddo': 'Guarding the pass into the Jezreel Valley; not taken by Manasseh (1:27). Deborah\'s song: "the kings of Canaan fought at Taanach by the waters of Megiddo" (5:19).',
    'Taanach': '"At Taanach by the waters of Megiddo" the kings of Canaan fought Barak (5:19).',
    'Acco': 'Asher did not drive out its people (1:31). The harbour city on the bay north of Carmel.',
    'Sidon': 'Asher did not drive out its people (1:31). Laish lived "after the manner of the Sidonians," far from Sidon (18:7, 28).',
    'Bochim': '"The weepers." The angel of the LORD came up from Gilgal and rebuked Israel, and the people wept and sacrificed (2:1–5). Its site is unknown; perhaps near Bethel.',
    'Gilgal': 'The angel of the LORD came up from Gilgal to Bochim (2:1). Ehud turned back "at the idols near Gilgal" to kill Eglon (3:19).',
    'Timnath-heres': 'Joshua\'s inheritance and burial place, "north of Mount Gaash" (2:9; Joshua 24:30 has Timnath-serah).',
    'Mount Baal-hermon': 'The Hivites lived "in the mountains of Lebanon from Mount Baal-hermon to Lebo-hamath" (3:3). Probably Mount Hermon or one of its peaks.',
    'Lebo-hamath': '"The entrance to Hamath," the northern limit of the land (3:3). Usually placed at Labweh in the Beqaa Valley.',
    'Hazor': 'Jabin king of Canaan reigned in Hazor, and Sisera led his army (4:2). The huge city was destroyed by fire at the end of the Late Bronze Age.',
    'Harosheth-hagoyim': '"Harosheth of the nations," Sisera\'s home and base, from which his 900 iron chariots came to the Kishon (4:2, 13, 16). Its site is unknown; it is usually looked for where the Kishon leaves the Jezreel Valley below Carmel.',
    'Ramah': 'Deborah judged under her palm tree "between Ramah and Bethel" (4:5). The Levite hoped to reach Gibeah or Ramah for the night (19:13).',
    'Kedesh': 'Barak\'s home, "Kedesh in Naphtali" (4:6). Heber the Kenite camped by the great tree of Zaanannim near Kedesh (4:11). Khirbet Qedish above the Sea of Galilee is the usual choice for this Kedesh, rather than the great Kedesh in upper Galilee.',
    'Mount Tabor': 'Barak gathered ten thousand men of Naphtali and Zebulun on Mount Tabor and charged down from it on Sisera\'s chariots (4:6, 12–14). Gideon\'s brothers were killed at Tabor (8:18).',
    'Moreh': 'The Midianite camp lay in the valley by the hill of Moreh, north of Gideon at the spring of Harod (7:1).',
    'Harod': 'Gideon camped at the spring of Harod, and here the LORD reduced his army to 300 men by how they drank (7:1–7). Its name may mean "trembling" (compare 7:3).',
    'Ophrah': 'Ophrah of the Abiezrites, Gideon\'s town, where the angel of the LORD met him at the winepress, he tore down his father\'s altar of Baal (6:11–32), and later set up the ephod (8:27). The site is uncertain.',
    'Abel-meholah': 'The fleeing Midianites ran toward Zererah, "as far as the border of Abel-meholah near Tabbath" (7:22). Later the home of Elisha (1 Kings 19:16).',
    'Succoth': 'The men of Succoth refused Gideon bread, and he punished its elders on his return (8:5–16). Excavated at Tell Deir Alla, where a plaster text about Balaam son of Beor was found.',
    'Penuel': 'Penuel also refused Gideon bread, and he tore down its tower (8:8–9, 17). Jacob wrestled with God here (Genesis 32:30–31).',
    'Karkor': 'Zebah and Zalmunna rested at Karkor with 15,000 men, far out on the caravan route east of Nobah and Jogbehah, thinking themselves safe (8:10–11). Its site is uncertain.',
    'Shechem': 'In the pass between Ebal and Gerizim. Gideon\'s son Abimelech was made king by the pillar in Shechem (9:6); the city turned against him, and he razed it and burned its tower with the temple of El-berith (9:22–49).',
    'Mount Gerizim': 'Jotham stood on top of Mount Gerizim and called out his parable of the trees to the leaders of Shechem (9:7–21).',
    'Thebez': 'A woman dropped an upper millstone on Abimelech\'s head from its tower (9:50–54).',
    'Mizpah': 'Mizpah of Benjamin, where all Israel "from Dan to Beersheba" assembled before the LORD over the outrage at Gibeah (20:1–3; 21:1–8). Later the city of Samuel\'s assemblies (1 Samuel 7; 10).',
    'Mizpah of Gilead': 'Jephthah\'s home in Gilead, where Israel camped against the Ammonites (10:17), Jephthah was made leader (11:11), and his daughter came out to meet him (11:34). Its site is unknown; Jel\'ad is one proposal.',
    'Tob': 'Jephthah fled to the land of Tob, east of Gilead, and gathered men around him there (11:3–5).',
    'Aroer': 'Aroer on the edge of the Arnon gorge, on Israel\'s southern border east of the Jordan (11:26). The Aroer of 11:33 may be this one or another near Rabbah of the Ammonites.',
    'Heshbon': 'The city of Sihon king of the Amorites. Jephthah answered the Ammonite king that Israel had lived in Heshbon and Aroer for 300 years (11:19–26).',
    'Jahaz': 'Sihon gathered his army at Jahaz and was defeated by Israel (11:20–21).',
    'Minnith': 'Jephthah struck twenty cities "from Aroer to the vicinity of Minnith, as far as Abel-keramim" (11:33).',
    'Abel-keramim': '"Meadow of vineyards," the limit of Jephthah\'s victory over the Ammonites (11:33).',
    'Zaphon': 'The men of Ephraim crossed the Jordan to Zaphon to quarrel with Jephthah (12:1). Gilead then held the fords: "Shibboleth" (12:5–6).',
    'Pirathon': 'The town of the judge Abdon in Ephraim (12:13–15).',
    'Zorah': 'The home of Manoah, Samson\'s father (13:2). The Spirit of the LORD began to stir Samson between Zorah and Eshtaol, and he was buried there (13:25; 16:31). The Danites sent out their five spies from here (18:2).',
    'Eshtaol': 'With Zorah, the home of Samson and the Danites (13:25; 16:31; 18:2, 11).',
    'Mahaneh-dan': '"The camp of Dan," between Zorah and Eshtaol (13:25), where the six hundred Danites camped west of Kiriath-jearim (18:12). Its site is unknown.',
    'Timnah': 'A Philistine town in the Sorek Valley where Samson found his wife and killed a lion on the way down (14:1–6). Excavated at Tel Batash.',
    'Etam': 'Samson stayed in a cave at the rock of Etam, and the men of Judah handed him over there to the Philistines (15:8–13).',
    'Lehi': '"Jawbone." Samson struck down a thousand Philistines here with a donkey\'s jawbone and named the place Ramath-lehi; God split open a hollow and water came out, En-hakkore, "the spring of the caller" (15:9–19).',
    'Mount Heres': '"Mountain of the sun." The Amorites held on at Mount Heres, Aijalon and Shaalbim (1:35). Probably Beth-shemesh of Judah ("house of the sun").',
    'Kiriath-jearim': 'The Danites camped west of it at Mahaneh-dan (18:12).',
    'Dan': 'Formerly Laish, a quiet and secure town far from Sidon. The Danites took it, renamed it Dan, and set up Micah\'s idol with a priest descended from Moses (18:7–31). The northern end of the land, "from Dan to Beersheba" (20:1).',
    'Beth-rehob': 'Laish lay in the valley near Beth-rehob (18:28).',
    'Bethlehem': 'Bethlehem in Judah: home of the young Levite who became Micah\'s priest (17:7–9) and of the concubine of the Levite of Ephraim (19:1–2). Ibzan the judge was from a Bethlehem (12:8–10), perhaps the one in Zebulun.',
    'Gibeah': 'Gibeah of Benjamin, where the Levite\'s concubine was abused and killed (19), which led to the war against Benjamin (20). Later Saul\'s home (1 Samuel 10:26).',
    'Baal-tamar': 'Israel drew up at Baal-tamar while the ambush rushed out west of Gibeah (20:33).',
    'Rimmon': 'Six hundred Benjamites fled to the rock of Rimmon and held out there four months (20:45–47; 21:13).',
    'Shiloh': 'The house of God was at Shiloh (18:31). At its yearly feast the remaining Benjamites seized wives from the girls who came out to dance (21:19–23).',
    'Lebonah': 'Shiloh is "north of Bethel, east of the road that goes up from Bethel to Shechem, and south of Lebonah" (21:19).',
    'Jabesh-gilead': 'It sent no one to the assembly at Mizpah, and was struck down; its four hundred young women were given to Benjamin (21:8–14). Saul would later rescue it (1 Samuel 11).',
    'Mount Sinai': '"The mountains quaked before the LORD, the One of Sinai" (5:5). The traditional site, Jebel Musa in southern Sinai, is shown; other sites are proposed.',
    'Kadesh-barnea': 'In Jephthah\'s history of Israel: after leaving Egypt they came through the wilderness to Kadesh (11:16–17).',
    'Beersheba': 'The southern end of the land, "from Dan to Beersheba" (20:1).',
    'Meroz': '"Curse Meroz… for they did not come to help the LORD" (5:23). The site is uncertain.',
    'Zaanannim': 'Heber the Kenite pitched his tent by the great tree of Zaanannim near Kedesh, where Jael killed Sisera (4:11, 17–21).',
    'Arumah': 'Abimelech stayed at Arumah while Zebul drove Gaal out of Shechem (9:41).',
    'Beer': 'Jotham fled to Beer and lived there, away from his brother Abimelech (9:21).',
    'Kamon': 'Where the judge Jair was buried (10:5).',
    'Beth-barah': 'The men of Ephraim seized the waters of the Jordan as far as Beth-barah to cut off the Midianites (7:24).',
    'Beth-shittah': 'The Midianite army fled toward Beth-shittah and Zererah (7:22).',
    'Jogbehah': 'Gideon went up the caravan route east of Nobah and Jogbehah to surprise the army at Karkor (8:11).',
    'Shaalbim': 'With Aijalon and Mount Heres, held by the Amorites until the house of Joseph pressed them into forced labour (1:35).',
    'Beth-anath': 'Naphtali lived among the Canaanites of Beth-shemesh and Beth-anath (1:33).',
    'Gaash': 'Joshua was buried at Timnath-heres, north of Mount Gaash (2:9).',
}

# places OpenBible's places layer leaves out (a spring, hills, rocks, a camp), with standard identifications
EXTRA = [
    {'n': 'Bezek', 'll': [35.3888, 32.3721], 'c': 1, 'm': 'Khirbet Ibziq?', 'f': '1:4'},
    {'n': 'Bochim', 'll': [35.2335, 31.9180], 'c': 0, 'm': 'near Bethel?', 'f': '2:1'},
    {'n': 'Mount Baal-hermon', 'll': [35.857, 33.416], 'c': 1, 'm': 'Mount Hermon', 'k': 'mount', 'f': '3:3'},
    {'n': 'Harosheth-hagoyim', 'll': [35.105, 32.712], 'c': 0, 'm': 'in the Kishon gorge below Carmel?', 'f': '4:2'},
    {'n': 'Harod', 'll': [35.3925, 32.5508], 'c': 1, 'm': 'the spring of Harod: Ein Harod', 'f': '7:1'},
    {'n': 'Mizpah of Gilead', 'll': [35.777, 32.1185], 'c': 0, 'm': 'Jel\'ad?', 'u': 'a0f8af9/mizpah-1', 'f': '10:17'},
    {'n': 'Mahaneh-dan', 'll': [35.03, 31.79], 'c': 0, 'm': 'near Kiriath-jearim?', 'f': '13:25'},
    {'n': 'Mount Heres', 'll': [34.9757, 31.7511], 'c': 1, 'm': 'Beth-shemesh (Tel Beit Shemesh)?', 'k': 'mount', 'f': '1:35'},
    {'n': 'Rimmon', 'll': [35.2967, 31.9333], 'c': 1, 'm': 'the rock of Rimmon: Rammun', 'f': '20:45'},
]

CONTEXT = [
    {'n': 'Ashdod', 'll': [34.6561, 31.7533], 'c': 2, 'm': 'Tel Ashdod',
     'note': 'One of the five cities of "the five rulers of the Philistines" (3:3), not named in Judges. The Ark was later taken to its temple of Dagon (1 Samuel 5).'},
    {'n': 'Gath', 'll': [34.8489, 31.7000], 'c': 2, 'm': 'Tell es-Safi',
     'note': 'One of the five Philistine cities (3:3), not named in Judges; later the home of Goliath. A large Philistine city through the 12th–9th centuries BC.'},
    {'n': 'Tell Qasile', 'll': [34.8063, 32.1020], 'c': 2, 'm': 'Tel Aviv',
     'note': 'A Philistine town founded in the 12th century BC on the Yarkon. Its temple roof rested on two central pillars, which helps picture the temple of Dagon at Gaza (16:25–30).'},
    {'n': '’Izbet Sartah', 'll': [34.9772, 32.1047], 'c': 2, 'm': '’Izbet Sartah',
     'note': 'A small Israelite village of the time of the Judges on the edge of the hill country, facing Aphek. One of the earliest Hebrew alphabet inscriptions was found here.'},
    {'n': 'Mount Ebal', 'll': [35.2731, 32.2332], 'c': 2, 'm': 'Jebel Eslamiyeh', 'k': 'mount',
     'note': 'Facing Gerizim across the valley of Shechem. An early Iron Age stone structure on the mountain has been interpreted as Joshua\'s altar (Joshua 8:30–35).'},
    {'n': 'Mount Gilboa', 'll': [35.42, 32.47], 'c': 2, 'm': 'the Gilboa ridge', 'k': 'mount',
     'note': 'The ridge above the spring of Harod. Many take "Mount Gilead" in 7:3 as a hill here. Saul and Jonathan later died on Gilboa (1 Samuel 31).'},
    {'n': 'Damascus', 'll': [36.30639, 33.51111], 'c': 2, 'm': 'Damascus',
     'note': 'The great city of Aram, beyond Mount Hermon. Israel served "the gods of Aram" (10:6).'},
]

REGIONS = [
    # the tribes (labels only)
    {'n': 'Asher', 'll': [35.2, 32.98], 'r': 1, 'link': False, 'note': 'The coast and hills from Carmel north toward Sidon. Asher lived among the Canaanites (1:31–32) and stayed by the coast in Deborah\'s war (5:17).'},
    {'n': 'Naphtali', 'll': [35.5, 33.17], 'r': 1, 'link': False, 'note': 'Upper Galilee. Barak came from Kedesh in Naphtali; the tribe "risked their lives on the heights of the field" (4:6; 5:18).'},
    {'n': 'Zebulun', 'll': [35.27, 32.78], 'r': 1, 'link': False, 'note': 'Lower Galilee, north of the Jezreel Valley; with Naphtali it fought Sisera (4:10; 5:18). Elon the judge was buried in Aijalon in Zebulun (12:12).'},
    {'n': 'Issachar', 'll': [35.45, 32.6], 'r': 1, 'link': False, 'note': 'The eastern Jezreel Valley; its leaders were with Deborah (5:15). Tola the judge was of Issachar (10:1).'},
    {'n': 'Manasseh', 'll': [35.15, 32.4], 'r': 1, 'link': False, 'note': 'The hill country north of Shechem to the Jezreel Valley. Gideon was of the clan of Abiezer in Manasseh (6:15).'},
    {'n': 'Ephraim', 'll': [35.2, 32.1], 'r': 1, 'link': False, 'note': 'The central hill country, with Shiloh, Shechem and Timnath-heres. Twice it quarrelled with a judge from across the Jordan (8:1–3; 12:1–6).'},
    {'n': 'Benjamin', 'll': [35.31, 31.84], 'r': 1, 'link': False, 'note': 'The small tribe between Judah and Ephraim; Ehud was a Benjamite (3:15). After the outrage at Gibeah it was almost wiped out (20–21).'},
    {'n': 'Tribe of Dan', 'label': 'Dan', 'll': [34.85, 31.93], 'r': 1, 'link': False, 'note': 'Allotted the Shephelah west of Benjamin, but the Amorites pressed it into the hill country (1:34). Samson was a Danite of Zorah; the tribe later moved north and took Laish (18).'},
    {'n': 'Judah', 'll': [35.13, 31.42], 'r': 1, 'link': False, 'note': 'The first to go up against the Canaanites (1:1–20). Othniel, the first judge, was of Judah (3:9).'},
    {'n': 'Simeon', 'll': [34.78, 31.17], 'r': 1, 'link': False, 'note': 'Towns within Judah\'s inheritance in the Negev; it fought alongside Judah (1:3, 17).'},
    {'n': 'Reuben', 'll': [35.8, 31.62], 'r': 1, 'link': False, 'note': 'The plateau east of the Salt Sea. In Deborah\'s war it stayed "among the sheepfolds" (5:15–16).'},
    {'n': 'Gad', 'll': [35.7, 32.0], 'r': 1, 'link': False, 'note': 'Gilead east of the Jordan, the land of Jephthah\'s war with the Ammonites (10–12).'},
    {'n': 'East Manasseh', 'label': 'Manasseh', 'll': [35.95, 32.62], 'r': 1, 'link': False, 'note': 'The half-tribe east of the Jordan, in northern Gilead and Bashan, with Jair\'s towns (10:3–4).'},
    # lands and regions
    {'n': 'Negev', 'll': [34.95, 30.85], 'r': 2, 'note': 'The dry south, where Achsah was given land and asked for springs of water (1:15), and the Kenites settled near Arad (1:16).'},
    {'n': 'Lebanon', 'll': [35.65, 33.6], 'r': 2, 'note': 'The mountains where the Hivites lived, left to test Israel (3:3); Jotham\'s "cedars of Lebanon" (9:15).'},
    {'n': 'Gilead', 'll': [35.85, 32.3], 'r': 2, 'note': 'The hill country east of the Jordan, home of Jair and Jephthah, oppressed by the Ammonites for eighteen years (10:3–12:7).'},
    {'n': 'Havvoth-jair', 'll': [35.95, 32.5], 'r': 3, 'note': '"The towns of Jair," thirty towns in Gilead held by the thirty sons of the judge Jair (10:3–4).'},
    {'n': 'Edom', 'll': [35.55, 30.55], 'r': 2, 'aka': ['Seir'], 'note': 'Seir, south-east of the Salt Sea. The LORD marched "from Seir… from the land of Edom" (5:4); Edom refused Israel passage (11:17).'},
    {'n': 'Moab', 'll': [35.85, 31.25], 'r': 2, 'note': 'The plateau east of the Salt Sea. Eglon king of Moab ruled Israel eighteen years, until Ehud killed him and Israel held the fords of the Jordan (3:12–30).'},
    {'n': 'Ammon', 'll': [36.12, 31.95], 'r': 2, 'link': False, 'note': 'The land of the Ammonites around Rabbah, east of Gilead. They oppressed Gilead until Jephthah defeated them (10:6–11:33).'},
    {'n': 'Land of the Philistines', 'label': 'Land of the\nPhilistines', 'll': [34.48, 31.45], 'r': 2, 'link': False, 'note': 'The coast of the five Philistine cities, Gaza, Ashdod, Ashkelon, Gath and Ekron (3:3). The Philistines ruled Israel forty years in Samson\'s day (13:1).'},
    {'n': 'Arabah', 'll': [35.38, 30.85], 'r': 3, 'link': False, 'note': 'The rift valley of the Jordan and the Salt Sea and south toward the Red Sea.'},
    {'n': 'Shephelah', 'll': [34.86, 31.68], 'r': 3, 'link': False, 'note': 'The "foothills" between the hill country of Judah and the coast, where Samson\'s stories take place.'},
    {'n': 'Valley of Jezreel', 'll': [35.3, 32.6], 'r': 3, 'hide': True, 'z': 9, 'note': 'The broad valley between Galilee and the hill country of Manasseh, where the Midianites and Amalekites camped "as thick as locusts" (6:33; 7:12).'},
    {'n': 'Valley of Sorek', 'll': [34.93, 31.77], 'r': 3, 'hide': True, 'z': 9.5, 'note': 'The valley running down past Beth-shemesh and Timnah to the coast, where Delilah lived (16:4).'},
    {'n': 'Kishon', 'll': [35.13, 32.68], 'hide': True, 'z': 9.5, 'note': 'The stream of the Jezreel Valley. "The torrent Kishon swept them away" (5:21): rain turned the valley to mud and stopped Sisera\'s chariots (4:7, 13; 5:20–21).'},
    {'n': 'Jordan', 'll': [35.56, 32.15], 'hide': True, 'z': 8, 'note': 'Its fords were held against Moab (3:28) and against the Midianites (7:24), and the Gileadites held them against Ephraim with "Shibboleth" (12:5–6).'},
    {'n': 'Arnon', 'll': [35.65, 31.46], 'hide': True, 'z': 9, 'note': 'The deep gorge into the Salt Sea, the southern border of Israel\'s land east of the Jordan "from the Arnon to the Jabbok" (11:13, 22).'},
    {'n': 'Jabbok', 'll': [35.65, 32.17], 'hide': True, 'z': 9.5, 'note': 'The river (Zarqa), the northern limit of the land the Ammonite king claimed (11:13, 22).'},
]
WATER = [
    {'n': 'The Great Sea', 's': '(Mediterranean)', 'll': [34.25, 32.45]},
    {'n': 'Sea of Chinnereth', 's': '(Galilee)', 'll': [35.59, 32.83]},
    {'n': 'Salt Sea', 's': '(Dead Sea)', 'll': [35.49, 31.5]},
    {'n': 'Jordan', 's': '', 'll': [35.555, 32.2]},
]

# verses where a linked name means a person, a tribe or another place, not the place on the map
EXCEPT = {'Dan': ['5:17', '18:29-30'], 'Gilead': ['7:3', '11:1-2'], 'Shechem': ['9:28'], 'Luz': ['1:26'], 'Aijalon': ['12:12'],
          'Mizpah': ['10:17', '11:11', '11:34']}
# where two places share a name, the one first named at this verse takes the name's links
PRIMARY = {'Aijalon': '1:35', 'Mizpah': '20:1'}


def build():
    verses = book_verses('JDG')
    layer = []
    for f in json.load(open(os.path.join(MAPS, 'places', 'JDG.json'), encoding='utf-8'))['features']:
        p = f['properties']
        if p.get('u') in DROP:
            continue
        n = RENAME.get(p['n'], p['n'])
        q = {'n': n, 'll': f['geometry']['coordinates'], 'c': p['c'], 'm': SITE.get(n, p.get('m') or ''), 'f': p.get('f', '')}
        if p.get('k') == 'mount':
            q['k'] = 'mount'
        if p.get('u'):
            q['u'] = p['u']
        layer.append(q)
    for q in layer:                                   # the first verse where the BSB names it
        if q['n'] == 'Dan':
            q['f'] = '18:29'
    named = layer + [dict(x) for x in EXTRA]
    named.sort(key=lambda q: (q['n'], PRIMARY.get(q['n'], q['f']) != q['f'], -q['c'], q['f'] and [int(x) for x in q['f'].split(':')]))
    seen = set()
    for q in named:
        if q['n'] not in seen:
            if q['n'] in AKA:
                q['aka'] = AKA[q['n']]
            if NOTES.get(q['n']) and 'note' not in q:
                q['note'] = NOTES[q['n']]
        seen.add(q['n'])
    # the second Aijalon and Luz get their own notes
    for q in named:
        if q['n'] == 'Aijalon' and q['f'] == '12:12':
            q['note'] = 'Aijalon in the land of Zebulun, where Elon the judge was buried (12:12); not the Aijalon of Dan (1:35).'
        if q['n'] == 'Aijalon' and q['f'] == '1:35':
            q['note'] = 'Aijalon in the valley below the Beth-horon pass; the Amorites held on here until the house of Joseph pressed them into forced labour (1:34–35).'
        if q['n'] == 'Luz' and q['f'] == '1:26':
            q['note'] = NOTES['Luz']

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
        'id': 'jdg-land', 'title': 'The Land in the Days of the Judges', 'ref': 'Judges', 'anchor': {'book': 'JDG', 'c': 1, 'v': 1},
        'bookwide': True, 'placesName': 'Judges', 'siteLabel': 'Site', 'groupsLabel': 'Places',
        'bounds': [[34.25, 30.5], [36.7, 33.7]], 'groupLabelZoom': 8.2, 'waterNames': WATER,
        'regions': regs, 'links': links, 'aliases': aliases, 'except': {k: v for k, v in EXCEPT.items() if k in links},
        'groups': [{'id': 'book', 'name': 'Named in Judges', 'color': RED, 'places': places, 'firstNamed': True},
                   {'id': 'other', 'name': 'Other places of the time', 'color': BLACK, 'places': CONTEXT}],
        'notes': [
            {'h': 'The land in the days of the Judges', 'p': [
                'Judges spans the passing of the Late Bronze Age into the early Iron Age. Egypt\'s hold on Canaan weakened and ended in the 12th century BC, '
                'and the Philistines, one of the Sea Peoples, settled on the southern coast in their five cities. In the hill country hundreds of small new villages appear in these centuries, '
                'with pillared houses, terraced fields and plastered cisterns, the setting of Gideon threshing wheat in a winepress and Micah\'s household shrine.',
                'The tribes lived largely apart, each facing its own neighbours: Moab, Midian and the people of the east, the Canaanite kings of the north, the Ammonites and the Philistines. '
                'The judges rose in different regions, and some of their times may overlap. The book closes with Israel united only to fight Benjamin, '
                'and the refrain "In those days there was no king in Israel" (17:6; 21:25).']},
            {'h': 'How to use this map', 'p': [
                'This map opens from any place named in Judges, in chapters that have no map of their own. The red dots are places named in Judges; the black dots are other places of the time, for context. '
                'The tribe names show roughly where each tribe lived. Two places share a name: Mizpah in Benjamin and Mizpah of Gilead, Jephthah\'s home; and Aijalon of Dan and Aijalon in Zebulun.']},
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
    idx['maps'].append({'id': m['id'], 'title': m['title'], 'ref': m['ref'], 'book': 'JDG', 'c': 1, 'v': 1,
                        'bookwide': True, 'links': m['links'], 'aliases': m['aliases'], 'except': m['except']})
    order = ['GEN', 'EXO', 'JOS', 'JDG', 'MAT']
    idx['maps'].sort(key=lambda e: (order.index(e['book']) if e['book'] in order else 99, e['c'], e['v']))
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    n = sum(len(g['places']) for g in m['groups'])
    print('%s: %d places, %d regions, %d tappable names' % (m['id'], n, len(m['regions']), len(m['links'])))
    print('   ', ', '.join(m['links']))


if __name__ == '__main__':
    main()
