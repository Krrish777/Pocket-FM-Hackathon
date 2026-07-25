/**
 * MOCK DATA — CANON: a playable branching layer over the Dexter novels
 * ─────────────────────────────────────────────────────────────────────
 * Retargeted 2026-07-26 to match `project_context.md` (the authoritative spec)
 * instead of the superseded `docs/REQUREMENTS.md` framing this file used to
 * implement. See `docs/API_CONTRACT_NOTES.md` for what changed for the backend.
 *
 * i18n: every user-facing string is LocalizedText { hi, en }. Use t(value, locale).
 *
 * ⚠ CONTENT WARNING (honesty, not legal): the character facts and the whole
 * 5-turn run below are HAND-AUTHORED for this demo, generic and widely-known
 * (blood-spatter analyst, foster sister/detective, suspicious colleague,
 * captain, girlfriend with two kids) — they are NOT extracted from the real
 * Jeff Lindsay novels and must not be treated as verified canon
 * (project_context.md §6.3, OD-2). `establishedIn: "Series canon"` marks a
 * baseline premise; `establishedIn: "Turn N"` marks something this run itself
 * established — neither is a real page/chapter citation. Real ingestion
 * replaces both with actual novel citations.
 *
 * `Choice.source` attributions (workTitle/author/platform) are invented
 * placeholders standing in for the real Branch Oracle's scraped fan-fiction
 * output (§5.2) — not real fan authors or real fics.
 *
 * ── REHEARSED DEMO PATH ──────────────────────────────────────────────
 *   Select CH-01 (Dexter) → play all 5 turns, always taking the "-A" choice
 *   → Output (closing beat) → REPLAY AS DEBRA → she visibly doesn't know
 *   what the audience just watched happen → then fire the planted-defect demo.
 */

// ═══════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════

export type Locale = "hi" | "en";
export type LocalizedText = Record<Locale, string>;

export const t = (v: LocalizedText, locale: Locale): string => v[locale];

/** Fixed 5 — project_context.md SD-6/§6.3. Order is fixed; no protagonist special-casing (M8). */
export type CharacterId = "CH-01" | "CH-02" | "CH-03" | "CH-04" | "CH-05";

export type Character = {
  id: CharacterId;
  name: LocalizedText;
  role: LocalizedText;
  blurb: LocalizedText;
  portraitUrl: string; // unused — portraits are procedural (ProceduralPortrait). Kept for contract parity.
};

/**
 * A story on the shelf. Original premises only (no third-party IP) — the
 * user's own reference points ("a Spiderman or Avengers-style story") are a
 * STYLE cue, not a license to use trademarked names, so these are original
 * epic/hero-flavored titles instead.
 *
 * Only `interactive: true` leads into a full playthrough; the others are
 * shelf realism — same "present but inert" precedent as before — but every
 * card's `voiceSummary` is real, spoken narration (lib/voice.ts), so holding
 * any card is a genuine, working interaction, not a dead click.
 */
export type Story = {
  id: string;
  title: LocalizedText;
  tagline: LocalizedText;
  /** Plain English — read aloud via the Web Speech API, not displayed as-is. */
  voiceSummary: string;
  interactive: boolean;
};

export type Fact = {
  factId: string;
  summary: LocalizedText;
  establishedIn: string; // "Series canon" | "Turn N" — see file header.
  /** §5.3 epistemic provenance. Illustrative — beliefState below is hand-authored, not derived from these at runtime. */
  witnessedBy: CharacterId[];
  toldTo: CharacterId[];
  inferredBy?: CharacterId[];
};

export type FactDelta = {
  invalidated: Fact[];
  held: Fact[];
  newNeeded: Fact[];
};

export type Choice = {
  choiceId: string;
  label: LocalizedText;
  weight: "low" | "medium" | "high";
  tone?: "heavy" | "standard";
  /** M4/SD-9 — must visibly read as fan-fiction-sourced, not invented by us. Mock/placeholder attribution. */
  source: { workTitle: string; author: string; platform: string };
};

/**
 * All 5 characters get one of these, every turn (M8 — uniform, never just the
 * acting character). beliefState/notYetKnown are hand-authored per turn, not
 * computed by a runtime diffing engine — that engine is the separate backend's
 * job; authoring is far cheaper and equally convincing for a mock.
 */
export type CharacterView = {
  sceneText: LocalizedText;
  beliefSummary: LocalizedText;
  beliefState: "invalid" | "hold" | "new" | "unaware";
  present: boolean;
  knownFactIds: string[];
  /** Only populated for the replay character(s) — facts the audience just watched that this character explicitly does not know. */
  notYetKnown?: LocalizedText[];
};

export type VerifierResult =
  | { status: "ok"; verifiedAgainst: number }
  | {
      status: "flagged";
      citation: {
        draftClaim: LocalizedText;
        canonFact: LocalizedText;
        sourceRef: string;
      };
    };

export type Turn = {
  turnIndex: number;
  actingCharacterId: CharacterId;
  sceneText: LocalizedText;
  verifier: VerifierResult;
  choices: Choice[];
  /** The rehearsed pick — only this choice has fully distinct downstream content (same simplification as the old ALT-B-falls-through-to-ALT-A pattern). */
  chosenChoiceId: string;
  delta: FactDelta;
  characterViews: Record<CharacterId, CharacterView>;
};

export type Run = {
  runId: string;
  title: LocalizedText;
  protagonistId: CharacterId;
  turns: Turn[];
};

// ═══════════════════════════════════════════════════════════════════
// UI STRINGS
// ═══════════════════════════════════════════════════════════════════

