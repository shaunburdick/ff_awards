# Implementation Plan: Format Arguments System

> **Spec ID**: 005
> **Status**: Implemented
> **Created**: 2025-11-14
> **Last Updated**: 2025-11-14

## Technology Choices

### Primary Stack
- **Language**: Python 3.9+
- **Pattern**: Dictionary-based parameter passing
- **Parsing**: Simple string splitting with validation

### Rationale
String-to-dict parsing is straightforward. Nested dict structure (global + formatter-specific) enables easy merging. Formatters responsible for type coercion keeps CLI generic.

**Constitutional Compliance**:
- Article I: 100% type coverage in parsing and helper functions
- Article VII: Self-documenting through clear function names

---

## Architecture Pattern

**Pattern**: Parameter Object with Helper Methods

**Justification**: Formatters receive dict of args, use helper methods to extract typed values. No central validation—formatters declare and handle their own args.

**Constitutional Compliance**:
- Article IV: CLI parses, formatters interpret (separation)
- No business logic in argument system

---

## Component Breakdown

### Component 1: CLI Argument Parsing

**Purpose**: Parse --format-arg flags into nested dict

**Responsibilities**:
- Split "key=value" or "formatter.key=value"
- Build nested dict structure
- Validate format (must have `=`)
- Accumulate multiple --format-arg flags

**Interface**:
```python
def parse_format_args(args_list: list[str] | None) -> dict[str, dict[str, str]]:
    """
    Parse format arguments into nested dictionary.

    Returns:
        {"_global": {...}, "formatter_name": {...}}
    """
```

### Component 2: Argument Merging

**Purpose**: Merge global and formatter-specific args

**Responsibilities**:
- Extract global args for formatter
- Override with formatter-specific args
- Return merged dict

**Interface**:
```python
def get_formatter_args(
    format_name: str,
    format_args_dict: dict[str, dict[str, str]]
) -> dict[str, str]:
    """Get merged arguments for specific formatter."""
```

### Component 3: BaseFormatter Helper Methods

**Purpose**: Type-safe argument extraction

**Responsibilities**:
- Extract string value with default
- Convert to boolean with validation
- Convert to integer with validation
- Handle missing keys gracefully

**Interface**:
```python
class BaseFormatter:
    format_args: dict[str, str]

    def _get_arg(self, key: str, default: str = "") -> str:
        """Get argument as string."""
        return self.format_args.get(key, default)

    def _get_arg_bool(self, key: str, default: bool = False) -> bool:
        """Get argument as boolean."""
        value = self.format_args.get(key, "").lower()
        if value in ("true", "yes", "1"):
            return True
        if value in ("false", "no", "0"):
            return False
        return default

    def _get_arg_int(self, key: str, default: int) -> int:
        """Get argument as integer."""
        try:
            return int(self.format_args.get(key, ""))
        except ValueError:
            return default
```

### Component 4: Formatter Self-Documentation

**Purpose**: Each formatter declares supported args

**Responsibilities**:
- List argument names
- Provide descriptions
- Specify defaults
- Used by --help generation

**Interface**:
```python
class ConsoleFormatter:
    @classmethod
    def get_supported_args(cls) -> dict[str, str]:
        """Return dict of {arg_name: description}."""
        return {
            "note": "Optional message displayed at top"
        }
```

---

## Data Flow

```
CLI: --format-arg note="Test" --format-arg email.accent_color="#ff0000"
    ↓
parse_format_args([...])
    ↓
{
    "_global": {"note": "Test"},
    "email": {"accent_color": "#ff0000"}
}
    ↓
Create email formatter:
    formatter_args = get_formatter_args("email", format_args_dict)
    # {"note": "Test", "accent_color": "#ff0000"}
    ↓
EmailFormatter(year, formatter_args)
    ↓
In formatter methods:
    note = self._get_arg("note")
    accent = self._get_arg("accent_color", "#ffc107")
    max_teams = self._get_arg_int("max_teams", 20)
```

---

## Implementation Phases

### Phase 1: Parsing Infrastructure

**Goal**: Parse --format-arg into nested dict

**Tasks**:
- [ ] Implement parse_format_args
- [ ] Handle global args (_global key)
- [ ] Handle formatter-specific args (formatter.key)
- [ ] Validate format (must have =)
- [ ] Test with various inputs

**Deliverable**: Parsing works correctly

**Dependencies**: None

### Phase 2: Merging Logic

**Goal**: Merge global and specific args

**Tasks**:
- [ ] Implement get_formatter_args
- [ ] Test override behavior (specific wins)
- [ ] Handle missing formatters gracefully

**Deliverable**: Merging works correctly

**Dependencies**: Phase 1 complete

### Phase 3: BaseFormatter Helpers

**Goal**: Add type-safe extraction methods

**Tasks**:
- [ ] Implement _get_arg
- [ ] Implement _get_arg_bool
- [ ] Implement _get_arg_int
- [ ] Add to BaseFormatter protocol

**Deliverable**: Formatters can extract typed values

**Dependencies**: Phase 2 complete

### Phase 4: Formatter Implementation

**Goal**: Use arguments in all formatters

**Tasks**:
- [ ] Implement note display in all formatters
- [ ] Add email-specific args (accent_color, max_teams)
- [ ] Add markdown-specific args (include_toc)
- [ ] Add json-specific args (pretty)
- [ ] Update formatter constructors to accept args

**Deliverable**: All formatters support arguments

**Dependencies**: Phase 3 complete

### Phase 5: CLI Integration

**Goal**: Wire to CLI and help text

**Tasks**:
- [ ] Add --format-arg to argparse
- [ ] Call parsing functions
- [ ] Pass args to formatters
- [ ] Update --help with examples
- [ ] Test end-to-end

**Deliverable**: System working in CLI

**Dependencies**: Phase 4 complete

---

## Performance Considerations

**Expected Load**: 5-10 format arguments typical
**Performance Target**: < 0.1 seconds parsing overhead
**Current Performance**: < 0.01 seconds (negligible)

---

## Complexity Tracking

> No constitutional deviations.

System is pure presentation customization, no business logic.

---

## Related Documentation

- **Feature Spec**: [spec.md](./spec.md)
- **BaseFormatter Protocol**: See spec 003 contracts
- **CLI Implementation**: main.py parse_format_args and get_formatter_args

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-14 | AI Agent | Initial format arguments plan |
