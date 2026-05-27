import copy
import json
import os

import anthropic

from dotenv import load_dotenv

load_dotenv()

# Constants
API_KEY = os.getenv("ANTHROPIC_API_KEY")
MAX_BILL_TOKENS = 180_000
CHUNK_SIZE = 720_000
PARSE_BILL_PROMPT = (
    "You are a nonpartisan bill analysis tool. Analyze the bill text provided "
    "and return only valid JSON — no preamble, no markdown, no code fences.\n\n"
    "If you cannot determine whether a flag is present, default to false.\n\n"
    "Return the following structure exactly:\n\n"
    "{\n"
    '    "flags": {\n'
    '        "corruption_or_reduced_oversight": {\n'
    '            "severity": "red",\n'
    '            "present": true | false,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "restricts_individual_rights": {\n'
    '            "severity": "red",\n'
    '            "present": true | false,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "misleading_title": {\n'
    '            "severity": "red",\n'
    '            "present": true | false,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "obfuscation_by_verbosity": {\n'
    '            "severity": "red",\n'
    '            "present": true | false,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "riders": {\n'
    '            "severity": "caution",\n'
    '            "present": true | false,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "cross_referencing_obfuscation": {\n'
    '            "severity": "caution",\n'
    '            "present": true | false,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "internal_contradiction": {\n'
    '            "severity": "informational",\n'
    '            "present": true | false,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "sunset_clauses": {\n'
    '            "severity": "informational",\n'
    '            "present": true | false,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        }\n'
    '    },\n'
    '    "categories": {\n'
    '        "Economy & Cost of Living": {\n'
    '            "direction": "Expand spending / stimulus" | "Cut spending / austerity" | "Not present" | "Internal contradiction",\n'
    '            "flagged": true | false\n'
    '        },\n'
    '        "Immigration & Border Security": {\n'
    '            "direction": "Expand pathways / access" | "Restrict entry / tighten borders" | "Not present" | "Internal contradiction",\n'
    '            "flagged": true | false\n'
    '        },\n'
    '        "Democracy & Governance": {\n'
    '            "direction": "Strengthen voting / institutions" | "Restrict voting / reduce oversight" | "Not present" | "Internal contradiction",\n'
    '            "flagged": true | false\n'
    '        },\n'
    '        "Housing & Affordability": {\n'
    '            "direction": "Expand housing access / funding" | "Cut housing programs / deregulate" | "Not present" | "Internal contradiction",\n'
    '            "flagged": true | false\n'
    '        },\n'
    '        "Healthcare": {\n'
    '            "direction": "Expand access / coverage" | "Reduce / restrict access" | "Not present" | "Internal contradiction",\n'
    '            "flagged": true | false\n'
    '        },\n'
    '        "Individual Rights & Civil Liberties": {\n'
    '            "direction": "Strengthen rights / protections" | "Restrict rights / increase restrictions" | "Not present" | "Internal contradiction",\n'
    '            "flagged": true | false\n'
    '        },\n'
    '        "Crime & Public Safety": {\n'
    '            "direction": "Expand rehabilitation / prevention" | "Increase enforcement / penalties" | "Not present" | "Internal contradiction",\n'
    '            "flagged": true | false\n'
    '        },\n'
    '        "Corruption & Government Accountability": {\n'
    '            "direction": "Increase transparency / oversight" | "Reduce oversight / accountability" | "Not present" | "Internal contradiction",\n'
    '            "flagged": true | false\n'
    '        },\n'
    '        "Social Programs & Safety Net": {\n'
    '            "direction": "Expand programs / benefits" | "Cut / reduce programs" | "Not present" | "Internal contradiction",\n'
    '            "flagged": true | false\n'
    '        },\n'
    '        "Environment & Energy": {\n'
    '            "direction": "Expand protections / clean energy" | "Reduce protections / expand fossil fuels" | "Not present" | "Internal contradiction",\n'
    '            "flagged": true | false\n'
    '        },\n'
    '        "Foreign Policy, War & National Security": {\n'
    '            "direction": "Diplomatic / reduce military spending" | "Military expansion / increase defense spending" | "Not present" | "Internal contradiction",\n'
    '            "flagged": true | false\n'
    '        }\n'
    '    },\n'
    '    "summary": "2-3 sentence plain language summary of what the bill actually does, no political framing"\n'
    "}\n\n"
    "Category flagging rules:\n"
    "- All 11 categories: flagged if the bill pulls in both directions within that category (internal contradiction).\n"
    "- 'Corruption & Government Accountability': also flagged if direction is 'Reduce oversight / accountability'.\n"
    "- 'Individual Rights & Civil Liberties': also flagged if direction is 'Restrict rights / increase restrictions'.\n\n"
    "Bill-level flag rules (independent of categories):\n"
    "- internal_contradiction: flag if the bill pulls in both directions within any single category.\n"
    "- obfuscation_by_verbosity: flag if length and complexity appear disproportionate to what the bill actually does.\n"
    "- riders: flag if unrelated provisions are attached to the bill.\n"
    "- cross_referencing_obfuscation: flag if the bill relies heavily on references to other legislation without plain language explanation.\n"
    "- sunset_clauses: flag if provisions expire after a defined period without clear plain language notice.\n"
    "- misleading_title: flag if the bill's title does not accurately represent its content.\n"
    "- corruption_or_reduced_oversight: flag if the bill reduces government accountability or oversight.\n"
    "- restricts_individual_rights: flag if the bill restricts individual rights or civil liberties.\n\n"
    "BILL TEXT:\n"
)
SYNTHESIZE_CHUNKS_PROMPT = (
    "You are a nonpartisan bill analysis tool. You have already analyzed a long bill in chunks. "
    "Below is a list of chunk analysis results in JSON format.\n\n"
    "Your job is to synthesize these chunks into a final assessment. "
    "You are looking at the full picture now — patterns across the entire bill that no single chunk could see.\n\n"
    "Return only valid JSON — no preamble, no markdown, no code fences.\n\n"
    "You may only SET flags to true, never to false. If a flag is already true in any chunk, leave it true.\n\n"
    "Reassess ONLY these flags with the full picture in mind:\n"
    "- obfuscation_by_verbosity: Is the bill's length and complexity disproportionate to what it actually does? "
    "Consider number of chunks, topic sprawl, and whether complexity serves the legislation or obscures it.\n"
    "- riders: Across all chunks, are there provisions unrelated to the bill's core purpose?\n"
    "- misleading_title: Does the bill's title accurately represent the full scope of what all chunks cover?\n"
    "- cross_referencing_obfuscation: Across all chunks, does the bill rely heavily on references to other "
    "legislation without plain language explanation?\n\n"
    "Also return:\n"
    "- A clean 2-3 sentence plain language summary of what the entire bill actually does. "
    "Write for a constituent who wants to know if this bill serves their interests. No political framing.\n"
    "- A confidence score (0.0 to 1.0) reflecting how complete and consistent the chunk analyses were. "
    "Low score means chunks were inconsistent, incomplete, or the bill was too complex to assess reliably. "
    "This score is for internal diagnostic use only — it is never shown to constituents.\n\n"
    "Return this structure exactly:\n\n"
    "{\n"
    '    "flags": {\n'
    '        "obfuscation_by_verbosity": {\n'
    '            "severity": "red",\n'
    '            "present": true | false,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "riders": {\n'
    '            "severity": "caution",\n'
    '            "present": true | false,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "misleading_title": {\n'
    '            "severity": "red",\n'
    '            "present": true | false,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "cross_referencing_obfuscation": {\n'
    '            "severity": "caution",\n'
    '            "present": true | false,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        }\n'
    '    },\n'
    '    "summary": "2-3 sentence plain language summary of what the bill actually does",\n'
    '    "confidence": 0.0 to 1.0\n'
    "}\n\n"
    "CHUNK RESULTS:\n"
)


