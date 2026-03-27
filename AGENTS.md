# Agent Guidelines for Wikipedia Archive Reader

Guidelines for agentic coding agents working on this repository.

## Build, Test, and Lint Commands

### Essential Commands

**Build the project:**
```bash
make build
```

**Run all tests:**
```bash
make test
```

**Run a single test file:**
```bash
pytest tests/test_archive_reader.py -v
```

**Run a specific test class:**
```bash
pytest tests/test_archive_reader.py::TestCleanText -v
```

**Run a single test:**
```bash
pytest tests/test_archive_reader.py::TestCleanText::test_remove_wikilinks -v
```

**Run tests quickly (without rebuild):**
```bash
make test-quick
```

**Full rebuild (clean + build):**
```bash
make rebuild
```

**Format all code:**
```bash
make format
```

**Lint code quality:**
```bash
make lint
```

## Code Style Guidelines

### Rust Code (`src/lib.rs`)

**Formatting:**
- Use `rustfmt` (invoked via `make format`)
- Default Rust 2021 edition formatting
- 4-space indentation (automatic via rustfmt)

**Naming Conventions:**
- Functions: `snake_case` (e.g., `extract_tag_content`, `remove_nested_braces`)
- Types/Structs: `PascalCase` (e.g., `Article`, `ArchiveReader`, `ArticleIterator`)
- Constants: `SCREAMING_SNAKE_CASE`
- Private functions/modules: prefix with `_` or keep private

**Documentation:**
- All public functions must have `///` doc comments
- Include examples for complex functions
- Document parameters and return values
- Use markdown formatting in comments

Example:
```rust
/// Removes wikilinks from text (content within [[ ]])
/// Preserves the link text, removes the brackets.
///
/// # Arguments
/// * `text` - The text to process
///
/// # Returns
/// String with wikilinks converted to plain text
fn remove_wikilinks(text: &str) -> String {
    // implementation
}
```

**Type Annotations:**
- Always explicit on function signatures
- Use specific types (avoid `String` where `&str` works)
- Leverage Rust's type system for safety

**Error Handling:**
- Use `Result<T, E>` for fallible operations
- Convert to `PyResult` at FFI boundaries
- Use `.map_err()` to provide context
- Never unwrap in production code (except in tests)

Example:
```rust
fn open_file(path: &str) -> PyResult<BufReader<File>> {
    File::open(path)
        .map_err(|e| PyErr::new::<PyIOError, _>(e.to_string()))
        .map(BufReader::new)
}
```

### Python Code (`tests/`, `wikipedia_archive_reader/`)

**Formatting:**
- Use `black` (invoked via `make format`)
- 88-character line length (black default)
- 4-space indentation

**Naming Conventions:**
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `SCREAMING_SNAKE_CASE`
- Private members: `_leading_underscore`

**Type Hints:**
- Use type hints for function signatures (required for test files)
- Import from `typing` when needed
- Example: `def test_something(self) -> None:`

**Docstrings:**
- Use triple-quoted docstrings for modules, classes, and functions
- Format: `"""Summary line. More details if needed."""`
- For tests, keep docstrings brief and descriptive

Example:
```python
def test_remove_wikilinks(self):
    """Test removal of wikilinks from text"""
    result = clean_text("[[link|text]]")
    assert "[[" not in result
```

**Test Structure:**
- Organize tests in classes (e.g., `TestCleanText`, `TestArchiveReader`)
- Use descriptive test names starting with `test_`
- Follow Arrange-Act-Assert pattern
- Use `@pytest.fixture` for setup/teardown

### Imports

**Rust:**
- Group imports by: standard library, external crates, internal modules
- Use `use` statements at module level
- Import specific items when possible: `use std::io::BufRead;`

Example:
```rust
use pyo3::prelude::*;
use std::fs::File;
use std::io::{BufRead, BufReader};
use regex::Regex;
```

**Python:**
- Standard library first
- Third-party packages second
- Project imports last
- Alphabetical within groups

Example:
```python
import os
import tempfile
from pathlib import Path

import pytest

from wikipedia_archive_reader import ArchiveReader, Article, clean_text
```

## Project Structure

```
src/lib.rs                    # Main Rust implementation (324 lines)
│ ├── Article struct          # Article data class
│ ├── ArchiveReader struct    # Main reader interface
│ ├── ArticleIterator struct  # Streaming parser
│ ├── ReaderSource enum       # Stdin/file abstraction
│ └── clean_text() function   # Text cleaning API

wikipedia_archive_reader/
├── __init__.py              # Package initialization and exports

tests/
└── test_archive_reader.py   # 24 comprehensive unit tests

Makefile                      # 8 build targets
pyproject.toml               # Python packaging config
Cargo.toml                   # Rust packaging config
```

## Key Design Patterns

**State Machine (ArticleIterator):**
- Tracks `in_article`, `in_text`, `in_revision` flags
- Processes line-by-line for O(1) memory
- Yields complete `Article` objects

**Enum for Type Abstraction (ReaderSource):**
- Supports both File and Stdin without trait objects
- Avoids runtime dispatch overhead
- Type-safe with pattern matching

**PyO3 Integration:**
- Use `#[pyclass]` for exportable structs
- Use `#[pyfunction]` for module-level functions
- Use `#[pymethods]` for method implementations
- Use `#[pyo3(get)]` for public fields

## Development Workflow

1. **Modify code** in `src/lib.rs` or test files
2. **Rebuild:** `make rebuild` (if major changes)
3. **Test:** `make test` to run full test suite
4. **Specific test:** Use `pytest` command for targeted testing
5. **Format:** `make format` before committing
6. **Lint:** `make lint` to check code quality

## Virtual Environment

- **Python version:** 3.8+
- **Location:** `.venv/`
- **Dependencies installed via:** `uv pip install`
- **Never install packages outside the venv**

Activate:
```bash
source .venv/bin/activate
```

## Performance Considerations

- Streaming parser processes one article per iteration (no buffering)
- Memory usage is O(1) relative to archive size
- Text cleaning uses compiled regex patterns
- Targets: 100,000+ articles/minute on modern hardware

## When Tests Fail

1. **Rebuild:** `make rebuild` to ensure fresh compilation
2. **Check encoding:** Ensure UTF-8: `export PYTHONIOENCODING=utf-8`
3. **Verbose output:** Use `pytest -v -s` to see print statements
4. **Single test:** Isolate with specific test command (see Build/Test section)
5. **Check venv:** Ensure `.venv` is activated

## External Tools Used

- **rustfmt:** Code formatting (Rust)
- **black:** Code formatting (Python)
- **pytest:** Test runner
- **maturin:** Build system (PyO3 -> Python extension)
- **uv:** Package/venv manager
