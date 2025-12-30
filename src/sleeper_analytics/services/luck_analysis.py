"""
Matchup Luck Analysis Service

Analyzes strength of schedule, lucky wins, and unlucky losses.
"""

import asyncio
import statistics
from typing import Any

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.models.luck import (
    LeagueLuckReport,
    LuckReport,
    StrengthOfSchedule,
    WeeklyLuckAnalysis,
)
from sleeper_analytics.services.matchups import MatchupService


class LuckAnalysisService:
    """
    Service for analyzing matchup luck and strength of schedule.

    Identifies teams that won/lost based on matchup luck rather than performance.
    """

    def __init__(self, client: SleeperClient, context: LeagueContext):
        self.client = client
        self.ctx = context
        self.matchup_service = MatchupService(client, context)

    async def analyze_weekly_luck(self, week: int) -> list[WeeklyLuckAnalysis]:
        """
        Analyze luck for all teams in a specific week.

        Args:
            week: Week number

        Returns:
            List of WeeklyLuckAnalysis for all teams
        """
        matchups = await self.matchup_service.get_weekly_matchups(week)

        # Collect all scores for this week
        all_scores: list[tuple[int, str, float, str]] = []  # (roster_id, team, points, result)
        matchup_results: dict[int, tuple[str, float, str]] = {}  # roster_id -> (result, opp_points, opp_name)

        for matchup in matchups:
            # Team 1
            all_scores.append((
                matchup.team1.roster_id,
                matchup.team1.team_name,
                matchup.team1.points,
                "W" if matchup.team1.points > matchup.team2.points else ("L" if matchup.team1.points < matchup.team2.points else "T")
            ))
            matchup_results[matchup.team1.roster_id] = (
                "W" if matchup.team1.points > matchup.team2.points else ("L" if matchup.team1.points < matchup.team2.points else "T"),
                matchup.team2.points,
                matchup.team2.team_name
            )

            # Team 2
            all_scores.append((
                matchup.team2.roster_id,
                matchup.team2.team_name,
                matchup.team2.points,
                "W" if matchup.team2.points > matchup.team1.points else ("L" if matchup.team2.points < matchup.team1.points else "T")
            ))
            matchup_results[matchup.team2.roster_id] = (
                "W" if matchup.team2.points > matchup.team1.points else ("L" if matchup.team2.points < matchup.team1.points else "T"),
                matchup.team1.points,
                matchup.team1.team_name
            )

        # Calculate median score
        scores_only = [s[2] for s in all_scores]
        league_median = statistics.median(scores_only)

        # Sort by points to get ranks
        sorted_scores = sorted(all_scores, key=lambda x: x[2], reverse=True)
        rank_map = {roster_id: rank + 1 for rank, (roster_id, _, _, _) in enumerate(sorted_scores)}

        # Analyze each team
        analyses: list[WeeklyLuckAnalysis] = []
        total_teams = len(all_scores)

        for roster_id, team_name, points, actual_result in all_scores:
            result_info, opp_points, opp_name = matchup_results[roster_id]

            # Count how many teams they'd beat if they played everyone
            wins_vs_all = sum(1 for _, _, opp_score, _ in all_scores if roster_id != _ and points > opp_score)

            expected_win_pct = wins_vs_all / (total_teams - 1) if total_teams > 1 else 0

            # Determine luck factor
            if actual_result == "T":
                luck_factor = "tie"
            elif actual_result == "W":
                if points < league_median:
                    luck_factor = "lucky_win"  # Won despite below-median score
                else:
                    luck_factor = "deserved_win"
            else:  # Loss
                if points > league_median:
                    luck_factor = "unlucky_loss"  # Lost despite above-median score
                else:
                    luck_factor = "deserved_loss"

            analyses.append(
                WeeklyLuckAnalysis(
                    week=week,
                    roster_id=roster_id,
                    team_name=team_name,
                    actual_result=actual_result,
                    points_scored=points,
                    opponent_points=opp_points,
                    opponent_name=opp_name,
                    league_median=league_median,
                    league_rank_this_week=rank_map[roster_id],
                    wins_vs_all=wins_vs_all,
                    expected_win_pct=round(expected_win_pct, 3),
                    luck_factor=luck_factor,
                )
            )

        return analyses

    async def calculate_strength_of_schedule(
        self, roster_id: int, weeks: int = 17
    ) -> StrengthOfSchedule:
        """
        Calculate strength of schedule for a team.

        Args:
            roster_id: Team's roster ID
            weeks: Number of weeks to analyze

        Returns:
            StrengthOfSchedule with metrics
        """
        season_matchups = await self.matchup_service.get_season_matchups(1, weeks)

        opponent_scores: list[float] = []
        opponent_ranks: list[int] = []
        week_difficulty: list[tuple[int, float]] = []  # (week, opp_score)

        for week, matchups in season_matchups.items():
            # Get all scores for this week to calculate ranks
            all_week_scores = []
            for m in matchups:
                all_week_scores.append((m.team1.roster_id, m.team1.points))
                all_week_scores.append((m.team2.roster_id, m.team2.points))

            # Sort to get ranks
            all_week_scores.sort(key=lambda x: x[1], reverse=True)
            rank_map = {rid: idx + 1 for idx, (rid, _) in enumerate(all_week_scores)}

            # Find this team's opponent
            for matchup in matchups:
                if matchup.team1.roster_id == roster_id:
                    opp_points = matchup.team2.points
                    opp_rank = rank_map.get(matchup.team2.roster_id, 99)
                    opponent_scores.append(opp_points)
                    opponent_ranks.append(opp_rank)
                    week_difficulty.append((week, opp_points))
                    break
                elif matchup.team2.roster_id == roster_id:
                    opp_points = matchup.team1.points
                    opp_rank = rank_map.get(matchup.team1.roster_id, 99)
                    opponent_scores.append(opp_points)
                    opponent_ranks.append(opp_rank)
                    week_difficulty.append((week, opp_points))
                    break

        # Calculate averages
        avg_opp_points = statistics.mean(opponent_scores) if opponent_scores else 0
        avg_opp_rank = statistics.mean(opponent_ranks) if opponent_ranks else 0

        # Find easiest and hardest weeks
        week_difficulty.sort(key=lambda x: x[1])
        easiest_weeks = [w for w, _ in week_difficulty[:3]]  # Bottom 3
        hardest_weeks = [w for w, _ in week_difficulty[-3:]]  # Top 3

        return StrengthOfSchedule(
            roster_id=roster_id,
            team_name=self.ctx.get_team_name(roster_id),
            avg_opponent_points=round(avg_opp_points, 2),
            avg_opponent_rank=round(avg_opp_rank, 2),
            toughest_schedule_rank=0,  # Will be set by league-wide comparison
            easiest_weeks=easiest_weeks,
            hardest_weeks=hardest_weeks,
            total_weeks=len(opponent_scores),
        )

    async def get_luck_report(self, roster_id: int, weeks: int = 17) -> LuckReport:
        """
        Get comprehensive luck report for a team.

        Args:
            roster_id: Team's roster ID
            weeks: Number of weeks to analyze

        Returns:
            LuckReport with all luck metrics
        """
        # Analyze all weeks concurrently
        tasks = [self.analyze_weekly_luck(week) for week in range(1, weeks + 1)]
        all_weekly_analyses = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and find this team's analyses
        team_weekly: list[WeeklyLuckAnalysis] = []
        for weekly in all_weekly_analyses:
            if isinstance(weekly, list):
                for analysis in weekly:
                    if analysis.roster_id == roster_id:
                        team_weekly.append(analysis)

        # Calculate actual record
        actual_wins = sum(1 for w in team_weekly if w.actual_result == "W")
        actual_losses = sum(1 for w in team_weekly if w.actual_result == "L")
        actual_ties = sum(1 for w in team_weekly if w.actual_result == "T")

        # Calculate expected wins (based on median)
        expected_wins = sum(
            1 for w in team_weekly if w.points_scored > w.league_median
        )

        # Find lucky wins and unlucky losses
        lucky_wins = [w for w in team_weekly if w.luck_factor == "lucky_win"]
        unlucky_losses = [w for w in team_weekly if w.luck_factor == "unlucky_loss"]

        # Calculate luck score
        luck_score = actual_wins - expected_wins

        # Get strength of schedule
        sos = await self.calculate_strength_of_schedule(roster_id, weeks)

        return LuckReport(
            roster_id=roster_id,
            team_name=self.ctx.get_team_name(roster_id),
            actual_wins=actual_wins,
            actual_losses=actual_losses,
            actual_ties=actual_ties,
            actual_record=f"{actual_wins}-{actual_losses}-{actual_ties}",
            expected_wins=float(expected_wins),
            expected_record=f"{expected_wins}-{weeks - expected_wins - actual_ties}-{actual_ties}",
            luck_score=float(luck_score),
            lucky_wins=lucky_wins,
            unlucky_losses=unlucky_losses,
            strength_of_schedule=sos,
        )

    async def get_league_luck_report(
        self, weeks: int = 17
    ) -> LeagueLuckReport:
        """
        Get league-wide luck analysis.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            LeagueLuckReport with all teams
        """
        # Get luck reports for all teams
        tasks = [
            self.get_luck_report(roster.roster_id, weeks)
            for roster in self.ctx.rosters
        ]
        team_reports = await asyncio.gather(*tasks)

        # Calculate SOS ranks
        sos_list = [(r.roster_id, r.strength_of_schedule.avg_opponent_points) for r in team_reports]
        sos_list.sort(key=lambda x: x[1], reverse=True)  # Highest avg = toughest
        sos_rank_map = {roster_id: rank + 1 for rank, (roster_id, _) in enumerate(sos_list)}

        # Update SOS ranks
        for report in team_reports:
            report.strength_of_schedule.toughest_schedule_rank = sos_rank_map[report.roster_id]

        # Find luckiest and unluckiest teams
        luckiest = max(team_reports, key=lambda x: x.luck_score)
        unluckiest = min(team_reports, key=lambda x: x.luck_score)

        return LeagueLuckReport(
            league_id=self.ctx.league_id,
            league_name=self.ctx.league_name,
            weeks_analyzed=weeks,
            team_reports=team_reports,
            luckiest_team=luckiest.team_name,
            unluckiest_team=unluckiest.team_name,
            luckiest_score=luckiest.luck_score,
            unluckiest_score=unluckiest.luck_score,
        )
