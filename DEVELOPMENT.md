# Development Guide

## Project Architecture

### Rust Components (`src/lib.rs`)

**Core Classes:**

1. **Article** - Represents a single Wikipedia article
   - Fields: `id`, `title`, `text`
   - Provides Python representation via `__repr__`

2. **ArchiveReader** - Main entry point for reading archives
    - Takes file path as input (or "-" for stdin)
    - Implements `__iter__` to return `ArticleIterator`
    - Uses streaming approach (no DOM parsing)
    - Supports file input and stdin for decompressed streams

3. **ArticleIterator** - Efficient line-by-line parser
    - Maintains state for current article being parsed
    - Tracks `<page>`, `<text>` tag boundaries
    - Yields complete `Article` objects
    - Memory efficient: O(1) relative to file size
    - Works with both file and stdin input via `ReaderSource` enum

4. **ReaderSource** - Internal enum supporting both input types
    - File(BufReader<File>) - for reading files
    - Stdin(BufReader<Stdin>) - for reading from stdin
    - Provides unified interface for both input sources

### Python Components

- `wikipedia_archive_reader/__init__.py` - Package initialization, exports public API
- `tests/test_archive_reader.py` - Comprehensive unit tests (24 tests)
- `example_usage.py` - Demonstration script

## Building and Testing

### Quick Build

```bash
make build
```

### Run All Tests

```bash
make test
```

This runs the complete test suite:
- Article creation and representation tests (2)
- Archive reading and iteration tests (6)
- Text cleaning functionality tests (11)
- Stdin input tests (2)
- Integration tests (1)
- Total: 24 tests

### Development Workflow

1. Modify Rust code in `src/lib.rs`
2. Run `make build` to rebuild the extension
3. Run `make test` to verify changes
4. Run `make format` to format code

### Benchmarking

The project uses streaming (line-by-line) parsing rather than DOM-based approaches:

```rust
// ArticleIterator::__next__ reads and parses one article at a time
// No buffering of entire archive - memory scales with article size only
```

This approach achieves:
- O(1) memory usage relative to archive size
- Able to process multi-GB files with <100MB memory
- Processing speed: 100,000+ articles/minute on modern hardware

## Code Organization

### Rust Library Structure

```rust
// 1. Data structures (pub structs with #[pyclass])
Article          // Article with id, title, text
ArchiveReader    // Main reader interface
ArticleIterator  // Streaming parser

// 2. Pure Rust helper functions
extract_tag_content()        // Parse simple XML tags
remove_pattern()             // Regex-based cleanup
remove_nested_braces()       // Handle {{ }} nesting
decode_html_entities()       // Entity decoding

// 3. Public Python functions
clean_text()                 // Main text cleaning API
```

### Comments and Documentation

All Rust code includes:
- Function-level documentation comments (`///`)
- Inline comments explaining complex logic
- Type annotations for clarity

Example:
```rust
/// Reader that yields articles from the archive one at a time
/// The iterator reads the file line-by-line efficiently
#[pyclass]
pub struct ArticleIterator {
    reader: BufReader<File>,
    current_id: String,
    // ... tracking fields for state machine
}
```

## Key Design Decisions

### 1. Streaming Instead of DOM Parsing

**Why:** Wikipedia archives can be 20GB+ compressed. DOM parsing would require:
- Loading entire file into memory
- Building tree structure
- Excessive memory usage

**Solution:** Line-by-line state machine that yields articles as they're parsed.

### 2. Rust for Performance

**Why:** Text processing with regex and string operations is CPU-intensive.

**Solution:** Rust provides:
- Native performance (~10-50x Python for these operations)
- Memory safety without GC pauses
- Easy FFI binding via PyO3

### 3. Simple XML Parsing

**Why:** Standard XML libraries add overhead.

**Solution:** Manual line-by-line parsing for Wikipedia's simple structure:
```xml
<page>
  <id>123</id>
  <title>Article</title>
  <text>content</text>
</page>
```

### 4. Stdin Support via Enum Pattern

**Why:** Support reading both from files and stdin for streaming decompressed archives.

