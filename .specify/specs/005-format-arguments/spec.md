# Feature: Format Arguments System

> **Spec ID**: 005
> **Status**: Active
> **Created**: 2025-11-14
> **Last Updated**: 2025-11-14

## Overview

Generic system for passing optional arguments to formatters, enabling customization without hardcoding format-specific logic in CLI. Supports both global arguments (all formats) and formatter-specific arguments.

---

## User Stories

### Story 1: Global Format Arguments

**As a** user generating multiple output formats
**I want** to set arguments that apply to all formats
**So that** I don't repeat myself for common customizations

**Acceptance Criteria:**
- [ ] `--format-arg key=value` syntax
- [ ] Global args apply to all formatters
- [ ] Can specify multiple --format-arg flags
- [ ] Common args: note (alert message)

### Story 2: Formatter-Specific Arguments

**As a** user with format-specific needs
**I want** to customize individual formatters
**So that** I can tailor output for specific use cases

**Acceptance Criteria:**
- [ ] `--format-arg formatter.key=value` syntax
- [ ] Specific args override global args
- [ ] Unknown formatters ignored with warning
- [ ] Each formatter declares supported args

### Story 3: Note Display

**As a** league manager sending reports
**I want** to add a custom note at the top
**So that** I can communicate important information

**Acceptance Criteria:**
- [ ] `--format-arg note="Message"` supported
- [ ] Console: Fancy table with note
- [ ] Email: Styled alert box
- [ ] Markdown: Blockquote
- [ ] JSON: Metadata field
- [ ] Sheets: First row

---

## Business Rules

1. **No Business Logic**: Arguments only affect presentation, never calculation
2. **Unknown Args Ignored**: Invalid args warn but don't fail
3. **Type Coercion**: Formatters handle string-to-type conversion
4. **Defaults**: Each formatter provides sensible defaults
5. **Merge Priority**: Specific args override global args

---

## Edge Cases and Error Scenarios

### Edge Case 1: Duplicate Argument Keys

**Situation**: Same key specified multiple times
**Expected Behavior**: Last value wins
**Rationale**: Matches common CLI behavior

### Edge Case 2: Empty Argument Value

**Situation**: `--format-arg note=`
**Expected Behavior**: Treat as empty string, use default
**Rationale**: User may want to clear a value

### Edge Case 3: Special Characters in Value

**Situation**: `--format-arg note="Text with = and , symbols"`
**Expected Behavior**: Parse correctly, preserve special chars
**Rationale**: Users need full flexibility in values

### Error Scenario 1: Invalid Argument Format

**Trigger**: `--format-arg invalidformat`
**Error Handling**: Raise ValueError with usage example
**User Experience**: "Invalid format argument: must be key=value or formatter.key=value"

### Error Scenario 2: Invalid Boolean Value

**Trigger**: `--format-arg json.pretty=maybe`
**Error Handling**: Warn and use default
**User Experience**: "Warning: Invalid boolean 'maybe', using default"

---

## Non-Functional Requirements

### Performance
- Argument parsing adds < 0.1 seconds overhead
- No impact on formatter performance

### Usability
- Syntax intuitive and discoverable via --help
- Error messages guide users to correct syntax
- Common use cases (note) work out of box

### Maintainability
- Adding new formatter arg requires only formatter code change
- No central registry of valid arguments
- Each formatter self-documenting via get_supported_args()

---

## Data Requirements

### Input Data
- **CLI**: Multiple `--format-arg KEY=VALUE` flags
- **Parsing**: Split on first `=`, check for `.` prefix
- **Validation**: Warn on invalid format, don't fail

### Output Data
- **Structure**: Nested dict
  - `_global`: dict[str, str] (global args)
  - `formatter_name`: dict[str, str] (specific args)
- **Merging**: Formatter-specific overrides global

---

## Format-Specific Arguments

### All Formatters
- `note`: Optional message to display prominently

### Email Formatter
- `accent_color`: Hex color code (default: #ffc107)
- `max_teams`: Maximum teams in overall rankings (default: 20)

### Markdown Formatter
- `include_toc`: Generate table of contents (default: false)

### JSON Formatter
- `pretty`: Enable indentation (default: true)

### Console Formatter
- (Only note currently)

### Sheets Formatter
- (Only note currently)

---

## Constraints

### Technical Constraints
- Arguments passed as strings, formatters convert types
- No validation of argument values at CLI level
- Format argument system generic, not format-specific

### Business Constraints
- Arguments must not enable business logic injection
- Arguments affect presentation only
- No security-sensitive values (credentials, etc.)

---

## Out of Scope

- Complex validation of argument values
- Type checking at CLI level
- Required arguments (all optional)
- Argument dependencies (if X then Y required)
- Configuration files for arguments

---

## Success Metrics

- **Usability**: Users successfully customize output
- **Extensibility**: New args added without CLI changes
- **Reliability**: Invalid args don't break formatting

---

## Related Specifications

- **003: Output Formatters**: All formatters use this system
- **CLI Interface**: Implements --format-arg parsing

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-14 | AI Agent | Initial format arguments specification |
