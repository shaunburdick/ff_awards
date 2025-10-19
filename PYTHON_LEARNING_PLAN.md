# Fantasy Football Tracker - Python Learning Plan

## Your Profile & Goals 🎯
- **Background**: 20 years programming experience (TypeScript/JavaScript/PHP)
- **Python Experience**: Complete beginner
- **Learning Focus**: "Pythonic" patterns, data processing, algorithms
- **Time Investment**: Quick wins (1-2 hours) + Weekend projects (4-8 hours)
- **Fantasy Football**: Very familiar - ready for new challenge types

## Learning Path Overview 🗺️

This plan leverages your existing programming knowledge while teaching Python-specific patterns. Each enhancement teaches core Python concepts through practical application.

---

## Phase 1: Python Fundamentals Through Quick Wins 🚀
*Goal: Learn Python syntax, data structures, and basic patterns*

### 📝 **Enhancement 1: Current Week Detection** *(1-2 hours)*
**Python Concepts**: Date/time handling, conditional logic, function design
**Difficulty**: ⭐⭐☆☆☆ | **Learning Value**: ⭐⭐⭐⭐☆

#### What You'll Learn:
- Python's `datetime` module vs JavaScript's `Date`
- Type hints and function annotations
- Python's import system
- Docstring conventions

#### The Task:
Improve the year detection logic in `ff_tracker/config.py` to auto-detect the current fantasy football season.

**Current Code** (line 147):
```python
# Determine year (could be enhanced to auto-detect current fantasy year)
import datetime
resolved_year = year if year is not None else datetime.datetime.now().year
```

#### Your Mission:
Fantasy football seasons run from late August to late December. Create logic that:
- Before August: Use previous year (e.g., in March 2025, use 2024 season)
- August-December: Use current year (e.g., in October 2025, use 2025 season)

#### Pythonic Patterns to Learn:
```python
from datetime import datetime
from typing import Optional

def detect_fantasy_year(override_year: Optional[int] = None) -> int:
    """
    Detect the current fantasy football season year.

    Fantasy seasons run from August to December, so:
    - January-July: Previous year's season
    - August-December: Current year's season
    """
    if override_year is not None:
        return override_year

    now = datetime.now()
    return now.year if now.month >= 8 else now.year - 1
```

#### JS/TS vs Python Differences:
- **Import**: `from datetime import datetime` vs `import { DateTime } from 'luxon'`
- **Type Hints**: `Optional[int]` vs `number | undefined`
- **Docstrings**: Triple quotes vs JSDoc comments
- **Snake Case**: `override_year` vs `overrideYear`

**✅ Success Criteria:**
- [ ] Function correctly detects fantasy year based on current date
- [ ] Proper type hints throughout
- [ ] Good docstring explaining the logic
- [ ] Integration with existing config system

---

### 📝 **Enhancement 2: Enhanced Username Detection** *(1-2 hours)*
**Python Concepts**: String methods, list comprehensions, boolean logic
**Difficulty**: ⭐⭐☆☆☆ | **Learning Value**: ⭐⭐⭐☆☆

