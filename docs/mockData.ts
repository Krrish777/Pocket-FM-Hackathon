/**
 * MOCK DATA — CANON: Story Time Machine  (Bilingual: हिन्दी / English)
 * ─────────────────────────────────────────────────────────────────────
 * Copy to: frontend/src/lib/mockData.ts
 *
 * Original story written for this project. No third-party IP.
 * Shapes match REQUIREMENTS.md §8 exactly → swapping mock → real API
 * is a one-line change per fetcher.
 *
 * i18n: every user-facing string is LocalizedText { hi, en }.
 * Use t(value, locale) to read. Default locale = 'hi'.
 *
 * ── REHEARSED DEMO PATH ──────────────────────────────────────────────
 *   ST-01 → E03 → CH-02 (देव) → ALT-A
 *   → Ripple: 11 invalidated / 20 hold / 3 new
 *   → Regenerated E04 → Verifier: ✓ consistent
 *   → Then fire the defect demo for the flagged state
 *
 * ⚠ STAGE NOTE — read before choosing your branch
 *   ALT-A is a death branch. It's the most powerful ripple (biggest
 *   invalidation cascade) but it's heavy for a room of judges, and the
 *   subject is sensitive. ALT-C is included as a high-stakes NON-fatal
 *   alternative with a nearly identical ripple size — same technical
 *   impact, lighter room. Decide during dry-run, not on stage.
 */

// ═══════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════

export type Locale = "hi" | "en";
export type LocalizedText = Record<Locale, string>;

export const t = (v: LocalizedText, locale: Locale): string => v[locale];

export type StorySummary = {
  id: string;
  title: LocalizedText;
  coverUrl: string;
  episodeCount: number;
  factCount: number;
  language: LocalizedText;
};

export type Character = {
  id: string;
  name: LocalizedText;
  role: LocalizedText;
  portraitUrl: string;
};

export type Episode = {
  id: string;
  index: number;
  title: LocalizedText;
  synopsis: LocalizedText;
  characters: string[];
};

export type StoryDetail = {
  id: string;
  title: LocalizedText;
  logline: LocalizedText;
  episodes: Episode[];
  characters: Character[];
};

export type Alternative = {
  altId: string;
  label: LocalizedText;
  weight: "low" | "medium" | "high";
  tone?: "heavy" | "standard";
};

export type Moment = {
  momentId: string;
  episodeId: string;
  characterId: string;
  originalLine: LocalizedText;
  alternatives: Alternative[];
};

export type Fact = {
  factId: string;
  summary: LocalizedText;
  establishedIn: string;
};

export type RippleResult = {
  rippleId: string;
  invalidated: Fact[];
  held: Fact[];
  newNeeded: Fact[];
};

export type VerifierResult =
  | { status: "ok"; verifiedAgainst: number }
  | {
      status: "flagged";
      citation: {
        draftClaim: LocalizedText;
        canonFact: LocalizedText;
        episodeRef: string;
      };
    };

export type RegenerateResult = {
  sceneText: LocalizedText;
  verifier: VerifierResult;
};

// ═══════════════════════════════════════════════════════════════════
// UI STRINGS — the whole interface switches with one toggle
// ═══════════════════════════════════════════════════════════════════

