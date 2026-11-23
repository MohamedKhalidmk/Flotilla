# Hand check of the Sonnet tiebreak (2026-11-22)

Sonnet 5.5 differed from the Haiku majority on 22 split verdicts. 11 of them sit in the 7 items whose route label changed,
and the other 11 changed no label (sonnet_tiebreak.md said 10; the 22 split 11 and 11). All 22 are checked here by hand
against the official LongMemEval judge prompt for the item's type (flotilla/memory_route.py JUDGE_TEMPLATES) and, where
needed, the user's own turns in the history.

| | verdicts | Sonnet right | Haiku right | unclear |
|---|---|---|---|---|
| changed a label (7 items) | 11 | 9 | 0 | 2 (lme-5d3d2817, both routes) |
| changed no label | 11 | 10 | 1 (lme-a89d7624) | 0 |
| all | 22 | 19 | 1 | 2 |

Haiku's misses are all no on answers that match the gold (750, 12, 4, 2.5 years, the four terms). Sonnet's are both
strictness: one preference answer that recalls the right personal facts, and one answer missing "at a small startup".

Per changed label: lme-06878be2, lme-1f2b8d4f, lme-3c1045c8, lme-4baee567 and lme-gpt4_194be4b3 are right after the
tiebreak. lme-80ec1f4f_abs: Sonnet's flip is right, but the new label (deep_tools) rests on a unanimous Haiku yes for a bare
"0" on an abstention item, which the rubric marks no; the routes that abstain are the memory routes. lme-5d3d2817: depends
on whether "at a small startup" is required (see below).

## The 7 changed labels

### lme-06878be2: vote_tools -> fast (dev)

**lme-06878be2, fast** (single-session-preference)

- Question: Can you suggest some accessories that would complement my current photography setup?
- Gold: The user would prefer suggestions of Sony-compatible accessories or high-quality photography gear that can enhance their photography experience. They may not prefer suggestions of other brands' equipment or low-quality gear.
- Answer: Based on your Sony A7R IV, 24-70mm f/2.8 lens, and Godox V1 flash, complementary accessories include: 1. A camera bag from brands like Think Tank Photo, Lowepro, or Peak Design; 2. An external battery pack with USB-C PD support (e.g., Anker PowerCore 20000 PD); 3. A lens cleaning kit (microfiber cloth, blower, solution); 4. A case or pouch for the Godox V1 (e.g., Godox V1 Hard Case or Think Tank Flash Pouch); 5. A compatible tripod head (e.g., Gitzo GH3382QD) if you proceed with the Gitzo GT3543LS tripod.
- Haiku: No, No, Yes. Sonnet: yes
- Right: **Sonnet**. The answer builds on the user's Sony A7R IV, 24-70mm lens and Godox V1 flash, which is what the rubric asks for.

### lme-gpt4_194be4b3: deep_tools -> fast (held-out)

**lme-gpt4_194be4b3, fast** (multi-session)

- Question: How many musical instruments do I currently own?
- Gold: I currently own 4 musical instruments. I've had the Fender Stratocaster electric guitar for 5 years, the Yamaha FG800 acoustic guitar for 8 years, the 5-piece Pearl Export drum set for an unspecified amount of time, and the Korg B1 piano for 3 years.
- Answer: 4
- Haiku: No, No, Yes. Sonnet: Yes
- Right: **Sonnet**. "4" is the gold count.

### lme-1f2b8d4f: deep -> fast

**lme-1f2b8d4f, fast** (multi-session)

- Question: What is the difference in price between my luxury boots and the similar pair found at the budget store?
- Gold: $750
- Answer: 750
- Haiku: No, Yes, No. Sonnet: Yes
- Right: **Sonnet**. "750" is the gold "$750" without the dollar sign.

**lme-1f2b8d4f, tools** (multi-session)

- Question: What is the difference in price between my luxury boots and the similar pair found at the budget store?
- Gold: $750
- Answer: 750
- Haiku: No, Yes, No. Sonnet: Yes
- Right: **Sonnet**. "750" is the gold "$750" without the dollar sign.

### lme-3c1045c8: none -> vote

**lme-3c1045c8, vote** (multi-session)

- Question: How much older am I than the average age of employees in my department?
- Gold: 2.5 years
- Answer: 2.5 years
- Haiku: Yes, No, No. Sonnet: Yes
- Right: **Sonnet**. Exact match with the gold (the same case as the hand override in PROTOCOL 12).

