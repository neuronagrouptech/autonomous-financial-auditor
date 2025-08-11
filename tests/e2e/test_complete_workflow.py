"""End-to-end tests for complete financial auditor workflow."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import os

from autonomous_financial_auditor.main import analyze_repository


class TestCompleteWorkflow:
    """Test complete end-to-end workflow."""
    
    @pytest.fixture
    def sample_pl_csv(self):
        """Sample P&L CSV content."""
        return """Line Item,Amount
Revenue,100000.00
Cost of Goods Sold,40000.00
Gross Profit,60000.00
Operating Expenses,35000.00
Operating Income,25000.00
Interest Expense,2000.00
Income Before Tax,23000.00
Income Tax,5000.00
Net Income,18000.00"""
    
    @pytest.fixture
    def sample_balance_sheet_csv(self):
        """Sample Balance Sheet CSV content."""
        return """Line Item,Amount
Cash,50000.00
Accounts Receivable,25000.00
Inventory,15000.00
Total Current Assets,90000.00
Property Plant Equipment,100000.00
Total Assets,190000.00
Accounts Payable,20000.00
Short-term Debt,10000.00
Total Current Liabilities,30000.00
Long-term Debt,50000.00
Total Liabilities,80000.00
Share Capital,50000.00
Retained Earnings,60000.00
Total Shareholders Equity,110000.00"""
    
    @pytest.fixture
    def inconsistent_balance_sheet_csv(self):
        """Balance Sheet with inconsistencies."""
        return """Line Item,Amount
