"""
Tests for ChampionshipService.

Focuses on roster position ordering and helper methods.
"""

from __future__ import annotations

import pytest

from ff_tracker.models.championship import ChampionshipRoster, ChampionshipTeam, RosterSlot
from ff_tracker.services.championship_service import ChampionshipService


class TestPositionOrdering:
    """Test position ordering functionality."""

    def test_position_order_constant_exists(self) -> None:
        """Test that POSITION_ORDER constant is defined."""
        assert hasattr(ChampionshipService, "POSITION_ORDER")
        assert isinstance(ChampionshipService.POSITION_ORDER, list)
        assert len(ChampionshipService.POSITION_ORDER) > 0

    def test_position_order_has_expected_positions(self) -> None:
        """Test that POSITION_ORDER contains expected fantasy positions."""
        order = ChampionshipService.POSITION_ORDER

        # Check that standard positions are present
        assert "QB" in order
        assert "RB" in order
        assert "WR" in order
        assert "TE" in order
        assert "K" in order
        assert "D/ST" in order
        assert "BE" in order
        assert "IR" in order

    def test_position_order_starts_with_qb(self) -> None:
        """Test that QB is first in the position order."""
        assert ChampionshipService.POSITION_ORDER[0] == "QB"

    def test_position_order_ends_with_bench_ir(self) -> None:
        """Test that bench and IR positions are at the end."""
        order = ChampionshipService.POSITION_ORDER
        # BE, BN, IR should be last three
        assert order[-3:] == ["BE", "BN", "IR"] or order[-2:] == ["BE", "IR"]

    def test_get_position_sort_key_for_qb(self) -> None:
        """Test sort key for QB position."""
        service = ChampionshipService()
        key = service._get_position_sort_key("QB")
        assert key == 0  # QB should be first

    def test_get_position_sort_key_for_known_positions(self) -> None:
        """Test sort keys for all known positions."""
        service = ChampionshipService()

        # Test a few known positions
        qb_key = service._get_position_sort_key("QB")
        rb_key = service._get_position_sort_key("RB")
        wr_key = service._get_position_sort_key("WR")
        k_key = service._get_position_sort_key("K")
        be_key = service._get_position_sort_key("BE")

        # QB should come before RB, which comes before WR
        assert qb_key < rb_key < wr_key

        # Starters (K) should come before bench
        assert k_key < be_key

    def test_get_position_sort_key_for_unknown_position(self) -> None:
        """Test sort key for unknown position."""
        service = ChampionshipService()
        key = service._get_position_sort_key("UNKNOWN_POS")

        # Unknown positions should sort to the end
        assert key == len(ChampionshipService.POSITION_ORDER)

    def test_get_position_sort_key_handles_flex_variants(self) -> None:
        """Test sort keys for FLEX position variants."""
        service = ChampionshipService()

        flex_key = service._get_position_sort_key("FLEX")
        espn_flex_key = service._get_position_sort_key("RB/WR/TE")

        # Both should be in the list
        assert flex_key < len(ChampionshipService.POSITION_ORDER)
        assert espn_flex_key < len(ChampionshipService.POSITION_ORDER)

    def test_position_sorting_order(self) -> None:
        """Test that positions sort in the correct order."""
        service = ChampionshipService()

        # Create a shuffled list of positions
        positions = ["BE", "K", "D/ST", "TE", "WR", "RB", "QB"]

        # Sort using the sort key
        sorted_positions = sorted(positions, key=service._get_position_sort_key)

        # Verify order matches expected pattern
        assert sorted_positions[0] == "QB"  # QB first
        assert sorted_positions[-1] == "BE"  # Bench last

        # Verify starters come before bench
        qb_idx = sorted_positions.index("QB")
        be_idx = sorted_positions.index("BE")
        assert qb_idx < be_idx