export const ui = {
  appName: { hi: "कैनन", en: "CANON" },
  appSubtitle: { hi: "कहानी टाइम मशीन", en: "STORY TIME MACHINE" },

  shelfHeading: {
    hi: "वो रास्ते जो कभी नहीं लिए गए",
    en: "The paths never taken",
  },
  shelfSub: {
    hi: "कोई कहानी चुनिए। कोई पल चुनिए। एक फ़ैसला बदलिए।",
    en: "Choose a story. Choose a moment. Change one decision.",
  },

  episodesLabel: { hi: "एपिसोड", en: "EPISODES" },
  factsLabel: { hi: "तथ्य", en: "FACTS" },
  charactersLabel: { hi: "किरदार", en: "CHARACTERS" },

  canonLabel: { hi: "मूल कथा", en: "CANON" },
  whatIfLabel: { hi: "और अगर…", en: "WHAT IF…" },
  flipButton: { hi: "यह पल बदलें", en: "FLIP THIS MOMENT" },

  rippleHeading: { hi: "प्रभाव-मानचित्र", en: "RIPPLE MAP" },
  invalidatedLabel: { hi: "अमान्य हुए", en: "INVALIDATED" },
  heldLabel: { hi: "अब भी सत्य", en: "STILL HOLD" },
  newNeededLabel: { hi: "नए चाहिए", en: "NEW REQUIRED" },
  seeResultButton: { hi: "आगे क्या हुआ, देखिए", en: "SEE WHAT HAPPENS" },

  revisedLabel: { hi: "पुनर्लिखित", en: "REVISED" },
  branchLabel: { hi: "शाखा", en: "BRANCH" },
  listenButton: { hi: "सुनिए", en: "LISTEN" },

  verifierOk: { hi: "कैनन-संगत", en: "CANON-CONSISTENT" },
  verifierOkDetail: {
    hi: "अप्रभावित तथ्यों के विरुद्ध सत्यापित",
    en: "VERIFIED AGAINST UNAFFECTED FACTS",
  },
  verifierFlagged: { hi: "विरोधाभास चिह्नित", en: "CONTRADICTION FLAGGED" },
  draftClaimLabel: { hi: "प्रारूप कहता है", en: "DRAFT CLAIM" },
  canonSaysLabel: { hi: "कैनन कहता है", en: "CANON SAYS" },

  loadingRipple: { hi: "प्रभाव की गणना…", en: "COMPUTING RIPPLE…" },
  loadingScene: { hi: "दृश्य पुनर्लिखित हो रहा है…", en: "REGENERATING SCENE…" },
} satisfies Record<string, LocalizedText>;

// ═══════════════════════════════════════════════════════════════════
// 1. SHELF   → GET /api/stories
// ═══════════════════════════════════════════════════════════════════

export const stories: StorySummary[] = [
  {
    id: "ST-01",
    title: { hi: "आख़िरी बेंच", en: "The Last Bench" },
    coverUrl: "/covers/last-bench.jpg",
    episodeCount: 6,
    factCount: 34,
    language: { hi: "हिन्दी", en: "HINDI" },
  },
  // Shelf-realism only — do NOT click during the demo.
  {
    id: "ST-02",
    title: { hi: "मानसून फ़्रीक्वेंसी", en: "Monsoon Frequency" },
    coverUrl: "/covers/monsoon.jpg",
    episodeCount: 8,
    factCount: 51,
    language: { hi: "हिन्दी", en: "HINDI" },
  },
  {
    id: "ST-03",
    title: { hi: "नक़्शानवीस की बेटी", en: "The Cartographer's Daughter" },
    coverUrl: "/covers/cartographer.jpg",
    episodeCount: 5,
    factCount: 29,
    language: { hi: "हिन्दी", en: "HINDI" },
  },
];

// ═══════════════════════════════════════════════════════════════════
// 2. STORY DETAIL   → GET /api/stories/ST-01
// ═══════════════════════════════════════════════════════════════════

