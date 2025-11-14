# Implementation Plan: Multi-Format Output System

> **Spec ID**: 003
> **Status**: Implemented
> **Created**: 2025-11-14
> **Last Updated**: 2025-11-14

## Technology Choices

### Primary Stack
- **Language**: Python 3.9+
- **Key Libraries**:
  - tabulate: Console table formatting
  - Standard library: json, html.escape, string formatting
- **Design Pattern**: Protocol-based interfaces

### Rationale
Protocol pattern enables extensibility without inheritance complexity. Each formatter is independent, making them easy to test and maintain. Minimal dependencies keep the system lightweight.

**Constitutional Compliance**:
- Article I: 100% type coverage with Protocol
- Article II: Immutable data passed to formatters
- Article IV: Display layer separate from business logic
- Article VI: All formatters equal, Protocol ensures consistency

---

## Architecture Pattern

**Pattern**: Protocol-Based Formatters with Strategy Pattern

**Justification**: Protocol defines the interface contract without forcing inheritance. Each formatter is a standalone strategy that can be swapped at runtime. Easy to add new formats without modifying existing code.

**Constitutional Compliance**:
- Article IV: Clear separation - formatters only format, never calculate
- Article VI: Protocol ensures all formatters are first-class citizens

---

## Component Breakdown

### Component 1: BaseFormatter (Protocol)

**Purpose**: Define the interface all formatters must implement

**Responsibilities**:
- Define format_output signature
- Declare format_args parameter
- Provide helper methods for common operations

**Interface/Public API**:
```python
from typing import Protocol

class BaseFormatter(Protocol):
    year: int
    format_args: dict[str, str]

    def format_output(
        self,
        divisions: list[DivisionData],
        challenges: list[ChallengeResult],
        weekly_challenges: list[WeeklyChallenge] | None,
        current_week: int | None
    ) -> str:
        """Format all data into output string."""

    def _get_arg(self, key: str, default: str = "") -> str:
        """Get format argument value."""

    def _get_arg_bool(self, key: str, default: bool = False) -> bool:
        """Get format argument as boolean."""

    def _get_arg_int(self, key: str, default: int) -> int:
        """Get format argument as integer."""
```

**Pattern**: Protocol (structural subtyping, not inheritance)

### Component 2: ConsoleFormatter

**Purpose**: Generate human-readable console output

**Responsibilities**:
- Use tabulate for table formatting
- Add section separators and headers
- Mark playoff teams with * indicator
- Handle optional note display
- Support emoji/Unicode properly

**Key Methods**:
```python
class ConsoleFormatter:
    def format_output(...) -> str:
        """Generate console tables."""

    def _format_standings(...) -> str:
        """Format league standings table."""

    def _format_season_challenges(...) -> str:
        """Format season challenges list."""

    def _format_weekly_highlights(...) -> str:
        """Format weekly team and player tables."""
```

**Format Arguments**:
- `note`: Optional message to display at top

### Component 3: SheetsFormatter

**Purpose**: Generate TSV for spreadsheet import

**Responsibilities**:
- Tab-separated output
- Clear section headers
- Consistent number formatting
- Optional note as first row

**Key Methods**:
```python
class SheetsFormatter:
    def format_output(...) -> str:
        """Generate TSV output."""

    def _format_row(values: list[str | float | int]) -> str:
        """Format single row with tabs."""
```

**Format Arguments**:
- `note`: Optional note as first row

### Component 4: EmailFormatter

**Purpose**: Generate mobile-friendly HTML

**Responsibilities**:
- Self-contained HTML (no external resources)
- Inline CSS for styling
- Responsive tables
- Customizable accent colors
- Optional note in alert box

**Key Methods**:
```python
class EmailFormatter:
    def format_output(...) -> str:
        """Generate HTML email."""

    def _get_accent_color(self) -> str:
        """Get accent color from args."""

    def _format_note_box(note: str, color: str) -> str:
        """Format note as styled alert box."""

    def _format_responsive_table(...) -> str:
        """Format table with responsive design."""
```