class TestRosterPositionSorting:
    """Test that rosters are sorted by position."""

    @pytest.fixture
    def sample_team(self) -> ChampionshipTeam:
        """Create a sample championship team."""
        return ChampionshipTeam(
            team_name="Test Team",
            owner_name="Test Owner",
            division_name="Test Division",
            team_id=1,
            seed=1,
        )

    @pytest.fixture
    def unsorted_roster_slots(self) -> list[RosterSlot]:
        """Create roster slots in random order."""
        return [
            # Intentionally out of order
            RosterSlot(
                position="K",
                player_name="Kicker Player",
                player_team="KC",
                projected_points=10.0,
                actual_points=12.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
            RosterSlot(
                position="QB",
                player_name="QB Player",
                player_team="KC",
                projected_points=25.0,
                actual_points=28.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
            RosterSlot(
                position="WR",
                player_name="WR Player",
                player_team="KC",
                projected_points=15.0,
                actual_points=18.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
            RosterSlot(
                position="RB",
                player_name="RB Player",
                player_team="KC",
                projected_points=20.0,
                actual_points=22.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
            RosterSlot(
                position="D/ST",
                player_name="Defense",
                player_team="KC",
                projected_points=12.0,
                actual_points=14.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
            RosterSlot(
                position="TE",
                player_name="TE Player",
                player_team="KC",
                projected_points=14.0,
                actual_points=16.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
        ]

    def test_roster_slots_can_be_sorted(self, unsorted_roster_slots: list[RosterSlot]) -> None:
        """Test that roster slots can be sorted by position."""
        service = ChampionshipService()

        # Sort the slots
        sorted_slots = sorted(
            unsorted_roster_slots, key=lambda s: service._get_position_sort_key(s.position)
        )

        # Verify order
        positions = [slot.position for slot in sorted_slots]
        assert positions == ["QB", "RB", "WR", "TE", "D/ST", "K"]

    def test_roster_with_bench_sorts_correctly(
        self, unsorted_roster_slots: list[RosterSlot]
    ) -> None:
        """Test that bench players sort to the end."""
        service = ChampionshipService()

        # Add bench players
        all_slots = unsorted_roster_slots + [
            RosterSlot(
                position="BE",
                player_name="Bench RB",
                player_team="DAL",
                projected_points=8.0,
                actual_points=0.0,
                game_status="not_started",
                injury_status=None,
                is_bye=False,
                is_starter=False,
            ),
            RosterSlot(
                position="BE",
                player_name="Bench WR",
                player_team="DAL",
                projected_points=10.0,
                actual_points=0.0,
                game_status="not_started",
                injury_status=None,
                is_bye=False,
                is_starter=False,
            ),
        ]

        # Sort
        sorted_slots = sorted(all_slots, key=lambda s: service._get_position_sort_key(s.position))

        # Verify bench players are at the end
        positions = [slot.position for slot in sorted_slots]
        assert positions[-2:] == ["BE", "BE"]
        assert positions[0] == "QB"

    def test_roster_with_flex_sorts_correctly(self) -> None:
        """Test that FLEX positions sort correctly."""
        service = ChampionshipService()

        slots = [
            RosterSlot(
                position="QB",
                player_name="QB",
                player_team="KC",
                projected_points=25.0,
                actual_points=28.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
            RosterSlot(
                position="FLEX",
                player_name="FLEX",
                player_team="KC",
                projected_points=15.0,
                actual_points=18.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
            RosterSlot(
                position="K",
                player_name="K",
                player_team="KC",
                projected_points=10.0,
                actual_points=12.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
        ]

        sorted_slots = sorted(slots, key=lambda s: service._get_position_sort_key(s.position))
        positions = [slot.position for slot in sorted_slots]

        # FLEX should come after skill positions but before K/DST
        assert positions[0] == "QB"
        assert positions[1] == "FLEX"
        assert positions[2] == "K"

    def test_roster_with_espn_flex_notation(self) -> None:
        """Test that ESPN's RB/WR/TE FLEX notation sorts correctly."""
        service = ChampionshipService()

        slots = [
            RosterSlot(
                position="K",
                player_name="K",
                player_team="KC",
                projected_points=10.0,
                actual_points=12.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
            RosterSlot(
                position="RB/WR/TE",
                player_name="FLEX",
                player_team="KC",
                projected_points=15.0,
                actual_points=18.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
            RosterSlot(
                position="QB",
                player_name="QB",
                player_team="KC",
                projected_points=25.0,
                actual_points=28.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
        ]

        sorted_slots = sorted(slots, key=lambda s: service._get_position_sort_key(s.position))
        positions = [slot.position for slot in sorted_slots]

        assert positions[0] == "QB"
        assert positions[1] == "RB/WR/TE"
        assert positions[2] == "K"

    def test_multiple_same_positions_maintain_relative_order(self) -> None:
        """Test that multiple players at same position maintain relative order."""
        service = ChampionshipService()

        slots = [
            RosterSlot(
                position="RB",
                player_name="RB1",
                player_team="KC",
                projected_points=20.0,
                actual_points=22.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
            RosterSlot(
                position="QB",
                player_name="QB",
                player_team="KC",
                projected_points=25.0,
                actual_points=28.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
            RosterSlot(
                position="RB",
                player_name="RB2",
                player_team="DAL",
                projected_points=18.0,
                actual_points=20.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
        ]

        sorted_slots = sorted(slots, key=lambda s: service._get_position_sort_key(s.position))

        # QB should be first, then both RBs
        assert sorted_slots[0].position == "QB"
        assert sorted_slots[1].position == "RB"
        assert sorted_slots[2].position == "RB"

        # RB1 should still be before RB2 (stable sort)
        assert sorted_slots[1].player_name == "RB1"
        assert sorted_slots[2].player_name == "RB2"

    def test_championship_roster_validates_with_sorted_positions(
        self, sample_team: ChampionshipTeam
    ) -> None:
        """Test that ChampionshipRoster can be created with sorted positions."""
        service = ChampionshipService()

        # Create slots in random order
        starters = [
            RosterSlot(
                position="K",
                player_name="Kicker",
                player_team="KC",
                projected_points=10.0,
                actual_points=12.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
            RosterSlot(
                position="QB",
                player_name="Quarterback",
                player_team="KC",
                projected_points=25.0,
                actual_points=28.0,
                game_status="final",
                injury_status=None,
                is_bye=False,
                is_starter=True,
            ),
        ]

        # Sort them
        sorted_starters = sorted(starters, key=lambda s: service._get_position_sort_key(s.position))

        # Create roster
        roster = ChampionshipRoster(
            team=sample_team,
            starters=sorted_starters,
            bench=[],
            total_score=40.0,
            projected_score=35.0,
            is_complete=True,
            empty_slots=[],
            warnings=[],
            last_modified=None,
        )

        # Verify roster is valid and positions are sorted
        assert roster.starters[0].position == "QB"
        assert roster.starters[1].position == "K"