export const storyDetail: StoryDetail = {
  id: "ST-01",
  title: { hi: "आख़िरी बेंच", en: "The Last Bench" },
  logline: {
    hi: "तीन इंजीनियरिंग छात्र, एक ऐसा संस्थान जो झुकता नहीं, और वो एक रात जो तय कर देती है कि वे तीनों कौन बनेंगे।",
    en: "Three engineering students, one institution that never bends, and the night that decides who they all become.",
  },
  characters: [
    {
      id: "CH-01",
      name: { hi: "आरव सेन", en: "Aarav Sen" },
      role: { hi: "जो 'क्यों' पूछता है", en: "The one who asks why" },
      portraitUrl: "/portraits/aarav.jpg",
    },
    {
      id: "CH-02",
      name: { hi: "देवांश अय्यर", en: "Devansh Iyer" },
      role: { hi: "जो अपने पिता को ढो रहा है", en: "The one carrying his father" },
      portraitUrl: "/portraits/dev.jpg",
    },
    {
      id: "CH-03",
      name: { hi: "कबीर मल्होत्रा", en: "Kabir Malhotra" },
      role: { hi: "जिसका कैमरा छुपा हुआ है", en: "The one with a hidden camera" },
      portraitUrl: "/portraits/kabir.jpg",
    },
    {
      id: "CH-04",
      name: { hi: "प्रो. राजन व्यास", en: "Prof. Rajan Vyas" },
      role: { hi: "जिसने यह मशीन बनाई", en: "The one who built the machine" },
      portraitUrl: "/portraits/vyas.jpg",
    },
  ],
  episodes: [
    {
      id: "E01",
      index: 1,
      title: { hi: "दाख़िला", en: "Intake" },
      synopsis: {
        hi: "तीन अजनबियों को कमरा 114 मिलता है। देव एक सूटकेस लेकर आता है और एक छपी हुई सूची — जो उसके पिता ने बनाई है।",
        en: "Three strangers are assigned Room 114. Dev arrives with a suitcase and a printed list his father made.",
      },
      characters: ["CH-01", "CH-02", "CH-03"],
    },
    {
      id: "E02",
      index: 2,
      title: { hi: "बोर्ड", en: "The Board" },
      synopsis: {
        hi: "प्रो. व्यास गलियारे में पहली रैंकिंग लगाते हैं। देव का नाम नीचे से दूसरा है। वह उसे चार बार पढ़ता है।",
        en: "Prof. Vyas posts the first rankings in the corridor. Dev's name is second from the bottom. He reads it four times.",
      },
      characters: ["CH-01", "CH-02", "CH-03", "CH-04"],
    },
    {
      id: "E03",
      index: 3,
      title: { hi: "मुंडेर", en: "The Ledge" },
      synopsis: {
        hi: "वाइवा के बाद देव कमरे में वापस नहीं आता। आरव को छत का दरवाज़ा खुला मिलता है।",
        en: "Dev doesn't return to the room after the viva. Aarav finds the roof door propped open.",
      },
      characters: ["CH-01", "CH-02"],
    },
    {
      id: "E04",
      index: 4,
      title: { hi: "मुलाक़ात का समय", en: "Visiting Hours" },
      synopsis: {
        hi: "देव के पिता कैंपस आते हैं। आरव वो बात कह देता है जो अब तक किसी ने ज़ोर से नहीं कही।",
        en: "Dev's father arrives on campus. Aarav says the thing nobody has said out loud.",
      },
      characters: ["CH-01", "CH-02", "CH-04"],
    },
    {
      id: "E05",
      index: 5,
      title: { hi: "प्रदर्शनी", en: "Exhibition" },
      synopsis: {
        hi: "तीनों कॉलेज मेले के लिए कुछ बनाते हैं। क्रेट में कबीर की तस्वीरें मिल जाती हैं।",
        en: "The three build something for the college fair. Kabir's photographs are found in the crate.",
      },
      characters: ["CH-01", "CH-02", "CH-03"],
    },
    {
      id: "E06",
      index: 6,
      title: { hi: "दीक्षांत", en: "Convocation" },
      synopsis: {
        hi: "प्रो. व्यास देव को डिग्री देते हैं और एक पल के लिए हाथ नहीं छोड़ते।",
        en: "Prof. Vyas hands Dev his degree and, for one second, does not let go.",
      },
      characters: ["CH-01", "CH-02", "CH-03", "CH-04"],
    },
  ],
};

// ═══════════════════════════════════════════════════════════════════
// 3. MOMENTS   → GET /api/stories/ST-01/moments?episodeId=E03&characterId=CH-02
// ═══════════════════════════════════════════════════════════════════

