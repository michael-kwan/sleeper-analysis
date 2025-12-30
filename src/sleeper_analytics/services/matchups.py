"""
Matchup Analysis Service

Provides matchup analysis, standings, and team performance metrics.
"""

from collections import defaultdict
from typing import Any

import numpy as np

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.models.awards import SeasonAwardsReport, WeeklyAward
from sleeper_analytics.models.matchup import (
    Matchup,
    MatchupTeam,
    Standing,
    TeamPerformance,
    WeeklyResult,
)


class MatchupService:
    """
    Service for analyzing matchups and team performance.

    Provides methods to:
    - Get weekly matchups with scores
    - Calculate league standings
    - Analyze team performance over time
    - Find close games and best/worst weeks
    """

    def __init__(self, client: SleeperClient, context: LeagueContext):
        self.client = client
        self.ctx = context

    async def get_weekly_matchups(self, week: int) -> list[Matchup]:
        """
        Get formatted matchups for a specific week.

        Args:
            week: Week number

        Returns:
            List of Matchup objects with both teams
        """
        raw_matchups = await self.client.get_matchups(self.ctx.league_id, week)

        # Group by matchup_id
        matchup_groups: dict[int, list[dict]] = defaultdict(list)
        for m in raw_matchups:
            matchup_id = m.get("matchup_id")
            if matchup_id is not None:
                matchup_groups[matchup_id].append(m)

        matchups = []
        for matchup_id, teams in matchup_groups.items():
            if len(teams) == 2:
                team1_data, team2_data = teams

                team1 = MatchupTeam(
                    roster_id=team1_data["roster_id"],
                    team_name=self.ctx.get_team_name(team1_data["roster_id"]),
                    points=team1_data.get("points") or 0,
                    starters=team1_data.get("starters") or [],
                    players=team1_data.get("players") or [],
                    players_points=team1_data.get("players_points") or {},
                )

                team2 = MatchupTeam(
                    roster_id=team2_data["roster_id"],
                    team_name=self.ctx.get_team_name(team2_data["roster_id"]),
                    points=team2_data.get("points") or 0,
                    starters=team2_data.get("starters") or [],
                    players=team2_data.get("players") or [],
                    players_points=team2_data.get("players_points") or {},
                )

                matchups.append(
                    Matchup(week=week, matchup_id=matchup_id, team1=team1, team2=team2)
                )

        return matchups

    async def get_season_matchups(
        self, start_week: int = 1, end_week: int = 17
    ) -> dict[int, list[Matchup]]:
        """
        Get all matchups for the season.

        Args:
            start_week: Starting week
            end_week: Ending week

        Returns:
            Dict mapping week number to list of Matchup objects
        """
        matchups_by_week = await self.client.get_matchups_range(
            self.ctx.league_id, start_week, end_week
        )

        result = {}
        for week, raw_matchups in matchups_by_week.items():
            # Group by matchup_id
            matchup_groups: dict[int, list[dict]] = defaultdict(list)
            for m in raw_matchups:
                matchup_id = m.get("matchup_id")
                if matchup_id is not None:
                    matchup_groups[matchup_id].append(m)

            week_matchups = []
            for matchup_id, teams in matchup_groups.items():
                if len(teams) == 2:
                    team1_data, team2_data = teams

                    team1 = MatchupTeam(
                        roster_id=team1_data["roster_id"],
                        team_name=self.ctx.get_team_name(team1_data["roster_id"]),
                        points=team1_data.get("points") or 0,
                        starters=team1_data.get("starters") or [],
                        players=team1_data.get("players") or [],
                        players_points=team1_data.get("players_points") or {},
                    )

                    team2 = MatchupTeam(
                        roster_id=team2_data["roster_id"],
                        team_name=self.ctx.get_team_name(team2_data["roster_id"]),
                        points=team2_data.get("points") or 0,
                        starters=team2_data.get("starters") or [],
                        players=team2_data.get("players") or [],
                        players_points=team2_data.get("players_points") or {},
                    )

                    week_matchups.append(
                        Matchup(week=week, matchup_id=matchup_id, team1=team1, team2=team2)
                    )

            result[week] = week_matchups

        return result

    async def get_team_performance(
        self, roster_id: int, weeks: int = 17
    ) -> TeamPerformance:
        """
        Analyze a team's performance across the season.

        Args:
            roster_id: Team's roster ID
            weeks: Number of weeks to analyze

        Returns:
            TeamPerformance object with detailed stats
        """
        season_matchups = await self.get_season_matchups(1, weeks)

        wins, losses, ties = 0, 0, 0
        total_points_for = 0.0
        total_points_against = 0.0
        weekly_points: list[float] = []
        weekly_results: list[WeeklyResult] = []

        for week in range(1, weeks + 1):
            matchups = season_matchups.get(week, [])

            for matchup in matchups:
                if matchup.team1.roster_id == roster_id:
                    my_points = matchup.team1.points
                    opp_points = matchup.team2.points
                    opponent = matchup.team2.team_name
                elif matchup.team2.roster_id == roster_id:
                    my_points = matchup.team2.points
                    opp_points = matchup.team1.points
                    opponent = matchup.team1.team_name
                else:
                    continue

                total_points_for += my_points
                total_points_against += opp_points
                weekly_points.append(my_points)

                if my_points > opp_points:
                    result = "W"
                    wins += 1
                elif my_points < opp_points:
                    result = "L"
                    losses += 1
                else:
                    result = "T"
                    ties += 1

                weekly_results.append(
                    WeeklyResult(
                        week=week,
                        points=my_points,
                        opponent=opponent,
                        opponent_points=opp_points,
                        result=result,
                    )
                )

        games = wins + losses + ties
        avg_points = total_points_for / games if games > 0 else 0
        consistency = float(np.std(weekly_points)) if len(weekly_points) > 1 else 0

        return TeamPerformance(
            roster_id=roster_id,
            team_name=self.ctx.get_team_name(roster_id),
            wins=wins,
            losses=losses,
            ties=ties,
            points_for=round(total_points_for, 2),
            points_against=round(total_points_against, 2),
            avg_points=round(avg_points, 2),
            consistency=round(consistency, 2),
            weekly_results=weekly_results,
        )

    async def get_league_standings(self, weeks: int = 17) -> list[Standing]:
        """
        Get league standings with detailed stats.

        Args:
            weeks: Number of weeks to consider

        Returns:
            List of Standing objects, sorted by rank
        """
        standings = []

        for roster in self.ctx.rosters:
            perf = await self.get_team_performance(roster.roster_id, weeks)
            standings.append(perf)

        # Sort by wins (desc), then points for (desc)
        standings.sort(key=lambda x: (x.wins, x.points_for), reverse=True)

        return [
            Standing(
                rank=i + 1,
                roster_id=perf.roster_id,
                team_name=perf.team_name,
                wins=perf.wins,
                losses=perf.losses,
                ties=perf.ties,
                points_for=perf.points_for,
                points_against=perf.points_against,
                win_pct=perf.win_pct,
                avg_points=perf.avg_points,
            )
            for i, perf in enumerate(standings)
        ]

    async def get_close_games(
        self, threshold: float = 10.0, weeks: int = 17
    ) -> list[dict[str, Any]]:
        """
        Find all close games (within threshold points).

        Args:
            threshold: Maximum point differential for close game
            weeks: Number of weeks to analyze

        Returns:
            List of close game dictionaries sorted by margin
        """
        season_matchups = await self.get_season_matchups(1, weeks)

        close_games = []
        for week, matchups in season_matchups.items():
            for matchup in matchups:
                if matchup.margin <= threshold:
                    close_games.append({
                        "week": week,
                        "team1": matchup.team1.team_name,
                        "team1_points": matchup.team1.points,
                        "team2": matchup.team2.team_name,
                        "team2_points": matchup.team2.points,
                        "margin": round(matchup.margin, 2),
                        "winner": matchup.winner.team_name if matchup.winner else "Tie",
                    })

        close_games.sort(key=lambda x: x["margin"])
        return close_games

    async def get_best_worst_weeks(
        self, roster_id: int, weeks: int = 17
    ) -> dict[str, WeeklyResult | None]:
        """
        Find a team's best and worst weekly performances.

        Args:
            roster_id: Team's roster ID
            weeks: Number of weeks to analyze

        Returns:
            Dict with best_week and worst_week
        """
        perf = await self.get_team_performance(roster_id, weeks)

        if not perf.weekly_results:
            return {"best_week": None, "worst_week": None}

        best = max(perf.weekly_results, key=lambda x: x.points)
        worst = min(perf.weekly_results, key=lambda x: x.points)

        return {"best_week": best, "worst_week": worst}

    async def get_head_to_head(
        self, roster_id_1: int, roster_id_2: int, weeks: int = 17
    ) -> dict[str, Any]:
        """
        Get head-to-head record between two teams.

        Args:
            roster_id_1: First team's roster ID
            roster_id_2: Second team's roster ID
            weeks: Number of weeks to analyze

        Returns:
            Head-to-head record and matchup history
        """
        season_matchups = await self.get_season_matchups(1, weeks)

        team1_name = self.ctx.get_team_name(roster_id_1)
        team2_name = self.ctx.get_team_name(roster_id_2)

        matchups_history = []
        team1_wins = 0
        team2_wins = 0
        ties = 0

        for week, matchups in season_matchups.items():
            for matchup in matchups:
                roster_ids = {matchup.team1.roster_id, matchup.team2.roster_id}
                if roster_id_1 in roster_ids and roster_id_2 in roster_ids:
                    if matchup.team1.roster_id == roster_id_1:
                        t1_pts = matchup.team1.points
                        t2_pts = matchup.team2.points
                    else:
                        t1_pts = matchup.team2.points
                        t2_pts = matchup.team1.points

                    if t1_pts > t2_pts:
                        team1_wins += 1
                        winner = team1_name
                    elif t2_pts > t1_pts:
                        team2_wins += 1
                        winner = team2_name
                    else:
                        ties += 1
                        winner = "Tie"

                    matchups_history.append({
                        "week": week,
                        f"{team1_name}_points": t1_pts,
                        f"{team2_name}_points": t2_pts,
                        "winner": winner,
                    })

        return {
            "team1": team1_name,
            "team2": team2_name,
            "team1_wins": team1_wins,
            "team2_wins": team2_wins,
            "ties": ties,
            "matchups": matchups_history,
        }

    async def get_weekly_high_low(self, week: int) -> WeeklyAward:
        """
        Find the highest and lowest scorers for a specific week.

        Args:
            week: Week number

        Returns:
            WeeklyAward with high and low scorers
        """
        matchups = await self.get_weekly_matchups(week)

        if not matchups:
            raise ValueError(f"No matchups found for week {week}")

        # Collect all team scores
        all_scores: list[tuple[int, str, float]] = []
        for matchup in matchups:
            all_scores.append((
                matchup.team1.roster_id,
                matchup.team1.team_name,
                matchup.team1.points
            ))
            all_scores.append((
                matchup.team2.roster_id,
                matchup.team2.team_name,
                matchup.team2.points
            ))

        # Sort by points
        all_scores.sort(key=lambda x: x[2])

        # Lowest scorer
        low_roster_id, low_team, low_score = all_scores[0]

        # Highest scorer
        high_roster_id, high_team, high_score = all_scores[-1]

        return WeeklyAward(
            week=week,
            high_scorer_roster_id=high_roster_id,
            high_scorer=high_team,
            high_score=high_score,
            low_scorer_roster_id=low_roster_id,
            low_scorer=low_team,
            low_score=low_score,
        )

    async def get_season_awards(self, weeks: int = 17) -> SeasonAwardsReport:
        """
        Get season-long awards summary with payout tracking.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            SeasonAwardsReport with all weekly awards and payout calculations
        """
        # Fetch all weekly awards concurrently
        import asyncio

        tasks = [self.get_weekly_high_low(week) for week in range(1, weeks + 1)]
        weekly_awards = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out any exceptions (weeks with no matchups)
        valid_awards = [
            award for award in weekly_awards
            if isinstance(award, WeeklyAward)
        ]

        # Count high and low score occurrences
        high_score_counts: dict[str, int] = {}
        low_score_counts: dict[str, int] = {}

        for award in valid_awards:
            high_score_counts[award.high_scorer] = (
                high_score_counts.get(award.high_scorer, 0) + 1
            )
            low_score_counts[award.low_scorer] = (
                low_score_counts.get(award.low_scorer, 0) + 1
            )

        # Calculate net payouts (high scorers get $5, low scorers pay $5)
        payout_by_team: dict[str, float] = {}

        for team_name in set(list(high_score_counts.keys()) + list(low_score_counts.keys())):
            high_count = high_score_counts.get(team_name, 0)
            low_count = low_score_counts.get(team_name, 0)
            net_payout = (high_count * 5.0) - (low_count * 5.0)
            payout_by_team[team_name] = net_payout

        return SeasonAwardsReport(
            league_id=self.ctx.league_id,
            league_name=self.ctx.league_name,
            weeks_analyzed=len(valid_awards),
            weekly_awards=valid_awards,
            high_score_leaders=high_score_counts,
            low_score_leaders=low_score_counts,
            total_payout_high=sum(high_score_counts.values()) * 5.0,
            total_payout_low=sum(low_score_counts.values()) * 5.0,
            payout_by_team=payout_by_team,
        )