export const ui = {
  appName: { hi: "कैनन", en: "CANON" },
  appSubtitle: { hi: "एक खेली जाने वाली शाखा", en: "A PLAYABLE BRANCH" },

  shelfHeading: {
    hi: "एक कहानी चुनिए",
    en: "Choose a story",
  },
  shelfSub: {
    hi: "किसी भी कार्ड को दबाकर रखिए — कहानी ख़ुद अपनी आवाज़ में बताएगी कि वह किस बारे में है।",
    en: "Hold any card — the story tells you what it's about, in its own voice.",
  },
  holdToHearLabel: { hi: "सुनने के लिए दबाएँ", en: "TAP TO HEAR IT" },
  nowPlayingLabel: { hi: "अभी बज रहा है…", en: "NOW PLAYING…" },
  comingSoonLabel: { hi: "जल्द आ रहा है", en: "COMING SOON — VOICE ONLY FOR NOW" },
  enterThisStoryButton: { hi: "इस कहानी में जाएँ", en: "ENTER THIS STORY" },

  plotInputHeading: { hi: "अब कहानी बदलिए", en: "Now change the story" },
  plotInputSub: {
    hi: "अपना ख़ुद का 'क्या हो अगर…' लिखिए। यह ठीक उसी पल में बदलाव लाएगा।",
    en: "Write your own \"what if\". It changes exactly this moment in the story.",
  },
  plotInputPlaceholder: {
    hi: "जैसे: क्या हो अगर उसे उसी रात पकड़ लिया जाता?",
    en: "e.g. What if he got caught that very night?",
  },
  generateButton: { hi: "कहानी बनाइए", en: "GENERATE THE STORY" },
  generatingLabel: { hi: "आपकी कहानी लिखी जा रही है…", en: "WRITING YOUR STORY…" },

  playNarrationButton: { hi: "सुनिए", en: "PLAY NARRATION" },
  pauseNarrationButton: { hi: "रोकिए", en: "PAUSE" },
  addYourMusicNote: {
    hi: "यहाँ बैकग्राउंड म्यूज़िक जोड़ने की जगह है — एडिटिंग में डालें।",
    en: "Background music goes here — add it in your edit.",
  },

  rippleCaption: {
    hi: "आपके फ़ैसले से हर किरदार की जानकारी कैसे बदलती है, यही यहाँ दिख रहा है।",
    en: "This is how your choice changes what each character knows.",
  },

  characterSelectHeading: {
    hi: "एक किरदार चुनिए। उसकी आँखों से खेलिए।",
    en: "Choose a character. Play forward through their eyes.",
  },
  characterSelectSub: {
    hi: "हर किरदार सिर्फ़ वही जानता है जो उसने सीखा है — बाक़ी सब आपसे छुपा है, जब तक आप कोई और नहीं बन जाते।",
    en: "Every character remembers only what they actually learned — the rest stays hidden, until you become someone else.",
  },
  infinityBannerLead: {
    hi: "हर चुनाव किसी और के लिए एक अलग सच बनाता है।",
    en: "Every choice makes a different truth for someone else.",
  },
  infinityBannerSub: {
    hi: "अंत में, वही घटनाएँ किसी और किरदार की नज़र से फिर से जीकर देखिए।",
    en: "At the end, replay the very same events through another character's eyes.",
  },
  navHome: { hi: "होम", en: "Home" },
  navJourneys: { hi: "यात्राएं", en: "My Journeys" },
  navTimeMachine: { hi: "टाइम मशीन", en: "Time Machine" },
  navUniverse: { hi: "ब्रह्मांड", en: "Universe" },
  navFavorites: { hi: "पसंदीदा", en: "Favorites" },
  navSettings: { hi: "सेटिंग्स", en: "Settings" },

  charactersLabel: { hi: "किरदार", en: "CAST" },
  turnsCountLabel: { hi: "पल", en: "TURNS" },
  viewJourneyButton: { hi: "इसे खेलिए", en: "PLAY THIS ONE" },
  enterPlaythroughButton: { hi: "खेल शुरू करें", en: "BEGIN THE PLAYTHROUGH" },
  inertCharacterNote: {
    hi: "बाक़ी किरदारों के पूरे खेल अभी नहीं बने — रीप्ले में इन्हें देखिए।",
    en: "Full playthroughs for the rest aren't built yet — meet them in the replay instead.",
  },

  canonLabel: { hi: "मूल", en: "CANON" },
  turnLabel: { hi: "पल", en: "TURN" },
  choicesHeading: { hi: "आगे क्या होता है", en: "WHAT HAPPENS NEXT" },
  sourcedFromLabel: { hi: "फ़ैन-फ़िक्शन से लिया गया", en: "SOURCED FROM FAN FICTION" },
  commitChoiceButton: { hi: "यह चुनाव करें", en: "MAKE THIS CHOICE" },

  beliefRippleHeading: { hi: "अब हर किरदार क्या मानता है", en: "WHAT THE CAST NOW BELIEVES" },
  invalidatedLabel: { hi: "धारणा टूटी", en: "BELIEF OVERTURNED" },
  heldLabel: { hi: "अब भी सच", en: "STILL HOLDS" },
  newNeededLabel: { hi: "नई जानकारी", en: "NEW KNOWLEDGE" },
  unawareLabel: { hi: "अब भी अनजान", en: "STILL UNAWARE" },
  seeResultButton: { hi: "देखिए किसे क्या पता है", en: "SEE WHO KNOWS WHAT" },
  continueButton: { hi: "आगे बढ़िए", en: "CONTINUE" },

  verifierOk: { hi: "कैनन-संगत", en: "CANON-CONSISTENT" },
  verifierOkDetail: {
    hi: "अप्रभावित तथ्यों के विरुद्ध सत्यापित",
    en: "VERIFIED AGAINST UNAFFECTED FACTS",
  },
  verifierFlagged: { hi: "विरोधाभास चिह्नित", en: "CONTRADICTION FLAGGED" },
  draftClaimLabel: { hi: "प्रारूप कहता है", en: "DRAFT CLAIM" },
  canonSaysLabel: { hi: "कैनन कहता है", en: "CANON SAYS" },

  outputHeading: { hi: "अंतिम दृश्य", en: "FINAL SCENE" },
  replayAsDebraButton: { hi: "देब्रा के रूप में फिर से देखिए →", en: "REPLAY AS DEBRA →" },
  replayBadgeLabel: { hi: "देब्रा के रूप में रीप्ले हो रहा है", en: "REPLAYING AS DEBRA" },
  notYetKnownHeading: { hi: "जो वह अब तक नहीं जानती", en: "WHAT SHE DOESN'T KNOW YET" },
  exitReplayButton: { hi: "← अंत पर वापस", en: "← BACK TO THE ENDING" },

  loadingRipple: { hi: "विश्वास की गणना…", en: "COMPUTING BELIEF…" },
  loadingScene: { hi: "दृश्य लिखा जा रहा है…", en: "WRITING THE SCENE…" },
} satisfies Record<string, LocalizedText>;

// ═══════════════════════════════════════════════════════════════════
// 1. CHARACTERS   → GET /api/characters
// ═══════════════════════════════════════════════════════════════════

export const characters: Character[] = [
  {
    id: "CH-01",
    name: { hi: "डेक्सटर मॉर्गन", en: "Dexter Morgan" },
    role: { hi: "जो हिसाब से मारता है", en: "The one who kills by a code" },
    blurb: {
      hi: "मायामी मेट्रो का ब्लड-स्पैटर विश्लेषक।\nअपने पालक पिता हैरी के सिखाए एक निजी नियम से जीता है।",
      en: "Miami Metro's blood-spatter analyst.\nLives by a private code his foster father Harry taught him.",
    },
    portraitUrl: "/portraits/dexter.jpg",
  },
  {
    id: "CH-02",
    name: { hi: "देब्रा मॉर्गन", en: "Debra Morgan" },
    role: { hi: "जासूस, डेक्सटर की पालक बहन", en: "Detective, Dexter's foster sister" },
    blurb: {
      hi: "अपने केस ख़ुद हल करना चाहती है, किसी की मदद से नहीं।\nअपने भाई पर शक करने का कोई कारण उसके पास कभी नहीं रहा।",
      en: "Wants every case to be her own win, not a favor.\nHas never once had reason to suspect her brother.",
    },
    portraitUrl: "/portraits/debra.jpg",
  },
  {
    id: "CH-03",
    name: { hi: "जेम्स डोक्स", en: "James Doakes" },
    role: { hi: "जो कभी भरोसा नहीं करता", en: "The one who never trusted him" },
    blurb: {
      hi: "मायामी मेट्रो का जासूस। डेक्सटर को शुरू से अजीब पाता है।\nसबूत के बग़ैर भी शक करना जानता है।",
      en: "Miami Metro detective. Has found Dexter off from day one.\nKnows how to suspect someone without a shred of proof.",
    },
    portraitUrl: "/portraits/doakes.jpg",
  },
  {
    id: "CH-04",
    name: { hi: "मारिया लागार्टा", en: "Maria LaGuerta" },
    role: { hi: "कैप्टन, मायामी मेट्रो होमिसाइड", en: "Captain, Miami Metro Homicide" },
    blurb: {
      hi: "नतीजों से विभाग को चलाती है, अफ़वाहों से नहीं।\nएक बंद केस उसके लिए एक अच्छा हफ़्ता है।",
      en: "Runs the department on results, not rumor.\nA closed case is a good week, as far as she's concerned.",
    },
    portraitUrl: "/portraits/laguerta.jpg",
  },
  {
    id: "CH-05",
    name: { hi: "रीटा बेनेट", en: "Rita Bennett" },
    role: { hi: "डेक्सटर की प्रेमिका, दो बच्चों की माँ", en: "Dexter's girlfriend, mother of two" },
    blurb: {
      hi: "एक ख़राब शादी के बाद एक शांत ज़िंदगी चाहती है।\nडेक्सटर की थकान में उसे कभी कुछ अजीब नहीं लगा।",
      en: "Wants a quiet life after a bad marriage.\nHas never once read anything strange into Dexter's tiredness.",
    },
    portraitUrl: "/portraits/rita.jpg",
  },
];

