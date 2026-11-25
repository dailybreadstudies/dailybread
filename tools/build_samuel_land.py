#!/usr/bin/env python3
"""The book maps of 1 and 2 Samuel, so every place in Samuel can be tapped in the text.

    python3 tools/build_samuel_land.py && python3 tools/check_maps.py

- 1sa-land, 2sa-land  "The Land in the Days of Samuel, Saul and David"

1 and 2 Samuel are one book in the Hebrew Bible, so both maps show the same land and the same places: the places named
in the book being read are red ("Named in 1 Samuel"), those named only in the other book are dark ("Named in 2 Samuel"),
and a few other places of the time are black. Each map is a book map ("bookwide") for its own book: its names are
tappable in every chapter of that book.

Places come from data/maps/places/1SA.json and 2SA.json (OpenBible.info, CC BY 4.0), with corrections noted below,
plus places OpenBible's layer leaves out (standard identifications, noted in each place). A place is "named" in a
book when one of its forms is found in that book's BSB text; places that are not found in either book are dropped
and listed when the script runs. Gentilic forms ("Ahithophel the Gilonite") point to their town, as "Nazarene" does
on the Matthew map. Tribe names and peoples are labels only.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_book_maps import book_verses  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAPS = os.path.join(ROOT, 'data', 'maps')
RED, DARK, BLACK = '#a0443a', '#4f6d7a', 'var(--dbm-city)'
BOOKS = {'1SA': '1 Samuel', '2SA': '2 Samuel'}
TITLE = 'The Land in the Days of Samuel, Saul and David'

# OpenBible name → the BSB spelling
RENAME = {'Telem': 'Telaim', 'En-dor': 'Endor'}
# OpenBible entries left out:
#   Millo, Perez-uzzah: placed at Jerusalem itself (the BSB says "supporting terraces"; the threshing floor of Nacon is unknown)
#   Siphmoth: put on Eshtemoa's spot ("within 30 km"); Bethel-2 and the Arnon Aroer are added below under their own names
#   Ephraim-1 (2 Samuel 13:23): the same spot as Ophrah, which takes the name "Ephraim" there (AKA, NEED)
#   Kadesh-2, Tibhath, Lehi: not named in the BSB text of Samuel (it reads Tahtim-hodshi, Betah)
DROP = {'a734b66/millo', 'ae67841/perez-uzzah', 'a077262/siphmoth', 'aeb5f24/bethel-2', 'ae46f2e/aroer-1', 'adc9b5a/kadesh-2',
        'a7cdf52/tibhath', 'aeeaca0/lehi', 'a507da9/ephraim-1'}
# corrections to OpenBible's points
FIX = {
    # OpenBible puts Samuel's Ramah beside Gibeah; the usual identification is er-Ram (as in its other books)
    'Ramah': {'ll': [35.23161, 31.85434], 'c': 1, 'm': 'er-Ram? (other sites proposed)', 'u': 'a6d57ed/ramah-1'},
    'Naioth': {'ll': [35.2296, 31.8559], 'c': 0, 'm': 'in Ramah'},
    'Beth-aven': {'ll': [35.2745, 31.8768], 'm': 'near Michmash; Tell Maryam?'},       # shares Tell Maryam with Migron
    'Aroer': {'m': 'Khirbet ’Ar’arah'},
}
# other forms in the text (gentilics point to the town); "need": the form links only after these words
AKA = {
    'Ramah': ['Ramathaim-zophim'], 'Jabesh-gilead': ['Jabesh'], 'Mount Gilboa': ['Gilboa'], 'City of David': ['Zion'],
    'Kiriath-jearim': ['Baale of Judah'], 'Beth-rehob': ['Rehob'], 'Ophrah': ['Ephraim'],
    'Anathoth': ['Anathothite'], 'Beeroth': ['Beerothite', 'Beerothites'], 'Bethlehem': ['Bethlehemite'], 'Carmel': ['Carmelite'],
    'Ekron': ['Ekronites'], 'Giloh': ['Gilonite'], 'Gath': ['Gittite', 'Gittites'], 'Harod': ['Harodite'], 'Hushah': ['Hushathite'],
    'Netophah': ['Netophathite'], 'Pirathon': ['Pirathonite'], 'Tekoa': ['Tekoite'], 'Ziph': ['Ziphites'],
}
NEED = {'Ephraim': r'\bnear\s*$'}          # "Baal-hazor near Ephraim" (2 Samuel 13:23) is a town, not the tribe or its hills
# verses where a linked name means a person or another place, per book
EXCEPT = {
    '1SA': {'Bethel': ['30:27'], 'Jezreel': ['25:43', '27:3', '30:5'], 'Ebenezer': ['7:12'], 'Negev': ['30:27']},
    '2SA': {'Jezreel': ['2:2', '3:2'], 'Maacah': ['3:3'], 'Rehob': ['8:3', '8:12']},
}

NOTES = {
    'Adullam': 'David escaped here from Gath and hid in the cave of Adullam; his family came to him, and about four hundred men in trouble or debt gathered around him (1 Samuel 22:1–2). The three mighty men came to him at the cave at harvest time (2 Samuel 23:13).',
    'Aijalon': 'After Jonathan\'s exploit at Michmash, Israel struck down the Philistines "from Michmash to Aijalon" (1 Samuel 14:31), down the Beth-horon road toward the coastal plain.',
    'Aphek': 'At the springs of the Yarkon, where the coast road meets the hills. The Philistines camped here before the battle in which the Ark was taken (1 Samuel 4:1–11), and mustered here again before Gilboa (29:1). Some take the Aphek of chapter 29 to be another town, nearer Jezreel.',
    'Aroer': 'A town in the Negev of Judah to which David sent a share of the plunder taken from the Amalekites (1 Samuel 30:26–28).',
    'Aroer on the Arnon': 'On the rim of the Arnon gorge. Joab\'s officers began the census here, "south of the town in the middle of the valley" (2 Samuel 24:5).',
    'Aroer in the Negev': 'A town in the Negev of Judah to which David sent a share of the plunder taken from the Amalekites (1 Samuel 30:26–28); not the Aroer on the Arnon of 2 Samuel 24:5.',
    'Ashdod': 'The Philistines carried the captured Ark into the temple of Dagon at Ashdod; Dagon fell on his face before it, and the city was struck with tumours (1 Samuel 5:1–7).',
    'Ashkelon': 'One of the five Philistine cities that sent a gold tumour with the Ark (1 Samuel 6:17). "Tell it not in Gath, proclaim it not in the streets of Ashkelon" (2 Samuel 1:20).',
    'Azekah': 'The Philistines camped "between Socoh and Azekah, in Ephes-dammim" before Goliath came out (1 Samuel 17:1), and were chased back past it.',
    'Beersheba': 'The southern end of the land, "from Dan to Beersheba" (1 Samuel 3:20; 2 Samuel 24:2). Samuel\'s sons judged here and took bribes (1 Samuel 8:1–3).',
    'Beth-aven': 'Near Michmash: the Philistines camped at Michmash, "east of Beth-aven," and the battle moved past it (1 Samuel 13:5; 14:23). Its site is uncertain.',
    'Beth-shan': 'After Gilboa the Philistines fastened the bodies of Saul and his sons to the wall of Beth-shan, until the men of Jabesh-gilead came by night and took them down (1 Samuel 31:10–13; 2 Samuel 21:12).',
    'Beth-shemesh': 'The cows pulling the cart with the Ark went straight up the road to Beth-shemesh, to the field of Joshua; the people were struck for looking into the Ark (1 Samuel 6:9–20).',
    'Bethel': 'Samuel went on a yearly circuit from Bethel to Gilgal to Mizpah (1 Samuel 7:16); Saul would meet three men going up to God at Bethel (10:3). The Bethel of 30:27 is another town, in the Negev.',
    'Bethel in the Negev': 'David sent plunder "to those in Bethel" (1 Samuel 30:27): a town in the Negev of Judah, probably Bethul or Bethuel (Joshua 19:4; 1 Chronicles 4:30), not the Bethel north of Jerusalem.',
    'Bethlehem': 'The town of Jesse, where Samuel anointed David (1 Samuel 16:1–13; 17:12). David longed for water from its well while a Philistine garrison held it (2 Samuel 23:14–17). Asahel was buried in his father\'s tomb here (2:32).',
    'Bezek': 'Saul mustered Israel and Judah at Bezek, across the valley from Jabesh-gilead, before he rescued the city (1 Samuel 11:8–11).',
    'Carmel': 'A town in the hill country of Judah (not Mount Carmel by the sea). Saul set up a monument for himself here (1 Samuel 15:12). Nabal sheared his sheep at Carmel, and Abigail met David with gifts (25).',
    'Dan': 'The northern end of the land: "all Israel from Dan to Beersheba" (1 Samuel 3:20; 2 Samuel 3:10; 17:11; 24:2, 15). Excavated at Tel Dan.',
    'Ebenezer': '"Stone of help." Israel camped at Ebenezer, facing the Philistines at Aphek, and the Ark was taken (1 Samuel 4:1–11); Izbet Sartah is a likely site. Twenty years later Samuel set up a stone between Mizpah and Shen and named it Ebenezer, "Thus far the LORD has helped us" (7:12): that stone stood near Mizpah.',
    'Ekron': 'The Ark was sent on from Gath to Ekron, whose people cried out (1 Samuel 5:10–12); the cows took it from Ekron to Beth-shemesh (6:16). At Tel Miqne an inscription naming Ekron and its kings was found in 1996.',
    'Endor': 'Saul went by night to the medium at En-dor, across the valley from the Philistine camp at Shunem, the night before he died on Gilboa (1 Samuel 28:7–25).',
    'Ephes-dammim': 'The Philistine camp before Goliath came out, between Socoh and Azekah (1 Samuel 17:1).',
    'Eshtemoa': 'One of the towns of Judah to which David sent plunder (1 Samuel 30:28). Modern as-Samu.',
    'Gallim': 'Saul gave Michal, David\'s wife, to Palti son of Laish from Gallim (1 Samuel 25:44).',
    'Gath': 'Philistine city, the home of Goliath (1 Samuel 17:4). The Ark was sent here (5:8); David feigned madness before Achish king of Gath (21:10–15) and later lived in his service (27). At Tell es-Safi a potsherd with two names similar to Goliath was found.',
    'Gaza': 'The southernmost Philistine city, one of the five that sent a guilt offering with the Ark (1 Samuel 6:17).',
    'Geba': 'Jonathan struck the Philistine garrison at Geba (1 Samuel 13:3), across the gorge from Michmash; Saul\'s army held it (13:16).',
    'Gibeah': 'Gibeah of Saul, his home and royal seat (1 Samuel 10:26; 11:4; 15:34). Seven of Saul\'s descendants were put to death here (2 Samuel 21:6). Tell el-Ful, north of Jerusalem, is the usual site. "Gibeah of God" (1 Samuel 10:5) may be Geba, or this town.',
    'Gilgal': 'In the Jordan valley near Jericho. Samuel came here on his circuit (1 Samuel 7:16); Saul was confirmed as king here (11:14–15), offered the burnt offering before Samuel came (13:8–14), and was rejected after the war with Amalek (15:12–35). Judah met David here on his return (2 Samuel 19:15, 40).',
    'Hachilah': '"The hill of Hachilah, opposite Jeshimon": David hid here, and here he took Saul\'s spear and water jug while Saul slept (1 Samuel 23:19; 26:1–12).',
    'Hazor': 'Named in Samuel\'s farewell: the LORD sold Israel "into the hand of Sisera, commander of the army of Hazor" (1 Samuel 12:9).',
    'Hebron': 'David sent plunder here (1 Samuel 30:31). He was anointed king of Judah at Hebron and reigned here seven and a half years, and here all Israel made him king (2 Samuel 2:1–4, 11; 5:1–5). Joab killed Abner in its gate (3:27), and Absalom began his revolt here (15:7–10).',
    'Hormah': 'One of the towns to which David sent plunder (1 Samuel 30:30).',
    'Jabesh-gilead': 'Saul\'s first victory was to save it from Nahash the Ammonite (1 Samuel 11). Its men never forgot it: they took the bodies of Saul and his sons from the wall of Beth-shan and buried them (31:11–13; 2 Samuel 2:4–7). David later moved the bones to Zela (21:12–14).',
    'Jattir': 'One of the towns to which David sent plunder (1 Samuel 30:27).',
    'Jerusalem': 'David brought Goliath\'s head to Jerusalem (1 Samuel 17:54). He took the city from the Jebusites and made it his capital (2 Samuel 5:6–10), brought up the Ark (6), and was promised a house and a kingdom forever (7).',
    'Jezreel': 'Israel camped by the spring in Jezreel before the battle on Gilboa (1 Samuel 29:1, 11); Ish-bosheth was made king over Jezreel (2 Samuel 2:9). Ahinoam "of Jezreel," David\'s wife, came from another Jezreel, in the hill country of Judah.',
    'Jezreel in Judah': 'A town in the hill country of Judah near Maon and Carmel (Joshua 15:55–56), probably the home of David\'s wife Ahinoam "of Jezreel" (1 Samuel 25:43; 2 Samuel 3:2). Its site is unknown.',
    'Keilah': 'David saved Keilah from the Philistines, but the LORD told him its people would hand him over to Saul, so he left (1 Samuel 23:1–13).',
    'Kiriath-jearim': 'The Ark stayed in the house of Abinadab here for twenty years (1 Samuel 6:21–7:2), until David brought it up from "Baale of Judah" (2 Samuel 6:2).',
    'Maon': 'Home of Nabal (1 Samuel 25:2). In the Wilderness of Maon Saul was closing in on David when news of a Philistine raid called him away, at the Rock of Escape (23:24–28).',
    'Michmash': 'The Philistines camped at Michmash. Jonathan and his armour-bearer climbed the cliffs between the crags Bozez and Seneh and threw the camp into panic (1 Samuel 13:23–14:23).',
    'Migron': 'Saul stayed "under the pomegranate tree in Migron" on the outskirts of Gibeah with six hundred men (1 Samuel 14:2).',
    'Mizpah': 'Israel gathered at Mizpah; Samuel prayed, and the LORD thundered against the Philistines (1 Samuel 7:5–11). Here Saul was chosen by lot (10:17–24). Tell en-Nasbeh.',
    'Mount Gilboa': 'Saul and three of his sons died on Mount Gilboa fighting the Philistines (1 Samuel 31:1–6). David\'s lament: "O mountains of Gilboa, may you have no dew or rain" (2 Samuel 1:21).',
    'Naioth': 'In Ramah, where Samuel led a company of prophets. David fled here; Saul\'s messengers, and then Saul himself, began to prophesy (1 Samuel 19:18–24).',
    'Nob': '"The town of the priests." Ahimelech gave David the holy bread and Goliath\'s sword (1 Samuel 21:1–9); Doeg the Edomite killed its priests (22:9–19). It stood within sight of Jerusalem (Isaiah 10:32), perhaps on Mount Scopus.',
    'Ophrah': 'Ophrah of Benjamin: a Philistine raiding party went toward Ophrah (1 Samuel 13:17). The town "Ephraim" near Baal-hazor (2 Samuel 13:23) is usually taken to be the same place (compare John 11:54).',
    'Ramah': 'Ramathaim-zophim, Samuel\'s home: he was born, lived, judged and was buried here (1 Samuel 1:1, 19; 7:17; 25:1). Er-Ram, north of Jerusalem, is the usual site; OpenBible.info puts it beside Gibeah, and Rentis, farther west, is also proposed (see "Where was Ramah?" in the notes).',
    'Secu': 'Saul came to "the great cistern at Secu" on his way to Naioth (1 Samuel 19:22).',
    'Shaaraim': 'The wounded Philistines fell "along the road to Shaaraim" after Goliath died (1 Samuel 17:52). Khirbet Qeiyafa, with its two gates, has been proposed (Shaaraim means "two gates").',
    'Shiloh': 'The house of the LORD stood here. Hannah prayed for a son, and Samuel grew up serving under Eli; the LORD revealed Himself to him at Shiloh (1 Samuel 1–3). The Ark was taken from here into battle and lost (4:3–11).',
    'Shunem': 'The Philistines camped at Shunem, facing Saul on Gilboa (1 Samuel 28:4).',
    'Shur': 'Saul struck the Amalekites "from Havilah to Shur, east of Egypt" (1 Samuel 15:7); David raided toward Shur from Ziklag (27:8).',
    'Socoh': 'Socoh of Judah, where the Philistines gathered before Goliath came out (1 Samuel 17:1).',
    'Telaim': 'Saul numbered his troops at Telaim before the war with Amalek (1 Samuel 15:4); probably Telem in the Negev (Joshua 15:24).',
    'Ziklag': 'Achish of Gath gave Ziklag to David (1 Samuel 27:6). The Amalekites burned it while David was away, and he pursued them and recovered all (30). Here he heard of Saul\'s death (2 Samuel 1:1). Tell esh-Sharia is the usual site; Khirbet al-Ra\'i near Lachish has also been proposed.',
    'Ziph': 'The Ziphites twice told Saul where David was hiding (1 Samuel 23:19; 26:1). In the Wilderness of Ziph Jonathan met David for the last time (23:15–18).',
    'En-gedi': 'The oasis by the Dead Sea. David hid in its strongholds; in a cave in the wilderness of En-gedi he cut off the corner of Saul\'s robe but spared his life (1 Samuel 23:29–24:22).',
    'Horesh': 'David stayed at Horesh in the Wilderness of Ziph, and Jonathan came there to strengthen his hand in God (1 Samuel 23:15–19). Khirbet Khoreisa, south of Ziph, is one proposal.',
    'Hereth': 'The prophet Gad told David to leave the stronghold, and he went to the forest of Hereth in Judah (1 Samuel 22:5). Its site is unknown; Kharas near Keilah is one proposal.',
    # 2 Samuel
    'Abel-beth-maacah': 'Sheba son of Bichri took refuge here; a wise woman of the city persuaded its people to throw his head over the wall to Joab (2 Samuel 20:14–22).',
    'Ammah': 'Joab and Abishai chased Abner until sunset, "to the hill of Ammah, opposite Giah" (2 Samuel 2:24).',
    'Anathoth': 'Home of Abiezer the Anathothite, one of David\'s mighty men (2 Samuel 23:27); later Jeremiah\'s town.',
    'Baal-hazor': 'Absalom\'s sheepshearing, where he had his brother Amnon killed (2 Samuel 13:23–29). Jebel Asur, the highest point of the central hills.',
    'Baal-perazim': '"Lord of breaking through": David defeated the Philistines here: "The LORD has broken out against my enemies like a bursting flood" (2 Samuel 5:20). Near the Valley of Rephaim; the site is uncertain.',
    'Bahurim': 'Paltiel followed Michal weeping as far as Bahurim (2 Samuel 3:16). Shimei cursed David here (16:5–13), and Jonathan and Ahimaaz hid in a well in a courtyard (17:18–20).',
    'Beeroth': 'Town of Rechab and Baanah, who murdered Ish-bosheth (2 Samuel 4:2–3).',
    'Beth-rehob': 'The Ammonites hired Arameans of Beth-rehob and Zobah against David (2 Samuel 10:6, 8). In the far north, near Dan (Judges 18:28).',
    'City of David': 'The fortress of Zion, the Jebusite stronghold on the ridge south of the Temple Mount, which David captured and named for himself (2 Samuel 5:7–9). The Stepped Stone Structure and the "Large Stone Structure" above it, excavated here, have been proposed as remains of David\'s city and palace; their dating is debated.',
    'Damascus': 'When the Arameans of Damascus came to help Hadadezer, David defeated them and put garrisons in Aram of Damascus (2 Samuel 8:5–6).',
    'Gaash': 'Hiddai, one of David\'s mighty men, came "from the brooks of Gaash" (2 Samuel 23:30), by Joshua\'s burial place.',
    'Gezer': 'David struck down the Philistines "all the way from Gibeon to Gezer" (2 Samuel 5:25).',
    'Gibeon': 'Twelve of Abner\'s men and twelve of Joab\'s fought by the pool of Gibeon, and the place was named Helkath-hazzurim (2 Samuel 2:12–17). Joab killed Amasa at the great stone in Gibeon (20:8–10). The Gibeonites avenged Saul\'s wrong against them (21:1–9). A great rock-cut pool with a spiral stair was excavated at el-Jib.',
    'Giloh': 'Ahithophel the Gilonite, David\'s counsellor, joined Absalom from his town of Giloh (2 Samuel 15:12).',
    'Gittaim': 'The Beerothites fled to Gittaim (2 Samuel 4:3).',
    'Hamath': 'Toi king of Hamath, an enemy of Hadadezer, sent his son with gifts to congratulate David (2 Samuel 8:9–10). Hama, on the Orontes in Syria.',
    'Harod': 'Home of Shammah and Elika the Harodites, two of David\'s mighty men (2 Samuel 23:25). Not the spring of Harod (Judges 7:1).',
    'Helam': 'Hadadezer brought Arameans from beyond the Euphrates to Helam, and David defeated them there and killed their commander Shobach (2 Samuel 10:16–18).',
    'Hushah': 'Home of Sibbecai the Hushathite, who killed the giant Saph (2 Samuel 21:18).',
    'Jazer': 'On the census route through the land east of the Jordan (2 Samuel 24:5).',
    'Jericho': 'David\'s envoys, shamed by Hanun the Ammonite, stayed at Jericho until their beards grew back (2 Samuel 10:5).',
    'Kabzeel': 'Home of Benaiah son of Jehoiada, who killed the lion in the pit on a snowy day (2 Samuel 23:20).',
    'Lo-debar': 'Mephibosheth lived here in the house of Machir until David sent for him to eat at his table (2 Samuel 9:4–13). Machir later brought supplies to David at Mahanaim (17:27).',
    'Mahanaim': 'East of the Jordan. Abner made Ish-bosheth king here (2 Samuel 2:8–12). David fled here from Absalom and sat in its gate waiting for news of the battle (17:24–18:33).',
    'Mount of Olives': 'David went up the Mount of Olives weeping, barefoot and with his head covered, as he fled from Absalom; Hushai met him at the summit, "where God used to be worshipped" (2 Samuel 15:30–32).',
    'Netophah': 'Home of Maharai and Heled the Netophathites, two of David\'s mighty men (2 Samuel 23:28–29).',
    'Pirathon': 'Home of Benaiah the Pirathonite, one of David\'s mighty men (2 Samuel 23:30), and of the judge Abdon (Judges 12:13–15).',
    'Rabbah': 'The Ammonite capital. Uriah was sent to his death during its siege (2 Samuel 11). Joab took "the city of waters," and David took the king\'s crown (12:26–31). The citadel of Amman.',
    'Rogelim': 'Home of Barzillai the Gileadite, who provided for David at Mahanaim (2 Samuel 17:27–29; 19:31–39).',
    'Sidon': 'On the census route, which went round "toward Sidon" (2 Samuel 24:6).',
    'Tekoa': 'Joab brought a wise woman from Tekoa to win Absalom\'s return (2 Samuel 14:1–24); Ira the Tekoite was one of the mighty men (23:26). Later the home of Amos.',
    'Thebez': 'Joab expected David to remember how Abimelech was killed by a millstone a woman dropped from the wall of Thebez (2 Samuel 11:21; Judges 9:50–54).',
    'Tob': 'The Ammonites hired men of Tob against David (2 Samuel 10:6–8). Jephthah had fled to the land of Tob (Judges 11:3).',
    'Tyre': 'Hiram king of Tyre sent cedar logs, carpenters and stonemasons to build David\'s house (2 Samuel 5:11). The census reached "the fortress of Tyre" (24:7).',
    'Zela': 'David buried the bones of Saul and Jonathan in the tomb of Saul\'s father Kish at Zela in Benjamin (2 Samuel 21:14).',
    'En-rogel': 'The spring below the City of David where Jonathan and Ahimaaz waited for news to take to David (2 Samuel 17:17). Bir Ayyub, where the Kidron meets the Hinnom Valley.',
    'Threshing Floor of Araunah': 'David bought the threshing floor of Araunah the Jebusite, built an altar, and the plague was stopped (2 Samuel 24:16–25). Solomon built the Temple here, on Mount Moriah (2 Chronicles 3:1).',
}

# places OpenBible's places layer leaves out or gives one spot for two towns; `in`: book and verse where it is meant
EXTRA = [
    {'n': 'En-gedi', 'll': [35.3889, 31.4614], 'c': 2, 'm': 'Tel Goren, En-gedi'},
    {'n': 'Horesh', 'll': [35.1305, 31.4572], 'c': 0, 'm': 'Khirbet Khoreisa?'},
    {'n': 'Hereth', 'll': [35.0500, 31.6000], 'c': 0, 'm': 'near Keilah?'},
    {'n': 'En-rogel', 'll': [35.2353, 31.7676], 'c': 2, 'm': 'Bir Ayyub'},
    {'n': 'Threshing Floor of Araunah', 'aka': ['threshing floor of Araunah'], 'll': [35.2355, 31.7780], 'c': 1, 'm': 'the Temple Mount'},
    {'n': 'Bethel in the Negev', 'll': [35.12438, 31.34495], 'c': 0, 'm': 'Bethul? Khirbet el-Qaryatein?', 'u': 'aeb5f24/bethel-2',
     'in': {'1SA': '30:27'}},
    {'n': 'Jezreel in Judah', 'll': [35.09, 31.44778], 'c': 0, 'm': 'near Juttah?', 'u': 'ad94cc9/jezreel-1',
     'in': {'1SA': '25:43', '2SA': '2:2'}},
]
# the same name for two towns: each map's own book keeps the name, the other town gets a longer one
TWIN = {'Aroer': {'1SA': ('Aroer', 'Aroer on the Arnon', [35.81939, 31.4708], 'Arair', 'ae46f2e/aroer-1', '2SA', '24:5'),
                  '2SA': ('Aroer', 'Aroer in the Negev', [34.97907, 31.15214], 'Khirbet ’Ar’arah', 'a1b9ca6/aroer-3', '1SA', '30:28')}}
TWIN_AT = {'1SA': [34.97907, 31.15214], '2SA': [35.81939, 31.4708]}   # where "Aroer" is in each book
TWIN_SITE = {'1SA': ('Khirbet ’Ar’arah', 'a1b9ca6/aroer-3'), '2SA': ('Arair', 'ae46f2e/aroer-1')}

CONTEXT = [
    {'n': 'Khirbet Qeiyafa', 'll': [34.9573, 31.6964], 'c': 2, 'm': 'Khirbet Qeiyafa',
     'note': 'A fortified town above the Valley of Elah, built about 1000 BC with a casemate wall and two gates, excavated from 2007. An ink inscription found here is among the earliest alphabetic texts from Judah. Some identify it with Shaaraim (1 Samuel 17:52).'},
    {'n': 'Tell Qasile', 'll': [34.8063, 32.1020], 'c': 2, 'm': 'Tel Aviv',
     'note': 'A Philistine town on the Yarkon with a temple of the 12th–11th centuries BC, the kind of shrine the Ark was taken into at Ashdod (1 Samuel 5:2).'},
    {'n': 'Shechem', 'll': [35.28194, 32.21361], 'c': 2, 'm': 'Tell Balatah', 'u': 'adf74d4/shechem',
     'note': 'Not named in Samuel. In the pass between Ebal and Gerizim; here Israel later gathered to make Rehoboam king and the kingdom divided (1 Kings 12).'},
    {'n': 'Megiddo', 'll': [35.18444, 32.58528], 'c': 2, 'm': 'Tel Megiddo', 'u': 'a8554e3/megiddo',
     'note': 'Not named in Samuel. The city guarding the pass into the Jezreel Valley, fortified by Solomon (1 Kings 9:15).'},
    {'n': 'Mount Carmel', 'll': [35.03, 32.74], 'c': 2, 'm': 'the Carmel ridge', 'k': 'mount',
     'note': 'The ridge by the sea where Elijah later faced the prophets of Baal (1 Kings 18). Not the town of Carmel in Judah, where Saul set up his monument and Nabal kept his flocks (1 Samuel 15:12; 25).'},
]

REGIONS = [
    # the tribes (labels only)
    {'n': 'Asher', 'll': [35.2, 32.98], 'r': 1, 'link': False, 'note': 'The coast and hills from Carmel north toward Tyre and Sidon. Ish-bosheth was made king over Gilead, Asher, Jezreel, Ephraim and Benjamin (2 Samuel 2:9).'},
    {'n': 'Naphtali', 'll': [35.5, 33.17], 'r': 1, 'link': False, 'note': 'Upper Galilee. Abel-beth-maacah, where Sheba\'s revolt ended, lay at its northern edge (2 Samuel 20:14–22).'},
    {'n': 'Zebulun', 'll': [35.27, 32.78], 'r': 1, 'link': False, 'note': 'Lower Galilee, north of the Jezreel Valley.'},
    {'n': 'Issachar', 'll': [35.45, 32.62], 'r': 1, 'link': False, 'note': 'The eastern Jezreel Valley, where the Philistines camped at Shunem before Gilboa (1 Samuel 28:4).'},
    {'n': 'Manasseh', 'll': [35.15, 32.4], 'r': 1, 'link': False, 'note': 'The hill country north of Shechem to the Jezreel Valley.'},
    {'n': 'Ephraim', 'll': [35.2, 32.1], 'r': 1, 'link': False, 'note': 'The central hill country. Samuel\'s family came from the hill country of Ephraim (1 Samuel 1:1), and Shiloh lay in it. Sheba son of Bichri was "from the hill country of Ephraim" (2 Samuel 20:21).'},
    {'n': 'Benjamin', 'll': [35.31, 31.84], 'r': 1, 'link': False, 'note': 'Saul\'s tribe (1 Samuel 9:1–2), the small hill country between Judah and Ephraim, with Gibeah, Geba, Michmash, Mizpah, Ramah and Gibeon. Much of Saul\'s war with the Philistines was fought here.'},
    {'n': 'Tribe of Dan', 'label': 'Dan', 'll': [34.85, 31.93], 'r': 1, 'link': False, 'note': 'Dan\'s first allotment, west of Benjamin. Most of the tribe had moved north and taken Laish, which they named Dan (Judges 18).'},
    {'n': 'Judah', 'll': [35.13, 31.42], 'r': 1, 'link': False, 'note': 'David\'s tribe. He hid from Saul in its wildernesses, and reigned over Judah at Hebron for seven and a half years before all Israel made him king (2 Samuel 2:1–11; 5:1–5).'},
    {'n': 'Simeon', 'll': [34.78, 31.17], 'r': 1, 'link': False, 'note': 'Towns within Judah in the Negev. Ziklag had been allotted to Simeon (Joshua 19:5).'},
    {'n': 'Reuben', 'll': [35.8, 31.62], 'r': 1, 'link': False, 'note': 'The plateau east of the Salt Sea, north of the Arnon. David\'s census began at Aroer on the Arnon (2 Samuel 24:5).'},
    {'n': 'Gad', 'll': [35.7, 32.0], 'r': 1, 'link': False, 'note': 'Gilead east of the Jordan. When the Philistines gathered at Michmash, some Hebrews crossed the Jordan "into the land of Gad and Gilead" (1 Samuel 13:7).'},
    {'n': 'East Manasseh', 'label': 'Manasseh', 'll': [35.95, 32.62], 'r': 1, 'link': False, 'note': 'The half-tribe east of the Jordan, in northern Gilead and Bashan.'},
    # lands and regions
    {'n': 'Land of the Philistines', 'label': 'Land of the\nPhilistines', 'll': [34.48, 31.45], 'r': 2, 'link': False,
     'note': 'The coast of the five Philistine cities, Gaza, Ashdod, Ashkelon, Gath and Ekron (1 Samuel 6:17). The Philistines were Israel\'s great enemy through Samuel\'s and Saul\'s days, until David subdued them (2 Samuel 5:17–25; 8:1).'},
    {'n': 'Amalek', 'label': 'Amalekites', 'll': [34.55, 30.7], 'r': 2, 'link': False,
     'note': 'Raiding nomads of the Negev and Sinai. Saul fought them and spared Agag (1 Samuel 15); they burned Ziklag, and David pursued and struck them (30).'},
    {'n': 'Negev', 'll': [34.95, 30.85], 'r': 2, 'note': 'The dry south. David, living at Ziklag, told Achish he had raided "the Negev of Judah" (1 Samuel 27:10); the Amalekites raided the Negev and Ziklag (30:1, 14).'},
    {'n': 'Wilderness of Paran', 'll': [34.75, 30.6], 'r': 3, 'note': 'After Samuel died, David went down to the Wilderness of Paran (1 Samuel 25:1), the desert south of Judah (Greek manuscripts read Maon).'},
    {'n': 'Wilderness of Ziph', 'll': [35.2, 31.5], 'r': 3, 'note': 'The barren hills east of Ziph, falling to the Dead Sea, where David hid from Saul (1 Samuel 23:14–24; 26:2).'},
    {'n': 'Wilderness of Maon', 'll': [35.21, 31.38], 'r': 3, 'note': 'The wilderness east of Maon "in the Arabah south of Jeshimon," where Saul almost caught David (1 Samuel 23:24–28).'},
    {'n': 'Wilderness of En-gedi', 'aka': ['wilderness of En-gedi'], 'll': [35.33, 31.47], 'hide': True, 'z': 10,
     'note': 'The cliffs and caves above En-gedi, where David spared Saul\'s life (1 Samuel 24).'},
    {'n': 'Arabah', 'll': [35.52, 31.98], 'r': 3, 'note': 'The rift valley of the Jordan and the Salt Sea. Abner\'s men marched all night through the Arabah after the battle at Gibeon (2 Samuel 2:29).'},
    {'n': 'Gilead', 'aka': ['Gileadite'], 'll': [35.85, 32.3], 'r': 2, 'note': 'The hill country east of the Jordan, with Jabesh-gilead and Mahanaim. Ish-bosheth was made king over Gilead (2 Samuel 2:9); Absalom\'s army camped in the land of Gilead (17:26).'},
    {'n': 'Moab', 'll': [35.85, 31.25], 'r': 2, 'note': 'David took his parents to the king of Moab at "Mizpeh of Moab" while he hid from Saul (1 Samuel 22:3–4); Ruth, his great-grandmother, was a Moabite. Saul fought Moab (14:47), and David later made it subject (2 Samuel 8:2).'},
    {'n': 'Edom', 'll': [35.55, 30.55], 'r': 2, 'note': 'South-east of the Salt Sea. Saul fought Edom (1 Samuel 14:47); David put garrisons throughout Edom (2 Samuel 8:14).'},
    {'n': 'Ammon', 'label': 'Ammonites', 'll': [36.12, 31.95], 'r': 2, 'link': False, 'note': 'The land around Rabbah. Nahash the Ammonite besieged Jabesh-gilead (1 Samuel 11); his son Hanun shamed David\'s envoys, which led to the war in which Uriah was killed (2 Samuel 10–12).'},
    {'n': 'Aram', 'll': [36.55, 33.25], 'r': 2, 'note': 'The Aramean kingdoms north-east of Israel. David defeated Hadadezer and "Aram of Damascus," and put garrisons there (2 Samuel 8:3–6).'},
    {'n': 'Zobah', 'll': [36.25, 33.95], 'r': 2, 'note': 'The Aramean kingdom of Hadadezer son of Rehob, in the Beqaa Valley and beyond, reaching toward the Euphrates. Saul fought its kings (1 Samuel 14:47); David defeated Hadadezer twice (2 Samuel 8:3–8; 10:6–19).'},
    {'n': 'Geshur', 'll': [35.72, 32.92], 'r': 3, 'note': 'A small Aramean kingdom east of the Sea of Chinnereth. David married Maacah, daughter of Talmai king of Geshur; their son Absalom fled to his grandfather here for three years (2 Samuel 3:3; 13:37–38).'},
    {'n': 'Maacah', 'aka': ['Maacathite'], 'll': [35.75, 33.18], 'r': 3, 'note': 'A small Aramean kingdom below Mount Hermon, which sent a thousand men to help the Ammonites (2 Samuel 10:6–8).'},
    # valleys and streams: tappable, not labelled
    {'n': 'Valley of Elah', 'll': [34.965, 31.692], 'hide': True, 'z': 11, 'note': 'The valley where Israel faced the Philistines and David killed Goliath (1 Samuel 17:2–52; 21:9). Wadi es-Sunt, below Socoh and Azekah.'},
    {'n': 'Valley of Rephaim', 'll': [35.2, 31.755], 'hide': True, 'z': 11, 'note': 'South-west of Jerusalem. The Philistines spread out here twice and David defeated them (2 Samuel 5:18–25); the three mighty men broke through their camp here for water from Bethlehem (23:13–17).'},
    {'n': 'Kidron Valley', 'll': [35.2375, 31.776], 'hide': True, 'z': 13, 'note': 'Between the City of David and the Mount of Olives. David crossed it weeping as he fled from Absalom (2 Samuel 15:23).'},
    {'n': 'Valley of Salt', 'll': [35.3, 30.95], 'hide': True, 'z': 9, 'note': 'Where David\'s army struck down 18,000 Edomites (2 Samuel 8:13). Usually placed in the Arabah south of the Salt Sea; others suggest the valley east of Beersheba.'},
    {'n': 'Brook of Besor', 'll': [34.48, 31.29], 'hide': True, 'z': 10, 'note': 'Two hundred of David\'s men were too exhausted to cross it, and stayed with the baggage. David ruled that they share the plunder equally with those who fought (1 Samuel 30:9–25). Nahal Besor, south of Gaza.'},
    {'n': 'forest of Ephraim', 'll': [35.74, 32.22], 'hide': True, 'z': 10, 'note': 'East of the Jordan, near Mahanaim: Absalom\'s army was defeated here, and his head caught in a great oak (2 Samuel 18:6–15). "The forest devoured more people that day than the sword."'},
    {'n': 'Jordan', 'll': [35.56, 32.15], 'hide': True, 'z': 8, 'note': 'David crossed the Jordan fleeing from Absalom, and the men of Judah brought him back across it (2 Samuel 17:22; 19:15–18).'},
]
WATER = [
    {'n': 'The Great Sea', 's': '(Mediterranean)', 'll': [34.25, 32.45]},
    {'n': 'Sea of Chinnereth', 's': '(Galilee)', 'll': [35.59, 32.83]},
    {'n': 'Salt Sea', 's': '(Dead Sea)', 'll': [35.49, 31.5]},
    {'n': 'Jordan', 's': '', 'll': [35.555, 32.2]},
]

PERSON_AFTER = re.compile(r'^[’ʼ]?\s*(?:,\s*)?(?:said|says|answered|replied|asked|fathered|begot|son of|daughter of|the son of|the daughter of)\b')
PERSON_BEFORE = re.compile(r'\b(?:son|daughter|father|mother|brother|sister|wife|husband) of\s*$')


def in_range(cv, rules):
    for r in rules or []:
        m = re.match(r'^(\d+):(\d+)(?:-(\d+))?$', r)
        if m and int(m[1]) == cv[0] and int(m[2]) <= cv[1] <= int(m[3] or m[2]):
            return True
    return False


def make_finder(b, all_forms):
    """First verse where a form would be linked in book b (same rules as linkPlaces in maps.js)."""
    verses = book_verses(b)
    longest = sorted(all_forms, key=len, reverse=True)
    rx = re.compile(r'(?<![A-Za-z\-])(' + '|'.join(re.escape(k) for k in longest) + r')(?![A-Za-z]|-[a-z])')
    hits = {}
    for c, v, t in verses:
        for mt in rx.finditer(t):
            f = mt[1]
            if f in hits:
                continue
            before, after = t[:mt.start()], t[mt.end():]
            if in_range((c, v), EXCEPT[b].get(f)):
                continue
            if f in NEED and not re.search(NEED[f], before):
                continue
            if PERSON_AFTER.search(after) or PERSON_BEFORE.search(before):
                continue
            hits[f] = '%d:%d' % (c, v)
    return hits


def load_places():
    """Every place of the two books, once, keyed by name."""
    out = {}
    for b in BOOKS:
        for f in json.load(open(os.path.join(MAPS, 'places', b + '.json'), encoding='utf-8'))['features']:
            p = f['properties']
            if p.get('u') in DROP:
                continue
            n = RENAME.get(p['n'], p['n'])
            if n in out:
                continue
            q = {'n': n, 'll': f['geometry']['coordinates'], 'c': p['c'], 'm': p.get('m') or '', 'k': 'mount' if p.get('k') == 'mount' else '',
                 'u': p.get('u', '')}
            q.update(FIX.get(n, {}))
            out[n] = q
    for x in EXTRA:
        out[x['n']] = dict(x)
    out['Ophrah']['m'] = 'et-Taiyibeh'
    out['Ammah']['k'] = 'mount'
    out['Baal-hazor']['k'] = 'mount'
    for n, q in out.items():
        q['aka'] = q.get('aka', []) + AKA.get(n, [])
        q['note'] = NOTES.get(n, '')
    return out


def build(b):
    other = '2SA' if b == '1SA' else '1SA'
    places = load_places()
    # this book's Aroer keeps the name; the other book's Aroer gets its own name
    places['Aroer'].update({'ll': TWIN_AT[b], 'm': TWIN_SITE[b][0], 'u': TWIN_SITE[b][1]})
    _, twin_n, twin_ll, twin_m, twin_u, twin_b, twin_f = TWIN['Aroer'][b]
    places['Aroer']['note'] = NOTES['Aroer'] if b == '1SA' else NOTES['Aroer on the Arnon']
    places[twin_n] = {'n': twin_n, 'll': twin_ll, 'c': 2, 'm': twin_m, 'u': twin_u, 'k': '', 'aka': [], 'note': NOTES[twin_n],
                      'in': {twin_b: twin_f}}

    forms = {f for q in list(places.values()) + REGIONS for f in [q['n']] + q.get('aka', [])}
    found = {bk: make_finder(bk, forms) for bk in BOOKS}

    def where(q, bk):
        """first verse in book bk naming the place (and the form found), or (None, [])"""
        fs = [(found[bk][f], f) for f in [q['n']] + q['aka'] if f in found[bk]]
        if bk == other and q['n'] == 'Aroer':
            return None, []                   # the other book's "Aroer" is the twin, not this one
        if fs:
            fs.sort(key=lambda x: [int(y) for y in x[0].split(':')])
            return fs[0][0], [f for _, f in fs]
        if q.get('in', {}).get(bk):
            return q['in'][bk], []
        return None, []

    links, aliases = [], {}
    mine, theirs, dropped = [], [], []
    for n in sorted(places):
        q = places[n]
        f_here, forms_here = where(q, b)
        f_there, _ = where(q, other)
        out = {k: q[k] for k in ('n', 'll', 'c', 'm', 'u', 'k') if q.get(k) or k == 'c'}
        if f_here:
            out['f'] = f_here
            for f in forms_here:
                if f not in links:
                    links.append(f)
                if f != n:
                    aliases[f] = n
            out['note'] = q['note']
            mine.append(out)
        elif f_there:
            out['f'] = 'first at %s' % f_there
            out['note'] = q['note']
            theirs.append(out)
        else:
            dropped.append(n)
    regs = []
    for r in REGIONS:
        regs.append({k: r[k] for k in ('n', 'label', 'll', 'r', 'hide', 'z', 'note') if k in r})
        if r.get('link', True):
            for f in [r['n']] + r.get('aka', []):
                if f in found[b] and f not in links:
                    links.append(f)
                    if f != r['n']:
                        aliases[f] = r['n']
    if dropped:
        print('  not named in either book (left out):', ', '.join(dropped))
    name, oname = BOOKS[b], BOOKS[other]
    need = {f: rx for f, rx in NEED.items() if f in links}
    return {
        'id': b.lower() + '-land', 'title': TITLE, 'ref': name, 'anchor': {'book': b, 'c': 1, 'v': 1},
        'bookwide': True, 'placesName': name, 'siteLabel': 'Site', 'groupsLabel': 'Places',
        'bounds': [[34.25, 30.5], [36.7, 33.7]], 'groupLabelZoom': 8.2, 'waterNames': WATER,
        'regions': regs, 'links': links, 'aliases': aliases, 'need': need,
        'except': {k: v for k, v in EXCEPT[b].items() if k in links},
        'groups': [{'id': 'book', 'name': 'Named in ' + name, 'color': RED, 'places': mine, 'firstNamed': True},
                   {'id': 'sister', 'name': 'Named in ' + oname, 'color': DARK, 'places': theirs},
                   {'id': 'other', 'name': 'Other places of the time', 'color': BLACK, 'places': CONTEXT}],
        'alternates': {'for': 'Ramah', 'bounds': [[34.97, 31.79], [35.3, 32.06]],
                       'sites': [{'name': 'beside Gibeah (OpenBible.info)', 'll': [35.23072, 31.82311]},
                                 {'name': 'Rentis', 'll': [35.01944, 32.02806]}]},
        'notes': [
            {'h': 'The land in the days of Samuel, Saul and David', 'p': [
                'The books of Samuel cover roughly a century, from Samuel\'s birth to the last years of David, about 1100–970 BC: the end of the Iron Age I and the beginning of the Iron Age II. '
                'In the Hebrew Bible they are one book. The Philistines, strong in their five cities on the coast, pushed into the hill country, took the Ark at Ebenezer and set garrisons as far inland as Geba and Bethlehem.',
                'Against them Israel asked for a king. Saul, from Gibeah in Benjamin, fought the Philistines in the hills north of Jerusalem and died on Gilboa. '
                'David, from Bethlehem in Judah, was hunted through the wildernesses of Judah, reigned in Hebron, then took Jerusalem from the Jebusites and made it the city of the Ark. '
                'He subdued the Philistines, Moab, Ammon, Edom and the Aramean kingdoms of Zobah and Damascus.']},
            {'h': 'Where was Ramah?', 'alternates': True, 'p': [
                'Samuel\'s home is called Ramathaim-zophim in 1 Samuel 1:1 and Ramah everywhere else. This map follows the usual identification, er-Ram, '
                'about 8 km north of Jerusalem, the Ramah of Benjamin. OpenBible.info places it right beside Gibeah instead. Others look for it at Rentis, '
                'on the western edge of the hill country of Ephraim (1:1), the likely site of New Testament Arimathea.']},
            {'h': 'How to use this map', 'p': [
                'This map opens from any place named in ' + name + '. The red dots are places named in ' + name + ', the blue-grey dots places named only in ' + oname + ', '
                'and the black dots other places of the time, for context; tap a group in the key to show or hide it. The tribe names show roughly where each tribe lived. '
                'Two towns are called Aroer (in the Negev, 1 Samuel 30:28, and on the Arnon, 2 Samuel 24:5), and Bethel and Jezreel each have a namesake in Judah.']},
        ],
        'sources': 'Scripture: Berean Standard Bible (public domain). Places: OpenBible.info Bible Geocoding Data (CC BY 4.0) and standard identifications, as noted for each place. '
                   'Ancient Dead Sea outline from OpenBible.info (CC BY 4.0). Ancient roads are approximations. Terrain: Terrain Tiles on AWS Open Data (Mapzen). '
                   'Street map © OpenStreetMap contributors. Imagery © Esri. Map engine: MapLibre GL.',
    }


def main():
    idx_path = os.path.join(MAPS, 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8'))
    for b in BOOKS:
        print(b)
        m = build(b)
        with open(os.path.join(MAPS, m['id'] + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(m, fh, ensure_ascii=False, indent=1)
        idx['maps'] = [e for e in idx['maps'] if e['id'] != m['id']]
        e = {'id': m['id'], 'title': m['title'], 'ref': m['ref'], 'book': b, 'c': 1, 'v': 1, 'bookwide': True,
             'links': m['links'], 'aliases': m['aliases'], 'except': m['except']}
        if m['need']:
            e['need'] = m['need']
        idx['maps'].append(e)
        n = [len(g['places']) for g in m['groups']]
        print('  %s: %d + %d + %d places, %d regions, %d tappable names' % (m['id'], n[0], n[1], n[2], len(m['regions']), len(m['links'])))
        print('   ', ', '.join(m['links']))
    order = ['GEN', 'EXO', 'JOS', 'JDG', '1SA', '2SA', 'MAT']
    idx['maps'].sort(key=lambda e: (order.index(e['book']) if e['book'] in order else 99, e['c'], e['v']))
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