#### What You'll Learn:
- Python string methods vs JavaScript
- List comprehensions (Python's killer feature!)
- Generator expressions
- `any()` and `all()` built-ins

#### The Task:
Improve the `_looks_like_username` function in both the old and new code to better detect usernames vs real names.

**Current Logic** (from original monolithic script):
```python
def _looks_like_username(self, name: str) -> bool:
    username_indicators = [
        name.startswith('ESPNFAN'),
        name.startswith('espn'),
        len(name) > 15 and any(c.isdigit() for c in name),
        name.islower() and len(name) > 8,
        sum(c.isdigit() for c in name) > len(name) // 2,
    ]
    return any(username_indicators)
```

#### Your Mission:
Add more sophisticated detection patterns:
- All caps names (likely usernames)
- Names with underscores or numbers
- Common username prefixes/suffixes
- Very short names (< 3 characters)

#### Pythonic Patterns to Learn:
```python
def looks_like_username(name: str) -> bool:
    """Check if a name appears to be a username rather than a real name."""
    name = name.strip()
    if not name:
        return True

    # Python's any() with generator expression - very pythonic!
    username_patterns = [
        name.startswith(('ESPNFAN', 'espn', 'user', 'player')),
        '_' in name or '-' in name,
        name.isupper() and len(name) > 4,  # ALL CAPS
        len(name) < 3,  # Too short
        # List comprehension to count digits
        sum(1 for c in name if c.isdigit()) > len(name) // 3,
        # Check for common username endings
        name.lower().endswith(('123', '2024', '2025', 'ff', 'fb')),
    ]

    return any(username_patterns)
```

#### JS/TS vs Python Key Differences:
- **String Methods**: `.startswith(tuple)` vs `.startsWith()`
- **List Comprehensions**: `[expr for item in iterable]` vs `.map()`
- **Generator Expressions**: `(expr for item in iterable)` - memory efficient!
- **Built-ins**: `any()`, `all()` vs manual loops

**✅ Success Criteria:**
- [ ] Improved username detection accuracy
- [ ] Uses list comprehensions and generator expressions
- [ ] Comprehensive test cases for edge cases
- [ ] Documentation explaining the detection logic

---

### 📝 **Enhancement 3: Simple Data Export Formatter** *(1-2 hours)*
**Python Concepts**: Protocol pattern, JSON handling, file I/O
**Difficulty**: ⭐⭐☆☆☆ | **Learning Value**: ⭐⭐⭐⭐☆

#### What You'll Learn:
- Python's Protocol typing (like TypeScript interfaces)
- JSON serialization vs JavaScript
- File handling with context managers
- The `pathlib` module (modern file paths)

#### The Task:
Create a JSON formatter for the display system following the existing Protocol pattern.

#### Your Mission:
Add `ff_tracker/display/json.py` that exports data as clean JSON.

#### Pythonic Patterns to Learn:
```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import Formatter
from ..models import DivisionData, ChallengeResult

class JsonFormatter(Formatter):
    """Export fantasy football data as JSON."""

    def format_results(self, divisions: list[DivisionData], challenges: list[ChallengeResult]) -> str:
        """Format results as JSON string."""
        # Dictionary comprehension - very pythonic!
        data = {
            "divisions": [
                {
                    "name": div.name,
                    "league_id": div.league_id,
                    "teams": [
                        {
                            "name": team.name,
                            "owner": team.owner,
                            "points_for": team.points_for,
                            "points_against": team.points_against,
                            "wins": team.wins,
                            "losses": team.losses,
                        }
                        for team in div.teams  # List comprehension inside dict
                    ]
                }
                for div in divisions
            ],
            "challenges": [
                {
                    "name": challenge.challenge_name,
                    "winner": challenge.winner,
                    "owner": challenge.owner,
                    "division": challenge.division,
                    "description": challenge.description,
                }
                for challenge in challenges
            ]
        }

        # Python's json module with pretty printing
        return json.dumps(data, indent=2, ensure_ascii=False)
```

#### JS/TS vs Python Key Differences:
- **Protocols**: `Protocol` vs `interface`
- **List Comprehensions**: Nested comprehensions vs nested `.map()`
- **JSON**: `json.dumps()` vs `JSON.stringify()`
- **Context Managers**: `with open()` vs manual file handling

**✅ Success Criteria:**
- [ ] Follows existing Protocol pattern
- [ ] Clean, well-structured JSON output
- [ ] Proper error handling for file operations
- [ ] Integration with CLI `--format json`

---

## Phase 2: Data Processing & Algorithm Design 🧮
*Goal: Learn Python's data processing strengths and algorithm patterns*

### 📝 **Enhancement 4: Advanced Challenge Types** *(Weekend Project - 4-6 hours)*
**Python Concepts**: Algorithm design, data analysis, statistical functions
**Difficulty**: ⭐⭐⭐☆☆ | **Learning Value**: ⭐⭐⭐⭐⭐

#### What You'll Learn:
- Python's data processing patterns
- Statistical analysis with built-ins
- Algorithm design for sports analytics
- Working with collections and itertools

#### The Task:
Design and implement 3-5 new fantasy football challenges that could be used next season.

#### Suggested New Challenges:
1. **Most Consistent Team** - Lowest standard deviation in weekly scores
2. **Biggest Blowout** - Largest margin of victory
3. **Most Unlucky Team** - Highest points against average
4. **Boom or Bust** - Highest scoring variance (inconsistent team)
5. **Best Draft** - Team performance vs draft position correlation

#### Your Mission:
Add new challenge methods to `ChallengeService` class.

#### Pythonic Patterns to Learn:
```python
import statistics
from collections import defaultdict
from itertools import groupby

def calculate_most_consistent_team(self) -> ChallengeResult:
    """Find team with most consistent weekly scores (lowest std dev)."""
    if not self.games:
        return self._create_no_data_placeholder("Most Consistent Team")

    # Group games by team using defaultdict - very pythonic!
    team_scores = defaultdict(list)
    for game in self.games:
        team_scores[game.team_name].append(game.score)

    # Find team with lowest standard deviation
    most_consistent = min(
        team_scores.items(),
        key=lambda item: statistics.stdev(item[1]) if len(item[1]) > 1 else float('inf')
    )

    team_name, scores = most_consistent
    std_dev = statistics.stdev(scores)

    return ChallengeResult(
        challenge_name="Most Consistent Team",
        winner=team_name,
        owner=self._get_owner_for_team(team_name),
        division=self._get_division_for_team(team_name),
        description=f"Std Dev: {std_dev:.2f} points"
    )

def calculate_biggest_blowout(self) -> ChallengeResult:
    """Find the largest margin of victory."""
    if not self.games:
        return self._create_no_data_placeholder("Biggest Blowout")

    # Using max with key function - pythonic way to find maximum
    biggest_win = max(
        (game for game in self.games if game.won),
        key=lambda game: game.margin,
        default=None
    )

    if not biggest_win:
        return self._create_no_data_placeholder("Biggest Blowout")

    return ChallengeResult(
        challenge_name="Biggest Blowout",
        winner=biggest_win.team_name,
        owner=self._get_owner_for_team(biggest_win.team_name),
        division=biggest_win.division,
        description=f"Won by {biggest_win.margin:.1f} points (Week {biggest_win.week})"
    )
```

#### Fantasy Football Algorithm Concepts:
- **Consistency Analysis**: Standard deviation, variance
- **Performance Metrics**: Points per game, strength of schedule
- **Comparative Analysis**: Team vs league averages
- **Trend Analysis**: Performance over time

#### JS/TS vs Python Key Differences:
- **Statistics Module**: Built-in `statistics.stdev()` vs manual calculation
- **Collections**: `defaultdict` vs `Map` or objects
- **Iterator Tools**: `itertools.groupby()` vs manual grouping
- **Generator Expressions**: Memory-efficient data processing

**✅ Success Criteria:**
- [ ] 3+ new challenges implemented
- [ ] Proper statistical calculations
- [ ] Good algorithm design and efficiency
- [ ] Comprehensive testing with real data
- [ ] Documentation for each challenge logic

---

### 📝 **Enhancement 5: Caching System** *(Weekend Project - 4-6 hours)*
**Python Concepts**: Decorators, file I/O, serialization, performance optimization
**Difficulty**: ⭐⭐⭐☆☆ | **Learning Value**: ⭐⭐⭐⭐☆

#### What You'll Learn:
- Python decorators (function wrappers)
- Pickle serialization vs JSON
- File-based caching strategies
- Performance measurement

#### The Task:
Add optional caching to ESPN API calls to speed up repeated runs during development.

#### Your Mission:
Create a caching decorator that can be applied to ESPN service methods.

#### Pythonic Patterns to Learn:
```python
import pickle
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

F = TypeVar('F', bound=Callable[..., Any])

def cache_api_call(cache_duration_hours: int = 1) -> Callable[[F], F]:
    """
    Decorator to cache ESPN API calls to disk.

    This is a higher-order function that returns a decorator - advanced Python!
    """
    def decorator(func: F) -> F:
        @wraps(func)  # Preserves original function metadata
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            cache_file = Path(f".cache/{cache_key}.pkl")

            # Check if cache exists and is fresh
            if cache_file.exists():
                cache_age = time.time() - cache_file.stat().st_mtime
                if cache_age < cache_duration_hours * 3600:
                    with cache_file.open('rb') as f:
                        return pickle.load(f)

            # Cache miss - call original function
            result = func(*args, **kwargs)

            # Save to cache
            cache_file.parent.mkdir(exist_ok=True)
            with cache_file.open('wb') as f:
                pickle.dump(result, f)

            return result
        return wrapper
    return decorator

# Usage in ESPNService:
class ESPNService:
    @cache_api_call(cache_duration_hours=2)
    def extract_division_data(self, league_id: int, year: int) -> DivisionData:
        # Original expensive API call
        pass
```

#### Advanced Python Concepts:
- **Decorators**: Function modification without changing source
- **Higher-Order Functions**: Functions that return functions
- **Type Variables**: Generic type annotations
- **Context Managers**: `with` statements for resource management
- **Path Objects**: Modern file path handling

**✅ Success Criteria:**
- [ ] Configurable cache duration
- [ ] Proper cache invalidation
- [ ] Performance improvement measurement
- [ ] Clean decorator implementation
- [ ] Optional caching (can be disabled)

---

## Phase 3: Advanced Python Patterns 🏗️
*Goal: Learn sophisticated Python architecture and design patterns*

### 📝 **Enhancement 6: Plugin System for New Challenges** *(Weekend Project - 6-8 hours)*
**Python Concepts**: Abstract base classes, dynamic imports, plugin architecture
**Difficulty**: ⭐⭐⭐⭐☆ | **Learning Value**: ⭐⭐⭐⭐⭐

#### What You'll Learn:
- Abstract Base Classes (ABC)
- Dynamic module loading
- Plugin architecture patterns
- Metaclasses (advanced)

#### The Task:
Create a plugin system where new challenges can be added as separate files without modifying core code.

#### Your Mission:
Design a system where challenges are auto-discovered and loaded.

#### Advanced Python Patterns:
```python
from abc import ABC, abstractmethod
from typing import Protocol
import importlib
import pkgutil

class ChallengePlugin(ABC):
    """Abstract base class for challenge plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Challenge name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Challenge description."""
        pass

    @abstractmethod
    def calculate(self, games: list[GameResult], teams: list[TeamStats]) -> ChallengeResult:
        """Calculate challenge result."""
        pass

class PluginLoader:
    """Dynamically load challenge plugins."""

    def load_plugins(self, plugin_dir: str = "challenges") -> list[ChallengePlugin]:
        """Load all challenge plugins from directory."""
        plugins = []

        # Dynamic import - advanced Python feature
        for finder, name, ispkg in pkgutil.iter_modules([plugin_dir]):
            module = importlib.import_module(f"{plugin_dir}.{name}")

            # Find all classes that inherit from ChallengePlugin
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, ChallengePlugin) and
                    attr is not ChallengePlugin):
                    plugins.append(attr())

        return plugins
```

**✅ Success Criteria:**
- [ ] Plugin auto-discovery system
- [ ] Proper abstract base classes
- [ ] Example plugin implementations
- [ ] Integration with main challenge system
- [ ] Documentation for plugin developers

---

## Learning Resources by Phase 📚

### Phase 1 Resources:
- **Python vs JavaScript**: [Python for JavaScript Developers](https://realpython.com/python-vs-javascript/)
- **Type Hints**: [Python Type Hints](https://docs.python.org/3/library/typing.html)
- **List Comprehensions**: [Real Python List Comprehensions](https://realpython.com/list-comprehension-python/)

### Phase 2 Resources:
- **Data Processing**: [Python for Data Analysis](https://wesmckinney.com/book/)
- **Statistics Module**: [Python Statistics](https://docs.python.org/3/library/statistics.html)
- **Itertools**: [Itertools Recipes](https://docs.python.org/3/library/itertools.html)

### Phase 3 Resources:
- **Decorators**: [Real Python Decorators](https://realpython.com/primer-on-python-decorators/)
- **Abstract Base Classes**: [Python ABC](https://docs.python.org/3/library/abc.html)
- **Plugin Systems**: [Architecture Patterns with Python](https://www.cosmicpython.com/)

---

## Progress Tracking 📊

### Phase 1: Fundamentals ✅
- [ ] Current Week Detection
- [ ] Enhanced Username Detection
- [ ] JSON Export Formatter

### Phase 2: Data Processing ✅
- [ ] Advanced Challenge Types
- [ ] Caching System

### Phase 3: Advanced Patterns ✅
- [ ] Plugin System for Challenges

### Bonus Challenges 🎯
- [ ] Performance Benchmarking Tool
- [ ] Configuration Validation System
- [ ] Async API Calls (advanced)
- [ ] Data Visualization Integration

---

## Pythonic Principles You'll Master 🐍

1. **"Explicit is better than implicit"** - Clear, readable code
2. **"Simple is better than complex"** - Elegant solutions
3. **"Readability counts"** - Code as communication
4. **"There should be one obvious way to do it"** - Pythonic idioms
5. **"Beautiful is better than ugly"** - Clean, well-structured code

### Key Python vs JS/TS Mindset Shifts:
- **Duck Typing**: "If it walks like a duck..." vs strict interfaces
- **Generator Expressions**: Lazy evaluation vs eager computation
- **Context Managers**: Resource handling vs manual management
- **List Comprehensions**: Functional style vs imperative loops
- **Decorators**: Aspect-oriented programming vs inheritance

---

## Getting Started 🚀

1. **Pick Enhancement 1** (Current Week Detection)
2. **Read the relevant section** above
3. **Look at the existing code** in the mentioned files
4. **Start coding!** Don't worry about perfection
5. **Test your changes** with real data
6. **Check off your progress** in this file

Remember: You have 20 years of programming experience. Python syntax is just new clothes on familiar concepts. Focus on learning the "Pythonic way" of expressing ideas you already understand!

**Happy Coding! 🐍🏈**