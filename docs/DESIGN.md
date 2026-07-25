
# DESIGN SYSTEM — "CANON"
### Agent build spec. Every value here is literal — copy it, don't interpret it.

> [!danger] AGENT: READ BEFORE WRITING ANY COMPONENT
> This file defines the complete visual language. **Do not invent colors, spacing, radii, shadows, or motion values that aren't in this file.** If a value you need isn't defined here, use the closest defined token — do not improvise a new one. Consistency across every screen is the single most important quality bar for this build.
>
> Companion files: [[REQUIREMENTS]] (what to build) · [[FRONTEND_TECH_STACK]] (how to build it).

---

## 1. THE SIGNATURE IDEA — "Archival Terminal"

Every design decision in this file descends from one concept. Read this once, then apply it everywhere.

> **The product is a scholarly archive that computes.** Half literary manuscript, half forensic instrument. It should feel like a rare-book library and a laboratory occupying the same room — warm paper-toned narrative surfaces sitting inside a cold, precise, dark analytical shell.

**This produces three signature moves used consistently across every screen:**

1. **The Ledger Rule** — a 1px hairline in `--ink-line` separates every content region. Never a card shadow, never a border-radius wrapper. Regions are divided by *rules*, like a printed ledger or a technical drawing. This is the #1 recognizable trait of the UI.
2. **The Index Mark** — every interactive or referenceable element carries a small monospace index label in the top-left of its bounding box (`E03`, `F-127`, `CH-02`). Like archive catalog numbers. This single detail makes the whole product feel systematized and unrepeatable by a template.
3. **Paper-in-the-dark** — narrative text (story prose, generated scenes) always sits on a warm off-white "paper" surface. System/analysis text always sits on the dark shell. **The user learns instantly: light = story, dark = machine.** Never mix.

> [!success] Why this beats a generic dark dashboard
> Hairline rules + catalog indices + a light/dark story/system split is a *system*, not a decoration. It scales to every component, it's cheap to implement in Tailwind, and no AI-scaffolded template looks like this.

---

## 2. COLOR TOKENS — literal values, use these exact hexes

```css
/* globals.css — paste verbatim into :root */
:root {
  /* — SHELL (the machine) — */
  --shell-void:      #0A0908;  /* page background, deepest layer */
  --shell-base:      #12100E;  /* primary surface */
  --shell-raised:    #1A1714;  /* raised panels, hover states */
  --shell-sunken:    #060505;  /* insets, wells, input backgrounds */

  /* — PAPER (the story) — */
  --paper-warm:      #F4EFE6;  /* narrative text surface */
  --paper-aged:      #E8E0D2;  /* secondary paper, edges */
  --paper-ink:       #1A1714;  /* text ON paper */
  --paper-ink-soft:  #554E45;  /* secondary text on paper */

  /* — INK (text on shell) — */
  --ink-bright:      #F0EBE3;  /* primary text on dark */
  --ink-muted:       #8A8178;  /* secondary text on dark */
  --ink-faint:       #4A443D;  /* tertiary, disabled */
  --ink-line:        #2A2622;  /* THE hairline rule color */

  /* — ACCENT (single brand accent — used sparingly) — */
  --accent:          #C8553D;  /* burnt sienna. brand, primary CTA, active state */
  --accent-dim:      #8F3E2C;  /* pressed / darker variant */
  --accent-wash:     rgba(200, 85, 61, 0.08); /* subtle fill behind active items */

  /* — SEMANTIC: RESERVED. NEVER use these decoratively — */
  --state-invalid:   #D1495B;  /* Ripple: invalidated fact · Verifier: flagged */
  --state-hold:      #6A994E;  /* Ripple: fact still holds · Verifier: consistent */
  --state-new:       #4A7B9D;  /* Ripple: new fact required */
}
```

