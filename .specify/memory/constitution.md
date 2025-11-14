# FF-Awards Development Constitution

> **Version**: 1.0.0
> **Status**: Active and Immutable
> **Last Updated**: 2025-11-14

This document defines the **immutable architectural principles** that govern all development on the Fantasy Football Challenge Tracker. These principles are derived from the project's successful refactoring from a 1000+ line monolithic script to a modern, maintainable Python package.

All AI agents, developers, and code generation must adhere to these principles. Deviations require explicit documentation and approval.

---

## Article I: Type Safety First

**Principle**: Every component MUST maintain 100% type coverage with modern Python syntax.

### Requirements
- Use Python 3.9+ union syntax (`str | None`, not `Optional[str]`)
- Include `from __future__ import annotations` in all modules
- **Zero `Any` types permitted** - use `dict[str, str]` instead of `dict[str, Any]`
- Zero `# type: ignore` comments permitted
- All function signatures fully typed (parameters and returns)
- All class attributes fully typed
- Dictionaries must specify exact types for keys and values

### Rationale
Type safety prevents entire classes of bugs at development time, serves as inline documentation, and enables better IDE support. The `Any` type defeats the purpose of type checking and should never be used—if the type is truly unknown, use Union types or create proper type aliases.

### Validation
- Run type checker on all changes
- Code that introduces type errors, suppressions, or `Any` types must be rejected

---

## Article II: Data Immutability and Validation

**Principle**: Data models MUST be immutable and validate themselves at construction time.

### Requirements
- Use `@dataclass(frozen=True)` for all data models
- Implement `__post_init__` validation for all data classes
- Raise `DataValidationError` on invalid data
- No business logic in models (data only)
- Computed properties via `@property` decorator

### Rationale
Immutable data prevents accidental mutations and makes data flow explicit. Construction-time validation catches errors early with clear context. Separating data from behavior enables clean architecture.

### Example
```python
@dataclass(frozen=True)
class TeamStats:
    name: str
    points_for: float
    wins: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DataValidationError("Team name cannot be empty")
        if self.points_for < 0:
            raise DataValidationError(f"Points cannot be negative: {self.points_for}")

    @property
    def total_games(self) -> int:
        return self.wins + self.losses
```

---

## Article III: Fail-Fast Error Handling

**Principle**: All errors MUST be clear, actionable, and fail immediately—no silent failures, partial data, or retry logic.

### Requirements
- Custom exception hierarchy: `FFTrackerError` as base
- Specific exceptions: `ESPNAPIError`, `ConfigurationError`, `DataValidationError`, etc.
- No retry logic (external systems should be reliable or fail clearly)
- No partial data tolerance (incomplete data = failure, not degraded output)
- Error messages must explain what went wrong AND how to fix it
- Context managers (`__enter__`, `__exit__`) for resource cleanup

### Rationale
Users prefer clear, immediate failures over silent errors or mysterious retries. Partial data creates confusion and incorrect results. Actionable error messages reduce support burden. No retry logic simplifies debugging—if the API fails or data is incomplete, tell the user immediately.

### Example
```python
class ConfigurationError(FFTrackerError):
    """Configuration or environment setup error."""
    pass

# Usage
if not league_ids:
    raise ConfigurationError(
        "No league IDs provided. Use --env flag with LEAGUE_IDS environment variable, "
        "or pass league IDs as argument (e.g., ff-tracker 123456 or ff-tracker 123456,789012)"
    )
```

---

## Article IV: Modular Architecture with Clear Boundaries

**Principle**: System MUST maintain strict separation of concerns across three layers.

### Layer Responsibilities

#### Models Layer (`ff_tracker/models/`)
- **Purpose**: Type-safe data containers
- **Permitted**: Data validation, computed properties
- **Forbidden**: Business logic, external API calls, I/O operations

#### Services Layer (`ff_tracker/services/`)
- **Purpose**: Business logic and external integrations
- **Permitted**: Calculations, API calls, data transformations
- **Forbidden**: Presentation logic, direct output formatting

#### Display Layer (`ff_tracker/display/`)
- **Purpose**: Output formatting for different consumers
- **Permitted**: Format-specific rendering, string manipulation
- **Forbidden**: Business logic, data manipulation, calculations

### Requirements
- No cross-layer violations (e.g., models calling services)
- Dependencies flow downward only: Display → Services → Models
- Each component has a single, well-defined responsibility
- Protocol pattern for extensibility (interfaces, not inheritance)

### Rationale
Clear boundaries make the system easier to understand, test, and modify. New developers can immediately identify where code belongs. Changes in one layer don't cascade uncontrollably.

---

## Article V: External API Respect

**Principle**: Integration with ESPN API MUST be efficient, respectful, and resilient.

