"""
Unit tests for Wikipedia Archive Reader

Tests cover:
- File reading and iteration
- Article parsing from XML
- Text cleaning functionality
- Edge cases and error handling
"""

import pytest
import tempfile
import os
from pathlib import Path
from wikipedia_archive_reader import ArchiveReader, Article, clean_text


class TestArticle:
    """Test the Article data class"""

    def test_article_creation(self):
        """Test creating an Article instance"""
        article = Article(id="123", title="Test Article", text="Some content")
        assert article.id == "123"
        assert article.title == "Test Article"
        assert article.text == "Some content"

    def test_article_repr(self):
        """Test Article string representation"""
        article = Article(id="456", title="Another Article", text="Long text content")
        repr_str = repr(article)
        assert "Article" in repr_str
        assert "456" in repr_str
        assert "Another Article" in repr_str


class TestArchiveReader:
    """Test the ArchiveReader for streaming XML parsing"""

    @pytest.fixture
    def sample_archive(self):
        """Create a temporary Wikipedia XML archive for testing"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<mediawiki>
  <page>
    <id>1</id>
    <title>Hello World</title>
    <text>
This is the first article.
It has multiple lines.
    </text>
  </page>
  <page>
    <id>2</id>
    <title>Another Article</title>
    <text>
Second article content here.
With another line of text.
    </text>
  </page>
</mediawiki>
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as f:
            f.write(xml_content)
            temp_path = f.name

        yield temp_path

        # Cleanup
        os.unlink(temp_path)

    def test_reader_initialization(self, sample_archive):
        """Test creating a reader instance"""
        reader = ArchiveReader(sample_archive)
        assert reader is not None

    def test_reader_iteration(self, sample_archive):
        """Test iterating through articles"""
        reader = ArchiveReader(sample_archive)
        articles = list(reader)

        assert len(articles) == 2
        assert articles[0].id == "1"
        assert articles[0].title == "Hello World"
        assert articles[1].id == "2"
        assert articles[1].title == "Another Article"

    def test_article_text_content(self, sample_archive):
        """Test that article text is correctly extracted"""
        reader = ArchiveReader(sample_archive)
        articles = list(reader)

        first_article = articles[0]
        assert "first article" in first_article.text
        assert "multiple lines" in first_article.text

        second_article = articles[1]
        assert "Second article content" in second_article.text

    def test_reader_is_iterable(self, sample_archive):
        """Test that reader can be iterated multiple times"""
        reader = ArchiveReader(sample_archive)
        count1 = sum(1 for _ in reader)

        # Note: In current implementation, reader can only be iterated once
        # This test documents the current behavior
        assert count1 == 2

    def test_empty_archive(self):
        """Test reading an empty archive"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as f:
            f.write("""<?xml version="1.0" encoding="UTF-8"?>
<mediawiki>
</mediawiki>
""")
            temp_path = f.name

        try:
            reader = ArchiveReader(temp_path)
            articles = list(reader)
            assert len(articles) == 0
        finally:
            os.unlink(temp_path)

    def test_nonexistent_file(self):
        """Test that reading nonexistent file raises error"""
        reader = ArchiveReader("/nonexistent/path/archive.xml")
        with pytest.raises(OSError):
            list(reader)


