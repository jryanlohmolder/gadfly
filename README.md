# Gadfly

**Gadfly** is a civic transparency tool that ingests congressional voting data from the Congress API and presents it as accessible, searchable profiles for every sitting member of Congress.

> **Status:** Data pipeline complete (members, votes, bill text, member positions, and AI categorization). Web interface is in progress — sections marked _Planned_ below are not yet built.

---

## What It Does

The goal: enter your zip code to pull up your two U.S. Senators and your House Representative, then click any of them to see how they actually vote — in plain language.

For each member the data layer currently supports:

- **Voting profile** — a full log of their votes, each with a plain-language summary of the bill, the policy categories it touches, the directional lean within each category, and any flags raised during analysis.
- **Legislation** — the bills they sponsored or cosponsored, with policy area.

A derived "accountability" view (bills that reduced government oversight, expanded military spending, or restricted individual rights) is _Planned_ — it will be built on top of the flags and category directions already stored per vote.

---

## Data Model

All data is stored in SQLite. Fields are sourced from the Congress API unless noted.

### Members
| Field | Source |
|---|---|
| `member_id` | Congress API (bioguideId) |
| `name` | Congress API |
| `state` | Congress API |
| `district` | Congress API (null for senators) |
| `party` | Congress API |
| `chamber` | Congress API |
| `picture_url` | Congress API |
| `photo_cred` | Congress API |

> Sponsored and cosponsored legislation are stored in their own tables (below), not as columns on Members. Committee data is out of scope for the MVP.

### Votes
| Field | Source |
|---|---|
| `vote_id` | Generated (autoincrement) |
| `congress` | Congress API |
| `session` | Congress API |
| `roll_call_number` | Congress API |
| `legislation_number` | Congress API |
| `legislation_type` | Congress API |
| `result` | Congress API |
| `date` | Congress API |
| `bill_text` | Congress API (full bill text) |
| `summary` | Generated via Claude API |
| `chunk_count` | Generated via Claude API |

### MemberVotes
| Field | Source |
|---|---|
| `id` | Generated (autoincrement) |
| `member_id` | Foreign key to Members |
| `vote_id` | Foreign key to Votes |
| `position` | Congress API (yea / nay / not voting) |

### VoteCategories
| Field | Source |
|---|---|
| `id` | Generated (autoincrement) |
| `vote_id` | Foreign key to Votes |
| `category` | Generated via Claude API |
| `direction` | Generated via Claude API (directional label, or "Internal contradiction") |
| `flagged` | Generated via Claude API (true if internally contradictory) |

### VoteFlags
| Field | Source |
|---|---|
| `id` | Generated (autoincrement) |
| `vote_id` | Foreign key to Votes |
| `flag_name` | Generated via Claude API |
| `severity` | Generated via Claude API |
| `explanation` | Generated via Claude API |

### SponsoredLegislation
| Field | Source |
|---|---|
| `id` | Generated (autoincrement) |
| `member_id` | Foreign key to Members |
| `legislation_number` | Congress API |
| `legislation_type` | Congress API |
| `policy_area` | Congress API (may be null) |

### CosponsoredLegislation
| Field | Source |
|---|---|
| `id` | Generated (autoincrement) |
| `member_id` | Foreign key to Members |
| `legislation_number` | Congress API |
| `legislation_type` | Congress API |
| `policy_area` | Congress API (may be null) |

### Flags Reference
| Flag | Severity | Triggers When |
|---|---|---|
| `corruption_or_reduced_oversight` | Red | Bill removes, weakens, or limits any existing mechanism for government accountability or oversight |
| `restricts_individual_rights` | Red | Bill removes, limits, or adds new restrictions on rights or liberties currently held by individuals |
| `misleading_title` | Red | Bill's title does not accurately represent its content |
| `obfuscation_by_verbosity` | Red | Bill's substance can be stated in 1-2 sentences but is buried in excessive legal jargon |
| `riders` | Caution | Unrelated provisions are attached to the bill |
| `cross_referencing_obfuscation` | Caution | Bill relies heavily on references to other legislation without plain language explanation |
| `subordinates_us_interests` | Caution | Bill grants, transfers, or defers authority or resources to a foreign government or international body in a way that limits US autonomy |
| `internal_contradiction` | Informational | Bill pulls in both directions within a single category |
| `sunset_clauses` | Informational | Provisions expire after a defined period without clear plain language notice |

---

## Policy Categories

Each vote is tagged with the applicable categories from the list below. For each applicable category, the bill is classified as moving in one of two directions (Binary A or Binary B). If the bill pulls both ways within a single category, that category is marked as an internal contradiction and flagged.

| # | Category | Binary A | Binary B |
|---|---|---|---|
| 1 | **Economy & Cost of Living** | Expand spending / stimulus | Cut spending / austerity |
| 2 | **Immigration & Border Security** | Expand pathways / access | Restrict entry / tighten borders |
| 3 | **Democracy & Governance** | Strengthen voting / institutions | Restrict voting / reduce oversight |
| 4 | **Housing & Affordability** | Expand housing access / funding | Cut housing programs / deregulate |
| 5 | **Healthcare** | Expand access / coverage | Reduce / restrict access |
| 6 | **Individual Rights & Civil Liberties** | Strengthen rights / protections | Restrict rights / increase restrictions |
| 7 | **Crime & Public Safety** | Expand rehabilitation / prevention | Increase enforcement / penalties |
| 8 | **Corruption & Government Accountability** | Increase transparency / oversight | Reduce oversight / accountability |
| 9 | **Social Programs & Safety Net** | Expand programs / benefits | Cut / reduce programs |
| 10 | **Environment & Energy** | Expand protections / clean energy | Reduce protections / expand fossil fuels |
| 11 | **Foreign Policy, War & National Security** | Diplomatic / reduce military spending | Military expansion / increase defense spending |
| 12 | **National Interest & Foreign Influence** | Prioritizes US interests | Subordinates US interests to foreign interests |

---

## AI-Assisted Categorization

Each bill is sent to the Claude API with its full text and the 12 categories above. Claude is instructed to:

1. Identify which categories apply to the bill.
2. For each applicable category, determine which directional binary the bill moves toward.
3. Raise any applicable flags (see Flags Reference) and mark internal contradictions.
4. Write a plain-language summary describing only what the bill mechanically changes — what it adds, removes, restricts, allocates, or requires — without characterizing intent or likely impact.

Bills whose text exceeds the token limit are split into chunks, analyzed separately, and synthesized into a single result.

The summary is stored in the `summary` field of the `Votes` table. All applicable categories are stored in `VoteCategories`; categories with an internal contradiction are stored with `flagged = true`. Categories that don't apply to a bill are dropped rather than stored.

---

## Web Interface _(Planned)_

Built with **Flask**. Planned navigation:

- **Home** — zip-code member selection (look up your senators + house rep)
- **Member Profile** — per-member voting record and legislation
- **About** — searchable list of bills surfaced by the accountability flags (reduced oversight, expanded military spending, restricted individual rights), with sponsors and summaries

### Member Profile Page _(Planned)_

The **header** (always visible) displays: photo, chamber, state, and party.

Below the header, tabbed sections:

| Tab | Contents |
|---|---|
| **Voting Profile** | Directional-lean bars across the 12 categories, plus the member's vote log with summaries and flags |
| **Legislation** | Bills the member sponsored or cosponsored, by policy area |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data storage | SQLite |
| Backend | Python / Flask |
| AI categorization | Claude API |
| Data source | Congress API |
