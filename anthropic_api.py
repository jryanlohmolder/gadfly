import os
import requests

from dotenv import load_dotenv

load_dotenv()

# Constants
PARSE_BILL_PROMPT = (
    "You are a nonpartisan bill analysis tool. Analyze the bill text provided "
    "and return only valid JSON — no preamble, no markdown, no code fences.\n\n"
    "Return the following structure exactly:\n\n"
    "{\n"
    '    "flags": {\n'
    '        "corruption_or_reduced_oversight": '
    '{"present": true/false, "explanation": "1-2 sentence explanation or null"},\n'
    '        "restricts_individual_rights": '
    '{"present": true/false, "explanation": "1-2 sentence explanation or null"},\n'
    '        "misleading_title": '
    '{"present": true/false, "explanation": "1-2 sentence explanation or null"},\n'
    '        "internal_contradiction": '
    '{"present": true/false, "explanation": "1-2 sentence explanation or null"}\n'
    "    },\n"
    '    "categories": {\n'
    '        "Economy & Cost of Living": '
    '{"direction": "Expand spending / stimulus OR Cut spending / austerity OR Not present", "flagged": true/false},\n'
    '        "Immigration & Border Security": '
    '{"direction": "Expand pathways / access OR Restrict entry / tighten borders OR Not present", "flagged": true/false},\n'
    '        "Democracy & Governance": '
    '{"direction": "Strengthen voting / institutions OR Restrict voting / reduce oversight OR Not present", "flagged": true/false},\n'
    '        "Housing & Affordability": '
    '{"direction": "Expand housing access / funding OR Cut housing programs / deregulate OR Not present", "flagged": true/false},\n'
    '        "Healthcare": '
    '{"direction": "Expand access / coverage OR Reduce / restrict access OR Not present", "flagged": true/false},\n'
    '        "Individual Rights & Civil Liberties": '
    '{"direction": "Strengthen rights / protections OR Restrict rights / increase restrictions OR Not present", "flagged": true/false},\n'
    '        "Crime & Public Safety": '
    '{"direction": "Expand rehabilitation / prevention OR Increase enforcement / penalties OR Not present", "flagged": true/false},\n'
    '        "Corruption & Government Accountability": '
    '{"direction": "Increase transparency / oversight OR Reduce oversight / accountability OR Not present", "flagged": true/false},\n'
    '        "Social Programs & Safety Net": '
    '{"direction": "Expand programs / benefits OR Cut / reduce programs OR Not present", "flagged": true/false},\n'
    '        "Environment & Energy": '
    '{"direction": "Expand protections / clean energy OR Reduce protections / expand fossil fuels OR Not present", "flagged": true/false},\n'
    '        "Foreign Policy, War & National Security": '
    '{"direction": "Diplomatic / reduce military spending OR Military expansion / increase defense spending OR Not present", "flagged": true/false}\n'
    "    },\n"
    '    "summary": "2-3 sentence plain language summary of what the bill actually does, no political framing"\n'
    "}\n\n"
    "A category is flagged if it falls under corruption_or_reduced_oversight or "
    "restricts_individual_rights. internal_contradiction should be flagged if the "
    "bill pulls in both directions within a single category.\n\n"
    "BILL TEXT:\n"
)