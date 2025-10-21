# Type stubs for espn_api.football
# Based on actual ESPN API source code analysis

from __future__ import annotations

from datetime import datetime
from logging import Logger
from typing import Any, TypedDict

# Type definitions for API structures
class NotificationSetting(TypedDict):
    """ESPN notification setting structure from API."""

    enabled: bool
    id: str
    type: str

class Owner(TypedDict):
    """ESPN owner structure from API."""

    displayName: str
    firstName: str
    lastName: str
    id: str
    notificationSettings: list[NotificationSetting]

class BasePick:
    """ESPN draft pick object."""
    def __init__(self) -> None: ...

    # Attributes
    bid_amount: int
    keeper_status: bool
    nominatingTeam: Team | None
    playerId: int
    playerName: str
    round_num: int
    round_pick: int
    team: Team

    # Methods
    def auction_repr(self) -> str: ...

class Player:
    """ESPN player object."""
    def __init__(
        self, data: dict[str, Any], year: int, pro_team_schedule: dict[str, Any] | None = None
    ) -> None: ...

    # Core attributes
    name: str
    playerId: int
    posRank: int
    eligibleSlots: list[str]
    acquisitionType: str
    proTeam: str
    injuryStatus: str
    onTeamId: int
    lineupSlot: str
    position: str
    injured: bool
    percent_owned: float
    percent_started: float
    active_status: str
    total_points: float
    projected_total_points: float
    avg_points: float
    projected_avg_points: float

    # Complex attributes
    stats: dict[int, dict[str, Any]]  # Week -> stats
    schedule: dict[str, dict[str, Any]]  # Week -> game info

    def __repr__(self) -> str: ...

class BoxPlayer(Player):
    """Player with extra data from a matchup."""
    def __init__(
        self,
        data: dict[str, Any],
        pro_schedule: dict[str, Any],
        positional_rankings: dict[str, Any],
        week: int,
        year: int,
    ) -> None: ...

    # Additional attributes specific to BoxPlayer
    slot_position: str
    pro_opponent: str
    pro_pos_rank: int
    game_played: int
    on_bye_week: bool
    game_date: datetime
    points: float
    points_breakdown: dict[str, Any]
    projected_points: float
    projected_breakdown: dict[str, Any]

    def __repr__(self) -> str: ...

class EspnFantasyRequests:
    """ESPN API request handler."""
    def __init__(
        self,
        sport: str,
        year: int,
        league_id: int,
        cookies: dict[str, str] | None = None,
        logger: Logger | None = None,
    ) -> None: ...

    # Attributes
    ENDPOINT: str
    LEAGUE_ENDPOINT: str
    NEWS_ENDPOINT: str
    cookies: dict[str, str] | None
    league_id: int
    logger: Logger
    year: int

    # Methods
    def checkRequestStatus(self) -> Any: ...
    def get(self) -> Any: ...
    def get_league(self) -> dict[str, Any]: ...
    def get_league_draft(self) -> dict[str, Any]: ...
    def get_league_message_board(self, msg_types: list[str] | None = None) -> dict[str, Any]: ...
    def get_player_card(self, player_ids: list[int], scoring_period: int) -> dict[str, Any]: ...
    def get_player_news(self) -> Any: ...
    def get_pro_players(self) -> Any: ...
    def get_pro_schedule(self) -> Any: ...
    def league_get(
        self,
        extend: str = "",
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]: ...
    def news_get(self) -> Any: ...

class League:
    """ESPN Fantasy Football League."""
    def __init__(
        self,
        league_id: int,
        year: int,
        espn_s2: str | None = None,
        swid: str | None = None,
        fetch_league: bool = True,
        debug: bool = False,
    ) -> None: ...

    # Direct attributes
    league_id: int
    year: int
    teams: list[Team]
    settings: Settings
    current_week: int
    currentMatchupPeriod: int
    scoringPeriodId: int
    firstScoringPeriod: int
    finalScoringPeriod: int
    previousSeasons: list[int]
    nfl_week: int
    members: list[dict[str, Any]]
    draft: list[BasePick]
    player_map: dict[str, int]  # Player name -> ID
    espn_request: EspnFantasyRequests
    logger: Logger

    # Core methods
    def fetch_league(self) -> None: ...
    def refresh(self) -> None: ...
    def refresh_draft(
        self, refresh_players: bool = False, refresh__teams: bool = False
    ) -> None: ...
    def load_roster_week(self, week: int) -> None: ...

    # Standings and rankings
    def standings(self) -> list[Team]: ...
    def standings_weekly(self, week: int) -> list[Team]: ...
    def power_rankings(self, week: int | None = None) -> list[tuple[Team, float]]: ...

    # Team stats
    def top_scorer(self) -> Team: ...
    def least_scorer(self) -> Team: ...
    def most_points_against(self) -> Team: ...
    def top_scored_week(self) -> tuple[Team, float]: ...
    def least_scored_week(self) -> tuple[Team, float]: ...

    # Matchups and scores
    def box_scores(self, week: int | None = None) -> list[BoxScore]: ...
    def scoreboard(self, week: int | None = None) -> list[Matchup]: ...

    # Players and free agents
    def free_agents(
        self,
        week: int | None = None,
        size: int = 50,
        position: str | None = None,
        position_id: int | None = None,
    ) -> list[BoxPlayer]: ...
    def player_info(
        self, name: str | None = None, playerId: int | list[int] | None = None
    ) -> Player | list[Player] | None: ...

    # League activity
    def recent_activity(
        self, size: int = 25, msg_type: str | None = None, offset: int = 0
    ) -> list[Activity]: ...
    def message_board(self, msg_types: list[str] | None = None) -> list[dict[str, Any]]: ...
    def transactions(
        self,
        scoring_period: int | None = None,
        types: set[str] | None = None,
    ) -> list[Transaction]: ...

    # Internal helper methods
    def get_team_data(self, team_id: int) -> Team | None: ...
    def _fetch_league(self) -> dict[str, Any]: ...
    def _fetch_teams(self, data: dict[str, Any]) -> None: ...
    def _fetch_players(self) -> None: ...
    def _get_positional_ratings(self, week: int) -> dict[str, Any]: ...
    def _get_pro_schedule(self, week: int) -> dict[str, Any]: ...
    def _get_all_pro_schedule(self) -> dict[str, Any]: ...