export const moments: Moment[] = [
  {
    momentId: "M-0301",
    episodeId: "E03",
    characterId: "CH-02",
    originalLine: {
      hi: "आरव समय रहते छत पर पहुँच जाता है। वह चिल्लाता नहीं। वह छह फ़ुट दूर बजरी पर बैठ जाता है और बेमतलब की बातें करता रहता है, जब तक देव भी बैठ नहीं जाता।",
      en: "Aarav reaches the roof in time. He does not shout. He sits down on the gravel, six feet away, and talks about nothing at all until Dev sits down too.",
    },
    alternatives: [
      {
        altId: "ALT-A",
        label: {
          hi: "आरव ग़लत सीढ़ी ले लेता है। वह चार मिनट देर से पहुँचता है।",
          en: "Aarav takes the wrong staircase. He arrives four minutes late.",
        },
        weight: "high",
        tone: "heavy",
      },
      {
        altId: "ALT-B",
        label: {
          hi: "देव ख़ुद नीचे उतर आता है। आरव को कभी पता ही नहीं चलता कि वह ऊपर था।",
          en: "Dev comes down on his own. Aarav never learns he was up there.",
        },
        weight: "medium",
        tone: "standard",
      },
      {
        altId: "ALT-C",
        label: {
          hi: "प्रो. व्यास उसे पहले ढूँढ लेते हैं — और अगली सुबह बोर्ड नहीं लगता।",
          en: "Prof. Vyas finds him first — and the next morning, the board does not go up.",
        },
        weight: "high",
        tone: "standard",
      },
    ],
  },
  {
    momentId: "M-0501",
    episodeId: "E05",
    characterId: "CH-03",
    originalLine: {
      hi: "कबीर उन्हें तस्वीरें ढूँढ लेने देता है। वह कोई सफ़ाई नहीं देता।",
      en: "Kabir lets them find the photographs. He does not explain them.",
    },
    alternatives: [
      {
        altId: "ALT-D",
        label: {
          hi: "कबीर एक रात पहले निगेटिव जला देता है।",
          en: "Kabir burns the negatives the night before.",
        },
        weight: "medium",
      },
      {
        altId: "ALT-E",
        label: {
          hi: "प्रो. व्यास उन्हें पहले पा लेते हैं — और ख़ुद जमा कर देते हैं।",
          en: "Prof. Vyas finds them first, and submits them himself.",
        },
        weight: "medium",
      },
    ],
  },
];

// ═══════════════════════════════════════════════════════════════════
// 4. RIPPLE — ALT-A   → POST /api/divergence
//    11 invalidated · 20 hold · 3 new
// ═══════════════════════════════════════════════════════════════════

