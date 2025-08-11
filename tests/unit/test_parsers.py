"""Unit tests for document parsers."""

import pytest
from unittest.mock import Mock, patch

from autonomous_financial_auditor.parsers.csv_parser import CSVParser
from autonomous_financial_auditor.parsers.markdown_parser import MarkdownParser
from autonomous_financial_auditor.parsers.factory import ParserFactory
from autonomous_financial_auditor.models import FinancialDocumentType


class TestCSVParser:
    """Test CSV parser functionality."""
    
    def test_can_parse(self):
        """Test CSV file detection."""
        parser = CSVParser()
        
        assert parser.can_parse("test.csv") is True
        assert parser.can_parse("test.tsv") is True
        assert parser.can_parse("test.md") is False
        assert parser.can_parse("test.txt") is False
    
    def test_parse_simple_csv(self):
        """Test parsing a simple CSV file."""
        parser = CSVParser()
        
        csv_content = """Name,Amount
Revenue,1000.00
Expenses,500.00
Net Income,500.00"""
        
        document = parser.parse("test_pl.csv", csv_content)
        
        assert document is not None
        assert document.document_type == FinancialDocumentType.PROFIT_LOSS
        assert len(document.line_items) == 3
        
        revenue_item = document.get_line_item("revenue")
        assert revenue_item is not None
        assert revenue_item.value == 1000.00
    
    def test_parse_with_categories(self):
        """Test parsing CSV with categories."""
        parser = CSVParser()
        
        csv_content = """Item,Category,Amount
Revenue,Income,1000.00
COGS,Expense,300.00
Operating Expenses,Expense,200.00"""
        
        document = parser.parse("test.csv", csv_content)
        
        assert len(document.line_items) == 3
        
        # Check categories are preserved
        revenue_item = document.get_line_item("revenue")
        assert revenue_item.category == "Income"
        
        expense_items = document.get_line_items_by_category("Expense")
        assert len(expense_items) == 2


class TestMarkdownParser:
    """Test Markdown parser functionality."""
    
    def test_can_parse(self):
        """Test Markdown file detection."""
        parser = MarkdownParser()
        
        assert parser.can_parse("test.md") is True
        assert parser.can_parse("test.markdown") is True
        assert parser.can_parse("test.csv") is False
    
    def test_parse_markdown_table(self):
        """Test parsing Markdown table."""
        parser = MarkdownParser()
        
        markdown_content = """# Q1 2024 P&L

| Line Item | Amount |
|-----------|--------|
| Revenue | $1,000.00 |
| COGS | $300.00 |
| Net Income | $700.00 |
"""
        
        document = parser.parse("q1_pl.md", markdown_content)
        
        assert document is not None
        assert len(document.line_items) >= 3
        
        revenue_item = document.get_line_item("revenue")
        assert revenue_item is not None
        assert revenue_item.value == 1000.00
    
    def test_parse_list_items(self):
        """Test parsing Markdown list items."""
        parser = MarkdownParser()
        
        markdown_content = """# Financial Summary

- Revenue: $5,000
- Cost of Goods Sold: $2,000
- Gross Profit: $3,000
- Operating Expenses: $1,500
- Net Income: $1,500
"""
        
        document = parser.parse("summary.md", markdown_content)
        
        assert document is not None
        assert len(document.line_items) >= 4
        
        revenue_item = document.get_line_item("revenue")
        assert revenue_item is not None
        assert revenue_item.value == 5000.00
    
    def test_clean_value_string(self):
        """Test value string cleaning."""
        parser = MarkdownParser()
        
        # Test various formats
        assert parser._clean_value_string("$1,000.00") == "1000.00"
        assert parser._clean_value_string("(500.00)") == "-500.00"
        assert parser._clean_value_string("1,234.56") == "1234.56"
        assert parser._clean_value_string("  123.45  ") == "123.45"
    
    def test_is_likely_financial_term(self):
        """Test financial term detection."""
        parser = MarkdownParser()
        
        assert parser._is_likely_financial_term("Revenue") is True
        assert parser._is_likely_financial_term("Total Assets") is True
        assert parser._is_likely_financial_term("Net Income") is True
        assert parser._is_likely_financial_term("Cash Flow") is True
        
        assert parser._is_likely_financial_term("Random Text") is False
        assert parser._is_likely_financial_term("Company Name") is False


class TestParserFactory:
    """Test parser factory functionality."""
    
    def test_get_parser(self):
        """Test getting appropriate parser."""
        factory = ParserFactory()
        
        csv_parser = factory.get_parser("test.csv")
        assert isinstance(csv_parser, CSVParser)
        
        md_parser = factory.get_parser("test.md")
        assert isinstance(md_parser, MarkdownParser)
        
        no_parser = factory.get_parser("test.txt")
        assert no_parser is None
    
    def test_parse_file(self):
        """Test parsing file through factory."""
        factory = ParserFactory()
        
        csv_content = """Name,Amount
Revenue,1000
Expenses,500"""
        
        document = factory.parse_file("test.csv", csv_content)
        
        assert document is not None
        assert len(document.line_items) == 2
    
    def test_get_supported_extensions(self):
        """Test getting supported file extensions."""
        factory = ParserFactory()
        
        extensions = factory.get_supported_extensions()
        
        assert ".csv" in extensions
        assert ".md" in extensions
        assert ".tsv" in extensions
        assert ".markdown" in extensions
    
    def test_add_custom_parser(self):
        """Test adding custom parser."""
        factory = ParserFactory()
        
        # Mock custom parser
        custom_parser = Mock()
        custom_parser.can_parse.return_value = True
        
        original_count = len(factory.parsers)
        factory.add_parser(custom_parser)
        
        assert len(factory.parsers) == original_count + 1
    
    def test_remove_parser(self):
        """Test removing parser."""
        factory = ParserFactory()
        
        original_count = len(factory.parsers)
        removed = factory.remove_parser(CSVParser)
        
        assert removed is True
        assert len(factory.parsers) == original_count - 1
        
        # Try to remove again
        removed_again = factory.remove_parser(CSVParser)
        assert removed_again is False