// ═══════════════════════════════════════════════════════════════════
// 1B. SHELF — GET /api/stories (original premises, no third-party IP)
// ═══════════════════════════════════════════════════════════════════

export const stories: Story[] = [
  {
    id: "ST-01",
    title: { hi: "एक रात, दो सज़ाएँ", en: "One Night, Two Sentences" },
    tagline: {
      hi: "एक जासूस जो ख़ुद ही अपराधी है। एक बहन जो कभी शक नहीं करती।",
      en: "A detective who is also the killer. A sister who never suspects.",
    },
    voiceSummary:
      "In a city that thinks it knows its heroes, one detective keeps a secret code only he lives by. Every case he closes hides another he's already solved himself. Tonight, someone gets close enough to almost see it.",
    interactive: true,
  },
  {
    id: "ST-02",
    title: { hi: "आयरनक्लैड", en: "Ironclad" },
    tagline: {
      hi: "एक गिरा हुआ इंजीनियर, एक छुपी हुई कवच।",
      en: "A fallen engineer. A suit only he knows exists.",
    },
    voiceSummary:
      "A brilliant engineer, cast out of his own company, builds one last invention in secret — a suit of armor strong enough to protect the city that forgot him. Nobody knows the hero behind the helmet is the man they already wrote off.",
    interactive: false,
  },
  {
    id: "ST-03",
    title: { hi: "लास्ट वॉच", en: "Last Watch" },
    tagline: {
      hi: "पाँच अजनबी। एक उलटी गिनती जो सबको जोड़ देती है।",
      en: "Five strangers. One countdown that forces them together.",
    },
    voiceSummary:
      "Five strangers, each hiding a power they've never told anyone about, are pulled into the same impossible night when a countdown starts over the city. None of them trust each other. All of them are the only ones who can stop it.",
    interactive: false,
  },
];

// ═══════════════════════════════════════════════════════════════════
// 2. FACTS — baseline (Series canon) + what each turn establishes
// ═══════════════════════════════════════════════════════════════════

const F00: Fact = { factId: "F-00", summary: { hi: "डेक्सटर मायामी मेट्रो होमिसाइड का ब्लड-स्पैटर विश्लेषक है", en: "Dexter is Miami Metro Homicide's blood-spatter analyst" }, establishedIn: "Series canon", witnessedBy: ["CH-01", "CH-02", "CH-03", "CH-04"], toldTo: [] };
const F01: Fact = { factId: "F-01", summary: { hi: "डेक्सटर हैरी के सिखाए एक निजी नियम — हैरी कोड — से चलता है", en: "Dexter operates by a private code his foster father Harry taught him" }, establishedIn: "Series canon", witnessedBy: ["CH-01"], toldTo: [] };
const F02: Fact = { factId: "F-02", summary: { hi: "डोक्स ने कभी डेक्सटर पर पूरा भरोसा नहीं किया", en: "Doakes has never fully trusted Dexter" }, establishedIn: "Series canon", witnessedBy: ["CH-01", "CH-03"], toldTo: [] };
const F03: Fact = { factId: "F-03", summary: { hi: "देब्रा डेक्सटर की पालक बहन और मायामी मेट्रो में जासूस है", en: "Debra is Dexter's foster sister and a detective at Miami Metro" }, establishedIn: "Series canon", witnessedBy: ["CH-01", "CH-02"], toldTo: [] };
const F04: Fact = { factId: "F-04", summary: { hi: "रीटा डेक्सटर की प्रेमिका है, पिछली शादी से दो बच्चे पाल रही है", en: "Rita is Dexter's girlfriend, raising two children from a previous marriage" }, establishedIn: "Series canon", witnessedBy: ["CH-01", "CH-05"], toldTo: [] };
const F05: Fact = { factId: "F-05", summary: { hi: "लागार्टा मायामी मेट्रो होमिसाइड की कैप्टन है", en: "LaGuerta is captain of Miami Metro Homicide" }, establishedIn: "Series canon", witnessedBy: ["CH-01", "CH-02", "CH-03", "CH-04"], toldTo: [] };
const F06: Fact = { factId: "F-06", summary: { hi: "रे केसलर एक तकनीकी ख़ामी की वजह से दो साल से सज़ा से बचा हुआ है", en: "Ray Kessler has evaded justice for two years on a technicality" }, establishedIn: "Series canon", witnessedBy: ["CH-01"], toldTo: [] };

const F10: Fact = { factId: "F-10", summary: { hi: "डोक्स ने डेक्सटर की एक पूरी रात का हिसाब न मिलना नोट किया", en: "Doakes clocked a full night of Dexter's whereabouts as unaccounted for" }, establishedIn: "Turn 1", witnessedBy: ["CH-03"], toldTo: [] };
const F11: Fact = { factId: "F-11", summary: { hi: "डेक्सटर ने डोक्स की परछाईं भाँपकर केसलर से मिलने की योजना टाल दी", en: "Dexter aborted his planned visit to Kessler after spotting Doakes's tail" }, establishedIn: "Turn 2", witnessedBy: ["CH-01", "CH-03"], toldTo: [] };
const F12: Fact = { factId: "F-12", summary: { hi: "डोक्स के पास अब डेक्सटर के बर्ताव का एक ऐसा सबूत है जिसे वह समझा नहीं सकता", en: "Doakes now has behavioral evidence of Dexter he can't explain away" }, establishedIn: "Turn 2", witnessedBy: ["CH-03"], toldTo: [] };
const F13: Fact = { factId: "F-13", summary: { hi: "देब्रा के केस की ब्लड पैनल रिपोर्ट आख़िर उसके काम की निकली", en: "Debra's blood panel on her case finally came back favorable" }, establishedIn: "Turn 3", witnessedBy: ["CH-01", "CH-02"], toldTo: ["CH-02"] };
const F14: Fact = { factId: "F-14", summary: { hi: "देब्रा मानती है कि यह ब्रेक सिर्फ़ लैब की समय-सारणी से मिला", en: "Debra believes this break came purely from lab timing" }, establishedIn: "Turn 3", witnessedBy: ["CH-02"], toldTo: [] };

