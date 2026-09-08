# Gadfly

**Gadfly** is a civic transparency tool that ingests congressional voting data from the Congress API and presents it as accessible, searchable profiles for every sitting member of Congress. Gadfly is designed to be explicitly non-partisan. It is designed so that anyone, regardless of party affiliation, background, or socioeconomic status can easily see if their representative actually represents their interests.

> **Status:** Data pipeline for house members is complete (members, votes, bill text, member positions, and AI categorization). The senate pipeline is being designed currently. Website is live at www.gadfly-congress.com

---

## How it Works

Enter your zip code to pull up your two U.S. Senators and your House Representative, then click any of them to see how they actually vote in an easily digestible voter profile, compared against Gadfly's 11 category Framework.

- **Voter profile** - a full log of their votes, each with a plain-language summary of the bill, the policy categories it touches, the directional lean within each category, and any flags raised during analysis.

---


## Policy Categories

These 11 categories were specifically picked for how they affect the lives of the majority of Americans. Each vote is tagged with the applicable categories from the list below. For each applicable category, the bill is classified as moving in one of two directions (Binary A or Binary B). If the bill pulls both ways within a single category, that category is marked as an internal contradiction and flagged.

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
| 11 | **Foreign Policy, War & National Security** | Diplomatic / de-escalatory | Coercive / military might |

---

### Flags Reference
| Flag | Severity | Triggers When |
|---|---|---|
| `corruption_or_reduced_oversight` | Red | Bill removes, weakens, or limits any existing mechanism for government accountability or oversight |
| `restricts_individual_rights` | Red | Bill removes, limits, or adds new restrictions on rights or liberties currently held by individuals |
| `subordinates_us_interests` | Caution | Bill grants, transfers, or defers authority or resources to a foreign government or international body in a way that limits US autonomy |
| `misleading_title` | Caution | Bill's title does not accurately represent its content |
| `obfuscation_by_verbosity` | Caution | Bill's substance can be stated in 1-2 sentences but is buried in excessive legal jargon |
| `riders` | Caution | Unrelated provisions are attached to the bill |
| `cross_referencing_obfuscation` | Caution | Bill relies heavily on references to other legislation without plain language explanation |
| `internal_contradiction` | Informational | Bill pulls in both directions within a single category |
| `sunset_clauses` | Informational | Provisions expire after a defined period without clear plain language notice |

---

## AI-Assisted Categorization

Each bill is sent to the Claude API with its full text and the 11 categories above. Claude is instructed to:

1. Identify which categories apply to the bill.
2. For each applicable category, determine which directional binary the bill moves toward.
3. Raise any applicable flags (see Flags Reference) and mark internal contradictions.
4. Write a plain-language summary describing only what the bill mechanically changes - what it adds, removes, restricts, allocates, or requires - without characterizing intent or likely impact.

Bills whose text exceeds the token limit are split into chunks, analyzed separately, and synthesized into a single result.

The summary is stored in the `summary` field of the `Votes` table. All applicable categories are stored in `VoteCategories`; categories with an internal contradiction are stored with `flagged = true`. Categories that don't apply to a bill are dropped rather than stored.

---

## Data Model

All data is stored in PostgreSQL. Fields for all House voting data are sourced from the Congress API.

See [database schema diagram](docs/db_design/table_relationship_diagram.svg) for the full database structure.

---

## Web Interface 

Built with **Flask**. Navigation:

- **Home** - zip-code member selection (look up your senators + house rep)
- **Member Profile** - per-member voting record and legislation
- **About** - Information about the project and the impetus behind it.

### Member Profile Page 

The **header** (always visible) displays: photo, chamber, state, and party.

Below the header, tabbed sections:

| Tab | Contents |
|---|---|
| **Voter Profile** | Directional-lean bars across the 11 categories, plus the member's vote log with summaries and flags |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data storage | PostgreSQL |
| Backend | Python / Flask |
| AI categorization | Claude API |
| Data source | Congress API |
| Hosting | DigitalOcean VPS |
