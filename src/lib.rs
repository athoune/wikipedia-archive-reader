use pyo3::prelude::*;
use std::fs::File;
use std::io::{BufRead, BufReader};

/// Represents a Wikipedia article with its ID and text content
#[pyclass]
#[derive(Clone, Debug)]
pub struct Article {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub title: String,
    #[pyo3(get)]
    pub text: String,
}

#[pymethods]
impl Article {
    #[new]
    fn new(id: String, title: String, text: String) -> Self {
        Article { id, title, text }
    }

    fn __repr__(&self) -> String {
        format!(
            "Article(id='{}', title='{}', text_length={})",
            self.id,
            self.title,
            self.text.len()
        )
    }
}

/// Fast, streaming reader for Wikipedia XML archives
/// Reads line-by-line without building a DOM tree
/// Pass file path or "-" to read from stdin
#[pyclass]
pub struct ArchiveReader {
    file_path: String,
}

#[pymethods]
impl ArchiveReader {
    /// Initialize the reader with a file path or "-" for stdin
    /// 
    /// Args:
    ///     file_path: Path to XML file, or "-" to read from stdin
    ///                Useful with: zstdcat archive.xml.zst - or gzcat archive.xml.gz -
    ///
    /// Assumes UTF-8 encoding and valid Wikipedia XML structure
    #[new]
    fn new(file_path: String) -> PyResult<Self> {
        Ok(ArchiveReader { file_path })
    }

    /// Returns an iterator over articles in the archive
    /// The iterator reads the file or stdin line-by-line efficiently
    fn __iter__(slf: PyRef<Self>) -> PyResult<ArticleIterator> {
        let reader = if slf.file_path == "-" {
            // Read from stdin
            ReaderSource::Stdin(BufReader::new(std::io::stdin()))
        } else {
            // Read from file
            let file = File::open(&slf.file_path)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            ReaderSource::File(BufReader::new(file))
        };

        Ok(ArticleIterator {
            reader,
            current_id: String::new(),
            current_title: String::new(),
            current_text: String::new(),
            in_article: false,
            in_text: false,
            in_revision: false,
        })
    }
}

/// Internal enum to support both file and stdin readers
enum ReaderSource {
    File(BufReader<File>),
    Stdin(BufReader<std::io::Stdin>),
}

impl ReaderSource {
    /// Read a line from either file or stdin
    fn read_line(&mut self, buf: &mut String) -> std::io::Result<usize> {
        match self {
            ReaderSource::File(reader) => reader.read_line(buf),
            ReaderSource::Stdin(reader) => reader.read_line(buf),
        }
    }
}

/// Iterator that yields articles from the archive one at a time
/// Supports both file and stdin input
#[pyclass]
pub struct ArticleIterator {
    reader: ReaderSource,
    current_id: String,
    current_title: String,
    current_text: String,
    in_article: bool,
    in_text: bool,
    in_revision: bool,  // Track if we're inside a <revision> tag to avoid capturing revision IDs
}

#[pymethods]
impl ArticleIterator {
    fn __iter__(slf: PyRef<Self>) -> PyRef<Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<Self>) -> PyResult<Option<Article>> {
        use std::io::BufRead;

        let mut line = String::new();

        loop {
            line.clear();
            let n = slf
                .reader
                .read_line(&mut line)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

            if n == 0 {
                // End of file reached
                if !slf.current_id.is_empty() {
                    let article = Article {
                        id: slf.current_id.clone(),
                        title: slf.current_title.clone(),
                        text: slf.current_text.clone(),
                    };
                    slf.current_id.clear();
                    slf.current_title.clear();
                    slf.current_text.clear();
                    return Ok(Some(article));
                }
                return Ok(None);
            }

            let trimmed = line.trim();

            // Check for opening page tag
            if trimmed == "<page>" {
                slf.in_article = true;
                continue;
            }

            // Check for closing page tag - yield the article
            if trimmed == "</page>" && slf.in_article {
                slf.in_article = false;
                slf.in_text = false;  // Ensure text mode is off
                if !slf.current_id.is_empty() {
                    let article = Article {
                        id: slf.current_id.clone(),
                        title: slf.current_title.clone(),
                        text: slf.current_text.clone(),
                    };
                    slf.current_id.clear();
                    slf.current_title.clear();
                    slf.current_text.clear();
                    return Ok(Some(article));
                }
            }

            // Track revision opening and closing tags
            if trimmed == "<revision>" {
                slf.in_revision = true;
                continue;
            }
            if trimmed == "</revision>" {
                slf.in_revision = false;
                continue;
            }

            // Extract ID (only if not inside revision tag - we want the page ID, not revision contributor ID)
            if slf.in_article && !slf.in_revision && trimmed.starts_with("<id>") && trimmed.ends_with("</id>") {
                // Only set ID if we don't already have one (the page ID comes first)
                if slf.current_id.is_empty() {
                    slf.current_id = extract_tag_content(trimmed);
                }
                continue;
            }

            // Extract title
            if slf.in_article && trimmed.starts_with("<title>") && trimmed.ends_with("</title>") {
                slf.current_title = extract_tag_content(trimmed);
                continue;
            }

            // Track text section opening - handle both <text> and <text ...attributes>
            if slf.in_article && trimmed.starts_with("<text") {
                // Check if text content is on the same line as opening tag
                if let Some(end_bracket) = trimmed.find('>') {
                    let content_after = &trimmed[end_bracket + 1..];
                    slf.in_text = true;
                    
                    // If there's content after the opening tag on the same line
                    if !content_after.is_empty() && content_after != "</text>" {
                        slf.current_text.push_str(content_after);
                    }
                }
                continue;
            }

            if slf.in_article && trimmed == "</text>" {
                slf.in_text = false;
                continue;
            }

            // Accumulate text content
            if slf.in_article && slf.in_text && !trimmed.is_empty() {
                if !slf.current_text.is_empty() {
                    slf.current_text.push('\n');
                }
                slf.current_text.push_str(trimmed);
            }
        }
    }
}

