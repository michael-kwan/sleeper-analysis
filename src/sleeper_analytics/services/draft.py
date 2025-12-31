"""
Draft Analysis Service

Analyzes draft performance and identifies best/worst picks.
"""

from collections import defaultdict

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.models.draft import (
    DraftAnalysisReport,
    DraftPick,
    RoundSummary,
    TeamDraftGrade,
)


class DraftAnalysisService:
    """
    Service for analyzing draft performance.

    Evaluates draft picks based on points scored and roster retention.
    """

    def __init__(self, client: SleeperClient, context: LeagueContext):
        self.client = client
        self.ctx = context

    async def _get_player_points_by_week(
        self, player_id: str, weeks: int = 17
    ) -> dict[int, float]:
        """Get points scored by a player each week."""
        matchups_by_week = await self.client.get_matchups_range(
            self.ctx.league_id, 1, weeks
        )

        points_by_week: dict[int, float] = {}

        for week, matchups in matchups_by_week.items():
            for matchup in matchups:
                players_points = matchup.get("players_points", {})
                if player_id in players_points:
                    points_by_week[week] = float(players_points[player_id])
                    break

        return points_by_week

    def _calculate_value_rating(
        self, points: float, round_num: int, avg_round_points: float
    ) -> str:
        """Classify pick as Hit/Solid/Bust."""
        # Early rounds (1-4) held to higher standard
        if round_num <= 4:
            if points >= avg_round_points * 1.5:
                return "Hit"
            elif points >= avg_round_points * 0.7:
                return "Solid"
            else:
                return "Bust"
        # Later rounds (5+)
        else:
            if points >= avg_round_points * 1.3:
                return "Hit"
            elif points >= avg_round_points * 0.5:
                return "Solid"
            else:
                return "Bust"

    def _calculate_draft_grade(self, avg_points_per_pick: float, league_avg: float) -> str:
        """Calculate letter grade based on performance vs league average."""
        ratio = avg_points_per_pick / league_avg if league_avg > 0 else 1.0

        if ratio >= 1.40:
            return "A+"
        elif ratio >= 1.25:
            return "A"
        elif ratio >= 1.15:
            return "B+"
        elif ratio >= 1.05:
            return "B"
        elif ratio >= 0.95:
            return "C+"
        elif ratio >= 0.85:
            return "C"
        elif ratio >= 0.75:
            return "D"
        else:
            return "F"

    async def analyze_draft(self, weeks: int = 17) -> DraftAnalysisReport:
        """
        Analyze draft performance for the league.

        Args:
            weeks: Number of weeks to analyze for points

        Returns:
            DraftAnalysisReport with complete analysis
        """
        # Get draft data
        drafts = await self.client.get_drafts(self.ctx.league_id)

        if not drafts:
            raise ValueError(f"No drafts found for league {self.ctx.league_id}")

        # Get the most recent draft (usually index 0)
        draft = drafts[0]
        draft_id = draft.get("draft_id")

        if not draft_id:
            raise ValueError("Draft ID not found")

        # Get all draft picks
        draft_picks_raw = await self.client.get_draft_picks(draft_id)

        if not draft_picks_raw:
            raise ValueError(f"No draft picks found for draft {draft_id}")

        # Process each pick
        all_picks: list[DraftPick] = []

        for pick_data in draft_picks_raw:
            pick_number = pick_data.get("pick_no", 0)
            round_num = pick_data.get("round", 0)
            pick_in_round = pick_data.get("draft_slot", 0)
            roster_id = pick_data.get("roster_id")
            player_id = pick_data.get("player_id")

            if not all([roster_id, player_id]):
                continue

            # Get player points
            points_by_week = await self._get_player_points_by_week(player_id, weeks)
            total_points = sum(points_by_week.values())
            games_played = len([p for p in points_by_week.values() if p > 0])
            ppg = total_points / games_played if games_played > 0 else 0

            # Check if still on roster
            current_roster = next(
                (r for r in self.ctx.rosters if r.roster_id == roster_id), None
            )
            is_on_roster = (
                current_roster and player_id in current_roster.players
                if current_roster
                else False
            )

            team_name = self.ctx.get_team_name(roster_id)
            player_name = self.ctx.get_player_name(player_id)
            position = self.ctx.get_player_position(player_id)

            all_picks.append(
                DraftPick(
                    pick_number=pick_number,
                    round=round_num,
                    pick_in_round=pick_in_round,
                    roster_id=roster_id,
                    team_name=team_name,
                    player_id=player_id,
                    player_name=player_name,
                    position=position,
                    points_scored=round(total_points, 2),
                    games_played=games_played,
                    points_per_game=round(ppg, 2),
                    is_on_roster=is_on_roster,
                    value_rating="Pending",  # Will calculate after round averages
                )
            )

        # Calculate round averages for value ratings
        rounds_dict: dict[int, list[DraftPick]] = defaultdict(list)
        for pick in all_picks:
            rounds_dict[pick.round].append(pick)

        round_avgs = {
            round_num: sum(p.points_scored for p in picks) / len(picks)
            for round_num, picks in rounds_dict.items()
        }

        # Update value ratings
        for pick in all_picks:
            avg_for_round = round_avgs.get(pick.round, 0)
            pick.value_rating = self._calculate_value_rating(
                pick.points_scored, pick.round, avg_for_round
            )

        # Create round summaries
        round_summaries: list[RoundSummary] = []
        total_rounds = max(p.round for p in all_picks)

        for round_num in range(1, total_rounds + 1):
            round_picks = rounds_dict[round_num]
            avg_points = round_avgs[round_num]

            best_pick = max(round_picks, key=lambda p: p.points_scored)
            worst_pick = min(round_picks, key=lambda p: p.points_scored)

            hits = len([p for p in round_picks if p.value_rating == "Hit"])
            hit_rate = (hits / len(round_picks) * 100) if round_picks else 0

            round_summaries.append(
                RoundSummary(
                    round_number=round_num,
                    total_picks=len(round_picks),
                    avg_points=round(avg_points, 2),
                    best_pick=best_pick,
                    worst_pick=worst_pick,
                    hit_rate=round(hit_rate, 1),
                )
            )

        # Create team grades
        teams_dict: dict[int, list[DraftPick]] = defaultdict(list)
        for pick in all_picks:
            teams_dict[pick.roster_id].append(pick)

        team_grades: list[TeamDraftGrade] = []

        for roster_id, team_picks in teams_dict.items():
            total_points = sum(p.points_scored for p in team_picks)
            avg_ppick = total_points / len(team_picks) if team_picks else 0

            best_pick = max(team_picks, key=lambda p: p.points_scored)
            worst_pick = min(team_picks, key=lambda p: p.points_scored)

            # Hit rate: picks that are still on roster or had good production
            hits = len([p for p in team_picks if p.is_on_roster or p.value_rating == "Hit"])
            hit_rate = (hits / len(team_picks) * 100) if team_picks else 0

            team_grades.append(
                TeamDraftGrade(
                    roster_id=roster_id,
                    team_name=self.ctx.get_team_name(roster_id),
                    total_picks=len(team_picks),
                    total_points=round(total_points, 2),
                    avg_points_per_pick=round(avg_ppick, 2),
                    best_pick=best_pick,
                    worst_pick=worst_pick,
                    hit_rate=round(hit_rate, 1),
                    draft_grade="Pending",
                    picks=sorted(team_picks, key=lambda p: p.pick_number),
                )
            )

        # Calculate league average
        league_avg_ppick = sum(p.points_scored for p in all_picks) / len(all_picks)

        # Assign grades
        for team_grade in team_grades:
            team_grade.draft_grade = self._calculate_draft_grade(
                team_grade.avg_points_per_pick, league_avg_ppick
            )

        # Sort teams by avg points per pick
        team_grades.sort(key=lambda t: t.avg_points_per_pick, reverse=True)

        # Identify best/worst drafters
        best_drafter = team_grades[0]
        worst_drafter = team_grades[-1]

        # Best overall pick and biggest bust
        best_overall_pick = max(all_picks, key=lambda p: p.points_scored)
        biggest_bust = min(
            [p for p in all_picks if p.round <= 3],  # Only consider first 3 rounds for bust
            key=lambda p: p.points_scored,
            default=None,
        )

        # League hit rate
        total_hits = len([p for p in all_picks if p.value_rating == "Hit"])
        league_hit_rate = (total_hits / len(all_picks) * 100) if all_picks else 0

        return DraftAnalysisReport(
            league_id=self.ctx.league_id,
            league_name=self.ctx.league_name,
            draft_id=draft_id,
            total_rounds=total_rounds,
            total_picks=len(all_picks),
            weeks_analyzed=weeks,
            team_grades=team_grades,
            round_summaries=round_summaries,
            best_drafter=best_drafter.team_name,
            best_drafter_avg_ppick=best_drafter.avg_points_per_pick,
            worst_drafter=worst_drafter.team_name,
            worst_drafter_avg_ppick=worst_drafter.avg_points_per_pick,
            best_overall_pick=best_overall_pick,
            biggest_bust=biggest_bust,
            league_avg_points_per_pick=round(league_avg_ppick, 2),
            league_hit_rate=round(league_hit_rate, 1),
        )
