# Type stubs for espn_api.football
# Based on actual ESPN API object inspection from debug logging

from __future__ import annotations

from logging import Logger
from typing import Any, TypedDict

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
    """ESPN player object in team roster."""
    def __init__(self) -> None: ...

    # Attributes from roster debug inspection
    acquisitionType: str
    active_status: str
    avg_points: float
    eligibleSlots: list[Any]
    injured: bool
    injuryStatus: str
    lineupSlot: str
    name: str
    onTeamId: int
    percent_owned: float
    percent_started: float
    playerId: int
    posRank: int
    position: str
    proTeam: str
    projected_avg_points: float
    projected_total_points: float
    schedule: dict[str, Any]
    stats: dict[str, Any]
    total_points: float

class BoxPlayer:
    """ESPN player object in lineup/roster."""
    def __init__(self) -> None: ...

    # Attributes from debug inspection
    acquisitionType: list[Any]
    active_status: str
    avg_points: int
    eligibleSlots: list[Any]
    game_date: Any  # datetime object
    game_played: int
    injured: bool
    injuryStatus: str
    lineupSlot: str
    name: str
    onTeamId: int
    on_bye_week: bool
    percent_owned: int
    percent_started: int
    playerId: int
    points: float
    points_breakdown: int
    posRank: list[Any]
    position: str
    proTeam: str
    pro_opponent: str
    pro_pos_rank: int
    projected_avg_points: int
    projected_breakdown: dict[str, Any]
    projected_points: float
    projected_total_points: int
    schedule: dict[str, Any]
    slot_position: str
    stats: dict[str, Any]
    total_points: int

class EspnFantasyRequests:
    """ESPN API request handler."""
    def __init__(self) -> None: ...

    # Attributes
    ENDPOINT: str
    LEAGUE_ENDPOINT: str
    NEWS_ENDPOINT: str
    cookies: None  # Always None based on debug output
    league_id: int
    logger: Logger
    year: int

    # Methods
    def checkRequestStatus(self) -> Any: ...
    def get(self) -> Any: ...
    def get_league(self) -> Any: ...
    def get_league_draft(self) -> Any: ...
    def get_league_message_board(self) -> Any: ...
    def get_player_card(self) -> Any: ...
    def get_player_news(self) -> Any: ...
    def get_pro_players(self) -> Any: ...
    def get_pro_schedule(self) -> Any: ...
    def league_get(self) -> Any: ...
    def news_get(self) -> Any: ...

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
    previousSeasons: list[int]  # List of previous season years
    nfl_week: int
    members: list[Owner]  # List of league members with same structure as Owner
    draft: list[BasePick]  # List of draft picks
    player_map: dict[int, str]  # Maps player IDs to player names
    espn_request: EspnFantasyRequests  # ESPN API request handler
    logger: Logger  # Python logging.Logger

    # Methods based on actual ESPN API inspection
    def box_scores(self, week: int | None = None) -> list[BoxScore]: ...
    def fetch_league(self) -> None: ...
    def free_agents(
        self,
        week: int | None = None,
        size: int = 50,
        position: str | None = None,
        position_id: int | None = None,
    ) -> list[Any]: ...  # Returns List[Player] but Player not defined yet
    def get_team_data(self, team_id: int) -> list[Any]: ...
    def least_scored_week(self) -> tuple[Team, int]: ...
    def least_scorer(self) -> Team: ...
    def load_roster_week(self, week: int) -> None: ...
    def message_board(self, msg_types: list[str] | None = None) -> Any: ...
    def most_points_against(self) -> Team: ...
    def player_info(
        self, name: str | None = None, playerId: int | list[int] | None = None
    ) -> Any: ...  # Returns Player or List[Player]
    def power_rankings(self, week: int | None = None) -> Any: ...
    def recent_activity(
        self, size: int = 25, msg_type: str | None = None, offset: int = 0
    ) -> list[Any]: ...  # Returns List[Activity]
    def refresh(self) -> None: ...
    def refresh_draft(self, refresh_players: bool = False, refresh__teams: bool = False) -> None: ...
    def scoreboard(self, week: int | None = None) -> list[Any]: ...  # Returns List[Matchup]
    def standings(self) -> list[Team]: ...
    def standings_weekly(self, week: int) -> list[Team]: ...
    def top_scored_week(self) -> tuple[Team, int]: ...
    def top_scorer(self) -> Team: ...
    def transactions(
        self,
        scoring_period: int | None = None,
        types: set[str] | None = None,
    ) -> list[Any]: ...  # Returns List[Transaction]

class Team:
    def __init__(self) -> None: ...

    # Direct attributes (not properties)
    team_id: int
    team_name: str | None
    team_abbrev: str | None
    division_id: int
    division_name: str
    owners: list[Owner]
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
    roster: list[Player]
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
    home_lineup: list[BoxPlayer]
    away_lineup: list[BoxPlayer]

class Settings:
    def __init__(self) -> None: ...

    # Direct attributes (not properties)
    name: str | None
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
