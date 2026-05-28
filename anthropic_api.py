import copy
import json
import os
import requests

from anthropic import Anthropic

from dotenv import load_dotenv

from congress_api import exponential_backoff

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
    '            "present": True | False,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "restricts_individual_rights": {\n'
    '            "severity": "red",\n'
    '            "present": True | False,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "misleading_title": {\n'
    '            "severity": "red",\n'
    '            "present": True | False,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "obfuscation_by_verbosity": {\n'
    '            "severity": "red",\n'
    '            "present": True | False,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "riders": {\n'
    '            "severity": "caution",\n'
    '            "present": True | False,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "cross_referencing_obfuscation": {\n'
    '            "severity": "caution",\n'
    '            "present": True | False,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "internal_contradiction": {\n'
    '            "severity": "informational",\n'
    '            "present": True | False,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        },\n'
    '        "sunset_clauses": {\n'
    '            "severity": "informational",\n'
    '            "present": True | False,\n'
    '            "explanation": "1-2 sentence explanation or null if present is false"\n'
    '        }\n'
    '    },\n'
    '    "categories": {\n'
    '        "Economy & Cost of Living": {\n'
    '            "direction": "Expand spending / stimulus" | "Cut spending / austerity" | "Not present" | "Internal contradiction",\n'
    '            "flagged": True | False\n'
    '        },\n'
    '        "Immigration & Border Security": {\n'
    '            "direction": "Expand pathways / access" | "Restrict entry / tighten borders" | "Not present" | "Internal contradiction",\n'
    '            "flagged": True | False\n'
    '        },\n'
    '        "Democracy & Governance": {\n'
    '            "direction": "Strengthen voting / institutions" | "Restrict voting / reduce oversight" | "Not present" | "Internal contradiction",\n'
    '            "flagged": True | False\n'
    '        },\n'
    '        "Housing & Affordability": {\n'
    '            "direction": "Expand housing access / funding" | "Cut housing programs / deregulate" | "Not present" | "Internal contradiction",\n'
    '            "flagged": True | False\n'
    '        },\n'
    '        "Healthcare": {\n'
    '            "direction": "Expand access / coverage" | "Reduce / restrict access" | "Not present" | "Internal contradiction",\n'
    '            "flagged": True | False\n'
    '        },\n'
    '        "Individual Rights & Civil Liberties": {\n'
    '            "direction": "Strengthen rights / protections" | "Restrict rights / increase restrictions" | "Not present" | "Internal contradiction",\n'
    '            "flagged": True | False\n'
    '        },\n'
    '        "Crime & Public Safety": {\n'
    '            "direction": "Expand rehabilitation / prevention" | "Increase enforcement / penalties" | "Not present" | "Internal contradiction",\n'
    '            "flagged": True | False\n'
    '        },\n'
    '        "Corruption & Government Accountability": {\n'
    '            "direction": "Increase transparency / oversight" | "Reduce oversight / accountability" | "Not present" | "Internal contradiction",\n'
    '            "flagged": True | False\n'
    '        },\n'
    '        "Social Programs & Safety Net": {\n'
    '            "direction": "Expand programs / benefits" | "Cut / reduce programs" | "Not present" | "Internal contradiction",\n'
    '            "flagged": True | False\n'
    '        },\n'
    '        "Environment & Energy": {\n'
    '            "direction": "Expand protections / clean energy" | "Reduce protections / expand fossil fuels" | "Not present" | "Internal contradiction",\n'
    '            "flagged": True | False\n'
    '        },\n'
    '        "Foreign Policy, War & National Security": {\n'
    '            "direction": "Diplomatic / reduce military spending" | "Military expansion / increase defense spending" | "Not present" | "Internal contradiction",\n'
    '            "flagged": True | False\n'
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
    "You are a nonpartisan bill analysis tool. Below are JSON analyses of a long bill, "
    "processed in chunks. Synthesize them into a single final result.\n\n"
    "Return valid JSON only — no preamble, no markdown, no code fences.\n\n"
    "Use the exact same JSON structure as the chunk results below.\n\n"
    "Rules:\n"
    "- You may only SET flags to true, never to false\n"
    "- If a category has contradicting directions across chunks, set direction to 'Internal contradiction' and flagged to true\n"
    "- Reassess obfuscation_by_verbosity, riders, misleading_title, and cross_referencing_obfuscation "
    "with the full picture in mind — no single chunk could see the whole bill\n"
    "- Write a fresh 2-3 sentence plain language summary covering the entire bill\n\n"
    "CHUNK RESULTS:\n"
)