Cash,50000.00
Accounts Receivable,25000.00
Inventory,15000.00
Total Current Assets,90000.00
Property Plant Equipment,100000.00
Total Assets,190000.00
Accounts Payable,20000.00
Short-term Debt,10000.00
Total Current Liabilities,30000.00
Long-term Debt,50000.00
Total Liabilities,80000.00
Share Capital,50000.00
Retained Earnings,50000.00
Total Shareholders Equity,100000.00"""  # Total Assets (190k) ≠ Liabilities (80k) + Equity (100k) = 180k
    
    @patch('autonomous_financial_auditor.main.FinancialAnalysisAgent')
    @patch('autonomous_financial_auditor.main.get_settings')
    @pytest.mark.asyncio
    async def test_analyze_repository_success(self, mock_get_settings, mock_agent_class):
        """Test successful repository analysis."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.github_repo_owner = "test-owner"
        mock_settings.github_repo_name = "test-repo"
        mock_get_settings.return_value = mock_settings
        
        # Mock successful analysis result
        from autonomous_financial_auditor.models import AnalysisResult
        
        mock_result = AnalysisResult(
            analysis_id="test-123",
            repository="test-owner/test-repo",
            commit_sha="abc123",
            documents=[],
            discrepancies=[],
            summary="No discrepancies found"
        )
        
        mock_agent = Mock()
        mock_agent.analyze_repository = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent
        
        # Test successful analysis
        exit_code = await analyze_repository(repo="test-owner/test-repo", ref="main", manual_trigger=True)
        
        assert exit_code == 0
        mock_agent.analyze_repository.assert_called_once_with(repo="test-owner/test-repo", ref="main")
    
    @patch('autonomous_financial_auditor.main.FinancialAnalysisAgent')
    @patch('autonomous_financial_auditor.main.get_settings')
    @pytest.mark.asyncio
    async def test_analyze_repository_with_discrepancies(self, mock_get_settings, mock_agent_class):
        """Test repository analysis with discrepancies found."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.github_repo_owner = "test-owner"
        mock_settings.github_repo_name = "test-repo"
        mock_get_settings.return_value = mock_settings
        
        # Mock analysis result with discrepancies
        from autonomous_financial_auditor.models import AnalysisResult, FinancialDiscrepancy, DiscrepancySeverity
        
        discrepancy = FinancialDiscrepancy(
            id="test-1",
            title="Balance Sheet Imbalance",
            description="Assets ≠ Liabilities + Equity",
            severity=DiscrepancySeverity.CRITICAL,
            confidence=0.95,
            source_document="balance_sheet"
        )
        
        mock_result = AnalysisResult(
            analysis_id="test-123",
            repository="test-owner/test-repo",
            commit_sha="abc123",
            documents=[],
            discrepancies=[discrepancy],
            summary="Critical issues found"
        )
        
        mock_agent = Mock()
        mock_agent.analyze_repository = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent
        
        # Test analysis with discrepancies
        exit_code = await analyze_repository(repo="test-owner/test-repo", ref="main", manual_trigger=True)
        
        assert exit_code == 2  # Exit code 2 for discrepancies found
    
    @patch('autonomous_financial_auditor.main.FinancialAnalysisAgent')
    @patch('autonomous_financial_auditor.main.get_settings')
    @pytest.mark.asyncio
    async def test_analyze_repository_failure(self, mock_get_settings, mock_agent_class):
        """Test repository analysis failure."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.github_repo_owner = "test-owner"
        mock_settings.github_repo_name = "test-repo"
        mock_get_settings.return_value = mock_settings
        
        # Mock failed analysis result
        from autonomous_financial_auditor.models import AnalysisResult
        
        mock_result = AnalysisResult(
            analysis_id="test-123",
            repository="test-owner/test-repo",
            commit_sha="abc123",
            documents=[],
            discrepancies=[],
            summary="Analysis failed",
            status="failed",
            error_message="Network error"
        )
        
        mock_agent = Mock()
        mock_agent.analyze_repository = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent
        
        # Test failed analysis
        exit_code = await analyze_repository(repo="test-owner/test-repo", ref="main", manual_trigger=True)
        
        assert exit_code == 1  # Exit code 1 for failure
    
    @patch('autonomous_financial_auditor.main.FinancialAnalysisAgent')
    @patch('autonomous_financial_auditor.main.get_settings')
    @pytest.mark.asyncio
    async def test_analyze_repository_exception(self, mock_get_settings, mock_agent_class):
        """Test repository analysis with unexpected exception."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.github_repo_owner = "test-owner"  
        mock_settings.github_repo_name = "test-repo"
        mock_get_settings.return_value = mock_settings
        
        # Mock agent that raises exception
        mock_agent = Mock()
        mock_agent.analyze_repository = AsyncMock(side_effect=Exception("Unexpected error"))
        mock_agent_class.return_value = mock_agent
        
        # Test exception handling
        exit_code = await analyze_repository(repo="test-owner/test-repo", ref="main", manual_trigger=True)
        
        assert exit_code == 1  # Exit code 1 for failure
    
    @pytest.mark.asyncio
    async def test_webhook_handler_main_branch(self):
        """Test webhook handler for main branch push."""
        from autonomous_financial_auditor.main import webhook_handler
        
        payload = {
            "action": "push",
            "repository": {"full_name": "test/repo"},
            "head_commit": {"id": "abc123"},
            "ref": "refs/heads/main",
            "pusher": {"name": "testuser"}
        }
        
        with patch('autonomous_financial_auditor.main.analyze_repository') as mock_analyze:
            mock_analyze.return_value = 0
            
            result = await webhook_handler(payload)
            
            assert result == 0
            mock_analyze.assert_called_once_with(repo="test/repo", ref="main")
    
    @pytest.mark.asyncio
    async def test_webhook_handler_non_main_branch(self):
        """Test webhook handler for non-main branch push."""
        from autonomous_financial_auditor.main import webhook_handler
        
        payload = {
            "action": "push",
            "repository": {"full_name": "test/repo"},
            "head_commit": {"id": "abc123"},
            "ref": "refs/heads/feature-branch",
            "pusher": {"name": "testuser"}
        }
        
        with patch('autonomous_financial_auditor.main.analyze_repository') as mock_analyze:
            result = await webhook_handler(payload)
            
            assert result == 0
            mock_analyze.assert_not_called()  # Should not analyze non-main branches
    
    def test_document_parsing_integration(self, sample_pl_csv, sample_balance_sheet_csv):
        """Test document parsing integration."""
        from autonomous_financial_auditor.parsers.factory import ParserFactory
        
        factory = ParserFactory()
        
        # Parse P&L document
        pl_doc = factory.parse_file("pl.csv", sample_pl_csv)
        assert pl_doc is not None
        assert pl_doc.document_type.value == "profit_loss"
        
        # Check key line items
        revenue = pl_doc.get_line_item("revenue")
        assert revenue is not None
        assert revenue.value == 100000.00
        
        net_income = pl_doc.get_line_item("net_income") 
        assert net_income is not None
        assert net_income.value == 18000.00
        
        # Parse Balance Sheet document
        bs_doc = factory.parse_file("balance_sheet.csv", sample_balance_sheet_csv)
        assert bs_doc is not None
        assert bs_doc.document_type.value == "balance_sheet"
        
        # Check balance sheet equation
        total_assets = bs_doc.get_line_item("total_assets")
        total_liabilities = bs_doc.get_line_item("total_liabilities")
        shareholders_equity = bs_doc.get_line_item("total_shareholders_equity")
        
        assert total_assets is not None
        assert total_liabilities is not None
        assert shareholders_equity is not None
        
        # Should balance: Assets = Liabilities + Equity
        assert total_assets.value == total_liabilities.value + shareholders_equity.value
    
    def test_financial_analysis_integration(self, sample_pl_csv, inconsistent_balance_sheet_csv):
        """Test financial analysis with inconsistent documents."""
        from autonomous_financial_auditor.parsers.factory import ParserFactory
        from autonomous_financial_auditor.agents.tools import FinancialAnalysisTool
        
        factory = ParserFactory()
        
        # Parse documents
        pl_doc = factory.parse_file("pl.csv", sample_pl_csv)
        bs_doc = factory.parse_file("balance_sheet.csv", inconsistent_balance_sheet_csv)
        
        # Convert to analysis format
        pl_dict = {
            "document_type": pl_doc.document_type.value,
            "file_path": pl_doc.file_path,
            "period": pl_doc.period,
            "line_items": [
                {
                    "name": item.name,
                    "value": str(item.value),
                    "category": item.category,
                    "metadata": item.metadata
                }
                for item in pl_doc.line_items
            ],
            "totals": {key: str(value) for key, value in pl_doc.totals.items()},
            "metadata": pl_doc.metadata
        }
        
        bs_dict = {
            "document_type": bs_doc.document_type.value,
            "file_path": bs_doc.file_path,
            "period": bs_doc.period,
            "line_items": [
                {
                    "name": item.name,
                    "value": str(item.value),
                    "category": item.category,
                    "metadata": item.metadata
                }
                for item in bs_doc.line_items
            ],
            "totals": {key: str(value) for key, value in bs_doc.totals.items()},
            "metadata": bs_doc.metadata
        }
        
        # This test would require mocking the async tool run method
        # In a real integration test, you would set up the full environment