### Requirements
- Context managers for all API connections
- Single API call when multiple data items can be fetched together
- Multi-output mode generates all formats from one API call
- Graceful degradation on partial failures (e.g., missing weekly data)
- No retry logic (fail clearly, let user retry manually)
- Rate limit awareness (though ESPN doesn't currently enforce limits)

### Rationale
ESPN provides this API as a courtesy to developers. We must not abuse it with redundant calls or aggressive retry logic. Efficient API usage also improves performance.

### Example
```python
# GOOD: Single API call, multiple outputs
with ESPNService(config) as service:
    divisions = service.load_all_divisions()
    # Generate all formats from this one data fetch

# BAD: Multiple API calls for same data
service1 = ESPNService(config)
data1 = service1.load_all_divisions()  # Call 1
service2 = ESPNService(config)
data2 = service2.load_all_divisions()  # Call 2 - wasteful!
```

---

## Article VI: Output Format Equality

**Principle**: All output formatters are first-class citizens with equal capability.

### Requirements
- Protocol-based interface (`BaseFormatter`) defines contract
- All formatters receive identical data (no format favoritism)
- Format-specific arguments supported via generic system
- New formats can be added without modifying existing code
- Each formatter independent (no shared state)

### Rationale
Users have different needs: console for development, email for weekly reports, JSON for APIs, etc. No format is more important than others. The Protocol pattern enables unlimited extensibility.

### Format Argument System
```python
# Global argument (all formats)
--format-arg note="Playoffs start next week!"

# Format-specific argument
--format-arg email.accent_color="#007bff"
--format-arg markdown.include_toc=true
```

---

## Article VII: Documentation as Code

**Principle**: Code MUST be self-documenting through types, names, and minimal comments.

### Requirements
- Descriptive variable and function names (no abbreviations except well-known ones)
- Type hints serve as primary documentation
- Docstrings for modules, classes, and public functions
- Comments only for non-obvious decisions or complex algorithms
- Avoid redundant comments that repeat the code

### Rationale
Code is read far more than written. Clear names and types eliminate most documentation needs. Comments should explain *why*, not *what*.

### Example
```python
# GOOD: Self-documenting
def calculate_most_points_overall(teams: list[TeamStats]) -> ChallengeResult:
    """Find team with highest total points across regular season."""
    winner = max(teams, key=lambda t: t.points_for)
    return ChallengeResult(
        challenge_name="Most Points Overall",
        team_name=winner.name,
        # ... rest of implementation
    )

# BAD: Needs comments to understand
def cmp1(t: list) -> dict:  # Calculate challenge 1
    w = max(t, key=lambda x: x[2])  # Get winner by index 2
    return {"n": "MP", "t": w[0]}  # Return name and team
```

---

## Article VIII: Testing Through Specifications

**Principle**: Behavior is defined by specifications, not implementation details.

### Requirements
- Specifications describe expected behavior, not implementation
- Edge cases explicitly documented in specs
- Performance requirements stated clearly
- Example outputs provided for validation
- Tests (when written) validate spec compliance, not code coverage

### Rationale
Specifications outlive implementations. Testing against specs allows implementations to change freely as long as behavior remains correct.

---

## Article IX: CLI Interface Consistency

**Principle**: Command-line interface MUST be intuitive, consistent, and follow Unix conventions.

### Requirements
- Single league: `ff-tracker LEAGUE_ID`
- Multiple leagues: `ff-tracker ID1,ID2,ID3` or `ff-tracker --env`
- Output control: `--format FORMAT` or `--output-dir DIR`
- Format customization: `--format-arg KEY=VALUE`
- Sensible defaults (console output, current year, public leagues)
- Help text (`--help`) always accurate and complete

### Rationale
CLI is the primary user interface. Consistency reduces cognitive load. Following conventions (flags with `--`, single-letter aliases like `-v`) meets user expectations.

---

## Article X: Performance Requirements

**Principle**: System MUST handle typical and stress scenarios efficiently.

### Requirements
- Typical: 3-4 leagues, 10 teams each, maximum 18 weeks → Under 5 seconds
- Stress: 10 leagues, 100+ teams, maximum 18 weeks → Under 15 seconds
- Memory: Efficient processing, no unbounded growth
- Single API call: Multi-output mode uses one ESPN API call
- No caching: Keep implementation simple, optimize if proven necessary

### Rationale
Performance directly affects user experience. Weekly reports need to run quickly in GitHub Actions. Fantasy football regular season is at most 18 weeks, providing clear upper bound for data volume. Current implementation easily meets these requirements without optimization.

---

## Amendments and Evolution

This constitution can be amended through the following process:

1. **Proposal**: Document the rationale for change
2. **Review**: Assess impact on existing code and specs
3. **Approval**: Requires maintainer consensus
4. **Migration**: Update all affected specs and code
5. **Version**: Increment constitution version, add dated amendment

### Amendment History
- **v1.0.0** (2025-11-14): Initial constitution based on successful refactoring

---

## Compliance

All code and specifications must adhere to this constitution. Non-compliance is only acceptable when:
1. Explicitly documented with rationale
2. Tracked in implementation plan's "Complexity Tracking" section
3. Approved by maintainers

**Constitutional violations are technical debt and should be resolved.**

---

**This constitution represents the collective wisdom gained from transforming a monolithic script into a production-ready, maintainable system. Respect these principles, and the codebase will remain clean, extensible, and reliable.**