def parse_bill_text(text):
    """
    Parse bill text through Claude and return structured flag and category analysis.
    
    Args:
        text (str): Raw bill text to analyze.
    
    Returns:
        dict: Structured analysis containing present flags, categories, and summary.
    
    Raises:
        json.JSONDecodeError: If Claude returns malformed JSON.
        ValueError: If all chunks fail JSON parsing.
        requests.exceptions.RetryError: If run_cap number is reached.
        anthropic.APIError: If a non-429 API error is returned.
    """
     
    client = Anthropic()
    
    # Count tokens
    token_count = client.messages.count_tokens(PARSE_BILL_PROMPT + text)

    if token_count <= MAX_BILL_TOKENS:
         # Initialize count
        count = 0
        run_cap = 5
       
        while count < run_cap:
            try:
                # Make API call
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4_000,
                    messages=[{"role": "user", "content": PARSE_BILL_PROMPT + text}]
                )
                break
            
            except Anthropic.RateLimitError:
                # Call backoff function
                exponential_backoff(count)
                # Increase count
                count += 1
                if count == run_cap:
                    raise requests.exceptions.RetryError("Max retries exceeded")
                # Retry from top of loop
                continue
            
            except Anthropic.APIError as e:
                print(f"API error: {e}")
                raise
        
        # Extract the text from the response
        raw = response.content[0].text
        
        # Parse JSON
        try:
            result = json.loads(raw)
        
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            raise

    else:
        chunk_results = []
        chunks = [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
        
        for chunk in chunks:    
            # Initialize count
            count = 0
            run_cap = 5
            
            while count < run_cap:
                try:
                    # Make API call
                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=4_000,
                        messages=[{"role": "user", "content": PARSE_BILL_PROMPT + chunk}]
                    )
                    break
                
                except Anthropic.RateLimitError:
                    # Call backoff function
                    exponential_backoff(count)
                    # Increase count
                    count += 1
                    if count == run_cap:
                        raise requests.exceptions.RetryError("Max retries exceeded")
                    # Retry from top of loop
                    continue
                
                except Anthropic.APIError as e:
                    print(f"API error: {e}")
                    raise
            
            # Extract the text from the response
            raw = response.content[0].text
            
            # Parse JSON
            try:
                chunk_result = json.loads(raw)
            
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                continue
            
            chunk_results.append(chunk_result)

        # Check to make sure chunk results worked
        if not chunk_results:
            raise ValueError("All chunks failed JSON parsing")

        combined_result = merge_chunks(chunk_results)
        
        # Initialize count
        count = 0
        run_cap = 5
        while count < run_cap:
            try:
                # Resend combined results to Claude
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4_000,
                    messages=[{"role": "user", "content": SYNTHESIZE_CHUNKS_PROMPT + json.dumps(combined_result)}]
                )
                break
            
            except Anthropic.RateLimitError:
                # Call backoff function
                exponential_backoff(count)
                # Increase count
                count += 1
                
                if count == run_cap:
                    raise requests.exceptions.RetryError("Max retries exceeded")
                # Retry from top of loop
                continue
            
            except Anthropic.APIError as e:
                print(f"API error: {e}")
                raise
        
        # Extract the text from the response
        raw = response.content[0].text
        
        # Parse JSON
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            raise

    return strip_absent(result)

def merge_chunks(chunk_results):
    """
    Merge a list of chunk analysis results into a single combined result.
    
    Args:
        chunk_results (list): List of parsed JSON dicts returned from chunk API calls.
    
    Returns:
        dict: Merged analysis where flags are set to true if present in any chunk,
              category directions are reconciled across chunks, and summaries are concatenated.
    """
    
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
    """
    Remove flags and categories that are not present from the analysis result.
    
    Args:
        result (dict): Structured analysis dict containing flags and categories.
    
    Returns:
        dict: Cleaned analysis with absent flags and unpresent categories removed.
    """
    
    # strip flags that are not present
    for flag in list(result["flags"].keys()):
        if result["flags"][flag]["present"] == False:
            del result["flags"][flag]

    # strip categories that are not present
    for category in list(result["categories"].keys()):
        if result["categories"][category]["direction"] == "Not present":
            del result["categories"][category]

    return result