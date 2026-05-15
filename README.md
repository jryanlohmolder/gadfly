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
| `bioguideId` | Congress API |
| `name` | Congress API |
| `state` | Congress API |
| `party` | Congress API |
| `chamber` | Congress API |
| `picture_url` | Congress API |
| `committees` | Congress API |
| `legislation_authored` | Congress API |
| `legislation_co_authored` | Congress API |

### Votes
| Field | Source |
|---|---|
| `vote_id` | Generated |
| `congress` | Congress API |
| `session` | Congress API |
| `roll_call_number` | Congress API |
| `legislation_number` | Congress API |
| `legislation_type` | Congress API |
| `result` | Congress API |
| `date` | Congress API |
| `description` | Generated via Claude API |

### MemberVotes
| Field | Source |
|---|---|
| `member_id` | bioguideId from Members |
| `vote_id` | Foreign key to Votes |
| `position` | Congress API (yea / nay) |

### VoteCategories
| Field | Source |
|---|---|
| `vote_id` | Foreign key to Votes |
| `category` | Generated via Claude API |
| `direction` | Generated via Claude API |

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
| **Voting Profile** | 11 category bars showing directional lean (0 direction: *reduce oversight / accountability*
- **Foreign Policy, War & National Security** direction: *restrict rights / increase restrictions*

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data storage | SQLite |
| Backend | Python / Flask |
| AI categorization | Claude API |
| Data source | Congress API |
