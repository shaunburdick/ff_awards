# FF-Awards Specification Directory

## Purpose

This directory contains **executable specifications** for the Fantasy Football Challenge Tracker. These specs are designed to be consumed by AI coding agents (GitHub Copilot, Cursor, Claude, etc.) to understand, maintain, and extend the system.

## Philosophy: Spec-Driven Development

Unlike traditional documentation, these specifications are:
- **Executable**: AI agents can generate working code directly from these specs
- **Idealized**: They describe what the system *should* do, not necessarily what it currently does
- **Living**: They evolve alongside the codebase and remain the source of truth
- **AI-Native**: Structured specifically for LLM consumption and code generation

## Directory Structure

```
.specify/
├── README.md              # This file - navigation and instructions
├── memory/
│   └── constitution.md    # Immutable architectural principles
├── templates/             # Reusable spec templates
├── specs/                 # Feature specifications
│   └── 001-season-challenges/
│       ├── spec.md        # What: Feature requirements
│       ├── plan.md        # How: Implementation approach
│       ├── research.md    # Why: Technical decisions
│       └── contracts/     # Component interfaces
└── examples/              # Usage examples and expected outputs
```

## How AI Agents Should Use This

### 1. Start with the Constitution
**Always** read `memory/constitution.md` first. It contains immutable principles that govern all development.

### 2. Understand the Feature
Read the relevant `spec.md` to understand:
- What needs to be built (user stories)
- Why it's needed (business value)
- What success looks like (acceptance criteria)

### 3. Review the Implementation Plan
Read `plan.md` to understand:
- Technology choices and rationale
- Architecture patterns
- Component breakdown
- Risk mitigations

### 4. Check Component Contracts
Review files in `contracts/` to understand:
- Interface definitions
- Data structures
- Validation rules
- Usage patterns

### 5. Validate Against Examples
Compare your implementation against files in `examples/` to ensure correctness.

## For Human Developers

These specs serve as:
- **Onboarding Material**: Understand the system quickly
- **Architecture Documentation**: See design decisions and rationale
- **Change Guides**: Modify specs first, then regenerate code
- **Quality Standards**: Constitutional principles ensure consistency

## Current Status

**Active Specifications:**
- ✅ 001: Season-Long Challenges (5 challenges)
- ✅ 002: Weekly Highlights (13 challenges)
- ✅ 003: Output Format System (5 formats)
- ✅ 004: Multi-League Support (divisions)
- ✅ 005: Format Arguments System

## Contributing

When adding new features:
1. Create a new numbered directory in `specs/`
2. Use templates from `templates/` directory
3. Ensure compliance with `memory/constitution.md`
4. Add examples to `examples/` directory
5. Update this README with the new spec status

## Versioning

Specifications are versioned alongside code:
- Specs describe the *desired* state
- Code implements the specs
- When specs change, code should be regenerated or updated to match
- The constitution remains stable; specs evolve

## Tools Compatibility

These specs work with:
- **GitHub Copilot**: Context for autocomplete and suggestions
- **Cursor**: Full feature generation from specs
- **Claude**: Spec-driven implementation workflows
- **Aider**: Spec-guided code modifications
- **Any LLM**: Standard Markdown format, easily parseable

---

**Last Updated**: 2025-11-14
**Spec Version**: 1.0.0
**Project Status**: Production (actively maintained)
