from typing import Dict
from pydantic import BaseModel
from typing import Literal, Dict, Any 

class MarkdownAnalysisRequest(BaseModel):
    """
    Input model for /analyze_markdown endpoint.

    Attributes:
        product (str): Product name ("TM" or "WST")
        markdown_text (str): Markdown string with one or more stitched files
    """
    markdown_text: str
    product: Literal["WST", "TM"]
    #auth: str  # Add this field


class SingleFileSummaryResponse(BaseModel):
    """
    Response model when only one file is present in the markdown.
    """
    Summary: str


class MultiFileAnalysisResponse(BaseModel):
    """
    Response model when multiple stitched files are present.

    Attributes:
        metrics (Dict): Structured metrics extracted from markdown
        report (str): Markdown report
        evaluation (Dict): LLM-generated evaluation
        brief_summary (str): Bullet list summary
    """
    metrics: Dict | None
    report: Dict[str, Any] | None
    evaluation: Dict | None
    brief_summary: str
    visualization_json: Dict[str, Any]