const heldFacts: Fact[] = [
  { factId: "F-001", summary: { hi: "संस्थान एक सार्वजनिक रैंकिंग बोर्ड चलाता है", en: "The institution operates a public ranking board" }, establishedIn: "E02" },
  { factId: "F-002", summary: { hi: "प्रो. राजन व्यास ने रैंकिंग प्रणाली बनाई", en: "Prof. Rajan Vyas designed the ranking system" }, establishedIn: "E02" },
  { factId: "F-003", summary: { hi: "आरव सार्वजनिक रूप से रैंकिंग पर सवाल उठाता है", en: "Aarav questions the ranking system publicly" }, establishedIn: "E02" },
  { factId: "F-004", summary: { hi: "कबीर के पास एक कैमरा है जिसे वह छुपाता है", en: "Kabir owns a camera he hides" }, establishedIn: "E01" },
  { factId: "F-005", summary: { hi: "कबीर का परिवार चाहता है कि वह इंजीनियर बने", en: "Kabir's family expects him to become an engineer" }, establishedIn: "E01" },
  { factId: "F-006", summary: { hi: "आरव और कबीर को कमरा 114 मिला है", en: "Aarav and Kabir are assigned Room 114" }, establishedIn: "E01" },
  { factId: "F-007", summary: { hi: "देव अपने पिता की लिखी सूची लेकर आता है", en: "Dev arrives with a written list from his father" }, establishedIn: "E01" },
  { factId: "F-008", summary: { hi: "पहले चक्र में देव नीचे से दूसरे स्थान पर है", en: "Dev ranks second from the bottom in the first cycle" }, establishedIn: "E02" },
  { factId: "F-009", summary: { hi: "हॉस्टल की छत का ताला टूटा हुआ है", en: "The hostel roof door lock is broken" }, establishedIn: "E03" },
  { factId: "F-010", summary: { hi: "प्रो. व्यास ने अपने पहले साल में एक छात्र खोया था", en: "Prof. Vyas lost a student in his first year of teaching" }, establishedIn: "E04" },
  { factId: "F-011", summary: { hi: "आरव के परिवार की मरम्मत की दुकान है", en: "Aarav's family runs a repair shop" }, establishedIn: "E01" },
  { factId: "F-012", summary: { hi: "कॉलेज मेला हर फ़रवरी में होता है", en: "The college fair is held every February" }, establishedIn: "E05" },
  { factId: "F-013", summary: { hi: "कबीर रात में कैंपस की तस्वीरें खींचता है", en: "Kabir photographs the campus at night" }, establishedIn: "E03" },
  { factId: "F-025", summary: { hi: "आरव पहले भी एक विषय में फ़ेल हुआ है और छुपाया है", en: "Aarav has failed a subject before and hidden it" }, establishedIn: "E02" },
  { factId: "F-026", summary: { hi: "वाइवा प्रो. व्यास ख़ुद लेते हैं", en: "The viva is conducted by Prof. Vyas personally" }, establishedIn: "E03" },
  { factId: "F-027", summary: { hi: "कबीर की तस्वीरें मौजूद हैं और क्रेट में हैं", en: "Kabir's photographs exist and are in the crate" }, establishedIn: "E05" },
  { factId: "F-028", summary: { hi: "प्रो. व्यास की मेज़ में एक बिना खुला ख़त पड़ा है", en: "Prof. Vyas keeps an unopened letter in his desk" }, establishedIn: "E04" },
  { factId: "F-029", summary: { hi: "प्रदर्शनी वाले यंत्र का विचार आरव का है", en: "The exhibition device concept is Aarav's idea" }, establishedIn: "E05" },
  { factId: "F-030", summary: { hi: "आरव रैंकिंग समारोह में जाने से मना कर देता है", en: "Aarav refuses to attend the ranking ceremony" }, establishedIn: "E02" },
  { factId: "F-031", summary: { hi: "कमरा 114 छत की सीढ़ी की ओर खुलता है", en: "Room 114 faces the roof staircase" }, establishedIn: "E01" },
];