def parse_bill_text(text):

    client = anthropic.Anthropic()
    
    # Count Tokens
    token_count = client.count_tokens(PARSE_BILL_PROMPT + text)

    
    if token_count <= MAX_BILL_TOKENS:

        # Make API call
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4_000,
            messages=[
                {"role": "user", "content": PARSE_BILL_PROMPT + text,}
            ]
        )

        # Extract the text from the response
        raw = response.content[0].text

        # Parse json
        try:
            result = json.loads(raw)
        
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            raise
    
    else:
        chunk_results = []
        chunks = [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
        for chunk in chunks:
            
            # Make API call
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4_000,
                messages=[
                    {"role": "user", "content": PARSE_BILL_PROMPT + chunk,}
                ]
            )

            # Extract the text from the response
            raw = response.content[0].text

            # Parse json
            try:
                result = json.loads(raw)

            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                continue

            chunk_results.append(result)

        # Check to make sure chunk results worked
        if not chunk_results:
            raise ValueError("All chunks failed JSON parsing")
        
        result = merge_chunks(chunk_results)

    return strip_absent(result)

def merge_chunks(chunk_results):
    
    # Create merged dict to be returned
    merged = {
        "flags": copy.deepcopy(chunk_results[0]["flags"]),
        "categories": copy.deepcopy(chunk_results[0]["categories"]),
        "summary": "",
    }

    # Create merged flags
    for flag_name in merged["flags"].keys():
        if any(chunk["flags"][flag_name]["present"] for chunk in chunk_results):
            merged["flags"][flag_name]["present"] = True
    
    # Create merged categories
    for category in merged["categories"].keys():
        directions = [chunk["categories"][category]["direction"] 
              for chunk in chunk_results 
              if chunk["categories"][category]["direction"] != "Not present"]
        
        # Create unique directions
        unique_directions = set(directions)

        # Flag if there are multiple directions
        if len(unique_directions) > 1:
            merged["categories"][category]["flagged"] = True
            merged["categories"][category]["direction"] = "Internal contradiction"

        elif len(unique_directions) == 1:
            merged["categories"][category]["direction"] = directions[0]

        else:
            merged["categories"][category]["direction"] = "Not present"
    
    # Create merged summary
    merged["summary"] = "\n".join(chunk["summary"] for chunk in chunk_results)    
        
    # return merged dict
    return merged

def strip_absent(result):
    
    # strip flags that are not present
    for flag in list(result["flags"].keys()):
        if result["flags"][flag]["present"] == False:
            del result["flags"][flag]

    # strip categories that are not present
    for category in list(result["categories"].keys()):
        if result["categories"][category]["direction"] == "Not present":
            del result["categories"][category]

    return result