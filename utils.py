# utils.py
import re
import os
from typing import Dict,List
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from app_logging import logger
import json
import re
from fastapi import HTTPException, Header, Body

load_dotenv()



# def sanitize_incoming_payload(payload: dict) -> dict:
#     """
#     Ensures the incoming payload is well-formed:
#     - Escapes control characters in markdown_text
#     - Validates required fields including Authorization
#     - Converts malformed inputs to usable format
#     """
#     if not isinstance(payload, dict):
#         raise HTTPException(status_code=400, detail="Payload must be a JSON object.")

#     # Updated to include Authorization
#     required_keys = {"markdown_text", "product", "auth"}
#     if not required_keys.issubset(payload.keys()):
#         raise HTTPException(status_code=400, detail=f"Missing required keys: {required_keys - payload.keys()}")

#     # Fix markdown_text issues
#     raw_markdown = payload.get("markdown_text")
#     if not isinstance(raw_markdown, str):
#         raise HTTPException(status_code=400, detail="`markdown_text` must be a string.")

#     # Escape problematic control characters
#     clean_markdown = raw_markdown.replace('\\', '\\\\')  # escape backslashes
#     clean_markdown = clean_markdown.replace('\t', '    ')  # tabs to spaces
#     clean_markdown = clean_markdown.replace('\r', '')  # remove carriage returns
#     clean_markdown = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', clean_markdown)
#     clean_markdown = re.sub(r'[\x00-\x1F\x7F]', '', clean_markdown)  # remove other control characters

#     # Validate product
#     product = payload.get("product", "").strip().upper()
#     if product not in {"WST", "TM"}:
#         raise HTTPException(status_code=400, detail="`product` must be 'WST' or 'TM'")

#     # Get and verify Authorization token exists (actual verification happens later)
#     auth_token = payload.get("auth")
#     if not isinstance(auth_token, str):
#         raise HTTPException(status_code=400, detail="`auth` must be a string")

#     return {
#         "markdown_text": clean_markdown,
#         "product": product,
#         "auth": auth_token  # Include in return dict
#     }
def sanitize_incoming_payload(payload: dict) -> dict:
    """
    Ensures the incoming payload is well-formed:
    - Escapes control characters in markdown_text
    - Validates required fields
    - Converts malformed inputs to usable format
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object.")

    required_keys = {"markdown_text", "product"}
    if not required_keys.issubset(payload.keys()):
        raise HTTPException(status_code=400, detail=f"Missing required keys: {required_keys - payload.keys()}")

    # Fix markdown_text issues
    raw_markdown = payload.get("markdown_text")
    if not isinstance(raw_markdown, str):
        raise HTTPException(status_code=400, detail="`markdown_text` must be a string.")

    # Escape problematic control characters
    clean_markdown = raw_markdown.replace('\\', '\\\\')  # escape backslashes
    clean_markdown = clean_markdown.replace('\t', '    ')  # tabs to spaces
    clean_markdown = clean_markdown.replace('\r', '')  # remove carriage returns
    clean_markdown = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', clean_markdown)
    clean_markdown = re.sub(r'[\x00-\x1F\x7F]', '', clean_markdown)  # remove other control characters

    # Validate product
    product = payload.get("product", "").strip().upper()
    if product not in {"WST", "TM"}:
        raise HTTPException(status_code=400, detail="`product` must be 'WST' or 'TM'")

    return {
        "markdown_text": clean_markdown,
        "product": product
    }


def extract_versions_wst(text):
    # Matches version numbers like 45.1.15.0 or 12.34.56.78
    version_pattern = r'\b\d{2}\.\d{1,2}\.\d{1,2}\.\d{1,2}\b'
    versions = re.findall(version_pattern, text)
    return sorted(set(versions))  # remove duplicates and sort


def split_joined_markdown_text(markdown_text: str) -> List[str]:
    """
    Splits stitched markdown using flexible 'End of Release Extract' markers with variable dashes.
    """
    pattern = r"[-=~*#]{2,}\s*End of Release Extract\s*[-=~*#]{2,}"
    parts = re.split(pattern, markdown_text)
    return [part.strip() for part in parts if part.strip()]



async def generate_single_file_summary(markdown_text: str, product: str) -> str:
    """
    Summarizes a single markdown string using Azure OpenAI.
    """
    llm = AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_API_VERSION"),
        azure_deployment=os.getenv("DEPLOYMENT_NAME"),
        temperature=0,
        max_tokens=1024,
        timeout=None
    )

    prompt = f"""