export const rippleALTA: RippleResult = {
  rippleId: "RP-0301-A",
  invalidated: [
    { factId: "F-014", summary: { hi: "देवांश अय्यर जीवित है", en: "Devansh Iyer is alive" }, establishedIn: "E01" },
    { factId: "F-015", summary: { hi: "देव दूसरा सेमेस्टर पूरा करता है", en: "Dev completes the second semester" }, establishedIn: "E04" },
    { factId: "F-016", summary: { hi: "देव के पिता कैंपस आते हैं और आरव से बात करते हैं", en: "Dev's father visits campus and speaks with Aarav" }, establishedIn: "E04" },
    { factId: "F-017", summary: { hi: "देव आरव और कबीर के साथ प्रदर्शनी का यंत्र बनाता है", en: "Dev builds the exhibition device with Aarav and Kabir" }, establishedIn: "E05" },
    { factId: "F-018", summary: { hi: "कबीर की तस्वीरें देव ही ढूँढता है", en: "Dev is the one who finds Kabir's photographs" }, establishedIn: "E05" },
    { factId: "F-019", summary: { hi: "देव स्नातक होता है", en: "Dev graduates" }, establishedIn: "E06" },
    { factId: "F-020", summary: { hi: "प्रो. व्यास देव को उसकी डिग्री देते हैं", en: "Prof. Vyas hands Dev his degree" }, establishedIn: "E06" },
    { factId: "F-021", summary: { hi: "प्रो. व्यास निजी तौर पर मानते हैं कि वे ग़लत थे", en: "Prof. Vyas privately concedes he was wrong" }, establishedIn: "E06" },
    { factId: "F-022", summary: { hi: "कमरा 114 पूरे साल तीन छात्रों से भरा रहता है", en: "Room 114 is occupied by three students through the year" }, establishedIn: "E01" },
    { factId: "F-023", summary: { hi: "आरव मानता है कि वह समय पर पहुँच गया था", en: "Aarav believes he arrived in time" }, establishedIn: "E03" },
    { factId: "F-024", summary: { hi: "देव महीनों बाद कबीर को छत के बारे में बताता है", en: "Dev tells Kabir about the roof, months later" }, establishedIn: "E05" },
  ],
  held: heldFacts,
  newNeeded: [
    { factId: "F-N01", summary: { hi: "E03 के बाद कमरा 114 का तीसरा बिस्तर किसे मिलता है?", en: "Who occupies the third bed in Room 114 after E03?" }, establishedIn: "—" },
    { factId: "F-N02", summary: { hi: "प्रो. व्यास अब रैंकिंग बोर्ड का क्या करते हैं?", en: "What does Prof. Vyas do with the ranking board now?" }, establishedIn: "—" },
    { factId: "F-N03", summary: { hi: "कबीर तस्वीरें अब भी छुपाता है, या छुपाना बंद कर देता है?", en: "Does Kabir still hide the photographs, or stop hiding?" }, establishedIn: "—" },
  ],
};

// ── ALT-C — high-stakes, NON-fatal. Nearly identical ripple size. ──
export const rippleALTC: RippleResult = {
  rippleId: "RP-0301-C",
  invalidated: [
    { factId: "F-023", summary: { hi: "आरव मानता है कि वह समय पर पहुँच गया था", en: "Aarav believes he arrived in time" }, establishedIn: "E03" },
    { factId: "F-001", summary: { hi: "संस्थान एक सार्वजनिक रैंकिंग बोर्ड चलाता है", en: "The institution operates a public ranking board" }, establishedIn: "E02" },
    { factId: "F-002", summary: { hi: "प्रो. राजन व्यास ने रैंकिंग प्रणाली बनाई", en: "Prof. Rajan Vyas designed the ranking system" }, establishedIn: "E02" },
    { factId: "F-021", summary: { hi: "प्रो. व्यास निजी तौर पर मानते हैं कि वे ग़लत थे", en: "Prof. Vyas privately concedes he was wrong" }, establishedIn: "E06" },
    { factId: "F-030", summary: { hi: "आरव रैंकिंग समारोह में जाने से मना कर देता है", en: "Aarav refuses to attend the ranking ceremony" }, establishedIn: "E02" },
    { factId: "F-024", summary: { hi: "देव महीनों बाद कबीर को छत के बारे में बताता है", en: "Dev tells Kabir about the roof, months later" }, establishedIn: "E05" },
    { factId: "F-008", summary: { hi: "पहले चक्र में देव नीचे से दूसरे स्थान पर है", en: "Dev ranks second from the bottom in the first cycle" }, establishedIn: "E02" },
    { factId: "F-003", summary: { hi: "आरव सार्वजनिक रूप से रैंकिंग पर सवाल उठाता है", en: "Aarav questions the ranking system publicly" }, establishedIn: "E02" },
    { factId: "F-028", summary: { hi: "प्रो. व्यास की मेज़ में एक बिना खुला ख़त पड़ा है", en: "Prof. Vyas keeps an unopened letter in his desk" }, establishedIn: "E04" },
  ],
  held: heldFacts.filter((f) => !["F-001", "F-002", "F-003", "F-008", "F-028", "F-030"].includes(f.factId)),
  newNeeded: [
    { factId: "F-N05", summary: { hi: "अगर बोर्ड नहीं है, तो छात्र ख़ुद को कैसे मापते हैं?", en: "Without the board, how do students measure themselves?" }, establishedIn: "—" },
    { factId: "F-N06", summary: { hi: "व्यास ने वो ख़त आख़िर क्यों खोला?", en: "Why does Vyas finally open the letter?" }, establishedIn: "—" },
  ],
};