const F15: Fact = { factId: "F-15", summary: { hi: "रे केसलर का हिसाब हैरी कोड के मुताबिक़ चुका दिया गया", en: "Ray Kessler has been dealt with, per Harry's Code" }, establishedIn: "Turn 4", witnessedBy: ["CH-01"], toldTo: [] };
const F16: Fact = { factId: "F-16", summary: { hi: "डोक्स उस रात गली के मुहाने पर मौजूद था, पर सबूत के बिना", en: "Doakes was present at the mouth of the street that night, with no proof" }, establishedIn: "Turn 4", witnessedBy: ["CH-01", "CH-03"], toldTo: [] };
const F17: Fact = { factId: "F-17", summary: { hi: "देब्रा को केस बंद करने पर विभाग में सराहा गया", en: "Debra received a formal commendation for closing her case" }, establishedIn: "Turn 5", witnessedBy: ["CH-01", "CH-02", "CH-04"], toldTo: ["CH-02"] };
const F18: Fact = { factId: "F-18", summary: { hi: "डोक्स का शक अब स्थायी है, पर सबूत के बग़ैर", en: "Doakes's suspicion is now permanent, but unproven" }, establishedIn: "Turn 5", witnessedBy: ["CH-01", "CH-03"], toldTo: [] };

// ═══════════════════════════════════════════════════════════════════
// 3. THE RUN — CH-01 (Dexter), 5 turns   → GET /api/runs/CH-01
// ═══════════════════════════════════════════════════════════════════

const held1 = [F00, F01, F02, F03, F04, F05, F06];
const held2 = [...held1, F10];
const held3 = [...held2, F11, F12];
// F15/F16 are brand new AT turn 4 (they live in that turn's `newNeeded`, not `held`);
// they graduate into `held` starting turn 5, once they're no longer new.
const held4 = [...held3.filter((f) => f.factId !== "F-06"), F13, F14];
const held5 = [...held4, F15, F16];

