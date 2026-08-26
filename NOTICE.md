# NOTICE

## This is a teaching demo. Everything in it is fictional.

**SlotSight** is an educational reference implementation built to demonstrate
**spec-driven development with GitHub Copilot and Visual Studio Code**. The casino
analytics domain is the vehicle; the configuration surface is the lesson.

---

## 🎰 The casino is invented

**Neon Palms Casino Resort** is a fictional property. It does not exist. Any
resemblance to a real casino, resort, or gaming operator — living, dead, or
recently acquired — is coincidental.

## 🎲 The game titles are invented

Slot titles in this repository (*Sunset Serpent*, *Neon Tiki Riches*,
*Cobalt Comet*, *Midnight Mesa*, *Velvet Rhino*, and the rest) are **made up for
this demo**. They are not real games, are not affiliated with any game
manufacturer, and are not intended to reference or evoke any specific
commercial title.

Manufacturer names in the sample data are likewise fictional house-brands
invented for this repository.

## 📊 The market data is synthetic

SlotSight models an "external market intelligence" capability. Real slot-floor
operators buy this class of data from commercial providers.

**This repository integrates with none of them.**

The market-intel layer is a **pluggable adapter interface**
(`apps/api/src/slotsight/market/`) with exactly one implementation shipped: a
**synthetic generator** that produces plausible-looking numbers from a fixed
random seed. The fictional provider names used in the code and UI —
`ReelIndex`, `FloorMetrics`, `GamingWire` — are placeholders that exist to show
*where* a real adapter would plug in.

There is **no scraping**, no API integration, no data licensing, and no
affiliation with or endorsement by any real market-data provider, gaming
publication, or research firm.

## 🔢 All performance data is generated

Every machine, every coin-in figure, every daily win number, and every trend in
this repository is produced by `data/generator/generate.py` from a deterministic
seed. **No real operator data was used, referenced, or reverse-engineered.**

The dataset contains deliberately planted signals so the demo tells a
consistent story on stage. See
[`docs/slot-analytics-primer.md`](docs/slot-analytics-primer.md).

## 🔒 There is no personally identifiable information

By design, SlotSight models **machines and money — never people**.

There are no player records, no loyalty accounts, no card numbers, no names, no
addresses, and no session-level player tracking anywhere in the schema, the
generator, or the API. This is both a privacy stance and a deliberate teaching
point: the interesting slot-floor analytics problem does not require player PII.

---

## Origin

The functional concept — an AI assistant for slot floor performance analysis —
is adapted from a hackathon concept presented at **NerdFest 2025**. This
implementation is an independent, from-scratch educational rebuild using
fictional data and fictional branding. It is not the original submission, and
it is not affiliated with or endorsed by any organization involved.

---

## Trademarks

All product names, logos, and brands referenced in the *documentation* —
GitHub, GitHub Copilot, Visual Studio Code, Microsoft, Azure, Docker,
PostgreSQL, React, and others — are property of their respective owners and are
used for identification purposes only. Use does not imply endorsement.

---

*Questions about this notice? Open an issue.*
