"""CSV parser for financial documents."""

import csv
import io
from decimal import Decimal
from typing import Dict, List, Optional

from autonomous_financial_auditor.models import FinancialDocument, FinancialLineItem
from autonomous_financial_auditor.parsers.base import BaseParser


class CSVParser(BaseParser):
    """Parser for CSV format financial documents."""
    
    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.lower().endswith(('.csv', '.tsv'))
    
    def parse(self, file_path: str, content: str) -> FinancialDocument:
        """Parse CSV content into a FinancialDocument."""
        self.logger.info(f"Parsing CSV file: {file_path}")
        
        # Detect document type
        document_type = self.detect_document_type(file_path, content)
        period = self.extract_period(file_path, content)
        
        # Parse CSV content
        line_items = self._parse_csv_content(content)
        
        # Calculate totals
        totals = self._calculate_totals(line_items)
        
        document = FinancialDocument(
            document_type=document_type,
            file_path=file_path,
            period=period,
            line_items=line_items,
            totals=totals,
            metadata={"parser": "CSVParser", "format": "csv"}
        )
        
        # Validate document
        warnings = self.validate_document(document)
        if warnings:
            self.logger.warning(f"Validation warnings for {file_path}: {warnings}")
            document.metadata["warnings"] = warnings
        
        return document
    
    def _parse_csv_content(self, content: str) -> List[FinancialLineItem]:
        """Parse CSV content and extract line items."""
        line_items = []
        
        # Try different CSV dialects
        dialects = [csv.excel, csv.excel_tab]
        
        for dialect in dialects:
            try:
                reader = csv.reader(io.StringIO(content), dialect=dialect)
                rows = list(reader)
                if len(rows) > 1:  # Has header and at least one data row
                    line_items = self._process_csv_rows(rows)
                    break
            except csv.Error:
                continue
        
        if not line_items:
            # Fallback: try with custom delimiter detection
            line_items = self._parse_with_delimiter_detection(content)
        
        return line_items
    
    def _process_csv_rows(self, rows: List[List[str]]) -> List[FinancialLineItem]:
        """Process CSV rows into line items."""
        if not rows:
            return []
        
        # Identify columns
        header = [col.strip().lower() for col in rows[0]]
        
        # Find name and value columns
        name_col = self._find_name_column(header)
        value_col = self._find_value_column(header)
        category_col = self._find_category_column(header)
        
        if name_col is None or value_col is None:
            self.logger.warning("Could not identify name or value columns in CSV")
            return []
        
        line_items = []
        
        for row_idx, row in enumerate(rows[1:], 1):  # Skip header
            if len(row) <= max(name_col, value_col):
                continue
            
            try:
                name = row[name_col].strip()
                if not name:
                    continue
                
                # Parse value
                value_str = row[value_col].strip()
                if not value_str:
                    continue
                
                # Normalize the name
                normalized_name = self.normalize_line_item_name(name)
                
                # Get category if available
                category = None
                if category_col is not None and len(row) > category_col:
                    category = row[category_col].strip() or None
                
                line_item = FinancialLineItem(
                    name=normalized_name,
                    value=value_str,  # Will be converted to Decimal by validator
                    category=category,
                    metadata={"original_name": name, "row": row_idx}
                )
                
                line_items.append(line_item)
                
            except (ValueError, IndexError) as e:
                self.logger.warning(f"Error parsing row {row_idx}: {e}")
                continue
        
        return line_items
    
    def _find_name_column(self, header: List[str]) -> Optional[int]:
        """Find the column containing line item names."""
        name_indicators = [
            "name", "item", "line item", "description", "account", 
            "category", "line", "detail", "particulars"
        ]
        
        for i, col in enumerate(header):
            for indicator in name_indicators:
                if indicator in col:
                    return i
        
        # Fallback: assume first column is name
        return 0 if header else None
    
    def _find_value_column(self, header: List[str]) -> Optional[int]:
        """Find the column containing monetary values."""
        value_indicators = [
            "amount", "value", "total", "balance", "sum", 
            "usd", "$", "dollars", "price", "cost"
        ]
        
        for i, col in enumerate(header):
            for indicator in value_indicators:
                if indicator in col:
                    return i
        
        # Fallback: look for numeric-looking headers or last column
        for i, col in enumerate(header):
            if any(char.isdigit() for char in col):
                return i
        
        # Last resort: assume last column is value
        return len(header) - 1 if header else None
    
    def _find_category_column(self, header: List[str]) -> Optional[int]:
        """Find the column containing categories."""
        category_indicators = [
            "category", "type", "class", "group", "section", "segment"
        ]
        
        for i, col in enumerate(header):
            for indicator in category_indicators:
                if indicator in col:
                    return i
        
        return None
    
    def _parse_with_delimiter_detection(self, content: str) -> List[FinancialLineItem]:
        """Parse CSV with automatic delimiter detection."""
        # Try common delimiters
        delimiters = [',', ';', '\t', '|']
        
        for delimiter in delimiters:
            try:
                lines = content.strip().split('\n')
                if not lines:
                    continue
                
                # Check if delimiter is consistent across lines
                first_line_count = lines[0].count(delimiter)
                if first_line_count == 0:
                    continue
                
                consistent = all(
                    line.count(delimiter) == first_line_count 
                    for line in lines[:min(5, len(lines))]  # Check first 5 lines
                )
                
                if consistent:
                    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
                    rows = list(reader)
                    return self._process_csv_rows(rows)
                    
            except (csv.Error, UnicodeError):
                continue
        
        self.logger.warning("Could not detect CSV delimiter")
        return []
    
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