export const run: Run = {
  runId: "RUN-DEX-01",
  title: { hi: "एक रात, दो सज़ाएँ", en: "One Night, Two Sentences" },
  protagonistId: "CH-01",
  turns: [
    // ── TURN 1 — the coffee machine ──────────────────────────────────
    {
      turnIndex: 1,
      actingCharacterId: "CH-01",
      sceneText: {
        hi: `डोक्स कॉफ़ी मशीन के पास खड़ा मिला, जो कभी अच्छा संकेत नहीं होता। डोक्स का कहीं भी खड़ा मिलना अच्छा संकेत नहीं होता, पर कॉफ़ी मशीन का मतलब था कि वह इतनी देर से खड़ा था कि उसने पूरा वाक्य सोच लिया हो।

"कल रात कहाँ थे, मॉर्गन?" कोई नमस्ते नहीं। डोक्स नमस्ते में विश्वास नहीं रखता।

मैंने उसे सच का वह टुकड़ा दिया जो एक वाक्य में समा जाए — एक पोकर गेम, किसी दोस्त का फ़्लैट, कुछ ऐसा जो गुरुवार से पहले जाँचा न जा सके। किसी को सच जैसी दिखने वाली, पर अंदर से खाली चीज़ थमा देना एक ख़ास हुनर है। मुझे इसका बहुत अभ्यास है।

डोक्स ने पलक नहीं झपकाई। वह कभी पहले पलक नहीं झपकाता। पर उसने कोई अगला सवाल भी नहीं पूछा — और डोक्स की तरफ़ से यह अपने आप में एक जवाब था।`,
        en: `Doakes was waiting by the coffee machine, which was never a good sign. Doakes waiting anywhere was never a good sign, but the coffee machine specifically meant he'd been standing there long enough to compose a full sentence.

"Where were you last night, Morgan?" No hello. Doakes didn't believe in hello.

I gave him the version of the truth that fit in a sentence — a poker game, a friend's apartment, nothing that could be checked before Thursday. It is a specific skill, handing someone a truth-shaped object made entirely of nothing. I have had a lot of practice.

Doakes didn't blink. He never blinks first. But he also didn't ask a follow-up question, which from Doakes was its own kind of answer.`,
      },
      verifier: { status: "ok", verifiedAgainst: held1.length },
      choices: [
        {
          choiceId: "T1-A",
          label: { hi: "एक हल्का झूठ और मज़ाक़ में बात टाल देना — डोक्स जो चाहे समझे", en: "Deflect with an easy lie and a joke, letting Doakes read whatever he wants into it" },
          weight: "high",
          source: { workTitle: "the code we keep", author: "nightshift_writes", platform: "mock fan-fiction archive" },
        },
        {
          choiceId: "T1-B",
          label: { hi: "आधा सच बताना — सही जगह, ग़लत रात", en: "Offer a half-truth — the right place, the wrong night" },
          weight: "medium",
          source: { workTitle: "half of anything", author: "quietmiami", platform: "mock fan-fiction archive" },
        },
        {
          choiceId: "T1-C",
          label: { hi: "कुछ न कहना, बस आगे बढ़ जाना", en: "Say nothing at all and walk past him" },
          weight: "low",
          tone: "heavy",
          source: { workTitle: "the long silence", author: "harrys_second_son", platform: "mock fan-fiction archive" },
        },
      ],
      chosenChoiceId: "T1-A",
      delta: { invalidated: [], held: held1, newNeeded: [F10] },
      characterViews: {
        "CH-01": {
          sceneText: { hi: "देखा ऊपर", en: "see scene above" },
          beliefSummary: { hi: "वह जानता है कि डोक्स कुछ जोड़ना शुरू कर चुका है।", en: "He knows Doakes is starting to add things up." },
          beliefState: "new",
          present: true,
          knownFactIds: ["F-00", "F-01", "F-02", "F-10"],
        },
        "CH-02": {
          sceneText: {
            hi: "मैं तीन डेस्क आगे बैठी, एक ऐसी चोरी की फ़ाइल में उलझी थी जो कहीं नहीं जा रही थी। मुझे यह भी पता नहीं चला कि डोक्स और डेक्सटर बात कर रहे थे।",
            en: "I was three desks over, elbow-deep in a robbery file that wasn't going anywhere. I didn't even clock Doakes and Dexter talking.",
          },
          beliefSummary: { hi: "देब्रा को इस बातचीत का कोई पता नहीं है।", en: "Debra has no idea this conversation happened." },
          beliefState: "unaware",
          present: false,
          knownFactIds: ["F-00", "F-03"],
        },
        "CH-03": {
          sceneText: {
            hi: "मॉर्गन की कहानी में कोई छेद नहीं था — और यही बात मुझे खटक रही थी। किसी की कहानी इतनी साफ़ नहीं होती।",
            en: "Morgan's story didn't have a hole in it, and that's exactly what bothered me. Nobody's story is that clean.",
          },
          beliefSummary: { hi: "डोक्स का शक अभी और पैना हो गया है।", en: "Doakes's suspicion just sharpened." },
          beliefState: "new",
          present: true,
          knownFactIds: ["F-00", "F-02", "F-10"],
        },
        "CH-04": {
          sceneText: { hi: "आज सुबह की ब्रीफ़िंग सामान्य रही। कुछ भी ध्यान देने लायक़ नहीं हुआ।", en: "Morning briefing was routine. Nothing worth noting." },
          beliefSummary: { hi: "अभी उसके राडार पर कुछ नहीं है।", en: "Nothing on her radar yet." },
          beliefState: "unaware",
          present: false,
          knownFactIds: ["F-00", "F-05"],
        },
        "CH-05": {
          sceneText: { hi: "डेक्सटर आते वक़्त दूध ले आया। कुछ भी ग़लत नहीं लगा।", en: "Dexter picked up milk on the way over. Nothing seemed wrong." },
          beliefSummary: { hi: "रीटा को इनमें से कुछ भी पता नहीं है।", en: "Rita remains entirely unaware." },
          beliefState: "unaware",
          present: false,
          knownFactIds: ["F-00", "F-04"],
        },
      },
    },

    // ── TURN 2 — the tail ─────────────────────────────────────────────
    {
      turnIndex: 2,
      actingCharacterId: "CH-01",
      sceneText: {
        hi: `एक ख़ास तरह की ख़ामोशी होती है जो बताती है कि कोई जान-बूझकर आपके पीछे है। साधारण पीछे वाली नहीं — मायामी का ट्रैफ़िक हर रात मेरे पीछे सौ गाड़ियाँ लगा देता था — बल्कि वह वाली, जहाँ वही हेडलाइट्स दो बार वही ग़लत मोड़ लें।

आज रात का काम बहुत साफ़ था। रे केसलर ने इसे हक़ से कमाया था — एक वर्कशॉप, एक सहायक, दो साल पुरानी एक तकनीकी ख़ामी जिसे जूरी ने बेगुनाही समझ लिया। हैरी का नियम सीधा है: पक्का होना चाहिए। मैं पक्का था।

हेडलाइट्स ने तीसरी बार मुड़ना दोहराया।

मैं डोक्स की गाड़ी को आठवीं सड़क की नाली के ऊपर से गुज़रने की आवाज़ से पहचानता हूँ। ऐसी बातें जानना मेरा एक शौक़ बन गया है।`,
        en: `There is a particular kind of quiet that means someone is behind you on purpose. Not the ordinary kind — Miami traffic put a hundred cars behind me every night — but the kind where the same headlights make the same wrong turn twice.

I had a very specific evening planned. Ray Kessler had earned it fairly — a workshop, an assistant, a technicality two years old that a jury had mistaken for innocence. Harry's rules are simple: you have to be sure, and I was sure.

The headlights turned a third time.

I know Doakes's car by the sound it makes over the storm drain on 8th. I have made a hobby of knowing things like that.`,
      },
      verifier: { status: "ok", verifiedAgainst: held2.length },
      choices: [
        {
          choiceId: "T2-A",
          label: { hi: "जान-बूझकर पीछा छुड़ाना — केसलर आज रात बच जाएगा, पर डोक्स को रास्ता नहीं दिखेगा", en: "Deliberately lose the tail — Kessler lives another night, but Doakes doesn't see where I go" },
          weight: "high",
          source: { workTitle: "the long way home", author: "nightshift_writes", platform: "mock fan-fiction archive" },
        },
        {
          choiceId: "T2-B",
          label: { hi: "खुलेआम रुककर डोक्स का सामना करना", en: "Turn and confront Doakes in the open" },
          weight: "medium",
          tone: "heavy",
          source: { workTitle: "headlights", author: "quietmiami", platform: "mock fan-fiction archive" },
        },
        {
          choiceId: "T2-C",
          label: { hi: "केसलर की तरफ़ बढ़ते रहना, आख़िरी मोड़ पर पीछा छुड़ाने की उम्मीद में", en: "Keep driving toward Kessler's and gamble on losing him at the last turn" },
          weight: "high",
          tone: "heavy",
          source: { workTitle: "cutting it close", author: "harrys_second_son", platform: "mock fan-fiction archive" },
        },
      ],
      chosenChoiceId: "T2-A",
      delta: { invalidated: [], held: held2, newNeeded: [F11, F12] },
      characterViews: {
        "CH-01": {
          sceneText: { hi: "देखा ऊपर", en: "see scene above" },
          beliefSummary: { hi: "उसकी योजना अभी रुक गई, और वह जानता है ठीक किसकी वजह से।", en: "His plan just got interrupted, and he knows exactly by whom." },
          beliefState: "invalid",
          present: true,
          knownFactIds: ["F-00", "F-01", "F-06", "F-10", "F-11", "F-12"],
        },
        "CH-02": {
          sceneText: { hi: "डेल्गादो फ़ाइल पर रात 11 बजे तक काम किया। डेस्क पर ठंडे नूडल्स खाए। कुछ ख़ास नहीं।", en: "Worked the Delgado file until 11pm. Ate cold noodles at my desk. Nothing." },
          beliefSummary: { hi: "देब्रा को कुछ पता नहीं।", en: "Debra remains unaware." },
          beliefState: "unaware",
          present: false,
          knownFactIds: ["F-00", "F-03"],
        },
        "CH-03": {
          sceneText: {
            hi: "मॉर्गन बीस मिनट तक चक्कर काटता रहा। बेगुनाह लोग चक्कर नहीं काटते। मैं उसे मरीना के पास खो बैठा, पर मुझे पता है 'मरीना के पास' कहाँ जाता है।",
            en: "Morgan drove in a circle for twenty minutes. Innocent people don't drive in circles. I lost him near the marina, but I know where 'near the marina' leads.",
          },
          beliefSummary: { hi: "डोक्स के पास अब ठोस सबूत है, भले ही वह अब भी नहीं जानता क्या।", en: "Doakes now has concrete evidence, though he still doesn't know what." },
          beliefState: "new",
          present: true,
          knownFactIds: ["F-00", "F-02", "F-10", "F-11", "F-12"],
        },
        "CH-04": {
          sceneText: { hi: "आज रात कोई रिपोर्ट नहीं आई। सामान्य रात।", en: "No reports came in tonight. An ordinary night." },
          beliefSummary: { hi: "अनजान बनी हुई है।", en: "Remains unaware." },
          beliefState: "unaware",
          present: false,
          knownFactIds: ["F-00", "F-05"],
        },
        "CH-05": {
          sceneText: { hi: "डेक्सटर फिर देर से घर आया। बोला ट्रैफ़िक था। मानने का कोई कारण भी नहीं है न मानने का।", en: "Dexter came home late again. Said it was traffic. I believe him because there's no reason not to." },
          beliefSummary: { hi: "अनजान बनी हुई है।", en: "Remains unaware." },
          beliefState: "unaware",
          present: false,
          knownFactIds: ["F-00", "F-04"],
        },
      },
    },

    // ── TURN 3 — Debra's case ────────────────────────────────────────
    {
      turnIndex: 3,
      actingCharacterId: "CH-01",
      sceneText: {
        hi: `देब्रा के बोर्ड पर केसलर का नाम पहले से था — एक दर्जन नामों में से एक, बाक़ियों से ज़्यादा वज़नी नहीं। वह दो महीने से एक ऐसे पैटर्न को महसूस कर रही थी जिसे वह अभी साबित नहीं कर पा रही थी: तीन असंबंधित हमले जो असल में असंबंधित नहीं थे।

उसने मुझसे वर्कशॉप केस का ब्लड पैनल दोबारा, चुपचाप, चलाने को कहा — क्योंकि असली लैब में छह हफ़्तों की लाइन थी और उसके पास छह हफ़्ते नहीं थे। मैं उसे बता सकता था कि पैनल वह नहीं कहेगा जो वह चाहती है। इसके बजाय मैंने उसे दो बार चलाया।

दूसरी बार, उसने वही कहा जो उसे चाहिए था। यह झूठ नहीं था — सबूत असली था, मैंने बस यह चुना कि किस दोपहर इसे नोटिस करूँ। फ़र्क़ है, और मैंने ख़ुद को इस बात से समझौता करा लिया है कि यह फ़र्क़ कितना पतला है।`,
        en: `Debra had Kessler's name on her board already — one name among a dozen, no more weight than the others. She was two months into a pattern she could feel but not yet prove: three unrelated assault cases that weren't unrelated at all.

She asked me to rerun a blood panel on the workshop case, off the books, because the official lab was backed up six weeks and she didn't have six weeks. I could have told her the panel wasn't going to say what she hoped. Instead I ran it twice.

The second time, it said what she needed. It wasn't a lie — the evidence was real, I only chose which afternoon to notice it. There's a difference, and I have made my peace with exactly how thin that difference is.`,
      },
      verifier: { status: "ok", verifiedAgainst: held3.length },
      choices: [
        {
          choiceId: "T3-A",
          label: { hi: "चुपचाप वह सबूत सामने लाना जो देब्रा को चाहिए, उसे अपने दम पर आगे बढ़ने देना", en: "Quietly surface the evidence Debra needs, let her case move on its own momentum" },
          weight: "medium",
          source: { workTitle: "off the books", author: "quietmiami", platform: "mock fan-fiction archive" },
        },
        {
          choiceId: "T3-B",
          label: { hi: "देब्रा को किसी और नाम की तरफ़ मोड़ देना, केसलर को अपने लिए बचाकर रखना", en: "Steer Debra toward a different name entirely, keeping Kessler for himself" },
          weight: "high",
          tone: "heavy",
          source: { workTitle: "a name off the board", author: "harrys_second_son", platform: "mock fan-fiction archive" },
        },
        {
          choiceId: "T3-C",
          label: { hi: "कुछ न बताना, केस को और छह हफ़्ते अटका रहने देना", en: "Tell her nothing and let the case stall another six weeks" },
          weight: "low",
          source: { workTitle: "six more weeks", author: "nightshift_writes", platform: "mock fan-fiction archive" },
        },
      ],
      chosenChoiceId: "T3-A",
      delta: { invalidated: [], held: held3, newNeeded: [F13, F14] },
      characterViews: {
        "CH-01": {
          sceneText: { hi: "देखा ऊपर", en: "see scene above" },
          beliefSummary: { hi: "वह देब्रा के केस को कवर की तरह इस्तेमाल कर रहा है, बिना उसे कभी पता चले।", en: "He's using her case as cover without her ever knowing it." },
          beliefState: "hold",
          present: true,
          knownFactIds: ["F-00", "F-01", "F-11", "F-13", "F-14"],
        },
        "CH-02": {
          sceneText: {
            hi: "आज पैनल की रिपोर्ट आई — आख़िरकार कुछ ऐसा जो टिकता है। केसलर का नाम बोर्ड पर अब बहुत भारी हो गया है। छोटी जीत है, पर मेरी है।",
            en: "Got the panel back today — finally something that holds up. Kessler's name just got a lot heavier on my board. Small win, but it's mine.",
          },
          beliefSummary: { hi: "देब्रा मानती है कि यह ब्रेक पूरी तरह उसका अपना काम है।", en: "Debra believes this break is entirely her own doing." },
          beliefState: "new",
          present: true,
          knownFactIds: ["F-00", "F-03", "F-13", "F-14"],
        },
        "CH-03": {
          sceneText: { hi: "आज कुछ नई ख़बर नहीं। मॉर्गन का शेड्यूल अब भी देख रहा हूँ।", en: "Nothing new to report today. Still watching Morgan's schedule, though." },
          beliefSummary: { hi: "इस ख़ास बातचीत से अनजान है।", en: "Unaware of this specific exchange." },
          beliefState: "unaware",
          present: false,
          knownFactIds: ["F-00", "F-02", "F-10", "F-11", "F-12"],
        },
        "CH-04": {
          sceneText: { hi: "जासूस मॉर्गन का बोर्ड आख़िरकार हिल रहा है। अच्छा है। वह केस बहुत लंबा खुला रहा।", en: "Detective Morgan's board is finally moving. Good. That case has been open too long." },
          beliefSummary: { hi: "एक बंद होते केस को अच्छी ख़बर की तरह देख रही है।", en: "Reads this as good news, nothing more." },
          beliefState: "hold",
          present: true,
          knownFactIds: ["F-00", "F-05", "F-13"],
        },
        "CH-05": {
          sceneText: { hi: "डेक्सटर आज देर से काम पर लगा रहा। कुछ भी असामान्य नहीं लगा।", en: "Dexter stayed late at work again. Nothing seemed out of place." },
          beliefSummary: { hi: "अनजान बनी हुई है।", en: "Remains unaware." },
          beliefState: "unaware",
          present: false,
          knownFactIds: ["F-00", "F-04"],
        },
      },
    },

    // ── TURN 4 — the night (heaviest turn) ───────────────────────────
    {
      turnIndex: 4,
      actingCharacterId: "CH-01",
      sceneText: {
        hi: `रे केसलर की वर्कशॉप का पिछला दरवाज़ा ठीक से बंद नहीं होता था, जो क़िस्मत से कम और न्यौते से ज़्यादा लगा — और मैंने कभी किसी न्यौते को ठुकराया नहीं।

मैं आगे जो हुआ उसका ब्यौरा नहीं दूँगा — हैरी ने कभी मुझसे यह नहीं माँगा, और मुझे कभी ख़ुद से भी पल-पल का हिसाब देने में कोई दिलचस्पी नहीं रही। बस इतना काफ़ी है कि यह ख़ामोश था, और यह उतना ही 'सही' था जितना 'सही' शब्द का मेरे लिए कभी कोई मतलब रहा है।

मैं तीन गलियाँ दूर था, खिड़कियाँ नीचे, रेडियो धीमा, जब मैंने डोक्स की गाड़ी फिर देखी — इस बार खड़ी, चल नहीं रही, ठीक उस गली के मुहाने पर जिसे मैं अभी छोड़कर आया था। वह मेरे पीछे अंदर नहीं आया था। उसने अंदाज़ा लगाया था, और फिर इंतज़ार किया था, जो कहीं ज़्यादा बुरा है।

वह गाड़ी से नहीं उतरा। बस मुझे गुज़रते हुए देखता रहा। किसी ने कुछ नहीं कहा — और मुझमें और डोक्स के बीच, यह अब पूरी बातचीत गिनी जाने लगी है।`,
        en: `Ray Kessler's workshop had a back door that didn't lock properly, which felt less like luck and more like an invitation, and I have never been someone who turns down an invitation.

I will not describe what happened next in detail — Harry never asked me to, and I've never seen the appeal of a play-by-play, even to myself. It is enough to say that it was quiet, and that it was fair, in the only sense of fair that has ever meant anything to me.

I was three streets away, windows down, radio low, when I saw Doakes's car again — parked, this time, not moving, at the mouth of the street I'd just left. He hadn't followed me in. He'd guessed, and then he'd waited, which is worse.

He didn't get out of the car. He just watched me drive past. Neither of us said anything, which between me and Doakes has started to count as a whole conversation.`,
      },
      verifier: { status: "ok", verifiedAgainst: held4.length },
      choices: [
        {
          choiceId: "T4-A",
          label: { hi: "बिना कोई प्रतिक्रिया दिए गुज़र जाना — डोक्स के पास अंदाज़ा है, सबूत नहीं", en: "Drive past without acknowledgment — Doakes has instinct, nothing he can act on" },
          weight: "high",
          tone: "heavy",
          source: { workTitle: "the mouth of the street", author: "harrys_second_son", platform: "mock fan-fiction archive" },
        },
        {
          choiceId: "T4-B",
          label: { hi: "रुककर मौक़े पर एक बहाना गढ़ लेना — सीधे डोक्स से झूठ बोलना", en: "Stop and manufacture an alibi on the spot, lying to Doakes's face" },
          weight: "medium",
          source: { workTitle: "forty minutes", author: "quietmiami", platform: "mock fan-fiction archive" },
        },
        {
          choiceId: "T4-C",
          label: { hi: "जान-बूझकर लंबा रास्ता लेना, यह देखने के लिए कि डोक्स पीछा करता है या नहीं", en: "Take a longer way home deliberately, to see if Doakes follows" },
          weight: "high",
          tone: "heavy",
          source: { workTitle: "provoking a shadow", author: "nightshift_writes", platform: "mock fan-fiction archive" },
        },
      ],
      chosenChoiceId: "T4-A",
      delta: { invalidated: [F06], held: held4, newNeeded: [F15, F16] },
      characterViews: {
        "CH-01": {
          sceneText: { hi: "देखा ऊपर", en: "see scene above" },
          beliefSummary: { hi: "वह जानता है कि डोक्स पहली बार इतना नज़दीक था कि मायने रखे।", en: "He knows Doakes was close enough to matter, for the first time." },
          beliefState: "invalid",
          present: true,
          knownFactIds: ["F-01", "F-15", "F-16"],
        },
        "CH-02": {
          sceneText: { hi: "आज आख़िरकार सामान्य समय पर डेस्क बंद किया। मुझे कोई अंदाज़ा नहीं कि केसलर के आस-पास कहीं कुछ हुआ हो।", en: "Closed my desk at a normal hour for once. No idea anything happened anywhere near Kessler that night." },
          beliefSummary: { hi: "पूरी तरह अनजान है।", en: "Entirely unaware." },
          beliefState: "unaware",
          present: false,
          knownFactIds: ["F-00", "F-03", "F-13"],
        },
        "CH-03": {
          sceneText: {
            hi: "मैंने कुछ ऐसा नहीं देखा जिसे रिपोर्ट में लिख सकूँ। यही पूरी दिक़्क़त है। मैंने जानने लायक़ बहुत कुछ देखा, और साबित करने लायक़ कुछ नहीं।",
            en: "I didn't see anything I can put in a report. That's the whole problem. I saw enough to know, and nothing I can prove.",
          },
          beliefSummary: { hi: "डोक्स का शक अब लगभग यक़ीन बन चुका है, सबूत के बग़ैर।", en: "Doakes's suspicion has crossed into near-certainty, with zero evidence." },
          beliefState: "new",
          present: true,
          knownFactIds: ["F-02", "F-10", "F-11", "F-12", "F-16"],
        },
        "CH-04": {
          sceneText: { hi: "आज रात कुछ रिपोर्ट नहीं आई।", en: "No reports tonight." },
          beliefSummary: { hi: "अनजान बनी हुई है।", en: "Remains unaware." },
          beliefState: "unaware",
          present: false,
          knownFactIds: ["F-00", "F-05"],
        },
        "CH-05": {
          sceneText: {
            hi: "बच्चों के सोने के थोड़ी देर बाद डेक्सटर घर आया। थका लग रहा था, पर वह अक्सर थका रहता है। मैंने इसे कुछ नहीं समझा।",
            en: "Dexter got home just after the kids fell asleep. He seemed tired, but he's always a little tired. I didn't think anything of it.",
          },
          beliefSummary: { hi: "अनजान बनी हुई है।", en: "Remains unaware." },
          beliefState: "unaware",
          present: true,
          knownFactIds: ["F-00", "F-04"],
        },
      },
    },

    // ── TURN 5 — what Doakes doesn't say ─────────────────────────────
    {
      turnIndex: 5,
      actingCharacterId: "CH-01",
      sceneText: {
        hi: `देब्रा ने केसलर केस मंगलवार को बंद किया, और लागार्टा ने सुबह की ब्रीफ़िंग में सच में मुस्कुराई — जो चंद्रग्रहण जितनी ही कम होता है। देब्रा को सराहा गया। उसकी हक़दार थी — काम असली था, भले ही उसे कभी पता न चले कि मैंने किस दोपहर उसे असली बनाने का फ़ैसला किया।

शिफ़्ट ख़त्म होने पर डोक्स मुझे अकेला अपनी गाड़ी के पास मिला। इस बार उसने नहीं पूछा कि मैं कहाँ था। वह बस देर तक मुझे देखता रहा, जैसे कोई गणित का सवाल हो जिसमें कहीं ग़लती पक्की हो, भले ही हर क़दम सही निकल रहा हो।

"एक दिन, मॉर्गन," उसने कहा। बस इतना। कोई सीधी धमकी नहीं — डोक्स सीधी बात नहीं करता। ज़्यादा एक निशान लगाने जैसा, बाद के लिए।

मैंने कहा कल मिलेंगे। उसने इसका भी जवाब नहीं दिया। मैं रीटा और बच्चों के पास घर चला गया, जिन्होंने मेरे लिए खाना बचाकर रखा था, और जो इनमें से कुछ भी नहीं जानते थे — जो, अगर मैं ख़ुद को सोचने दूँ, तो पूरी योजना का ठीक वैसे ही काम करना है जैसे इरादा था।`,
        en: `Debra closed the Kessler case on a Tuesday, and LaGuerta actually smiled at the morning briefing, which happens about as often as a lunar eclipse. Debra got a commendation. She deserved it — the work was real, even if she never learned which afternoon I'd decided to make it real.

Doakes found me alone by my car at the end of shift. He didn't ask where I'd been this time. He just looked at me for a while, the way you'd look at a math problem you're sure has an error in it somewhere, even though every step checks out.

"One day, Morgan," he said. That was all. Not a threat exactly — Doakes doesn't do exactly. More like a marker put down on a table, for later.

I told him I'd see him tomorrow. He didn't answer that either. I drove home to Rita and the kids, who had saved me a plate, and who knew absolutely nothing about any of it — which is, when I let myself think about it, the entire design working exactly as intended.`,
      },
      verifier: { status: "ok", verifiedAgainst: held5.length },
      choices: [
        {
          choiceId: "T5-A",
          label: { hi: "डोक्स को एक शांत, अस्पष्ट ग़ैर-जवाब देना — शक ज़िंदा रहे, पर साबित कभी न हो", en: "Give Doakes a calm, unreadable non-answer — the suspicion stays alive but permanently unprovable" },
          weight: "high",
          source: { workTitle: "one day, morgan", author: "harrys_second_son", platform: "mock fan-fiction archive" },
        },
        {
          choiceId: "T5-B",
          label: { hi: "बेगुनाही को ज़रूरत से ज़्यादा जताना, डोक्स की सतर्कता कम करने की कोशिश में", en: "Oversell the innocence, actively working to lower Doakes's guard" },
          weight: "medium",
          source: { workTitle: "too clean", author: "quietmiami", platform: "mock fan-fiction archive" },
        },
        {
          choiceId: "T5-C",
          label: { hi: "डोक्स को वापस उकसाना — एक छोटा, ख़तरनाक जवाबी वार", en: "Needle Doakes back — a small, risky provocation" },
          weight: "low",
          tone: "heavy",
          source: { workTitle: "pushing back", author: "nightshift_writes", platform: "mock fan-fiction archive" },
        },
      ],
      chosenChoiceId: "T5-A",
      delta: { invalidated: [], held: held5, newNeeded: [] },
      characterViews: {
        "CH-01": {
          sceneText: { hi: "देखा ऊपर", en: "see scene above" },
          beliefSummary: { hi: "वही एकमात्र है जो पूरा नक़्शा देखता है।", en: "He's the only one who sees the whole board." },
          beliefState: "hold",
          present: true,
          knownFactIds: ["F-01", "F-15", "F-16", "F-17", "F-18"],
        },
        "CH-02": {
          sceneText: {
            hi: "आज पूरे विभाग के सामने सराहा गया। बाद में डेक्सटर को बताया — वह सच में ख़ुश लगा मेरे लिए। अच्छा दिन।",
            en: "Got commended in front of the whole department today. Told Dexter about it later — he seemed genuinely happy for me. Good day.",
          },
          beliefSummary: {
            hi: "देब्रा को कोई अंदाज़ा नहीं कि इसका डेक्सटर से कोई सीधा नाता है — उसके हिसाब से, उसने यह केस अकेले, साफ़-साफ़ हल किया।",
            en: "Debra has no idea any of this connects to Dexter at all — as far as she knows, she solved this one clean.",
          },
          beliefState: "new",
          present: true,
          knownFactIds: ["F-00", "F-03", "F-13", "F-14", "F-17"],
          notYetKnown: [
            { hi: "कि रे केसलर कभी किसी सुनवाई तक नहीं पहुँचा, और किसी फ़ाइल में इसकी वजह कभी दर्ज नहीं होगी।", en: "That Ray Kessler never made it to trial for a reason no file will ever record." },
            { hi: "कि उसका अपना 'भाग्यशाली' फ़ॉरेंसिक ब्रेक लैब की क़तार से नहीं, उसके भाई से आया था।", en: "That her own 'lucky break' in the lab queue actually came from her brother, not from the queue." },
            { hi: "कि डोक्स पिछले दो हफ़्तों से यक़ीन कर चुका है कि उसका भाई एक पोकर रात से कहीं भारी कुछ छुपा रहा है।", en: "That Doakes has spent the last two weeks convinced her brother is hiding something far heavier than a poker night." },
            { hi: "कि गाड़ी के पास 'एक दिन, मॉर्गन' वाला पल हुआ भी था।", en: "That the 'one day, Morgan' moment even happened." },
          ],
        },
        "CH-03": {
          sceneText: {
            hi: "उससे कहा 'एक दिन।' वह बस मुस्कुराया और बोला कल मिलेंगे। मॉर्गन ऐसा ही है — कभी नहीं घबराता। मुझे यह पसंद नहीं।",
            en: "Told him 'one day.' He just smiled and said he'd see me tomorrow. That's Morgan for you — never rattled. I don't like it.",
          },
          beliefSummary: { hi: "डोक्स यक़ीन के साथ ख़त्म करता है कि कुछ ग़लत है, बिना कुछ दिखाने लायक़ के।", en: "Doakes ends the run certain something is wrong, with nothing to show for it." },
          beliefState: "new",
          present: true,
          knownFactIds: ["F-02", "F-10", "F-11", "F-12", "F-16", "F-18"],
        },
        "CH-04": {
          sceneText: {
            hi: "विभाग के लिए अच्छा हफ़्ता रहा। केस बंद, सराहना दी गई, आँकड़े साफ़ दिखते हैं। बस इतना काफ़ी है।",
            en: "Good week for the department. Case closed, commendation given, numbers look clean. That's all I need to know.",
          },
          beliefSummary: { hi: "इसे एक पूरी तरह साफ़ जीत की तरह पढ़ती है, इससे ज़्यादा कुछ नहीं।", en: "LaGuerta reads this as an unqualified win, nothing more." },
          beliefState: "hold",
          present: true,
          knownFactIds: ["F-00", "F-05", "F-13", "F-17"],
        },
        "CH-05": {
          sceneText: {
            hi: "उसके लिए खाना बचाकर रखा। वह चुपचाप खा गया, पर वह ऐसा ही करता है। बच्चों ने उसे अपना होमवर्क दिखाया। एक सामान्य मंगलवार।",
            en: "Saved him a plate. He ate quietly, but he does that. The kids showed him their homework. A normal Tuesday.",
          },
          beliefSummary: { hi: "रीटा इन सबसे पूरी तरह बाहर रहती है — डिज़ाइन से, हालाँकि वह इसे कभी ऐसा नहीं कहेगी।", en: "Rita remains completely outside all of it — by design, though she'd never think to call it that." },
          beliefState: "unaware",
          present: true,
          knownFactIds: ["F-00", "F-04"],
        },
      },
    },
  ],
};