> [!danger] HARD RULE — enforce this in every component
> `--state-invalid`, `--state-hold`, `--state-new` may **ONLY** appear on: Ripple Map nodes, Ripple Map counters, and the Verifier Badge. They may never be used for buttons, borders, hovers, icons, or any decorative purpose anywhere else in the app. This is what makes those three colors *mean* something the moment they appear on stage.

**Tailwind config mapping** (`tailwind.config.ts` → `theme.extend.colors`):
```ts
colors: {
  shell: { void:'#0A0908', base:'#12100E', raised:'#1A1714', sunken:'#060505' },
  paper: { warm:'#F4EFE6', aged:'#E8E0D2', ink:'#1A1714', 'ink-soft':'#554E45' },
  ink:   { bright:'#F0EBE3', muted:'#8A8178', faint:'#4A443D', line:'#2A2622' },
  accent:{ DEFAULT:'#C8553D', dim:'#8F3E2C' },
  state: { invalid:'#D1495B', hold:'#6A994E', new:'#4A7B9D' },
}
```

---

## 3. TYPOGRAPHY — three fonts, three jobs, zero overlap

| Token | Font | Used for — and ONLY for |
|---|---|---|
| `font-story` | **Fraunces** (variable serif) | Story prose, generated scenes, story titles, screen headlines |
| `font-ui` | **Geist** (sans) | Buttons, labels, navigation, descriptions, all UI chrome |
| `font-data` | **JetBrains Mono** | Index marks, fact counts, citations, verifier output, episode refs, any number |

```ts
// tailwind.config.ts → theme.extend.fontFamily
fontFamily: {
  story: ['var(--font-fraunces)', 'serif'],
  ui:    ['var(--font-geist)', 'sans-serif'],
  data:  ['var(--font-jetbrains)', 'monospace'],
}
```

### Type scale — use these exact steps, do not interpolate new ones

| Name | Size / line-height / tracking | Font | Where |
|---|---|---|---|
| `display` | `clamp(2.5rem, 5vw, 4rem)` / 1.05 / `-0.03em` | story | Screen headlines, story titles on shelf |
| `title` | `1.75rem` / 1.2 / `-0.02em` | story | Panel headers, episode titles |
| `prose` | `1.125rem` / 1.75 / `0` | story | Generated scene text (the payoff text) |
| `body` | `0.9375rem` / 1.6 / `0` | ui | Descriptions, option labels |
| `label` | `0.75rem` / 1.4 / `0.14em` **UPPERCASE** | ui | Button text, section labels |
| `index` | `0.6875rem` / 1 / `0.1em` **UPPERCASE** | data | Index marks (`E03`, `F-127`) |
| `metric` | `2.75rem` / 1 / `-0.02em` | data | Ripple counters (the big numbers) |
| `cite` | `0.8125rem` / 1.5 / `0` | data | Citations, verifier detail lines |

**Rule:** headlines are always `font-story`. Anything the user clicks is always `font-ui` at `label` size. Anything that is a number, ID, or proof is always `font-data`. No exceptions.

---

## 4. SPACING, RULES, RADII, SHADOW

```css
/* Spacing: 4px base. Use only these steps. */
--space-1: 4px;   --space-2: 8px;   --space-3: 12px;  --space-4: 16px;
--space-6: 24px;  --space-8: 32px;  --space-12: 48px; --space-16: 64px;
--space-24: 96px;

/* Radii — deliberately minimal. This product is not "rounded". */
--radius-none: 0px;    /* panels, cards, rules — DEFAULT for almost everything */
--radius-sm:   2px;    /* buttons, inputs, small chips */
--radius-full: 9999px; /* ONLY: ripple nodes, character portraits */

/* Elevation — ONE shadow exists. Do not create others. */
--shadow-lift: 0 8px 32px rgba(0,0,0,0.45);
```