**Format Arguments**:
- `note`: Optional alert box message
- `accent_color`: Hex color for highlights (default: #ffc107)
- `max_teams`: Limit top teams in standings (default: 20)

### Component 5: JsonFormatter

**Purpose**: Generate structured JSON

**Responsibilities**:
- Valid JSON output
- Proper type preservation (numbers as numbers)
- Metadata section
- Optional pretty-printing

**Key Methods**:
```python
class JsonFormatter:
    def format_output(...) -> str:
        """Generate JSON output."""

    def _should_pretty_print(self) -> bool:
        """Check if pretty-print enabled."""

    def _serialize_data(...) -> dict:
        """Convert models to JSON-serializable dict."""
```

**Format Arguments**:
- `note`: Optional metadata field
- `pretty`: Enable indentation (default: true)

### Component 6: MarkdownFormatter

**Purpose**: Generate GitHub-flavored markdown

**Responsibilities**:
- Markdown table syntax
- Header hierarchy
- Optional table of contents
- Bold/italic for emphasis
- Optional note as blockquote

**Key Methods**:
```python
class MarkdownFormatter:
    def format_output(...) -> str:
        """Generate markdown output."""

    def _generate_toc(...) -> str:
        """Generate table of contents."""

    def _format_markdown_table(...) -> str:
        """Format table using markdown syntax."""
```

**Format Arguments**:
- `note`: Optional blockquote at top
- `include_toc`: Generate table of contents (default: false)

---

## Data Flow

### High-Level Flow
1. **Input**: Calculated results from services (divisions, challenges)
2. **Selection**: CLI selects formatter based on --format argument
3. **Instantiation**: Formatter created with year and format_args
4. **Formatting**: format_output called with all data
5. **Output**: Formatted string returned to CLI for display/file write

### Formatter Invocation Pattern

```
CLI receives --format argument
    ↓
Parse --format-arg options into dict
    ↓
Select formatter class
    ↓
formatter = FormatterClass(year, format_args)
    ↓
output = formatter.format_output(divisions, challenges, weekly, week)
    ↓
Return formatted string
```

### Multi-Output Mode

```
CLI receives --output-dir argument
    ↓
Create output directory
    ↓
For each format in [console, sheets, email, json, markdown]:
    ├─> Create formatter instance
    ├─> Call format_output
    └─> Write to file (standings.txt, .tsv, .html, .json, .md)
    ↓
All formats generated from single data fetch
```

---

## Implementation Phases

### Phase 1: Protocol Definition

**Goal**: Define BaseFormatter protocol

**Tasks**:
- [ ] Create BaseFormatter protocol class
- [ ] Define format_output signature
- [ ] Add helper methods for format arguments
- [ ] Document protocol requirements

**Deliverable**: Protocol defined, type checker validates conformance

**Validation**: Empty formatters pass type checking

**Dependencies**: None

### Phase 2: Console Formatter

**Goal**: Implement human-readable console output

**Tasks**:
- [ ] Implement ConsoleFormatter class
- [ ] Use tabulate for table generation
- [ ] Add section separators and headers
- [ ] Implement note display
- [ ] Handle Unicode/emoji width correctly

**Deliverable**: Console formatter working

**Validation**: Output readable, tables aligned, playoff marks correct

**Dependencies**: Phase 1 complete

### Phase 3: Sheets Formatter

**Goal**: Implement TSV generation

**Tasks**:
- [ ] Implement SheetsFormatter class
- [ ] Generate tab-separated rows
- [ ] Add section headers
- [ ] Implement note as first row
- [ ] Test import to Google Sheets

**Deliverable**: Sheets formatter working

**Validation**: TSV imports cleanly, data accurate

**Dependencies**: Phase 1 complete

### Phase 4: Email Formatter

**Goal**: Implement HTML email generation

**Tasks**:
- [ ] Implement EmailFormatter class
- [ ] Create responsive HTML template
- [ ] Add inline CSS styling
- [ ] Implement customizable accent colors
- [ ] Add note alert box
- [ ] Test on multiple email clients

**Deliverable**: Email formatter working

**Validation**: Renders on mobile and desktop, all clients

**Dependencies**: Phase 1 complete

### Phase 5: JSON and Markdown Formatters

**Goal**: Implement structured data and markdown outputs

**Tasks**:
- [ ] Implement JsonFormatter class
- [ ] Implement MarkdownFormatter class
- [ ] Add pretty-print option to JSON
- [ ] Add TOC generation to markdown
- [ ] Validate JSON schema consistency

**Deliverable**: All 5 formatters working

**Validation**: JSON parseable, markdown renders correctly

**Dependencies**: Phase 1 complete

### Phase 6: Integration and Testing

**Goal**: Integrate with CLI and test all formats

**Tasks**:
- [ ] Wire formatters to CLI --format argument
- [ ] Implement multi-output mode (--output-dir)
- [ ] Test format argument system
- [ ] Performance validation
- [ ] Cross-format consistency checks

**Deliverable**: Production-ready formatter system

**Validation**: All formats work with real data, meet performance targets

**Dependencies**: Phases 2-5 complete

---

## Risk Assessment

### Risk 1: Email Client Compatibility

**Likelihood**: Medium
**Impact**: Medium
**Mitigation**: Use simple HTML with inline CSS, test on multiple clients
**Fallback**: Provide web-safe alternative HTML

### Risk 2: Unicode Handling

**Likelihood**: Low
**Impact**: Low
**Mitigation**: Use tabulate for proper width calculation, test with emoji
**Fallback**: Strip problematic characters with warning

### Risk 3: JSON Schema Changes

**Likelihood**: Low
**Impact**: High
**Mitigation**: Document schema, version it, test for breaking changes
**Fallback**: Maintain backwards compatibility, version in metadata

---

## Testing Strategy

### Unit Testing
- Test each formatter independently
- Test with empty data, single item, multiple items
- Test format argument parsing and application
- Test edge cases (long names, Unicode, etc.)

### Integration Testing
- Test all formatters with real ESPN data
- Verify multi-output mode generates all 5 files
- Test format arguments work across all formatters
- Validate cross-format consistency

### Validation Against Spec
- [ ] All 5 formatters implement BaseFormatter protocol
- [ ] Format arguments system works generically
- [ ] All formatters handle empty/missing data
- [ ] Performance targets met

---

## Performance Considerations

**Expected Load**: Format full season data with weekly highlights
**Performance Target**: < 1 second per format
**Current Performance**: ~0.1 seconds per format (well within target)

**Optimization Strategy**:
- Minimize string concatenation (use list + join)
- Avoid redundant data transformation
- Use generator expressions where possible
- No unnecessary copying of data structures

---

## Complexity Tracking

> No constitutional deviations in this implementation.

All formatters adhere to constitutional principles:
- ✅ Article I: 100% type coverage with Protocol
- ✅ Article IV: No business logic in display layer
- ✅ Article VI: All formatters equal via Protocol
- ✅ Article VII: Self-documenting through clear names and types

---

## Related Documentation

- **Feature Spec**: [spec.md](./spec.md)
- **Component Contracts**:
  - [base-formatter-protocol.md](./contracts/base-formatter-protocol.md)
  - [formatter-implementations.md](./contracts/formatter-implementations.md)
- **Format Arguments**: See spec 005 for detailed argument system design

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-14 | AI Agent | Initial plan for output formatters |