// ═══════════════════════════════════════════════════════════════════
// 5. REGENERATION   → POST /api/regenerate
// ═══════════════════════════════════════════════════════════════════

export const regenerateALTA: RegenerateResult = {
  sceneText: {
    hi: `तीसरा बिस्तर उन्होंने किसी और को नहीं दिया।

ग्यारह दिन तक वह लगा हुआ रहा, क्योंकि कबीर हर सुबह उसे लगा देता था, और आरव ने इस पर कुछ नहीं कहा — क्योंकि कुछ कहने का मतलब होता तय करना कि इसका मतलब क्या है।

रैंकिंग बोर्ड गुरुवार को लगा, जैसे हमेशा लगता था। आरव उसके सामने बहुत देर खड़ा रहा। उसका अपना नाम चार जगह ऊपर आ गया था। वहाँ खड़े-खड़े उसे समझ आया कि नाम इसलिए ऊपर आया है क्योंकि सूची में एक नाम कम हो गया है, और बोर्ड को यह नहीं पता, और बोर्ड को यह कभी नहीं पता चलेगा, और अगले गुरुवार को भी यह वैसे ही लग जाएगा।

प्रो. व्यास चार बजे गलियारे से गुज़रे। उन्होंने आरव को बोर्ड के सामने देखा। उन्होंने उसे हटने को नहीं कहा।

"तुम्हें मुझसे कुछ कहना है," व्यास ने कहा।

"नहीं, सर।" आरव ने मुड़कर नहीं देखा। "मुझे पूछना था। छपने में कितना समय लगता है?"

"क्या?"

"बोर्ड। जब आप उसे फ़ाइनल कर देते हैं, उसके बाद। छपने में कितना समय लगता है।"

व्यास ने कहा, "चालीस मिनट।"

"चालीस मिनट," आरव ने दोहराया। उसने धीरे से सिर हिलाया, जैसे उसे कोई ऐसी जानकारी मिली हो जो किसी चीज़ का बोझ उठाती है, और वह उसे अपनी जगह पर बिठा रहा हो। फिर वह कमरा 114 लौट गया, जहाँ कबीर ने अपना कैमरा अलमारी से निकालकर मेज़ पर सामने रख दिया था — और न उसे छुआ था, न वापस रखा था।`,
    en: `They did not reassign the third bed.

For eleven days it stayed made, because Kabir made it every morning, and Aarav said nothing about it, because saying something would have meant deciding what it meant.

The ranking board went up on Thursday, as it always did. Aarav stood in front of it for a long time. His own name had moved up four places. He understood, standing there, that it had moved up because there was one less name on the list, and that the board did not know this, and that the board would never know this, and that it would go up again next Thursday regardless.

Prof. Vyas came down the corridor at four. He saw Aarav at the board. He did not ask him to move along.

"You want to say something to me," Vyas said.

"No, sir." Aarav did not turn around. "I wanted to ask you something. How long does it take to print?"

"What?"

"The board. From when you finalise it. How long does the printing take."

Vyas said, "Forty minutes."

"Forty minutes," Aarav repeated. He nodded slowly, as though he had been given a piece of load-bearing information and was fitting it into place. Then he walked back to Room 114, where Kabir had taken his camera out of the cupboard and set it on the desk in plain sight, and had not touched it, and had not put it away either.`,
  },
  verifier: { status: "ok", verifiedAgainst: 20 },
};

