"""
Roster validation service for Championship Week.

This service provides validation logic for championship rosters including:
- Empty slot detection
- Injury status warnings
- Bye week checks
- Lineup completeness verification
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.championship import ChampionshipRoster

logger = logging.getLogger(__name__)


class RosterValidator:
    """Service for validating championship rosters."""

    def validate_roster(self, roster: ChampionshipRoster) -> dict[str, list[str]]:
        """
        Validate a championship roster and return warnings/errors.

        Args:
            roster: ChampionshipRoster to validate

        Returns:
            Dictionary with 'errors' and 'warnings' keys containing lists of messages
        """
        errors = []
        warnings = []

        # Check for empty slots
        if roster.empty_slots:
            errors.append(f"Empty starting slots: {', '.join(roster.empty_slots)}")

        # Check for injured players in starting lineup
        injured_starters = [
            slot for slot in roster.starters if slot.injury_status in {"OUT", "DOUBTFUL"}
        ]
        for slot in injured_starters:
            errors.append(f"{slot.position} {slot.player_name} is {slot.injury_status}")

        # Check for questionable players (warning, not error)
        questionable_starters = [
            slot for slot in roster.starters if slot.injury_status == "QUESTIONABLE"
        ]
        for slot in questionable_starters:
            warnings.append(f"{slot.position} {slot.player_name} is QUESTIONABLE")

        # Check for bye weeks (unlikely in Week 17 but possible)
        bye_starters = [slot for slot in roster.starters if slot.is_bye]
        for slot in bye_starters:
            errors.append(f"{slot.position} {slot.player_name} is on BYE week")

        # Check for zero-point projections (might indicate invalid slot)
        zero_projection_starters = [
            slot for slot in roster.starters if slot.projected_points == 0.0 and slot.player_name
        ]
        for slot in zero_projection_starters:
            warnings.append(f"{slot.position} {slot.player_name} has 0.0 projected points")

        logger.debug(
            f"Validated roster for {roster.team.team_name}: "
            f"{len(errors)} errors, {len(warnings)} warnings"
        )

        return {"errors": errors, "warnings": warnings}

    def validate_all_rosters(
        self, rosters: list[ChampionshipRoster]
    ) -> dict[str, dict[str, list[str]]]:
        """
        Validate all championship rosters.

        Args:
            rosters: List of ChampionshipRoster objects to validate

        Returns:
            Dictionary mapping team names to validation results
        """
        results = {}

        for roster in rosters:
            validation = self.validate_roster(roster)
            results[roster.team.team_name] = validation

        # Log summary
        total_errors = sum(len(v["errors"]) for v in results.values())
        total_warnings = sum(len(v["warnings"]) for v in results.values())

        logger.debug(
            f"Validated {len(rosters)} rosters: "
            f"{total_errors} total errors, {total_warnings} total warnings"
        )

        return results

    def get_roster_issues_summary(self, roster: ChampionshipRoster) -> str:
        """
        Get a human-readable summary of roster issues.

        Args:
            roster: ChampionshipRoster to summarize

        Returns:
            Human-readable string summarizing issues (empty if no issues)
        """
        validation = self.validate_roster(roster)
        errors = validation["errors"]
        warnings = validation["warnings"]

        if not errors and not warnings:
            return "✓ Roster looks good!"

        parts = []

        if errors:
            parts.append(f"⚠️  {len(errors)} ERRORS:")
            for error in errors:
                parts.append(f"  • {error}")

        if warnings:
            parts.append(f"⚡ {len(warnings)} warnings:")
            for warning in warnings:
                parts.append(f"  • {warning}")

        return "\n".join(parts)

    def has_critical_issues(self, roster: ChampionshipRoster) -> bool:
        """
        Check if a roster has critical issues that would prevent competition.

        Args:
            roster: ChampionshipRoster to check

        Returns:
            True if roster has critical issues, False otherwise
        """
        validation = self.validate_roster(roster)
        return len(validation["errors"]) > 0

    def get_optimal_lineup_suggestions(self, roster: ChampionshipRoster) -> list[str]:
        """
        Suggest lineup improvements based on bench players.

        Args:
            roster: ChampionshipRoster to analyze

        Returns:
            List of suggestions for lineup improvements
        """
        suggestions = []

        # Check for injured starters with healthy bench alternatives
        injured_starters = [
            slot for slot in roster.starters if slot.injury_status in {"OUT", "DOUBTFUL"}
        ]

        for injured_slot in injured_starters:
            # Find bench players at same position
            bench_alternatives = [
                slot
                for slot in roster.bench
                if slot.position == injured_slot.position
                and not slot.injury_status
                and not slot.is_bye
            ]

            if bench_alternatives:
                best_bench = max(bench_alternatives, key=lambda s: s.projected_points)
                suggestions.append(
                    f"Replace {injured_slot.position} {injured_slot.player_name} "
                    f"({injured_slot.injury_status}) with {best_bench.player_name} "
                    f"(proj: {best_bench.projected_points:.1f})"
                )

        # Check for underperforming starters with better bench options
        for starter in roster.starters:
            if not starter.injury_status and not starter.is_bye:
                # Find bench players at same position with higher projections
                better_bench = [
                    slot
                    for slot in roster.bench
                    if slot.position == starter.position
                    and slot.projected_points > starter.projected_points * 1.1  # 10% better
                    and not slot.injury_status
                    and not slot.is_bye
                ]

                if better_bench:
                    best_bench = max(better_bench, key=lambda s: s.projected_points)
                    suggestions.append(
                        f"Consider {starter.position} {best_bench.player_name} "
                        f"(proj: {best_bench.projected_points:.1f}) over "
                        f"{starter.player_name} (proj: {starter.projected_points:.1f})"
                    )

        return suggestions
