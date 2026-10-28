"""
Core data models for Fantasy Football Challenge Tracker.

This module defines type-safe data structures using modern Python typing
and dataclasses for representing fantasy football data.
"""

from __future__ import annotations

from .ai_summary import (
    MEMORY_READ_FAILED,
    MEMORY_READ_NONE,
    MEMORY_READ_OK,
    MEMORY_READ_STATUSES,
    MEMORY_WRITE_FAILED,
    MEMORY_WRITE_OK,
    MEMORY_WRITE_SKIPPED,
    MEMORY_WRITE_STATUSES,
    AIProvenance,
    AISummary,
    AISummaryLeague,
    AISummaryResult,
    AISummaryUnavailable,
)
from .base import Validatable
from .challenge import ChallengeResult
from .championship import (
    ChampionshipProgress,
    ChampionshipRoster,
    ChampionshipTeam,
    RosterSlot,
)
from .division import DivisionData
from .game import GameResult
from .owner import Owner
from .player import WeeklyPlayerStats
from .playoff import (
    ChampionshipEntry,
    ChampionshipLeaderboard,
    PlayoffBracket,
    PlayoffMatchup,
)
from .season_summary import (
    DivisionChampion,
    PlayoffRound,
    PlayoffSummary,
    RegularSeasonSummary,
    SeasonStructure,
    SeasonSummary,
)
from .team import TeamStats
from .week import WeeklyGameResult
from .weekly_challenge import WeeklyChallenge

__all__ = [
    "Validatable",
    "AIProvenance",
    "AISummary",
    "AISummaryLeague",
    "AISummaryResult",
    "AISummaryUnavailable",
    "MEMORY_READ_FAILED",
    "MEMORY_READ_NONE",
    "MEMORY_READ_OK",
    "MEMORY_READ_STATUSES",
    "MEMORY_WRITE_FAILED",
    "MEMORY_WRITE_OK",
    "MEMORY_WRITE_SKIPPED",
    "MEMORY_WRITE_STATUSES",
    "Owner",
    "GameResult",
    "TeamStats",
    "ChallengeResult",
    "ChampionshipProgress",
    "ChampionshipRoster",
    "ChampionshipTeam",
    "RosterSlot",
    "DivisionData",
    "WeeklyGameResult",
    "WeeklyPlayerStats",
    "WeeklyChallenge",
    "PlayoffMatchup",
    "PlayoffBracket",
    "ChampionshipEntry",
    "ChampionshipLeaderboard",
    "DivisionChampion",
    "PlayoffRound",
    "PlayoffSummary",
    "RegularSeasonSummary",
    "SeasonStructure",
    "SeasonSummary",
]