> [!danger] AGENT: RADIUS DISCIPLINE
> Default every panel, card, and container to `--radius-none` (square corners). Only buttons/inputs get `2px`. Only circles (ripple nodes, portraits) get `full`. **Never use `rounded-lg`, `rounded-xl`, or `rounded-2xl` anywhere in this project.** Square corners + hairline rules is the entire structural identity.

### The grain overlay (apply once, globally)
```css
body::after {
  content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 9999;
  opacity: 0.035;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
```
This single overlay is what makes the dark surfaces read as *material* rather than as flat CSS background. Non-negotiable, costs nothing.

---

## 5. LOGO / WORDMARK

**Wordmark:** `CANON` set in Fraunces, weight 600, `letter-spacing: 0.24em`, uppercase, in `--ink-bright`.

**The mark (build as inline SVG, 24×24):** a vertical hairline with a single horizontal branch splitting off at the 40% mark — the divergence glyph. Literally the product: one timeline, one fork.

```svg
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.25">
  <path d="M12 2 V22" />
  <path d="M12 9.6 H21" />
  <circle cx="12" cy="9.6" r="2" fill="currentColor" stroke="none"/>
</svg>
```

**Lockup:** mark, then `--space-3` gap, then wordmark. In the header, follow the wordmark with a `font-data` `index`-size subtitle: `STORY TIME MACHINE` in `--ink-muted`.

---

## 6. COMPONENT SPECS — literal, build exactly these

### 6.1 Button

Three variants only. All: `font-ui`, `label` type scale, `--radius-sm`, transition `160ms ease-out`.

| Variant | Rest | Hover | Active/Pressed |
|---|---|---|---|
| **Primary** | bg `--accent`, text `--shell-void`, padding `14px 28px` | bg `--accent-dim`, translateY(-1px) | translateY(0), bg `--accent-dim` |
| **Secondary** | transparent, 1px border `--ink-line`, text `--ink-bright`, padding `14px 28px` | border `--ink-muted`, bg `--shell-raised` | bg `--shell-sunken` |
| **Ghost** | transparent, no border, text `--ink-muted`, padding `10px 16px` | text `--ink-bright` | — |

**Primary button anatomy — the signature detail:** every primary button contains its label followed by `--space-3` and a `→` arrow glyph. On hover the arrow translates `+3px` on X. Nothing else moves. This one micro-detail repeats on every forward action in the app and becomes the product's tactile signature.

> NEVER: glow, gradient fill, scale-up-on-hover, or box-shadow on any button.

### 6.2 Panel (the universal container)

```
- background: --shell-base
- border: none
- separation from siblings: 1px solid --ink-line (the Ledger Rule)
- border-radius: 0
- padding: --space-8
- optional index mark: absolutely positioned top-left, --space-4 inset,
  font-data / index scale, color --ink-faint
```
Panels never float. They tile, divided by hairlines. If you feel the need to add a shadow to separate two panels, add a rule instead.

### 6.3 StoryCard (Shelf)

```
- aspect-ratio: 2/3 (book proportion)
- cover image fills, with a --shell-void → transparent gradient overlay on the bottom 45%
- title: font-story / title scale, --ink-bright, bottom-left, --space-4 inset
- meta line: font-data / index scale, --ink-muted → "06 EPISODES · 127 FACTS"
- index mark: top-left, "ST-01"
- border: 1px solid --ink-line
- hover: border-color → --accent, cover image scale(1.03) over 400ms ease-out.
  NOTHING ELSE. No lift, no glow, no shadow.
```

### 6.4 TimelineTrack

```
- horizontal 1px rule in --ink-line spanning full width, vertically centered
- episode nodes: 10px circles, --radius-full, on the rule
  · default:  fill --shell-raised, 1px border --ink-line
  · has-character-present: fill --ink-muted
  · selected: fill --accent, plus a 1px --accent ring at 20px diameter
- episode label below each node: font-data / index scale, --ink-faint → "E01"
- ambient motion: nodes breathe opacity 0.85 → 1.0, 4s ease-in-out, infinite,
  each staggered by 200ms. Very subtle — must not be distracting.
```

