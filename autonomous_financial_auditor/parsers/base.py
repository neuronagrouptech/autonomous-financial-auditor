"""Base parser for financial documents."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from autonomous_financial_auditor.models import FinancialDocument, FinancialDocumentType

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Abstract base class for financial document parsers."""
    
    def __init__(self) -> None:
        """Initialize the parser."""
        self.logger = logger
    
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the given file."""
        pass
    
    @abstractmethod
    def parse(self, file_path: str, content: str) -> FinancialDocument:
        """Parse the file content into a FinancialDocument."""
        pass
    
    def detect_document_type(self, file_path: str, content: str) -> FinancialDocumentType:
        """Detect the type of financial document based on file path and content."""
        file_path_lower = file_path.lower()
        content_lower = content.lower()
        
        # P&L indicators
        pl_indicators = [
            "profit", "loss", "p&l", "pl", "income statement", 
            "revenue", "cogs", "cost of goods sold", "gross profit",
            "operating income", "net income", "earnings"
        ]
        
        # Balance Sheet indicators
        bs_indicators = [
            "balance sheet", "balance", "bs", "assets", "liabilities",
            "equity", "shareholders equity", "stockholders equity",
            "current assets", "fixed assets", "current liabilities"
        ]
        
        # Check file path first
        for indicator in pl_indicators:
            if indicator.replace(" ", "") in file_path_lower.replace("_", "").replace("-", ""):
                return FinancialDocumentType.PROFIT_LOSS
        
        for indicator in bs_indicators:
            if indicator.replace(" ", "") in file_path_lower.replace("_", "").replace("-", ""):
                return FinancialDocumentType.BALANCE_SHEET
        
        # Check content
        pl_score = sum(1 for indicator in pl_indicators if indicator in content_lower)
        bs_score = sum(1 for indicator in bs_indicators if indicator in content_lower)
        
        if pl_score > bs_score and pl_score > 0:
            return FinancialDocumentType.PROFIT_LOSS
        elif bs_score > 0:
            return FinancialDocumentType.BALANCE_SHEET
        
        self.logger.warning(f"Could not determine document type for {file_path}")
        return FinancialDocumentType.UNKNOWN
    
    def extract_period(self, file_path: str, content: str) -> Optional[str]:
        """Extract the financial period from file path or content."""
        import re
        
        # Common period patterns
        patterns = [
            r"Q[1-4]\s*\d{4}",  # Q1 2024, Q1 2024
            r"\d{4}\s*Q[1-4]",  # 2024 Q1, 2024Q1
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{4}",  # Mar 2024
            r"\d{4}[-_](0[1-9]|1[0-2])",  # 2024-03, 2024_03
            r"(FY|Fiscal Year)\s*\d{4}",  # FY 2024
        ]
        
        text = f"{file_path} {content}"
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def normalize_line_item_name(self, name: str) -> str:
        """Normalize line item names for consistent matching."""
        # Remove common prefixes/suffixes and normalize spacing
        normalized = name.strip()
        
        # Remove common formatting
        normalized = normalized.replace(":", "").replace("$", "").replace(",", "")
        
        # Normalize spacing
        normalized = " ".join(normalized.split())
        
        # Common standardizations
        replacements = {
            "cost of goods sold": "cogs",
            "cost of sales": "cogs",
            "net income": "net_income",
            "gross profit": "gross_profit",
            "operating income": "operating_income",
            "total assets": "total_assets",
            "total liabilities": "total_liabilities",
            "shareholders equity": "shareholders_equity",
            "stockholders equity": "shareholders_equity",
            "retained earnings": "retained_earnings",
        }
        
        normalized_lower = normalized.lower()
        for old, new in replacements.items():
            if old in normalized_lower:
                return new
        
        return normalized
    
    def validate_document(self, document: FinancialDocument) -> List[str]:
        """Validate the parsed document and return list of warnings."""
        warnings = []
        
        if not document.line_items:
            warnings.append("Document contains no line items")
        
        if document.document_type == FinancialDocumentType.UNKNOWN:
            warnings.append("Could not determine document type")
        
        # Check for required line items based on document type
        if document.document_type == FinancialDocumentType.PROFIT_LOSS:
            required_items = ["revenue", "net_income"]
            for item in required_items:
                if not document.get_line_item(item):
                    warnings.append(f"Missing expected P&L item: {item}")
        
        elif document.document_type == FinancialDocumentType.BALANCE_SHEET:
            required_items = ["total_assets", "total_liabilities"]
            for item in required_items:
                if not document.get_line_item(item):
                    warnings.append(f"Missing expected Balance Sheet item: {item}")
        
        return warnings