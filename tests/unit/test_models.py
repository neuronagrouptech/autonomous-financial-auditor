"""Unit tests for data models."""

import pytest
from decimal import Decimal
from datetime import datetime

from autonomous_financial_auditor.models import (
    FinancialDocument,
    FinancialDocumentType,
    FinancialLineItem,
    FinancialDiscrepancy,
    DiscrepancySeverity,
    AnalysisResult,
)


class TestFinancialLineItem:
    """Test FinancialLineItem model."""
    
    def test_create_line_item(self):
        """Test creating a financial line item."""
        item = FinancialLineItem(
            name="Revenue",
            value="1000.50",
            category="Income"
        )
        
        assert item.name == "Revenue"
        assert item.value == Decimal("1000.50")
        assert item.category == "Income"
    
    def test_value_conversion(self):
        """Test value conversion to Decimal."""
        # Test string conversion
        item1 = FinancialLineItem(name="Test", value="1,500.75")
        assert item1.value == Decimal("1500.75")
        
        # Test parentheses as negative
        item2 = FinancialLineItem(name="Test", value="(500.00)")
        assert item2.value == Decimal("-500.00")
        
        # Test with currency symbol
        item3 = FinancialLineItem(name="Test", value="$2,500.00")
        assert item3.value == Decimal("2500.00")
    
    def test_invalid_value(self):
        """Test invalid value handling."""
        with pytest.raises(ValueError):
            FinancialLineItem(name="Test", value="invalid")


class TestFinancialDocument:
    """Test FinancialDocument model."""
    
    def test_create_document(self):
        """Test creating a financial document."""
        line_items = [
            FinancialLineItem(name="Revenue", value="1000", category="Income"),
            FinancialLineItem(name="Expenses", value="500", category="Costs"),
        ]
        
        doc = FinancialDocument(
            document_type=FinancialDocumentType.PROFIT_LOSS,
            file_path="/path/to/pl.csv",
            line_items=line_items
        )
        
        assert doc.document_type == FinancialDocumentType.PROFIT_LOSS
        assert doc.file_path == "/path/to/pl.csv"
        assert len(doc.line_items) == 2
    
    def test_get_line_item(self):
        """Test getting line item by name."""
        line_items = [
            FinancialLineItem(name="Revenue", value="1000"),
            FinancialLineItem(name="Net Income", value="500"),
        ]
        
        doc = FinancialDocument(
            document_type=FinancialDocumentType.PROFIT_LOSS,
            file_path="/path/to/pl.csv",
            line_items=line_items
        )
        
        # Case insensitive search
        revenue_item = doc.get_line_item("revenue")
        assert revenue_item is not None
        assert revenue_item.name == "Revenue"
        
        # Exact match
        net_income = doc.get_line_item("Net Income", case_sensitive=True)
        assert net_income is not None
        
        # Not found
        assert doc.get_line_item("Nonexistent") is None
    
    def test_calculate_total(self):
        """Test calculating totals."""
        line_items = [
            FinancialLineItem(name="Revenue", value="1000", category="Income"),
            FinancialLineItem(name="Other Income", value="200", category="Income"),
            FinancialLineItem(name="Expenses", value="500", category="Costs"),
        ]
        
        doc = FinancialDocument(
            document_type=FinancialDocumentType.PROFIT_LOSS,
            file_path="/path/to/pl.csv",
            line_items=line_items
        )
        
        # Total for specific category
        income_total = doc.calculate_total("Income")
        assert income_total == Decimal("1200")
        
        # Total for all items
        grand_total = doc.calculate_total()
        assert grand_total == Decimal("1700")


class TestFinancialDiscrepancy:
    """Test FinancialDiscrepancy model."""
    
    def test_create_discrepancy(self):
        """Test creating a financial discrepancy."""
        discrepancy = FinancialDiscrepancy(
            id="test-1",
            title="Test Discrepancy",
            description="This is a test discrepancy",
            severity=DiscrepancySeverity.HIGH,
            confidence=0.95,
            source_document=FinancialDocumentType.PROFIT_LOSS,
            expected_value=Decimal("1000"),
            actual_value=Decimal("950"),
            difference=Decimal("50")
        )
        
        assert discrepancy.id == "test-1"
        assert discrepancy.severity == DiscrepancySeverity.HIGH
        assert discrepancy.confidence == 0.95
        assert discrepancy.difference == Decimal("50")
    
    def test_confidence_validation(self):
        """Test confidence score validation."""
        with pytest.raises(ValueError):
            FinancialDiscrepancy(
                id="test",
                title="Test",
                description="Test",
                severity=DiscrepancySeverity.LOW,
                confidence=1.5,  # Invalid confidence > 1.0
                source_document=FinancialDocumentType.PROFIT_LOSS
            )


class TestAnalysisResult:
    """Test AnalysisResult model."""
    
    def test_create_analysis_result(self):
        """Test creating an analysis result."""
        discrepancies = [
            FinancialDiscrepancy(
                id="test-1",
                title="Test Critical",
                description="Critical issue",
                severity=DiscrepancySeverity.CRITICAL,
                confidence=0.9,
                source_document=FinancialDocumentType.PROFIT_LOSS
            ),
            FinancialDiscrepancy(
                id="test-2",
                title="Test High",
                description="High issue",
                severity=DiscrepancySeverity.HIGH,
                confidence=0.8,
                source_document=FinancialDocumentType.BALANCE_SHEET
            ),
        ]
        
        result = AnalysisResult(
            analysis_id="test-analysis",
            repository="test/repo",
            commit_sha="abc123",
            documents=[],
            discrepancies=discrepancies,
            summary="Test analysis"
        )
        
        assert result.total_discrepancies == 2
        assert result.critical_discrepancies == 1
        assert result.high_discrepancies == 1
        assert result.has_critical_issues() is True
    
    def test_get_discrepancies_by_severity(self):
        """Test filtering discrepancies by severity."""
        discrepancies = [
            FinancialDiscrepancy(
                id="test-1",
                title="Critical Issue",
                description="Critical",
                severity=DiscrepancySeverity.CRITICAL,
                confidence=0.9,
                source_document=FinancialDocumentType.PROFIT_LOSS
            ),
            FinancialDiscrepancy(
                id="test-2",
                title="Medium Issue",
                description="Medium",
                severity=DiscrepancySeverity.MEDIUM,
                confidence=0.7,
                source_document=FinancialDocumentType.BALANCE_SHEET
            ),
        ]
        
        result = AnalysisResult(
            analysis_id="test",
            repository="test/repo",
            commit_sha="abc123",
            documents=[],
            discrepancies=discrepancies,
            summary="Test"
        )
        
        critical_issues = result.get_discrepancies_by_severity(DiscrepancySeverity.CRITICAL)
        assert len(critical_issues) == 1
        assert critical_issues[0].title == "Critical Issue"
        
        medium_issues = result.get_discrepancies_by_severity(DiscrepancySeverity.MEDIUM)
        assert len(medium_issues) == 1