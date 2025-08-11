"""Markdown parser for financial documents."""

import re
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from autonomous_financial_auditor.models import FinancialDocument, FinancialLineItem
from autonomous_financial_auditor.parsers.base import BaseParser


class MarkdownParser(BaseParser):
    """Parser for Markdown format financial documents."""
    
    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.lower().endswith(('.md', '.markdown'))
    
    def parse(self, file_path: str, content: str) -> FinancialDocument:
        """Parse Markdown content into a FinancialDocument."""
        self.logger.info(f"Parsing Markdown file: {file_path}")
        
        # Detect document type
        document_type = self.detect_document_type(file_path, content)
        period = self.extract_period(file_path, content)
        
        # Parse content for line items
        line_items = self._parse_markdown_content(content)
        
        # Calculate totals
        totals = self._calculate_totals(line_items)
        
        document = FinancialDocument(
            document_type=document_type,
            file_path=file_path,
            period=period,
            line_items=line_items,
            totals=totals,
            metadata={"parser": "MarkdownParser", "format": "markdown"}
        )
        
        # Validate document
        warnings = self.validate_document(document)
        if warnings:
            self.logger.warning(f"Validation warnings for {file_path}: {warnings}")
            document.metadata["warnings"] = warnings
        
        return document
    
    def _parse_markdown_content(self, content: str) -> List[FinancialLineItem]:
        """Parse Markdown content and extract line items."""
        line_items = []
        
        # Try to parse markdown tables first
        table_items = self._parse_markdown_tables(content)
        if table_items:
            line_items.extend(table_items)
        
        # Parse list items
        list_items = self._parse_list_items(content)
        if list_items:
            line_items.extend(list_items)
        
        # Parse structured text patterns
        text_items = self._parse_text_patterns(content)
        if text_items:
            line_items.extend(text_items)
        
        return line_items
    
    def _parse_markdown_tables(self, content: str) -> List[FinancialLineItem]:
        """Parse Markdown tables to extract financial data."""
        line_items = []
        
        # Regex to match markdown tables
        table_pattern = r'^\|.*\|$'
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check if this line looks like a table row
            if re.match(table_pattern, line):
                # Found potential table start
                table_lines = []
                
                # Collect all consecutive table lines
                while i < len(lines) and re.match(table_pattern, lines[i].strip()):
                    table_lines.append(lines[i].strip())
                    i += 1
                
                # Parse this table
                if len(table_lines) >= 2:  # At least header and separator
                    table_items = self._process_markdown_table(table_lines)
                    line_items.extend(table_items)
            else:
                i += 1
        
        return line_items
    
    def _process_markdown_table(self, table_lines: List[str]) -> List[FinancialLineItem]:
        """Process a markdown table into line items."""
        if len(table_lines) < 3:  # Need header, separator, and at least one data row
            return []
        
        # Parse header
        header_line = table_lines[0]
        headers = [col.strip().strip('|').strip() for col in header_line.split('|')[1:-1]]
        
        # Skip separator line (table_lines[1])
        
        # Find relevant columns
        name_col = self._find_name_column_in_headers(headers)
        value_col = self._find_value_column_in_headers(headers)
        category_col = self._find_category_column_in_headers(headers)
        
        if name_col is None or value_col is None:
            self.logger.warning("Could not identify name or value columns in table")
            return []
        
        line_items = []
        
        # Process data rows
        for row_idx, line in enumerate(table_lines[2:], 1):
            cells = [cell.strip().strip('|').strip() for cell in line.split('|')[1:-1]]
            
            if len(cells) <= max(name_col, value_col):
                continue
            
            try:
                name = cells[name_col]
                value_str = cells[value_col]
                
                if not name or not value_str:
                    continue
                
                # Clean up value string
                value_str = self._clean_value_string(value_str)
                if not value_str:
                    continue
                
                # Normalize name
                normalized_name = self.normalize_line_item_name(name)
                
                # Get category
                category = None
                if category_col is not None and len(cells) > category_col:
                    category = cells[category_col] or None
                
                line_item = FinancialLineItem(
                    name=normalized_name,
                    value=value_str,
                    category=category,
                    metadata={"original_name": name, "source": "table", "row": row_idx}
                )
                
                line_items.append(line_item)
                
            except (ValueError, IndexError) as e:
                self.logger.warning(f"Error parsing table row {row_idx}: {e}")
                continue
        
        return line_items
    
    def _parse_list_items(self, content: str) -> List[FinancialLineItem]:
        """Parse list items (bullets, numbers) for financial data."""
        line_items = []
        
        # Patterns for list items with financial data
        patterns = [
            r'^[-*+]\s*(.+?):\s*\$?([\d,.-]+)',  # - Item: $1,000
            r'^(\d+\.)\s*(.+?):\s*\$?([\d,.-]+)',  # 1. Item: $1,000
            r'^[-*+]\s*(.+?)\s+\$?([\d,.-]+)',  # - Item $1,000
            r'^(\d+\.)\s*(.+?)\s+\$?([\d,.-]+)',  # 1. Item $1,000
        ]
        
        lines = content.split('\n')
        
        for line_idx, line in enumerate(lines):
            line = line.strip()
            
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    
                    if len(groups) == 2:  # Simple pattern without number
                        name, value_str = groups
                    elif len(groups) == 3:  # Pattern with number
                        _, name, value_str = groups
                    else:
                        continue
                    
                    # Clean and validate
                    name = name.strip()
                    value_str = self._clean_value_string(value_str)
                    
                    if name and value_str:
                        normalized_name = self.normalize_line_item_name(name)
                        
                        try:
                            line_item = FinancialLineItem(
                                name=normalized_name,
                                value=value_str,
                                metadata={"original_name": name, "source": "list", "line": line_idx + 1}
                            )
                            line_items.append(line_item)
                        except ValueError as e:
                            self.logger.warning(f"Error parsing list item on line {line_idx + 1}: {e}")
                    
                    break  # Found match, don't try other patterns for this line
        
        return line_items
    
    def _parse_text_patterns(self, content: str) -> List[FinancialLineItem]:
        """Parse unstructured text for financial data patterns."""
        line_items = []
        
        # Common patterns for financial line items in text
        patterns = [
            r'([A-Za-z][A-Za-z\s&]+?):\s*\$?([\d,.-]+)',  # Revenue: $1,000
            r'([A-Za-z][A-Za-z\s&]+?)\s+\$?([\d,.-]+)',  # Revenue $1,000
            r'\b([A-Za-z][A-Za-z\s&]+?)\s+of\s+\$?([\d,.-]+)',  # Revenue of $1,000
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                name, value_str = match.groups()
                
                # Clean up name
                name = name.strip().rstrip(':')
                value_str = self._clean_value_string(value_str)
                
                # Filter out non-financial terms
                if self._is_likely_financial_term(name) and value_str:
                    normalized_name = self.normalize_line_item_name(name)
                    
                    try:
                        line_item = FinancialLineItem(
                            name=normalized_name,
                            value=value_str,
                            metadata={"original_name": name, "source": "text"}
                        )
                        line_items.append(line_item)
                    except ValueError as e:
                        self.logger.warning(f"Error parsing text pattern '{name}': {e}")
        
        return line_items
    
    def _find_name_column_in_headers(self, headers: List[str]) -> Optional[int]:
        """Find name column in table headers."""
        name_indicators = ["name", "item", "line", "description", "account", "category"]
        
        for i, header in enumerate(headers):
            header_lower = header.lower()
            if any(indicator in header_lower for indicator in name_indicators):
                return i
        
        return 0 if headers else None  # Default to first column
    
    def _find_value_column_in_headers(self, headers: List[str]) -> Optional[int]:
        """Find value column in table headers."""
        value_indicators = ["amount", "value", "total", "balance", "usd", "$", "cost", "price"]
        
        for i, header in enumerate(headers):
            header_lower = header.lower()
            if any(indicator in header_lower for indicator in value_indicators):
                return i
        
        # Look for numeric patterns in headers
        for i, header in enumerate(headers):
            if re.search(r'\d', header):
                return i
        
        return len(headers) - 1 if headers else None  # Default to last column
    
    def _find_category_column_in_headers(self, headers: List[str]) -> Optional[int]:
        """Find category column in table headers."""
        category_indicators = ["category", "type", "class", "group", "section"]
        
        for i, header in enumerate(headers):
            header_lower = header.lower()
            if any(indicator in header_lower for indicator in category_indicators):
                return i
        
        return None
    
    def _clean_value_string(self, value_str: str) -> str:
        """Clean up a value string for parsing."""
        if not value_str:
            return ""
        
        # Remove common formatting
        cleaned = value_str.strip()
        cleaned = re.sub(r'[^\d.,-]', '', cleaned)  # Keep only digits, dots, commas, minus
        
        # Handle parentheses as negative (accounting format)
        if '(' in value_str and ')' in value_str:
            cleaned = '-' + cleaned
        
        return cleaned
    
    def _is_likely_financial_term(self, term: str) -> bool:
        """Check if a term is likely to be a financial line item."""
        term_lower = term.lower()
        
        # Common financial terms
        financial_keywords = [
            "revenue", "income", "sales", "profit", "loss", "cost", "expense",
            "asset", "liability", "equity", "cash", "debt", "loan", "interest",
            "tax", "depreciation", "amortization", "dividend", "earning",
            "receivable", "payable", "inventory", "goodwill", "capital"
        ]
        
        # Check if term contains financial keywords
        return any(keyword in term_lower for keyword in financial_keywords)
    
    def _calculate_totals(self, line_items: List[FinancialLineItem]) -> Dict[str, Decimal]:
        """Calculate totals by category."""
        totals = {}
        
        # Group by category
        categories = set(item.category for item in line_items if item.category)
        
        for category in categories:
            category_items = [item for item in line_items if item.category == category]
            total = sum(item.value for item in category_items)
            totals[f"{category}_total"] = total
        
        # Overall total
        totals["grand_total"] = sum(item.value for item in line_items)
        
        return totals