// ═══════════════════════════════════════════════════════════════════
// 4. PLANTED DEFECT   → POST /api/demo/defect
//    The on-stage proof moment. Draft contradicts what Turn 4 established.
// ═══════════════════════════════════════════════════════════════════

export const defectDemo: { sceneText: LocalizedText; verifier: VerifierResult } = {
  sceneText: {
    hi: `सोमवार सुबह रे केसलर गवाही देने के लिए कठघरे में खड़ा हुआ और सीधे डेक्सटर मॉर्गन की तरफ़ इशारा किया।`,
    en: `Ray Kessler took the stand on Monday morning and pointed directly at Dexter Morgan.`,
  },
  verifier: {
    status: "flagged",
    citation: {
      draftClaim: { hi: "रे केसलर ज़िंदा है और गवाही दे रहा है", en: "Ray Kessler is alive and testifying" },
      canonFact: { hi: "रे केसलर का हिसाब हैरी कोड के मुताबिक़ चुका दिया गया था — वह दोबारा सामने नहीं आता", en: "Ray Kessler was dealt with per Harry's Code — he does not resurface" },
      sourceRef: "Turn 4 — invalidated by RUN-DEX-01",
    },
  },
};

// ═══════════════════════════════════════════════════════════════════
// 5. MOCK API — swap for real fetchers one at a time
// ═══════════════════════════════════════════════════════════════════

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export const mockApi = {
  async getStories() {
    await delay(200);
    return stories;
  },
  async getCharacters() {
    await delay(300);
    return characters;
  },
  /** Only CH-01 has a fully authored run — same "present but inert" pattern as the old ST-02/ST-03 cards. */
  async getRun(_protagonistId: CharacterId) {
    await delay(300);
    return run;
  },
  async postChoice(_runId: string, turnIndex: number, _choiceId: string) {
    await delay(1200); // long enough for the belief cascade to feel earned
    const turn = run.turns.find((t) => t.turnIndex === turnIndex);
    if (!turn) throw new Error(`Unknown turn ${turnIndex}`);
    return { delta: turn.delta };
  },
  async postDefectDemo() {
    await delay(900);
    return defectDemo;
  },
};