You are a release readiness analyst.

Summarize the following {product} release markdown into 4–5 bullet points:

---
{markdown_text}
---

Rules:
- Use only the content from the markdown.
- Output plain bullet points.
- Do not add headings, intros, or conclusions.
"""
    response = await llm.ainvoke(prompt)
    return response.content.strip()

def evaluate_with_llm_judge(source_text: str, generated_report: str) -> dict:
    judge_llm = AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_API_VERSION"),
        azure_deployment=os.getenv("DEPLOYMENT_NAME"),
        temperature=0,
        max_tokens=512,
        timeout=None,
    )
   
    prompt = f"""Act as an impartial judge evaluating report quality. You will be given:
1. ORIGINAL SOURCE TEXT (extracted from PDF)
2. GENERATED REPORT (created by AI)

Evaluate based on:
- Data accuracy (50% weight): Does the report correctly reflect the source data?
- Analysis depth (30% weight): Does it provide meaningful insights?
- Clarity (20% weight): Is the presentation clear and professional?

ORIGINAL SOURCE:
{source_text}

GENERATED REPORT:
{generated_report}

INSTRUCTIONS:
1. For each category, give a score (integer) out of its maximum:
    - Data accuracy: [0-50]
    - Analysis depth: [0-30]
    - Clarity: [0-20]
2. Add up to a TOTAL out of 100.
3. Give a brief 2-3 sentence evaluation.
4. Use EXACTLY this format:
Data accuracy: [0-50]
Analysis depth: [0-30]
Clarity: [0-20]
TOTAL: [0-100]
Evaluation: [your evaluation]

Your evaluation:"""

    try:
        response = judge_llm.invoke(prompt)
        response_text = response.content

        # Robust extraction: matches label anywhere on line, any case, extra spaces, "35/50" or "35"
        def extract_score(label, default=0):
            regex = re.compile(rf"{label}\s*:\s*(\d+)", re.IGNORECASE)
            for line in response_text.splitlines():
                match = regex.search(line)
                if match:
                    return int(match.group(1))
            return default

        data_accuracy = extract_score("Data accuracy", 0)
        analysis_depth = extract_score("Analysis depth", 0)
        clarity = extract_score("Clarity", 0)
        total = extract_score("TOTAL", data_accuracy + analysis_depth + clarity)

        # Extract evaluation: combine lines after "Evaluation:" or the last non-score line
        evaluation = ""
        eval_regex = re.compile(r"evaluation\s*:\s*(.*)", re.IGNORECASE)
        found_eval = False
        for line in response_text.splitlines():
            match = eval_regex.match(line)
            if match:
                evaluation = match.group(1).strip()
                found_eval = True
                break
        # If not found, fallback: concatenate all lines not containing a score label
        if not found_eval:
            non_score_lines = [
                l for l in response_text.splitlines()
                if not any(lbl in l.lower() for lbl in ["data accuracy", "analysis depth", "clarity", "total"])
            ]
            evaluation = " ".join(non_score_lines).strip()

        return {
            "data_accuracy": data_accuracy,
            "analysis_depth": analysis_depth,
            "clarity": clarity,
            "total": total,
            "text": evaluation
        }
    except Exception as e:
        logger.error(f"Error parsing judge response: {e}\nResponse was:\n{locals().get('response_text', '')}")
        return {
            "data_accuracy": 0,
            "analysis_depth": 0,
            "clarity": 0,
            "total": 0,
            "text": "Could not parse evaluation"
        }
    
# def verify_auth_token(auth_token: str = Body(..., alias="auth")):
#     """
#     Verify if the provided auth token matches the expected token.
#     Raise 401 Unauthorized if it doesn't match.
#     """
#     DEFAULT_AUTH_TOKEN="asdfghjkl123456788"
#     if auth_token != DEFAULT_AUTH_TOKEN:
#         raise HTTPException(status_code=401, detail="Invalid or missing auth token.")


from fastapi import Header

def verify_auth_token(authorization: str = Header(...)):
    expected = "asdfghjkl123456788"
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing Authorization header.")
    
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid token.")
