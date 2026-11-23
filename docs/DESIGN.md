# Interface design

The interface was redesigned on 23 November 2026 after the owner called the first version boring and asked for the technical material to be for administrators only. This file records what was chosen and why, so the next person can extend it without undoing it.

## The brief

Readers of news (students, journalists, ordinary people, some of them reading Urdu) paste something they doubt and want a plain answer. The tool must stay honest: it says *Unverified* when it cannot tell and says what a result does not mean. The technical story (models, accuracy, methodology) is for the people who run the system.

## Three areas

| Area | Who | What |
|---|---|---|
| Public site | Anyone | Home page with the check box, a picture of what an answer looks like, the list of checks, what the tool cannot do; About; sign-in pages |
| The app | Signed-in users | Home, the six kinds of check, results, past checks, contact and feedback, profile, settings |
| Admin console | Administrators only | Overview, users, feedback review, audit log, models and measurements, methodology. Its own navigation and an *Admin console* badge, so it cannot be mistaken for the app |

## Palette

| Name | Value | Use |
|---|---|---|
| Midnight | `#141A3C` | Text, the navigation rail, the footer |
| Paper | `#F5F6FA` | Page background (a dark equivalent `#0E1126` is used in the dark theme) |
| Highlighter | `#FFD60A` | The main button, and the marked text. Used for the one thing to do on a screen |
| Verdict green / red / slate / amber | `#0F7A4D` / `#C42642` / `#3F456B` / `#8A5A00` | The band of a result: real, fake, "not sure", a flag to look closer |
| Link indigo | `#3438C8` | Links, focus ring, chart bars |

White text on each verdict colour has a contrast of at least 5.3:1 (4.8:1 in the dark theme); body text on paper is at least 7.7:1 and the faintest meta text is 4.9:1. The light and dark values are in `frontend/src/styles/index.css`.

## Type

Bricolage Grotesque (headings, the verdict word, numbers) and Instrument Sans (everything else), both variable fonts served from the package, so no request goes to a font host. Headings are heavy and tightly spaced; body text is 16 px with a 68-character line.

## The one memorable thing

The verdict band. A result opens with a wide field in the colour of its verdict and the verdict word at display size, with the one sentence that says what it does not mean. A reader sees the answer before reading anything. Everything around it is quiet: flat white panels with one thin line, no shadows. The only other loud object is the paste box on the home page, which has a hard offset shadow so that it reads as the place to start.

## Rules that kept it from looking like a template

- No eyebrow labels in capitals, no numbered markers (nothing here is a sequence), no gradient washes, no identical icon cards in a row on the home page.
- The highlighter is used for what the tool points at (marked words, the main button), never to colour a single word of a heading.
- Colour is never the only signal: every band, tag and chart carries the verdict in words.
- Motion answers an action (a button press) or shows one thing: the meter needle moves to its place when a result opens. Nothing else animates on page load, and `prefers-reduced-motion` turns the needle's motion off.
- Keyboard focus is a 3 px ring on every control. The layout was checked at 390 px wide, where the navigation rail becomes a menu.

## What ordinary readers do not see

The model registry, the measured accuracy, the methodology page, the technology list, the model's percentages, the word weights, the image measurements and the model name on a result. Ordinary readers get plain-language limits on every result and a *What it cannot do* section. The server refuses `/models` and the four evaluation routes to anyone who is not an administrator; hiding the links alone would not be access control. See limitation L19 for what this costs in transparency.

## Files

`frontend/src/styles/index.css` (tokens), `frontend/tailwind.config.ts`, `frontend/src/layouts/` (`RailShell`, `AppLayout`, `AdminLayout`, `PublicLayout`), `frontend/src/components/VerdictRuling.tsx` (the band), `frontend/src/pages/Landing.tsx`.
