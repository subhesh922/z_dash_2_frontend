from fastapi import FastAPI, Depends, Body
from fastapi import APIRouter, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.openapi.utils import get_openapi
from fastapi import Depends, FastAPI, HTTPException, status, Security
from pydantic import ValidationError
from models import MarkdownAnalysisRequest, SingleFileSummaryResponse, MultiFileAnalysisResponse
from visualization import visualize
from wst__markdown_processor import Wst_MarkdownExtractor,Wst_MarkdownHarmonizer
from wst_product_config import setup_crew_wst
from shared_state import shared_state
import time
import asyncio 
from utils import (
    split_joined_markdown_text,
    extract_versions_wst,
    generate_single_file_summary,
    evaluate_with_llm_judge,
    sanitize_incoming_payload,
    verify_auth_token
)
from app_logging import logger
import json

app = FastAPI()

bearer_scheme = HTTPBearer()


# Allow frontend calls (if re-enabled in future)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# @app.post("/analyze_markdown")
# async def analyze_markdown(request: MarkdownAnalysisRequest,auth=Body(verify_auth_token)):
# @app.post("/analyze_markdown")
# async def analyze_markdown(
#     request: MarkdownAnalysisRequest):
#     verify_auth_token(request.auth)  # Added explicit verification
# @app.post("/analyze_markdown")
# async def analyze_markdown(
#     request: MarkdownAnalysisRequest,
#     _=Depends(verify_auth_token)
#     ):
@app.post("/analyze_markdown")
async def analyze_markdown(
    request: MarkdownAnalysisRequest,
    token: str = Security(bearer_scheme)
):
    
    # ✅ Step 0A: Check token
    if token.credentials != "asdfghjkl123456788":
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        # Step 0: Sanitize payload
        sanitized_input = sanitize_incoming_payload(request.dict())
        markdown_text = sanitized_input["markdown_text"]
        product = sanitized_input["product"].upper()

        # Step 1: Extract versions from the markdown text
        versions = extract_versions_wst(markdown_text)

        # Step 2: Split stitched markdown into parts
        split_parts = split_joined_markdown_text(markdown_text)

        # Step 3: Handle single release summary
        if "End of Release Extract" not in markdown_text:
            summary = await generate_single_file_summary(markdown_text, product)
            return MultiFileAnalysisResponse(
            metrics=None,
            report=None,
            evaluation=None,
            brief_summary=summary
        )

        # Step 4: Extract each chunk using Wst_MarkdownExtractor
        version_to_extracted_md = {}
        for version, chunk in zip(versions, split_parts):
            try:
                extractor = Wst_MarkdownExtractor(chunk)
                extracted_md = extractor.extract()
                version_to_extracted_md[version] = extracted_md
            except Exception as e:
                logger.error(f"Extractor failed for version {version}: {e}")
                raise HTTPException(status_code=500, detail=f"Extractor failed for version {version}")

        # Step 5: Harmonize extracted markdowns
        harmonizer = Wst_MarkdownHarmonizer()
        harmonized_text = harmonizer.harmonize(version_to_extracted_md)
        logger.info("============= Final Harmonized Markdown =============")
        logger.info(harmonized_text[:1000])  # Truncated log for preview

        # Step 6: Route to crew setup
        if product == "WST":
            data_crew, report_crew, brief_crew, viz_crew = setup_crew_wst(harmonized_text, versions)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported product type: {product}")

        # Step 7: Run Data Crew first
        data_crew.kickoff()

        # Step 8: Run Report and Brief Crews in parallel
        report_crew.kickoff()
        brief_crew.kickoff()
        viz_crew.kickoff()

        # Step 9: Evaluate generated report
        evaluation_result = evaluate_with_llm_judge(
            source_text=harmonized_text,
            generated_report=json.dumps(shared_state.report_parts.get("structured_report", {}), indent=2)
        )

        # Step 10: Generate visualization data
        # visualization_json = visualize(shared_state.metrics)
        visualization_json = shared_state.visualization_json

        # Step 11: Return structured response
        return MultiFileAnalysisResponse(
            metrics=shared_state.metrics,
            report=shared_state.report_parts.get("structured_report", {}),
            evaluation=evaluation_result,
            brief_summary=shared_state.report_parts.get("brief_summary", ""),
            visualization_json=json.loads(visualization_json)
        )

    except ValidationError as ve:
        logger.error(f"Validation Error: {ve}")
        raise HTTPException(status_code=422, detail="Invalid request schema.")
    except Exception as e:
        logger.exception("Unexpected error during markdown analysis.")
        raise HTTPException(status_code=500, detail=str(e))