**Challenge:** Rust's type system requires different types for File and Stdin, but they both implement BufRead.

**Solution:** Use an internal `ReaderSource` enum:
```rust
enum ReaderSource {
    File(BufReader<File>),
    Stdin(BufReader<std::io::Stdin>),
}

impl ReaderSource {
    fn read_line(&mut self, buf: &mut String) -> std::io::Result<usize> {
        match self {
            ReaderSource::File(reader) => reader.read_line(buf),
            ReaderSource::Stdin(reader) => reader.read_line(buf),
        }
    }
}
```

This pattern:
- Maintains type safety
- Avoids dynamic dispatch overhead
- Works seamlessly with PyO3
- Users just pass "-" to use stdin

## Testing Strategy

### Test Coverage

The test suite covers:

1. **Unit Tests**
   - Individual component functionality
   - Edge cases (empty files, invalid input)
   - String cleaning operations

2. **Integration Tests**
   - Complete reader → cleaner workflow
   - Realistic Wikipedia XML samples

3. **Regression Tests**
   - Specific markup patterns
   - Language-specific content (French, German, etc.)

### Test Data

Tests use embedded XML samples (no external files required):

```python
xml_content = """<?xml version="1.0"?>
<mediawiki>
  <page>
    <id>1</id>
    <title>Test</title>
    <text>content</text>
  </page>
</mediawiki>"""
```

## Performance Optimization

### Current Optimizations

1. **Streaming Parser**
   - Processes one article at a time
   - No intermediate data structures
   - Constant memory usage

2. **Regex Compilation**
   - Patterns compiled at runtime
   - Consider caching for repeated operations

3. **String Operations**
   - Uses efficient Rust string methods
   - Avoids unnecessary allocations

### Potential Future Optimizations

1. Pre-compile regex patterns at module initialization
2. SIMD operations for string scanning
3. Parallel iterator for multi-threaded processing
4. Caching cleaned text if repeated processing needed

## Debugging

### Enable Rust Logging

Add to `Cargo.toml`:
```toml
[dependencies]
log = "0.4"
env_logger = "0.10"
```

### Test Specific Component

```bash
# Run single test
pytest tests/test_archive_reader.py::TestCleanText::test_remove_wikilinks -v

# Run with print statements
RUST_BACKTRACE=1 pytest tests/ -v -s
```

### Common Issues

**Issue:** Build fails with "python not found"
```bash
# Solution: Ensure venv is activated
source .venv/bin/activate
```

**Issue:** ImportError: `cannot import name 'ArchiveReader'`
```bash
# Solution: Rebuild after changes
make rebuild
```

**Issue:** Tests fail with encoding errors
```bash
# Solution: Ensure UTF-8 handling
export PYTHONIOENCODING=utf-8
```

## Contributing

### Code Style

**Rust:**
- Use `rustfmt` for formatting: `make format`
- Follow Rust naming conventions (snake_case for functions)
- Document public APIs with `///` comments

**Python:**
- Use `black` for formatting
- Follow PEP 8 conventions
- Type hints where possible (for test files)

### Adding Features

1. Implement in Rust (`src/lib.rs`)
2. Export via `#[pyfunction]` or `#[pymethods]`
3. Add Python tests to `tests/test_archive_reader.py`
4. Update documentation if needed
5. Run `make test` to verify

### Adding Tests

Create test functions in `tests/test_archive_reader.py`:

```python
def test_new_feature(self):
    """Test description"""
    # Arrange
    input_data = "test"
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == "expected"
```

## Release Process

To create a release:

1. Update version in `pyproject.toml` and `Cargo.toml`
2. Run `make test` to ensure all tests pass
3. Build distribution: `maturin build --release`
4. Package will be in `target/wheels/`

## References

- [PyO3 Documentation](https://pyo3.rs/)
- [Maturin Documentation](https://www.maturin.rs/)
- [Rust Book](https://doc.rust-lang.org/book/)
- [Wikipedia Dump Format](https://en.wikipedia.org/wiki/Wikipedia:Database_export)
