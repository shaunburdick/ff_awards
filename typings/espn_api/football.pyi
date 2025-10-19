# Type stubs for espn_api.football
# Based on actual ESPN API object inspection from debug logging

from __future__ import annotations

from typing import Any

class League:
    def __init__(
        self,
        league_id: int,
        year: int,
        espn_s2: str | None = None,
        swid: str | None = None,
        debug: bool = False,
    ) -> None: ...

    # Direct attributes (not properties)
    league_id: int
    year: int
    teams: list[Team]
    settings: Settings
    current_week: int
    currentMatchupPeriod: int
    scoringPeriodId: int
    firstScoringPeriod: int
    finalScoringPeriod: int
    previousSeasons: list[Any]
    nfl_week: int
    members: list[dict[str, Any]]
    draft: list[Any]
    player_map: dict[Any, Any]
    espn_request: Any
    logger: Any

    def box_scores(self, week: int) -> list[BoxScore]: ...

class Team:
    def __init__(self) -> None: ...

    # Direct attributes (not properties)
    team_id: int
    team_name: str
    team_abbrev: str
    division_id: int
    division_name: str
    owners: list[dict[str, Any]]
    wins: int
    losses: int
    ties: int
    points_for: float
    points_against: float
    scores: list[float]
    outcomes: list[str]
    mov: list[float]  # margin of victory
    acquisitions: int
    acquisition_budget_spent: int
    drops: int
    trades: int
    move_to_ir: int
    playoff_pct: float
    draft_projected_rank: int
    streak_length: int
    streak_type: str
    standing: int
    final_standing: int
    waiver_rank: int
    logo_url: str
    roster: list[Any]
    schedule: list[Team]
    stats: dict[str, float]

    def get_player_name(self, *args: Any) -> str: ...

class BoxScore:
    def __init__(self) -> None: ...

    # Direct attributes (not properties)
    matchup_type: str
    is_playoff: bool
    home_team: Team
    away_team: Team
    home_score: float
    away_score: float
    home_projected: float
    away_projected: float
    home_lineup: list[Any]
    away_lineup: list[Any]

class Settings:
    def __init__(self) -> None: ...

    # Direct attributes (not properties)
    name: str
    reg_season_count: int
    matchup_periods: dict[str, list[int]]
    veto_votes_required: int
    team_count: int
    playoff_team_count: int
    keeper_count: int
    trade_deadline: int
    division_map: dict[int, str]
    tie_rule: str
    playoff_tie_rule: str
    playoff_matchup_period_length: int
    playoff_seed_tie_rule: str
    scoring_type: str
    faab: bool
    acquisition_budget: int
    scoring_format: list[dict[str, Any]]
    position_slot_counts: dict[str, int]
