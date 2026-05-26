import os
import requests

import anthropic

from dotenv import load_dotenv

load_dotenv()

# Constants
API_KEY = os.getenv("ANTHROPIC_API_KEY")
PARSE_BILL_PROMPT = (
    "You are a nonpartisan bill analysis tool. Analyze the bill text provided "
    "and return only valid JSON — no preamble, no markdown, no code fences.\n\n"
    "Return the following structure exactly:\n\n"
    "{\n"
    '    "flags": {\n'
    '        "corruption_or_reduced_oversight": {\n'
    '            "severity": "red",\n'
    '            "present": true/false,\n'
    '            "explanation": "1-2 sentence explanation or null"\n'
    '        },\n'
    '        "restricts_individual_rights": {\n'
    '            "severity": "red",\n'
    '            "present": true/false,\n'
    '            "explanation": "1-2 sentence explanation or null"\n'
    '        },\n'
    '        "misleading_title": {\n'
    '            "severity": "red",\n'
    '            "present": true/false,\n'
    '            "explanation": "1-2 sentence explanation or null"\n'
    '        },\n'
    '        "obfuscation_by_verbosity": {\n'
    '            "severity": "red",\n'
    '            "present": true/false,\n'
    '            "explanation": "1-2 sentence explanation or null"\n'
    '        },\n'
    '        "riders": {\n'
    '            "severity": "caution",\n'
    '            "present": true/false,\n'
    '            "explanation": "1-2 sentence explanation or null"\n'
    '        },\n'
    '        "cross_referencing_obfuscation": {\n'
    '            "severity": "caution",\n'
    '            "present": true/false,\n'
    '            "explanation": "1-2 sentence explanation or null"\n'
    '        },\n'
    '        "internal_contradiction": {\n'
    '            "severity": "informational",\n'
    '            "present": true/false,\n'
    '            "explanation": "1-2 sentence explanation or null"\n'
    '        },\n'
    '        "sunset_clauses": {\n'
    '            "severity": "informational",\n'
    '            "present": true/false,\n'
    '            "explanation": "1-2 sentence explanation or null"\n'
    '        }\n'
    '    },\n'
    '    "categories": {\n'
    '        "Economy & Cost of Living": {\n'
    '            "direction": "Expand spending / stimulus OR Cut spending / austerity OR Not present",\n'
    '            "flagged": true/false\n'
    '        },\n'
    '        "Immigration & Border Security": {\n'
    '            "direction": "Expand pathways / access OR Restrict entry / tighten borders OR Not present",\n'
    '            "flagged": true/false\n'
    '        },\n'
    '        "Democracy & Governance": {\n'
    '            "direction": "Strengthen voting / institutions OR Restrict voting / reduce oversight OR Not present",\n'
    '            "flagged": true/false\n'
    '        },\n'
    '        "Housing & Affordability": {\n'
    '            "direction": "Expand housing access / funding OR Cut housing programs / deregulate OR Not present",\n'
    '            "flagged": true/false\n'
    '        },\n'
    '        "Healthcare": {\n'
    '            "direction": "Expand access / coverage OR Reduce / restrict access OR Not present",\n'
    '            "flagged": true/false\n'
    '        },\n'
    '        "Individual Rights & Civil Liberties": {\n'
    '            "direction": "Strengthen rights / protections OR Restrict rights / increase restrictions OR Not present",\n'
    '            "flagged": true/false\n'
    '        },\n'
    '        "Crime & Public Safety": {\n'
    '            "direction": "Expand rehabilitation / prevention OR Increase enforcement / penalties OR Not present",\n'
    '            "flagged": true/false\n'
    '        },\n'
    '        "Corruption & Government Accountability": {\n'
    '            "direction": "Increase transparency / oversight OR Reduce oversight / accountability OR Not present",\n'
    '            "flagged": true/false\n'
    '        },\n'
    '        "Social Programs & Safety Net": {\n'
    '            "direction": "Expand programs / benefits OR Cut / reduce programs OR Not present",\n'
    '            "flagged": true/false\n'
    '        },\n'
    '        "Environment & Energy": {\n'
    '            "direction": "Expand protections / clean energy OR Reduce protections / expand fossil fuels OR Not present",\n'
    '            "flagged": true/false\n'
    '        },\n'
    '        "Foreign Policy, War & National Security": {\n'
    '            "direction": "Diplomatic / reduce military spending OR Military expansion / increase defense spending OR Not present",\n'
    '            "flagged": true/false\n'
    '        }\n'
    '    },\n'
    '    "summary": "2-3 sentence plain language summary of what the bill actually does, no political framing"\n'
    "}\n\n"
    "Flag severity tiers:\n"
    "- red: corruption_or_reduced_oversight, restricts_individual_rights, "
    "misleading_title, obfuscation_by_verbosity\n"
    "- caution: riders, cross_referencing_obfuscation\n"
    "- informational: internal_contradiction, sunset_clauses\n\n"
    "A category is flagged if it falls under corruption_or_reduced_oversight "
    "or restricts_individual_rights.\n"
    "internal_contradiction should be flagged if the bill pulls in both "
    "directions within a single category.\n"
    "obfuscation_by_verbosity should be flagged if the bill's length and "
    "complexity appears disproportionate to what it actually does.\n"
    "riders should be flagged if unrelated provisions are attached to the bill.\n"
    "cross_referencing_obfuscation should be flagged if the bill relies heavily "
    "on references to other legislation without plain language explanation.\n"
    "sunset_clauses should be flagged if provisions expire quietly after a "
    "defined period without clear plain language notice.\n"
    "misleading_title should be flagged if the bill's title does not accurately "
    "represent its content.\n\n"
    "BILL TEXT:\n"
)