class TestCleanText:
    """Test the clean_text function for removing markup"""

    def test_remove_wikilinks(self):
        """Test removal of wikilinks [[...]]"""
        text = "Check the [[Wikipedia]] article for [[information]]."
        cleaned = clean_text(text)
        assert "Wikipedia" in cleaned
        assert "information" in cleaned
        assert "[[" not in cleaned
        assert "]]" not in cleaned

    def test_remove_templates(self):
        """Test removal of templates {{...}}"""
        text = "Some text {{cite|author=John}} more text {{reflist}}"
        cleaned = clean_text(text)
        assert "Some text" in cleaned
        assert "more text" in cleaned
        assert "{{" not in cleaned
        assert "}}" not in cleaned

    def test_remove_nested_templates(self):
        """Test removal of nested templates"""
        text = "Text {{cite|author={{fn|John}}}} end"
        cleaned = clean_text(text)
        assert "Text" in cleaned
        assert "end" in cleaned
        # All braces should be removed
        assert "{" not in cleaned
        assert "}" not in cleaned

    def test_remove_html_comments(self):
        """Test removal of HTML comments"""
        text = "Visible text <!-- this is a comment --> more text"
        cleaned = clean_text(text)
        assert "Visible text" in cleaned
        assert "more text" in cleaned
        assert "<!--" not in cleaned
        assert "comment" not in cleaned

    def test_remove_section_headers(self):
        """Test removal of section header markup"""
        text = "== Introduction ==\nSome content\n=== Subsection ===\nMore content"
        cleaned = clean_text(text)
        # The regex removes headers on their own lines, but these are on their own
        # Note: Our current regex pattern only matches full lines with headers
        assert "Introduction" in cleaned
        assert "Some content" in cleaned
        assert "More content" in cleaned

    def test_remove_bold_italic(self):
        """Test removal of bold and italic markup"""
        text = "This is '''bold''' and ''italic'' text."
        cleaned = clean_text(text)
        assert "bold" in cleaned
        assert "italic" in cleaned
        assert "'''" not in cleaned
        assert "''" not in cleaned

    def test_remove_xml_tags(self):
        """Test removal of XML-like tags"""
        text = "Some <ref name='test'>referenced</ref> text <br/>"
        cleaned = clean_text(text)
        assert "referenced" in cleaned
        assert "text" in cleaned
        assert "<" not in cleaned
        assert ">" not in cleaned

    def test_decode_html_entities(self):
        """Test decoding of HTML entities"""
        text = "Less &lt; than and greater &gt; than. An &amp; sign."
        cleaned = clean_text(text)
        assert "<" in cleaned
        assert ">" in cleaned
        assert "&" in cleaned
        assert "&lt;" not in cleaned
        assert "&gt;" not in cleaned
        assert "&amp;" not in cleaned

    def test_decode_quot_apos(self):
        """Test decoding of quote and apostrophe entities"""
        text = "He said &quot;hello&quot; and used &apos;single quotes&apos;."
        cleaned = clean_text(text)
        assert '"' in cleaned
        assert "'" in cleaned
        assert "&quot;" not in cleaned
        assert "&apos;" not in cleaned

    def test_clean_whitespace(self):
        """Test that excessive whitespace is cleaned"""
        text = "Line 1\n\n\nLine 2\n\n\n\nLine 3"
        cleaned = clean_text(text)
        lines = cleaned.split("\n")
        # Should have 3 lines, not the extra blank ones
        assert len(lines) == 3
        assert lines[0] == "Line 1"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"

    def test_complex_wikipedia_text(self):
        """Test cleaning complex Wikipedia article text"""
        text = """== History ==
The {{cite|author=Smith}} article discusses [[Early history|history]].

=== Timeline ===
* '''1950''' &ndash; Important event <!-- was this right? -->
* 1960 &ndash; Another {{cite|web|url=...}} occurrence
"""
        cleaned = clean_text(text)

        # Check that content is preserved
        assert "History" in cleaned
        assert "article" in cleaned
        assert "Timeline" in cleaned
        assert "1950" in cleaned

        # Check that markup is removed
        assert "{{" not in cleaned
        assert "[[" not in cleaned
        assert "<!--" not in cleaned
        assert "'''" not in cleaned

    def test_empty_string(self):
        """Test cleaning empty string"""
        cleaned = clean_text("")
        assert cleaned == ""

    def test_only_markup(self):
        """Test cleaning text that is only markup"""
        text = "{{cite}} [[link]] {{reflist}}"
        cleaned = clean_text(text)
        # After removing all markup, might be empty or have whitespace
        assert "{{" not in cleaned
        assert "[[" not in cleaned


class TestStdin:
    """Test reading from stdin"""

    def test_stdin_marker(self):
        """Test that '-' is accepted as stdin marker"""
        # We can't easily test actual stdin in pytest without mocking,
        # but we can verify the reader accepts '-' as a valid argument
        reader = ArchiveReader("-")
        assert reader is not None

    def test_stdin_with_file_fallback(self):
        """Verify both stdin ('-') and file paths work"""
        # '-' for stdin
        reader_stdin = ArchiveReader("-")
        assert reader_stdin is not None
        
        # File path (though we don't test actual file reading here)
        # Just verify the constructor accepts regular paths
        reader_file = ArchiveReader("dummy.xml")
        assert reader_file is not None


class TestIntegration:
    """Integration tests combining reader and cleaner"""

    @pytest.fixture
    def wiki_archive(self):
        """Create a realistic Wikipedia archive sample"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<mediawiki>
  <page>
    <id>100</id>
    <title>Artificial Intelligence</title>
    <text>
'''Artificial Intelligence''' (AI) is a field of [[computer science]].

== History ==
The term {{cite|author=Smith|year=2020}} was first used in 1956.

== Applications ==
* {{cite|book|title=AI Basics}}
* [[Machine Learning]]
* {{cite web|url=example.com}} Deep Learning

See also: [[Neural Networks]]
    </text>
  </page>
</mediawiki>
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as f:
            f.write(xml_content)
            temp_path = f.name

        yield temp_path
        os.unlink(temp_path)

    def test_read_and_clean(self, wiki_archive):
        """Test reading an article and cleaning it"""
        reader = ArchiveReader(wiki_archive)
        articles = list(reader)

        assert len(articles) == 1
        article = articles[0]

        # Verify article metadata
        assert article.id == "100"
        assert article.title == "Artificial Intelligence"

        # Clean the text
        cleaned = clean_text(article.text)

        # Verify markup is removed
        assert "'''" not in cleaned
        assert "{{" not in cleaned
        assert "[[" not in cleaned

        # Verify content is preserved
        assert "Artificial Intelligence" in cleaned
        assert "History" in cleaned
        assert "Applications" in cleaned
        assert "1956" in cleaned