### 6.5 CharacterPortrait

```
- 56px circle, --radius-full, 1px border --ink-line, grayscale(100%)
- name below: font-ui / label scale, --ink-muted
- hover:   grayscale(0%), border --ink-muted
- selected: grayscale(0%), border 1px --accent, name → --ink-bright
- transition 200ms ease-out
```

### 6.6 MomentCard (Divergence Selector)

```
- ORIGINAL line block:
  · background --paper-warm, text --paper-ink, font-story / prose scale
  · padding --space-6, radius 0
  · label above: font-data / index, --ink-muted → "CANON · E03"
- ALTERNATIVES: stacked list, each row:
  · padding --space-4, 1px bottom rule --ink-line, cursor pointer
  · text: font-ui / body, --ink-muted
  · index mark on left: font-data / index → "ALT-A", "ALT-B", "ALT-C"
  · hover:    text --ink-bright, background --shell-raised
  · selected: background --accent-wash, left 2px solid --accent border,
              text --ink-bright, index mark --accent
```
The paper/dark contrast here is doing the heavy lifting — canon is *paper*, the hypotheticals are *machine*.

### 6.7 RippleGraph — the hero component

```
LAYOUT
- Hand-authored fixed SVG node positions (per FRONTEND_TECH_STACK §3).
- Edges: 1px paths, --ink-line, opacity 0.4
- Nodes: 8px circles default

NODE STATES
- untouched: fill --shell-raised, 1px border --ink-line
- hold:      fill --state-hold,    opacity 1
- invalid:   fill --state-invalid, opacity 0.35, scale 0.75
- new:       fill --state-new,     1px --state-new ring at 16px, opacity 1

CASCADE ANIMATION (total ~2.4s)
1. 0.0s  fork point node pulses once, scale 1 → 1.8 → 1, 400ms
2. 0.4s  invalidated nodes transition in sequence, 40ms stagger,
         each 300ms ease-out: full → opacity 0.35 + scale 0.75.
         Edges into them fade to opacity 0.1.
3. 1.4s  held nodes brighten to --state-hold, 60ms stagger, 200ms each
4. 2.0s  new nodes fade in + ring expands, 300ms
5. Counters count up in sync with each phase (not after)

COUNTERS
- Three stacked rows, right side or below graph
- Number: font-data / metric scale, colored by its state token
- Label:  font-ui / label scale, --ink-muted → "INVALIDATED" / "STILL HOLD" / "NEW REQUIRED"
- Animate with a count-up hook, duration matched to its cascade phase
```

### 6.8 SceneOutputPanel

```
- The generated scene sits on PAPER: background --paper-warm, text --paper-ink,
  font-story / prose scale, max-width 68ch, padding --space-12
- Header above the paper (on shell): font-data / index →
  "EPISODE 03 · REVISED · BRANCH ALT-B"
- Drop cap on first letter: font-story, 3.5rem, float left, line-height 0.8,
  margin-right --space-2, color --accent
- Paper edge: 1px solid --paper-aged, plus --shadow-lift (this is the ONE
  place shadow is allowed — the paper physically sits above the shell)
```

### 6.9 VerifierBadge

```
CONSISTENT state:
- 1px border --state-hold, background transparent, padding --space-3 --space-4
- icon: Lucide "ShieldCheck", 16px, --state-hold
- text: font-ui / label → "CANON-CONSISTENT", --state-hold
- detail below: font-data / cite, --ink-muted → "VERIFIED AGAINST 117 FACTS"

FLAGGED state:
- 1px border --state-invalid, background rgba(209,73,91,0.06)
- icon: Lucide "TriangleAlert", 16px, --state-invalid
- text: font-ui / label → "CONTRADICTION FLAGGED", --state-invalid
- citation block below, font-data / cite:
    DRAFT CLAIM  → Kael is alive
    CANON        → Kael died · E02 §3
  Two-column, label column --ink-faint, value column --ink-bright.
- entrance: shake x: [0,-4,4,-3,3,0] over 400ms, once
```

