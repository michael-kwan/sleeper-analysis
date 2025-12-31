"""
Draft Analysis API Routes

Endpoints for analyzing draft performance.
"""

from fastapi import APIRouter

from sleeper_analytics.api.dependencies import LeagueContextDep, SleeperClientDep, WeeksQuery
from sleeper_analytics.models.draft import DraftAnalysisReport
from sleeper_analytics.services.draft import DraftAnalysisService

router = APIRouter()


@router.get(
    "/{league_id}/analysis",
    response_model=DraftAnalysisReport,
    summary="Get draft analysis",
    description="Analyze draft performance with grades, best/worst picks, and round summaries.",
)
async def get_draft_analysis(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    weeks: WeeksQuery = 17,
) -> DraftAnalysisReport:
    """Get complete draft analysis for the league."""
    service = DraftAnalysisService(client, ctx)
    return await service.analyze_draft(weeks)