export const regenerateALTC: RegenerateResult = {
  sceneText: {
    hi: `गुरुवार को गलियारा ख़ाली था।

छात्र आदत से उधर मुड़े, फिर रुक गए। दीवार पर सिर्फ़ पेंट था — हल्का-सा चौकोर निशान, जहाँ बीस साल से हर हफ़्ते एक काग़ज़ चिपकता आया था। किसी ने कुछ पूछा नहीं। पूछने का मतलब होता मान लेना कि वे रोज़ उसे देखने आते थे।

देव भी वहीं खड़ा था, भीड़ के पीछे। उसे यह नहीं पता था कि उस रात के बाद क्या बदल गया है, और किसी ने उसे बताया नहीं था। उसे सिर्फ़ इतना पता था कि प्रो. व्यास उसे छत से नीचे लाए थे, और नीचे आते वक़्त कुछ नहीं कहा था, पूरे रास्ते।

व्यास अपने कमरे में थे। मेज़ की दराज़ खुली हुई थी। उसमें एक ख़त था, बीस साल पुराना, बिना खुला — किसी और लड़के के पिता का लिखा हुआ।

उन्होंने उसे उठाया। बहुत देर तक हाथ में रखा।

फिर उन्होंने उसे खोला।`,
    en: `On Thursday the corridor was empty.

Students turned toward it out of habit, then stopped. There was only paint on the wall — a faint rectangle, where a sheet of paper had been pasted every week for twenty years. Nobody asked about it. Asking would have meant admitting they came to look at it daily.

Dev was there too, at the back of the crowd. He did not know what had changed since that night, and nobody had told him. He only knew that Prof. Vyas had brought him down from the roof, and had said nothing at all on the way down, the entire way.

Vyas was in his office. The desk drawer was open. Inside it was a letter, twenty years old, unopened — written by another boy's father.

He picked it up. Held it for a long time.

Then he opened it.`,
  },
  verifier: { status: "ok", verifiedAgainst: 14 },
};

// ═══════════════════════════════════════════════════════════════════
// 6. PLANTED DEFECT   → POST /api/demo/defect
//    The on-stage proof moment. Draft contradicts the ALT-A branch.
// ═══════════════════════════════════════════════════════════════════

export const defectDemo: RegenerateResult = {
  sceneText: {
    hi: `प्रदर्शनी के फ़र्श पर क्रेट खुल गया और तस्वीरें तिरपाल पर बिखर गईं — चालीस, सब रात में खींची हुई।

देव ने एक उठाई और रोशनी की तरफ़ घुमाई। "यह हमारी सीढ़ी है," उसने कहा। "तुमने यह छत से ली है।"`,
    en: `The crate came open on the exhibition floor and the photographs spilled across the tarpaulin — forty of them, all taken at night.

Dev picked one up and turned it toward the light. "This is our staircase," he said. "You took this from the roof."`,
  },
  verifier: {
    status: "flagged",
    citation: {
      draftClaim: {
        hi: "देवांश अय्यर मौजूद है और बोल रहा है",
        en: "Devansh Iyer is present and speaking",
      },
      canonFact: {
        hi: "इस शाखा में देवांश अय्यर जीवित नहीं है",
        en: "Devansh Iyer is not alive in this branch",
      },
      episodeRef: "E03 §4 — invalidated by RP-0301-A",
    },
  },
};

// ═══════════════════════════════════════════════════════════════════
// 7. MOCK API — swap for real fetchers one at a time
// ═══════════════════════════════════════════════════════════════════

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export const mockApi = {
  async getStories() {
    await delay(300);
    return stories;
  },
  async getStory(_id: string) {
    await delay(300);
    return storyDetail;
  },
  async getMoments(episodeId: string, characterId: string) {
    await delay(250);
    return moments.filter(
      (m) => m.episodeId === episodeId && m.characterId === characterId
    );
  },
  async postDivergence(_storyId: string, _momentId: string, altId: string) {
    await delay(1200); // long enough for the cascade to feel earned
    return altId === "ALT-C" ? rippleALTC : rippleALTA;
  },
  async postRegenerate(rippleId: string) {
    await delay(1800);
    return rippleId === "RP-0301-C" ? regenerateALTC : regenerateALTA;
  },
  async postDefectDemo() {
    await delay(900);
    return defectDemo;
  },
};