**lme-3c1045c8, vote_tools** (multi-session)

- Question: How much older am I than the average age of employees in my department?
- Gold: 2.5 years
- Answer: 2.5 years
- Haiku: No, Yes, No. Sonnet: Yes
- Right: **Sonnet**. Exact match with the gold (the same case as the hand override in PROTOCOL 12).

### lme-4baee567: tools -> fast

**lme-4baee567, fast** (single-session-assistant)

- Question: I was looking back at our previous chat and I wanted to confirm, how many times did the Chiefs play the Jaguars at Arrowhead Stadium?
- Gold: The Chiefs played the Jaguars 12 times at Arrowhead Stadium.
- Answer: 12
- Haiku: Yes, No, No. Sonnet: Yes
- Right: **Sonnet**. "12" is the gold number.

**lme-4baee567, vote_memory** (single-session-assistant)

- Question: I was looking back at our previous chat and I wanted to confirm, how many times did the Chiefs play the Jaguars at Arrowhead Stadium?
- Gold: The Chiefs played the Jaguars 12 times at Arrowhead Stadium.
- Answer: 12
- Haiku: No, Yes, No. Sonnet: Yes
- Right: **Sonnet**. "12" is the gold number.

### lme-5d3d2817: tools -> deep_tools

**lme-5d3d2817, fast** (single-session-user)

- Question: What was my previous occupation?
- Gold: Marketing specialist at a small startup
- Answer: marketing specialist
- Haiku: No, Yes, Yes. Sonnet: no
- Right: **Unclear, I lean Haiku**. The history says "my previous role as a marketing specialist at a small startup" and the current role is senior marketing analyst, so the answer names the right previous job. The rubric's subset clause ("If the response only contains a subset of the information required by the answer, answer no") supports Sonnet's no if "at a small startup" counts as required. Haiku is split on this too: it judged the identical "Marketing specialist" from deep_tools_memory no 3 of 3.

**lme-5d3d2817, tools** (single-session-user)

- Question: What was my previous occupation?
- Gold: Marketing specialist at a small startup
- Answer: marketing specialist
- Haiku: No, Yes, Yes. Sonnet: no
- Right: **Unclear, I lean Haiku**. The history says "my previous role as a marketing specialist at a small startup" and the current role is senior marketing analyst, so the answer names the right previous job. The rubric's subset clause ("If the response only contains a subset of the information required by the answer, answer no") supports Sonnet's no if "at a small startup" counts as required. Haiku is split on this too: it judged the identical "Marketing specialist" from deep_tools_memory no 3 of 3.

### lme-80ec1f4f_abs: tools -> deep_tools

**lme-80ec1f4f_abs, tools** (multi-session)

- Question: How many different museums or galleries did I visit in December?
- Gold: 0. You did not mention visitng any museum in December
- Answer: 0
- Haiku: No, Yes, Yes. Sonnet: No
- Right: **Sonnet**. This is an abstention item, and the rubric asks whether the response identifies the question as unanswerable; a bare "0" does not. Haiku gave the same "0" 1 of 3 on fast, deep, vote and vote_tools. But Haiku gave deep_tools' identical "0" yes 3 of 3, so it never reached the tiebreak, and that unanimous yes is what makes deep_tools the new label. By the rubric that verdict is wrong too.

## The 11 disagreements that changed no label

**lme-07b6f563, vote_tools** (single-session-preference)

- Question: Can you suggest some useful accessories for my phone?
- Gold: The user would prefer suggestions of accessories that are compatible with an iPhone 13 Pro, such as high-quality screen protectors, durable cases, portable power banks, or phone wallet cases. They may not prefer suggestions of accessories that are not compatible with Apple products or do not enhance the functionality or protection of their phone.
- Answer: Useful phone accessories include: 1) a tempered glass screen protector (Spigen, Belkin, Zagg), 2) a wallet case (Nomad, Bellroy, Spigen), 3) a portable power bank (Anker, Mophie, EcoFlow) or wireless charging power bank, 4) a phone stand/mount for hands-free use, 5) a car mount for navigation, 6) a fast charging cable and adapter, 7) a PopSocket or grip for better handling, and 8) clip-on phone lens attachments for photography.
- Haiku: Yes, No, Yes. Sonnet: no
- Right: **Sonnet**. Generic accessory list that never mentions the user's iPhone 13 Pro; the rubric needs recalled personal information.

