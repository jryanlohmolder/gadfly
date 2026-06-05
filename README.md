# Gadfly

**Gadfly** is a civic transparency tool that ingests congressional voting data from the Congress API and presents it as accessible, searchable profiles for every sitting member of Congress.

---

## What It Does

Enter your zip code on the homepage to pull up your two U.S. Senators and your House Representative. Click any of them to see:

- **Voting profile** a full log of their votes with bill descriptions
- **Committees** any bills they authored, co-authored, or voted *for* that reduced government accountability, expanded military spending, or restricted individual rights

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
| `committees` | Congress API |
| `authored_leg` | Congress API |
| `co_authored_leg` | Congress API |

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
| `direction` | Generated via Claude API |
| `flagged` | Generated via Claude API |

### VoteFlags
| Field | Source |
|---|---|
| `id` | Generated (autoincrement) |
| `vote_id` | Foreign key to Votes |
| `flag_name` | Generated via Claude API |
| `severity` | Generated via Claude API |
| `explanation` | Generated via Claude API |

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

Each vote is tagged with applicable categories from the following list. For each category, a vote *for* and a vote *against* the bill is mapped to one of two directional binaries.

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

Each bill is sent to the Claude API with its full text and the 11 categories above. Claude is instructed to:

1. Identify which categories apply to the bill
2. Determine which directional binary a **yea** vote and a **nay** vote corresponds to
3. Flag any internal contradictions within the bill across categories
4. Write a plain-language summary of the bill

The summary is stored in the `description` field of the `Votes` table. Categories (excluding any flagged contradictions) are stored in `VoteCategories`.

---

## Web Interface

Built with **Flask**. Navigation tabs:

- **Home** member selection
- **About** a searchable list of bills that reduced corruption oversight, expanded military spending, or restricted individual rights; includes bill author(s), co-authors, and description

### Member Profile Page

The **header** (always visible) displays: photo, chamber, state, party, and committee memberships.

Below the header, tabbed sections:

| Tab | Contents |
|---|---|
| **Voting Profile** | 12 category bars showing directional lean (0 direction: *reduce oversight / accountability*
- **Foreign Policy, War & National Security** direction: *restrict rights / increase restrictions*

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data storage | SQLite |
| Backend | Python / Flask |
| AI categorization | Claude API |
| Data source | Congress API |
