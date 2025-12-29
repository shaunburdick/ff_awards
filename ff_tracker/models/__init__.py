"""
Core data models for Fantasy Football Challenge Tracker.

This module defines type-safe data structures using modern Python typing
and dataclasses for representing fantasy football data.
"""

from __future__ import annotations

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
