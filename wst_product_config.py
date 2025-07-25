import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from shared_state import shared_state
import re
import json
import logging


# Load environment variables
load_dotenv()

# Logging setup
logger = logging.getLogger(__name__)

# Initialize Azure LLM
llm = LLM(
    model=f"azure/{os.getenv('DEPLOYMENT_NAME')}",
    api_version=os.getenv("AZURE_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
    temperature=0.1,
    top_p=0.95,
)

def extract_json_from_output(raw_output: str) -> dict:
    """
    Extracts JSON from an LLM output, whether in a code block or loose format.
    Raises ValueError if no valid JSON found.
    """
    # Try to extract from ```json ... ``` block
    match = re.search(r"```json\s*(\{.*?\})\s*```", raw_output, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # Fallback: extract any {...} block
    match = re.search(r"(\{.*?\})", raw_output, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    raise ValueError("No valid JSON found in agent output")

def save_wst_metrics(output):
    # logger.info("🔎 RAW OUTPUT from Structurer Agent:\n" + output.raw)

    structured = extract_json_from_output(output.raw)

    # logger.info("📦 STRUCTURED JSON Parsed:\n" + json.dumps(structured, indent=2))

    # Step 2.2: Validate expected keys and values
    release_scope = structured.get("release_scope", {})
    required_scope_keys = ["Release Epics", "Release PIRs", "SFDC Defects Fixed"]

    for key in required_scope_keys:
        if key not in release_scope:
            logger.warning(f"🚨 MISSING KEY in release_scope: {key}")
            continue

        version_data = release_scope[key]
        if not isinstance(version_data, dict):
            logger.warning(f"⚠️ Unexpected format for {key}: {version_data}")
            continue

        for version, metrics in version_data.items():
            if not isinstance(metrics, dict):
                logger.warning(f"⚠️ Unexpected structure for {key} -> {version}: {metrics}")
                continue
            for metric_name, value in metrics.items():
                if value is None:
                    logger.warning(f"❌ NULL VALUE: {key} -> {version} -> {metric_name}")

    # Optional: Add similar validation for critical_metrics
    critical_metrics = structured.get("critical_metrics", {})
    for metric, version_data in critical_metrics.items():
        for version, fields in version_data.items():
            for field_name, value in fields.items():
                if value is None:
                    logger.warning(f"❌ NULL VALUE: {metric} -> {version} -> {field_name}")

    # Optional: Add validation for health_trends
    health_trends = structured.get("health_trends", {})
    for metric, details in health_trends.items():
        for field in ["Criteria", "Previous", "Current", "Status", "Summary"]:
            if field not in details or details[field] in [None, ""]:
                logger.warning(f"⚠️ Incomplete {metric}: Missing or empty '{field}'")

    # Final assignment to shared state
    shared_state.metrics = structured


def setup_crew_wst(extracted_text: str, versions: list):
    """
    Sets up CrewAI agents for WST analysis.
    Returns: (data_crew, report_crew, brief_summary_crew)
    """
    version_string = ", ".join(versions)

    # 1️⃣ Structuring Agent
    structurer = Agent(
        role="Data Architect",
        goal="Extract structured WST release metrics into canonical JSON format",
        backstory="Expert in parsing WST markdown release reports into structured JSON datasets",
        llm=llm,
        verbose=False,
        memory=True,
    )
    
    # logger.info("\n=========================MARKDOWN INPUT TO STRUCTURER====================================\n")
    # print(extracted_text)
    # logger.info("============================Testing ends here========================================\n")

    STRUCTURER_PROMPT = f"""
You are given extracted WST markdown release reports. Extract structured data into valid JSON.

Input markdown contains sections with:
1. Release scope tables (Epics, PIRs, SFDC defects)
2. Critical metrics tables
3. Qualitative risk metrics
4. Health trends

Extract exactly the following structured JSON:

{{
  "release_scope": {{
    "Target Customers": "<extract target customers>",
    "Release Epics": {{
      "<version>": {{
        "Total": <integer from Total column>,
        "Open": <integer from Open column>
      }}
    }},
    "Release PIRs": {{
      "<version>": {{
        "Total": <integer from Total column>,
        "Open": <integer from Open column>
      }}
    }},
    "SFDC Defects Fixed": {{
      "<version>": {{
        "ATLs Fixed": <integer from ATL column>,
        "BTLs Fixed": <integer from BTL column>
      }}
    }}
  }},
  "critical_metrics": {{
    "Delivery Against Requirements": {{
      "<version>": {{
        "Value": <percentage value>,
        "Status": "<risk status>"
      }}
    }},
    "System / Solution Test Metrics": {{
      "<version>": {{
        "Total": <integer>,
        "Open": <integer>,
        "Status": "<risk status>"
      }}
    }},
    "System / Solution Test Coverage": {{
      "<version>": {{
        "Value": <percentage>,
        "Status": "<risk status>"
      }}
    }},
    "System / Solution Test Pass Rate": {{
      "<version>": {{
        "Value": <percentage>,
        "Status": "<risk status>"
      }}
    }},
    "Security Test Metrics": {{
      "<version>": {{
        "Total": <integer>,
        "Open": <integer>,
        "Status": "<risk status>"
      }}
    }},
    "Performance / Load Test Metrics": {{
      "<version>": {{
        "Total": <integer>,
        "Open": <integer>,
        "Status": "<risk status>"
      }}
    }}
  }},
  "health_trends": {{
    "Unit Test Coverage": {{
      "<version>": {{
        "Criteria": "<criteria text>",
        "Previous": "<previous value>",
        "Current": "<current value>",
        "Status": "<status text>",
        "Summary": "<summary text>"
      }}
    }},
    "Automation Test Coverage": {{
      "<version>": {{
        "Criteria": "<criteria text>",
        "Previous": "<previous value>",
        "Current": "<current value>",
        "Status": "<status text>",
        "Summary": "<summary text>"
      }}
    }}
  }}
}}

SPECIFIC INSTRUCTIONS:
1. For tables, extract values from the correct columns
2. For qualitative metrics (like Delivery Against Requirements), extract the percentage and status
3. For health trends, extract all available fields per version
4. If a value is missing, set it to null (not 0)
5. Only use data that is explicitly shown in the input
6. Pay special attention to version numbers matching the data

Example of table extraction:
Input:
| Release Epics | Total | Open |
|---------------|-------|------|
| 45.1.15.0     | 11    | 0    |

Output:
"Release Epics": {{
  "45.1.15.0": {{
    "Total": 11,
    "Open": 0
  }}
}}

Input markdown:
{extracted_text}
"""



    structurer_task = Task(
    description=STRUCTURER_PROMPT,
    agent=structurer,
    async_execution=False,
    expected_output="Valid JSON",
    callback=save_wst_metrics
)

    data_crew = Crew(
        agents=[structurer],
        tasks=[structurer_task],
        process=Process.sequential,
        verbose=False 
    )

    # 2️⃣ Report Agent
    reporter = Agent(
        role="Technical Writer",
        goal="Write professional WST markdown reports",
        backstory="Expert at converting structured data into clean release documentation",
        llm=llm,
        verbose=False,
        memory=True,
    )

    REPORT_PROMPT = """
You are given structured WST release metrics and must return a structured report as valid JSON. Do not return markdown.

Use this exact structure in your output:
{
  "Overview": "<Mention the versions being analyzed> \\n<Short paragraph summarizing overall release quality and trends>",
  "Metrics Summary": {
    "release_scope_metrics": {
      "Release Epics": [
        { "version": "45.1.15.0", "total": 11, "open": 0, "trend": "↔" },
        { "version": "45.1.16.0", "total": 11, "open": 0, "trend": "↔" },
        { "version": "45.1.17.0", "total": 19, "open": 0, "trend": "↑" }
      ],
      "Release PIRs": [
        { "version": "45.1.15.0", "total": 0, "open": 0, "trend": "↔" },
        { "version": "45.1.16.0", "total": 93, "open": 0, "trend": "↑" },
        { "version": "45.1.17.0", "total": 108, "open": 0, "trend": "↑" }
      ],
      "SFDC DEFECTS FIXED (ATLs)": [
        { "version": "45.1.15.0", "value": 83, "trend": "↔" },
        { "version": "45.1.16.0", "value": 92, "trend": "↑" },
        { "version": "45.1.17.0", "value": 87, "trend": "↓" }
      ],
      "SFDC DEFECTS FIXED (BTLs)": [
        { "version": "45.1.15.0", "value": 26, "trend": "↔" },
        { "version": "45.1.16.0", "value": 30, "trend": "↑" },
        { "version": "45.1.17.0", "value": 22, "trend": "↓" }
      ]
    },
    "critical_metrics": {
      "System / Solution Test Metrics (ATL)": [
        { "version": "45.1.15.0", "total": 177, "open": 1, "risk_status": "-", "comments": "-", "trend": "↔" },
        { "version": "45.1.16.0", "total": 1017, "open": 2, "risk_status": "-", "comments": "-", "trend": "↑" },
        { "version": "45.1.17.0", "total": 1250, "open": 8, "risk_status": "-", "comments": "-", "trend": "↑" }
      ],
      "System / Solution Test Metrics (BTL)": [
        { "version": "45.1.15.0", "total": 110, "open": 0, "risk_status": "-", "comments": "-", "trend": "↔" },
        { "version": "45.1.16.0", "total": 110, "open": 0, "risk_status": "-", "comments": "-", "trend": "↔" },
        { "version": "45.1.17.0", "total": 110, "open": 0, "risk_status": "-", "comments": "-", "trend": "↔" }
      ],
      "Security Test Metrics (ATL)": [...],
      "Security Test Metrics (BTL)": [...],
      "Performance / Load Test Metrics (ATL)": [...],
      "Performance / Load Test Metrics (BTL)": [...]
    },
    "health_trends": [
      {
        "version": "<version>",
        "metric": "Unit Test Coverage",
        "criteria": "<criteria text>",
        "previous": "<previous value>",
        "current": "<current value>",
        "status": "<status text>",
        "summary": "<summary text>"
      },
      {
        "version": "<version>",
        "metric": "Automation Test Coverage",
        "criteria": "<criteria text>",
        "previous": "<previous value>",
        "current": "<current value>",
        "status": "<status text>",
        "summary": "<summary text>"
      }
    ]
  },
  "Key findings": "<Bullet points or brief paragraph identifying key risks or anomalies>",
  "Recommendations": "<Bullet points or brief paragraph suggesting corrective actions or improvements>"
}

Instructions:
- For "release_scope_metrics", output **two completely separate tables**:
  1. One for "Release Epics" (only Epics data)
  2. One for "Release PIRs" (only PIRs data)
- Do NOT combine Epics and PIRs into a single entry or table.
- Each entry must include: version, total, open, and trend.
- SFDC Defects (ATLs and BTLs) must be listed as individual series with trend.
- In critical_metrics:
  - Follow exactly the Functional Group names from the original markdown (e.g., "System / Solution Test Metrics", "Security Test Metrics")
  - Split each Functional Group into "(ATL)" and "(BTL)" based on the 'Type' column
  - Extract: version, total, open, risk_status, comments, and trend for each
  - Key names must follow the format: "<Functional Group> (ATL)" and "<Functional Group> (BTL)"
- For "health_trends":
  - Output one entry per metric **per version**.
  - Each entry must include: version, metric, criteria, previous, current, status, summary, and trend.
  - Compute `trend` across entries of the **same metric** in version order:
    - For the **first version**, always use `"↔"` (no comparison available)
    - For subsequent versions:
      - "↑" if current > previous
      - "↓" if current < previous
      - "↔" if unchanged
- Use the structured input values — do not combine multiple metrics into the same row.
- Avoid any markdown, bullet points, or explanatory text in the output — return pure JSON only.

Trend Calculation Rules:
- Compute "trend" as:
  - "↑" if the current value is higher than the previous
  - "↓" if the current value is lower than the previous
  - "↔" if unchanged
- If there are fewer than 2 valid (non-null) values across versions for a metric, set trend to "↔"
- Skip null values in comparisons — do not compute trends across nulls
- Do not invent or hallucinate any data
- All output must be strictly valid JSON only — no markdown or extra formatting
"""



    report_task = Task(
    description=REPORT_PROMPT,
    agent=reporter,
    context=[structurer_task],
    expected_output="Structured JSON report",
    callback=lambda output: shared_state.report_parts.update({
        "structured_report": extract_json_from_output(output.raw)
    })
)



    report_crew = Crew(
        agents=[reporter],
        tasks=[report_task],
        process=Process.sequential,
        verbose=False
    )

    # 3️⃣ Brief Summary Agent
    brief_writer = Agent(
        role="Executive Summary Writer",
        goal="Generate concise summary bullets",
        backstory="Expert at condensing metrics into crisp summaries",
        llm=llm,
        verbose=False,
        memory=True,
    )

    BRIEF_PROMPT = """
Generate a concise executive summary based strictly on the structured WST release metrics.

- Output exactly 3-5 bullet points.
- Start each bullet with '-'
- Separate each bullet with a \\n
- Use precise wording, no filler language.
- Absolutely no headers, intros, or conclusions.
- Use only the provided structured metrics.
- No hallucination or invented information.
"""

    brief_task = Task(
    description=BRIEF_PROMPT,
    agent=brief_writer,
    context=[structurer_task],
    expected_output="Bullet list",
    callback=lambda output: shared_state.report_parts.update({"brief_summary": output.raw})
)


    brief_summary_crew = Crew(
        agents=[brief_writer],
        tasks=[brief_task],
        process=Process.sequential,
        verbose=False
    )

    return data_crew, report_crew, brief_summary_crew