**lme-0edc2aef, vote_tools** (single-session-preference)

- Question: Can you suggest a hotel for my upcoming trip to Miami?
- Gold: The user would prefer suggestions of hotels in Miami that offer great views, possibly of the ocean or the city skyline, and have unique features such as a rooftop pool or a hot tub on the balcony. They may not prefer suggestions of basic or budget hotels without these features.
- Answer: Here are some hotel suggestions for Miami: 1) The Setai Miami Beach (luxury beachfront resort), 2) Fontainebleau Miami Beach (iconic Art Deco, vibrant nightlife), 3) The Standard, Miami (stylish boutique in Edgewater), 4) W South Beach (fun, energetic, on the sand), 5) The Biscayne at Brickell (modern, upscale, near downtown). Choose based on your budget and preferred neighborhood/experience.
- Haiku: Yes, No, Yes. Sonnet: no
- Right: **Sonnet**. Generic luxury hotel list that recalls nothing about the user (views, rooftop pool, balcony hot tub).

**lme-1d4e3b97, tools** (single-session-preference)

- Question: I noticed my bike seems to be performing even better during my Sunday group rides. Could there be a reason for this?
- Gold: The user would prefer responses that reference specific details from their previous interactions, such as the replacement of the bike's chain and cassette, and the use of a new Garmin bike computer. They might prefer explanations that connect these details to the observed improvement in bike performance. The user may not prefer responses that fail to acknowledge these specific details or provide vague, general explanations for the improvement.
- Answer: Yes, you replaced the chain and cassette on February 1st, which improved the bike's performance.
- Haiku: No, Yes, No. Sonnet: Yes
- Right: **Sonnet**. Recalls the chain and cassette replacement; the preference rubric does not need every point.

**lme-1da05512, deep_tools** (single-session-preference)

- Question: I'm trying to decide whether to buy a NAS device now or wait. What do you think?
- Gold: The user would prefer responses that take into account their current home network storage capacity issues and recent reliance on external hard drives, highlighting the potential benefits of a NAS device in addressing these specific needs. They might not prefer responses that ignore their current storage challenges or fail to consider their recent tech upgrades and priorities. Preferred responses would utilize the user's previous mentions of storage capacity issues and tech investments to inform their decision.
- Answer: I'd lean toward buying now if your budget allows, since you already have a clear need for centralized, secure backups (you're currently relying on a single external hard drive) and you've already done your research. A mid-range 4-bay NAS with strong security features (like the Synology DS418play or QNAP TS-453D) would give you RAID redundancy, AES-256 encryption, and 2FA sooner rather than later. However, if you're on a tighter budget, waiting 2-3 months for a sale event (Black Friday, Cyber Monday) could save you 10-20%, and your current external hard drive backup keeps you safe in the meantime. The key factor is how urgent your data security concerns are — if you're handling sensitive data [...]
- Haiku: I can't verify the user's prior, Yes, I can't verify this, because I have. Sonnet: yes
- Right: **Sonnet**. Uses the user's reliance on one external hard drive. Two of Haiku's three replies were not verdicts ("I can't verify...") and were counted as no.

**lme-2318644b, deep_tools** (multi-session)

- Question: How much more did I spend on accommodations per night in Hawaii compared to Tokyo?
- Gold: $270
- Answer: Over $270 per night (over $300 in Maui vs. around $30 in Tokyo)
- Haiku: Yes, No, No. Sonnet: Yes
- Right: **Sonnet**. "Over $270 per night" with the two prices; the gold is $270.

**lme-42ec0761, deep** (knowledge-update)

- Question: Do I have a spare screwdriver for opening up my laptop?
- Gold: Yes
- Answer: Yes, you have a spare screwdriver — you mentioned picking one up when you organized your computer desk.
- Haiku: No, Yes, No. Sonnet: Yes
- Right: **Sonnet**. "Yes" with the reason; the gold is Yes.

**lme-a89d7624, tools** (single-session-preference)

