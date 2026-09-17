# Decis Analysis — Product Spec

Status: **approved · UI complete (pre-demo)**  
Track: Bitget AI Hackathon — **AI Trading Desk**  
Date: 2026-09-16  
Updated: 2026-09-16 (aligned to shipped desk)

---

## 1. One-liner

**AI processes the research, argues against itself, and hands you the call.**

**Decis Analysis** is a natural-language research workstation for Bitget rTokens around earnings and related evidence. AI ingests IAA research and surfaces it as structured signal — material / changed / implies — then stress-tests the thesis (bull, bear, invalidation). The trader keeps the final call (Hold / Review / Idea). Optional local loops: draft ticket, post-trade review & playbook. No exchange orders.

---

## 2. Positioning

| | |
|--|--|
| **Product** | Decis Analysis |
| **Hackathon track** | AI Trading Desk |
| **Backend research** | IAA artifacts (events, scores, paths) via frozen `desk_snapshot` |
| **Primary sub-theme** | Personalized research workstation |
| **Also covers** | Signal generation; decision stress-testing; local execution assist; post-trade review & self-development |
| **Explicitly not** | Proven alpha claim; live/paper Bitget order routing; Night Desk; Alpha Factory leaderboard-as-product |

---

## 3. User

**Primary user:** A discretionary trader / researcher evaluating an rToken around an earnings (or related) information event.

**Job to be done:**  
“Given this name and window, tell me what the evidence says, what changed, what it might mean, what would prove me wrong — then let me decide without the system trading for me.”

---

## 4. Core loop

1. **Select focus** — research event package (ticker + rToken + event).  
2. **Ingest** — load snapshot evidence for that focus.  
3. **Signal** — structured read: material / changed / implies (+ confidence notes).  
4. **Stress-test** — thesis summary, bull, bear, invalidation, advisory note.  
5. **Ask (optional)** — constrained NL Q&A over those objects only.  
6. **Decide** — Hold / Review / Idea + optional short note; local log / export.  
7. **Optional desk loop** — draft local ticket (Review/Idea) → post-trade review → promote lesson to playbook.

Live Bitget public quotes may appear as a **side panel** for context. They do not drive signal or stress-test.

---

## 5. Sub-theme mapping

### 5.1 Personalized research workstation (primary)

Workspace centered on one focus (ticker + token + event), not a marketing homepage.

Includes:
- Focus selector over **research packages** in `desk_snapshot` (not the full Bitget listing by default)
- Evidence feed, 180m path, AI summary, read-quality chips
- Optional live quote strip for the focused token
- Decision strip + local decision journal

### 5.2 Information insights and signal generation

Generated read, not raw JSON dump.

| Field | Meaning |
|-------|---------|
| `material` | What matters (surprise, path, clock quality) |
| `changed` | First print vs horizon / what shifted after the reaction |
| `implies` | Cautious posture suggestion (still human call) |
| `confidence_notes` | Limits (EDGAR clock, research path proxy, no orders) |

Rules:
- Claims cite snapshot / derived desk fields only.
- No invented prices, fills, or proven-edge language.
- Product posture is advisory: Decis does not place orders.

### 5.3 Decision stress-testing

| Field | Meaning |
|-------|---------|
| `thesis_summary` | One-line advisory reading from the signal |
| `bull_case` | Best supportive reading from the same evidence |
| `bear_case` | Best opposing argument |
| `invalidation` | Conditions that would kill the thesis |
| `advisory_note` | Reminder: research actions only; no exchange send |

### 5.4 Local execution support (option A)

Draft ticket worksheet (side, size USD, thesis) linked to a **Review** or **Idea**. Status stays local (`draft`). Never submitted to Bitget.

### 5.5 Post-trade review & self-development (one section)

Score a logged Review/Idea against path + invalidation; save outcome + lesson; optionally promote lesson into a local playbook (`localStorage` only).

---

## 6. Screens (information architecture)

Single-app scroll (nav anchors):

1. Workstation / focus + live quotes  
2. Themes strip  
3. Structured signal  
4. Stress-test  
5. Ask desk  
6. Human decision (+ note) + decision journal  
7. Execution support (draft ticket)  
8. Post-trade review & develop  

Out of scope for exchange: live order ticket, broker blotter, portfolio, real fills.

---

## 7. Human decisions

| Action | Meaning |
|--------|---------|
| **Hold** | Leave it; no pursuit |
| **Review** | Watchlist; not treating as actionable idea yet (may draft size locally) |
| **Idea** | Discretionary idea for later human work — **not** an order |

Optional **note** on each log. All three are research audit actions. Never sent to Bitget.

---

## 8. Data contract

Desk reads frozen `desk_snapshot.json` (rebuild: `python desk/build_desk_snapshot.py`).

Required: events, surprises/scores fields used by UI, replay paths, posture metadata (kept in snapshot; not used as a trading-edge claim in UI copy).

Derived in Decis: signal, stress-test, ask replies, confidence score.

Optional sidecar: `python desk/live_quotes.py` → public ticker for focused token.

Focus selector = research packages in the snapshot only.

---

## 9. Honesty rules (non-negotiable)

1. No claimed proven trading edge / alpha on the current challenger.  
2. No live or paper order placement from Decis.  
3. Clock and evidence limits labeled (e.g. EDGAR fallback).  
4. Paths are research charts, not executable fills.  
5. NL answers only from snapshot + derived desk objects.  
6. Draft tickets / reviews / playbook are local-only.

---

## 10. Non-goals

- Claiming proven edge  
- Routing live / paper orders to Bitget  
- Broker fill blotter / account balances  
- Automated strategy self-update from lessons  
- Alpha Factory leaderboard as the product  
- Agentic autonomous trading  
- Night Desk branding  
- Full Bitget Reality universe as the default focus list (research packages only)

---

## 11. NL layer

**v1 (shipped):** Deterministic generators + constrained Ask desk templates.  
**v1.1 (optional):** LLM rewrite only over structured objects already produced.

---

## 12. Success criteria (hackathon demo)

1. Open Decis and pick a research focus.  
2. See material / changed / implies.  
3. See thesis + bull / bear / invalidation.  
4. Ask a constrained question with cites.  
5. Log Hold / Review / Idea (+ note) with no order sent; see it in the journal.  
6. Optionally draft a local ticket and save a post-trade review / playbook lesson.  
7. Stay honest: no edge claim, no exchange send.

---

## 13. Build status

| Step | Deliverable | Status |
|------|-------------|--------|
| 1 | Product spec | **done** (this doc) |
| 2 | `desk_snapshot` schema + rebuild | **done** |
| 3 | Desk UI | **done** (`decis-ui/`) |
| 4 | Generators + Ask desk | **done** |
| 5 | Submit pack (DEMO, screenshots/video, host) | **DEMO.md ready** — screenshots/video when capturing |

---

## 14. Checkpoint

Product definition locked; SPEC/CLAIMS aligned. Demo script + host notes in **DEMO.md**. Capture screenshots/video from the checklist when ready to submit.