/// Extract content from simple XML tags
/// Assumes format: <tag>content</tag>
fn extract_tag_content(line: &str) -> String {
    if let Some(start) = line.find('>') {
        if let Some(end) = line.rfind('<') {
            if end > start {
                return line[start + 1..end].to_string();
            }
        }
    }
    String::new()
}

/// Clean Wikipedia article text by removing XML markup and templates
/// Returns plain text content suitable for text processing
///
/// Removes:
/// - MediaWiki markup: [[...]], {{...}}, ==...==, etc.
/// - HTML entities: &lt;, &gt;, &amp;, etc.
/// - Excessive whitespace
#[pyfunction]
pub fn clean_text(text: &str) -> String {
    // Remove common XML/HTML tags
    let mut result = text.to_string();

    // Remove wikilinks [[...]]
    result = remove_pattern(&result, r"\[\[([^\]]+)\]\]", "$1");

    // Remove templates {{...}} - handle nested braces
    result = remove_nested_braces(&result);

    // Remove HTML comments <!-- ... -->
    result = remove_pattern(&result, r"<!--.*?-->", "");

    // Remove section headers == ... == (multiline pattern)
    result = remove_pattern(&result, r"=+\s*(.+?)\s*=+", "$1");

    // Remove bold/italic markup '' and '''
    result = result.replace("'''", "").replace("''", "");

    // Remove remaining XML-like tags <...>
    result = remove_pattern(&result, r"<[^>]+>", "");

    // Decode HTML entities
    result = decode_html_entities(&result);

    // Clean up whitespace - remove multiple consecutive newlines
    let lines: Vec<&str> = result.lines().map(|l| l.trim()).filter(|l| !l.is_empty()).collect();
    lines.join("\n")
}

/// Remove pattern matching content (regex-based)
fn remove_pattern(text: &str, pattern: &str, replacement: &str) -> String {
    match regex::Regex::new(pattern) {
        Ok(re) => re.replace_all(text, replacement).to_string(),
        Err(_) => text.to_string(),
    }
}

/// Remove nested braces {{...}} handling multiple levels of nesting
fn remove_nested_braces(text: &str) -> String {
    let mut result = String::with_capacity(text.len());
    let mut brace_depth: i32 = 0;
    let mut chars = text.chars().peekable();

    while let Some(ch) = chars.next() {
        if ch == '{' && chars.peek() == Some(&'{') {
            chars.next(); // consume second {
            brace_depth += 1;
        } else if ch == '}' && chars.peek() == Some(&'}') {
            chars.next(); // consume second }
            brace_depth = (brace_depth - 1).max(0);
        } else if brace_depth == 0 {
            result.push(ch);
        }
    }

    result
}

/// Decode common HTML entities to their character equivalents
fn decode_html_entities(text: &str) -> String {
    text.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .replace("&quot;", "\"")
        .replace("&apos;", "'")
        .replace("&nbsp;", " ")
}

/// Python module initialization
#[pymodule]
fn wikipedia_archive_reader(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<ArchiveReader>()?;
    m.add_class::<Article>()?;
    m.add_class::<ArticleIterator>()?;
    m.add_function(wrap_pyfunction!(clean_text, m)?)?;

    Ok(())
}