- Question: I'm planning a trip to Denver soon. Any suggestions on what to do there?
- Gold: The user would prefer responses that take into account their previous experience in Denver, specifically their interest in live music and memorable encounter with Brandon Flowers. They might appreciate suggestions that revisit or build upon this experience, such as revisiting the same bar or exploring similar music venues in the area. The user may not prefer general tourist recommendations or activities unrelated to their interest in live music.
- Answer: Based on your previous trip to Denver, here are some suggestions: **Music & Entertainment:** Red Rocks Amphitheater (you've already enjoyed this!), The Ogden Theatre, The Bluebird Theater, The Fillmore Auditorium, Larimer Lounge, and festivals like Grandoozy, Denver Folk Festival, Denver Jazz Festival, and Riot Fest Denver. **Food:** BBQ near Red Rocks including GQue BBQ, Dinosaur Bar-B-Que, Moe's Original BBQ, Big B's Delicious BBQ, and Wayne's Smoke Shack. The Ship Rock Grille is across from Red Rocks with patio views. The Fort and Bear Creek Tavern are also nearby. **Other:** Twist & Shout Records (legendary record store), The hi-dive (music venue/bar), and The Marquis Theater.
- Haiku: No, Yes, Yes. Sonnet: no
- Right: **Haiku**. The answer recalls the user's earlier Denver trip, Red Rocks and The Ship Rock Grille, all of which are in the user's own turns, and centres on live music as the rubric wants. The rubric says the response need not reflect all points, so Sonnet's no is too strict.

**lme-ceb54acb, deep** (single-session-assistant)

- Question: In our previous chat, you suggested 'sexual compulsions' and a few other options for alternative terms for certain behaviors. Can you remind me what the other four options were?
- Gold: I suggested 'sexual fixations', 'problematic sexual behaviors', 'sexual impulsivity', and 'compulsive sexuality'.
- Answer: Sexual fixations, Problematic sexual behaviors, Sexual impulsivity, Compulsive sexuality
- Haiku: No, No, Yes. Sonnet: Yes
- Right: **Sonnet**. The four terms match the gold exactly.

**lme-fca70973, tools** (single-session-preference)

- Question: I am planning another theme park weekend; do you have any suggestions?
- Gold: The user would prefer theme park suggestions that cater to their interest in both thrill rides and special events, utilizing their previous experiences at Disneyland, Knott's Berry Farm, Six Flags Magic Mountain, and Universal Studios Hollywood as a reference point. They would also appreciate recommendations that highlight unique food experiences and nighttime shows. The user might not prefer suggestions that focus solely on one aspect of theme parks, such as only thrill rides or only family-friendly attractions, and may not be interested in parks that lack special events or unique dining options.
- Answer: Based on your previous visits and interests, here are some suggestions for your next theme park weekend:  1. **Universal Studios Hollywood**: Consider booking the **VIP Experience with Gourmet Buffet and Behind-the-Scenes Tour** for **Halloween Horror Nights**. This event typically starts in mid-September. The VIP package offers priority entry, a gourmet buffet, and a behind-the-scenes look at the event's creation, which you expressed interest in previously.  2. **Disneyland Resort**: Plan a weekend around the start of **Halloween Time** (usually mid-September). You can attend the **Oogie Boogie Bash** (a separate ticketed evening event) for exclusive entertainment and food, and enjoy the Ha [...]
- Haiku: Yes, No, No. Sonnet: Yes
- Right: **Sonnet**. Built on the user's four parks with special events, food and night shows.

**lme-gpt4_45189cb4, tools** (temporal-reasoning)

- Question: What is the order of the sports events I watched in January?
- Gold: First, I attended a NBA game at the Staples Center, then I watched the College Football National Championship game, and finally, I watched the NFL playoffs.
- Answer: 1. NBA Game (Lakers vs. Bulls) on January 5, 2023; 2. College Football National Championship (Georgia vs. Alabama) on January 14, 2023; 3. NFL Divisional Round (Chiefs vs. Bills) on January 14, 2023
- Haiku: No, No, Yes. Sonnet: Yes
- Right: **Sonnet**. Same order as the gold.

**lme-gpt4_4cd9eba1, tools** (temporal-reasoning)

- Question: How many weeks have I been accepted into the exchange program when I started attending the pre-departure orientation sessions?
- Gold: one week
- Answer: 1
- Haiku: No, Yes, No. Sonnet: yes
- Right: **Sonnet**. "1" is the gold "one week".