class Team:
    """ESPN fantasy football team."""
    def __init__(
        self,
        data: dict[str, Any],
        roster: dict[str, Any],
        schedule: list[dict[str, Any]],
        year: int,
        **kwargs: Any,
    ) -> None: ...

    # Core team attributes
    team_id: int
    team_name: str | None
    team_abbrev: str | None
    division_id: int
    division_name: str
    owners: list[dict[str, Any]]

    # Record and standings
    wins: int
    losses: int
    ties: int
    points_for: float
    points_against: float
    standing: int
    final_standing: int
    playoff_pct: float

    # Performance data
    scores: list[float]
    outcomes: list[str]  # 'W', 'L', 'T', 'U'
    mov: list[float]  # margin of victory

    # Transaction data
    acquisitions: int
    acquisition_budget_spent: int
    drops: int
    trades: int
    move_to_ir: int

    # Draft and waiver info
    draft_projected_rank: int
    waiver_rank: int

    # Streak info
    streak_length: int
    streak_type: str

    # Team details
    logo_url: str
    roster: list[Player]
    schedule: list[Team]  # List of opponent teams
    stats: dict[str, float]

    # Methods
    def get_player_name(self, playerId: int) -> str: ...
    def _fetch_roster(
        self, data: dict[str, Any], year: int, pro_schedule: dict[str, Any] | None = None
    ) -> None: ...
    def _fetch_schedule(self, data: list[dict[str, Any]]) -> None: ...
    def _get_winner(self, winner: str, is_away: bool) -> str: ...
    def __repr__(self) -> str: ...

class BoxScore:
    """ESPN fantasy football box score for a specific week."""
    def __init__(
        self,
        data: dict[str, Any],
        pro_schedule: dict[str, Any],
        positional_rankings: dict[str, Any],
        week: int,
        year: int,
    ) -> None: ...

    # Matchup info
    matchup_type: str
    is_playoff: bool

    # Team data
    home_team: Team
    away_team: Team
    home_score: float
    away_score: float
    home_projected: float
    away_projected: float

    # Lineups
    home_lineup: list[BoxPlayer]
    away_lineup: list[BoxPlayer]

    # Methods
    def _get_team_data(
        self,
        team: str,
        data: dict[str, Any],
        pro_schedule: dict[str, Any],
        positional_rankings: dict[str, Any],
        week: int,
        year: int,
    ) -> tuple[int, float, float, list[BoxPlayer]]: ...
    def _get_projected_score(self, projected_score: float, lineup: list[BoxPlayer]) -> float: ...
    def __repr__(self) -> str: ...

class Matchup:
    """ESPN fantasy football matchup."""
    def __init__(self, data: dict[str, Any]) -> None: ...

    # Matchup info
    matchup_type: str
    is_playoff: bool

    # Team references
    _home_team_id: int
    _away_team_id: int
    home_team: Team
    away_team: Team

    # Scores
    home_score: float
    away_score: float

    # Methods
    def _fetch_matchup_info(self, data: dict[str, Any], team: str) -> tuple[int, float]: ...
    def __repr__(self) -> str: ...

class Settings:
    """ESPN league settings."""
    def __init__(self, data: dict[str, Any]) -> None: ...

    # Basic settings
    name: str | None
    reg_season_count: int
    matchup_periods: dict[str, list[int]]
    veto_votes_required: int
    team_count: int
    playoff_team_count: int
    keeper_count: int
    trade_deadline: int
    division_map: dict[int, str]

    # Tiebreaker rules
    tie_rule: str
    playoff_tie_rule: str
    playoff_matchup_period_length: int
    playoff_seed_tie_rule: str

    # Scoring and roster
    scoring_type: str
    faab: bool
    acquisition_budget: int
    scoring_format: list[dict[str, Any]]
    position_slot_counts: dict[str, int]

class Activity:
    """ESPN league activity (transactions, trades, etc.)."""
    def __init__(
        self, data: dict[str, Any], player_map: dict[str, int], get_team_data: Any, player_info: Any
    ) -> None: ...

    # Attributes
    actions: list[tuple[Team, str, Player, int]]  # (team, action, player, bid_amount)
    date: int

    def __repr__(self) -> str: ...

class Transaction:
    """ESPN league transaction."""
    def __init__(
        self, data: dict[str, Any], player_map: dict[str, int], get_team_data: Any
    ) -> None: ...

    # Attributes
    team: Team
    type: str
    status: str
    scoring_period: int
    date: int | None
    bid_amount: int | None
    items: list[TransactionItem]

    def __repr__(self) -> str: ...

class TransactionItem:
    """Individual item in a transaction."""
    def __init__(self, data: dict[str, Any], player_map: dict[str, int]) -> None: ...

    # Attributes
    type: str
    player: str

    def __repr__(self) -> str: ...