---

## 7. MOTION SYSTEM

```
Durations:  instant 120ms · quick 200ms · base 320ms · slow 600ms · cascade 2400ms
Easing:     ease-out cubic-bezier(0.16,1,0.3,1) for everything EXCEPT
            the FLIP commit, which uses cubic-bezier(0.87,0,0.13,1) (sharp both ends)
```

**Screen transitions** (state-driven, single route): outgoing view `opacity 1→0, y 0→-8px` over `quick`; incoming `opacity 0→1, y 8px→0` over `base`, delayed 120ms. Consistent for all five screens.

> [!danger] MOTION RESTRAINT — the rule that preserves impact
> The ONLY two moments with assertive motion are **the FLIP commit** and **the Ripple cascade**. Everywhere else: opacity and 1–3px position shifts only. No scale-on-hover, no bounce, no spring physics, no parallax. If everything moves, the two moments that matter stop feeling special.

---

## 8. SCREEN COMPOSITION

**Global frame (every screen):** fixed header — 64px tall, bottom 1px rule `--ink-line`, logo lockup left, presenter-mode toggle right. Content area max-width `1280px`, centered, `--space-16` horizontal padding.

| Screen | Composition |
|---|---|
| **1 Shelf** | `display` headline left-aligned, `--space-16` below header. Below: 3-column grid of StoryCards, `--space-8` gap. Nothing else on screen. |
| **2 Timeline** | Story title (`title`) + index mark top. TimelineTrack centered vertically in upper third. CharacterPortrait row below, `--space-12` gap, horizontally centered. Left of the track: a `font-data` fact-count readout that ticks up as episodes are scanned. |
| **3 Divergence** | Two-column split with a **vertical hairline rule** between. Left: MomentCard original (paper). Right: alternatives list + primary button bottom-right. |
| **4 Ripple** | RippleGraph occupying centre 70% of viewport. Counters right-aligned in a stacked column, separated from graph by a vertical rule. Primary button bottom-right, appears only after cascade completes. |
| **5 Output** | SceneOutputPanel (paper) centered, max 68ch. VerifierBadge directly below, left-aligned to the paper edge. Audio controls (if built) below that. |

**Presenter Mode:** hides the header entirely, removes the max-width constraint, scales base font-size to `1.125×`, disables all hover states. Nothing else changes.

---

## 9. THE CONSISTENCY CHECKLIST — agent must verify before declaring any screen done

> [!todo]
> - [ ] Every panel/card uses square corners (`--radius-none`) — no `rounded-lg/xl/2xl` anywhere
> - [ ] Regions separated by 1px `--ink-line` rules, not by shadows
> - [ ] Every referenceable element has a `font-data` index mark
> - [ ] Narrative text is on `--paper-warm`; system text is on shell. Never mixed.
> - [ ] `--state-*` colors appear ONLY on Ripple nodes/counters and VerifierBadge
> - [ ] Every primary button has the `→` glyph that translates 3px on hover
> - [ ] Three fonts used strictly by role (story/ui/data), never substituted
> - [ ] Only two assertive motions in the whole app (FLIP, cascade)
> - [ ] Grain overlay present globally
> - [ ] Only one shadow in the codebase (`--shadow-lift`), used only on the paper panel

---

## 🔗 Related
[[REQUIREMENTS]] · [[FRONTEND_TECH_STACK]] · [[DECISION — Problem Statement Analysis]]

---
*Written 2026-07-25. Hand to Claude Code together with REQUIREMENTS.md and FRONTEND_TECH_STACK.md as one brief. Also copy §2–§7 into the repo's CLAUDE.md so the constraints persist across every generation.*
