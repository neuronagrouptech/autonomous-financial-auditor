"""Integration tests for the BeeAI financial analysis agent."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from autonomous_financial_auditor.agents import FinancialAnalysisAgent
from autonomous_financial_auditor.config import get_settings


class TestFinancialAnalysisAgent:
    """Test financial analysis agent integration."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock()
        settings.llm_provider = "ollama"
        settings.ollama_base_url = "http://localhost:11434"
        settings.ollama_model = "llama3.1"
        settings.github_token = "test-token"
        settings.github_repo_owner = "test-owner"
        settings.github_repo_name = "test-repo"
        settings.max_discrepancy_amount = 1000.0
        settings.analysis_confidence_threshold = 0.8
        return settings
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing."""
        llm = Mock()
        llm.run = AsyncMock(return_value="Mock LLM response")
        return llm
    
    @patch('autonomous_financial_auditor.agents.financial_agent.get_settings')
    def test_agent_initialization(self, mock_get_settings, mock_settings, mock_llm):
        """Test agent initialization."""
        mock_get_settings.return_value = mock_settings
        
        agent = FinancialAnalysisAgent(llm=mock_llm)
        
        assert agent.name == "FinancialAuditor"
        assert len(agent.tools) == 3  # DocumentParserTool, FinancialAnalysisTool, GitHubTool
        assert agent.llm == mock_llm
    
    @patch('autonomous_financial_auditor.agents.financial_agent.get_settings')
    def test_create_llm_bedrock(self, mock_get_settings, mock_settings):
        """Test LLM creation for Bedrock."""
        mock_settings.llm_provider = "bedrock"
        mock_settings.bedrock_model_id = "anthropic.claude-3-5-sonnet"
        mock_settings.bedrock_region = "us-east-1"
        mock_settings.get_aws_config.return_value = {"region_name": "us-east-1"}
        mock_get_settings.return_value = mock_settings
        
        with patch('autonomous_financial_auditor.agents.financial_agent.ChatModel') as MockChatModel:
            agent = FinancialAnalysisAgent()
            
            MockChatModel.from_name.assert_called_once_with(
                "bedrock:anthropic.claude-3-5-sonnet",
                region_name="us-east-1",
                **{"region_name": "us-east-1"}
            )
    
    @patch('autonomous_financial_auditor.agents.financial_agent.get_settings')
    def test_create_llm_openai(self, mock_get_settings, mock_settings):
        """Test LLM creation for OpenAI."""
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "test-key"
        mock_get_settings.return_value = mock_settings
        
        with patch('autonomous_financial_auditor.agents.financial_agent.ChatModel') as MockChatModel:
            agent = FinancialAnalysisAgent()
            
            MockChatModel.from_name.assert_called_once_with(
                "openai:gpt-4-turbo-preview",
                api_key="test-key"
            )
    
    @patch('autonomous_financial_auditor.agents.financial_agent.get_settings')
    def test_create_llm_invalid_provider(self, mock_get_settings, mock_settings):
        """Test LLM creation with invalid provider."""
        mock_settings.llm_provider = "invalid"
        mock_get_settings.return_value = mock_settings
        
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            FinancialAnalysisAgent()
    
    @patch('autonomous_financial_auditor.agents.financial_agent.get_settings')
    @pytest.mark.asyncio
    async def test_analyze_repository_success(self, mock_get_settings, mock_settings, mock_llm):
        """Test successful repository analysis."""
        mock_get_settings.return_value = mock_settings
        
        agent = FinancialAnalysisAgent(llm=mock_llm)
        
        # Mock the agent's run method to simulate successful analysis
        agent.run = AsyncMock(return_value="Analysis completed successfully")
        
        # Mock internal methods
        agent._discover_financial_files = AsyncMock(return_value={
            "pl": "financial/pl.csv",
            "balance_sheet": "financial/bs.csv"
        })
        
        agent._parse_documents = AsyncMock(return_value=[
            {"type": "pl", "file_path": "financial/pl.csv"},
            {"type": "balance_sheet", "file_path": "financial/bs.csv"}
        ])
        
        agent._handle_github_issue = AsyncMock()
        
        result = await agent.analyze_repository("test/repo", "main")
        
        assert result.status == "completed"
        assert result.repository == "test/repo"
        assert result.branch == "main"
        assert result.analysis_id is not None
        assert result.completed_at is not None
    
    @patch('autonomous_financial_auditor.agents.financial_agent.get_settings')
    @pytest.mark.asyncio
    async def test_analyze_repository_no_files(self, mock_get_settings, mock_settings, mock_llm):
        """Test repository analysis with no financial files found."""
        mock_get_settings.return_value = mock_settings
        
        agent = FinancialAnalysisAgent(llm=mock_llm)
        
        # Mock finding no files
        agent._discover_financial_files = AsyncMock(return_value={})
        
        result = await agent.analyze_repository("test/repo", "main")
        
        assert result.status == "failed"
        assert "No financial documents found" in result.error_message
    
    @patch('autonomous_financial_auditor.agents.financial_agent.get_settings')
    @pytest.mark.asyncio
    async def test_analyze_repository_exception(self, mock_get_settings, mock_settings, mock_llm):
        """Test repository analysis with unexpected exception."""
        mock_get_settings.return_value = mock_settings
        
        agent = FinancialAnalysisAgent(llm=mock_llm)
        
        # Mock an exception during file discovery
        agent._discover_financial_files = AsyncMock(side_effect=Exception("Network error"))
        
        result = await agent.analyze_repository("test/repo", "main")
        
        assert result.status == "failed"
        assert "Network error" in result.error_message
    
    def test_get_agent_instructions(self, mock_llm):
        """Test agent instructions are properly formatted."""
        with patch('autonomous_financial_auditor.agents.financial_agent.get_settings'):
            agent = FinancialAnalysisAgent(llm=mock_llm)
            
            instructions = agent._get_agent_instructions()
            
            assert "Financial Auditor AI agent" in instructions
            assert "CORE RESPONSIBILITIES" in instructions
            assert "ANALYSIS FRAMEWORK" in instructions
            assert "TOOLS AVAILABLE" in instructions
    
    def test_create_analysis_prompt(self, mock_llm):
        """Test analysis prompt creation."""
        with patch('autonomous_financial_auditor.agents.financial_agent.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.max_discrepancy_amount = 1000.0
            mock_settings.analysis_confidence_threshold = 0.8
            mock_get_settings.return_value = mock_settings
            
            agent = FinancialAnalysisAgent(llm=mock_llm)
            
            documents = [
                {"type": "pl", "file_path": "financial/pl.csv"},
                {"type": "balance_sheet", "file_path": "financial/bs.csv"}
            ]
            
            prompt = agent._create_analysis_prompt(documents)
            
            assert "financial_analysis tool" in prompt
            assert "CONSISTENCY CHECKS" in prompt
            assert "Net Income" in prompt
            assert "Assets = Liabilities + Equity" in prompt
            assert "1000.0" in prompt  # max_discrepancy_amount
            assert "0.8" in prompt  # confidence_threshold
    
    def test_create_analysis_prompt_missing_documents(self, mock_llm):
        """Test analysis prompt creation with missing documents."""
        with patch('autonomous_financial_auditor.agents.financial_agent.get_settings'):
            agent = FinancialAnalysisAgent(llm=mock_llm)
            
            # Missing balance sheet
            documents = [{"type": "pl", "file_path": "financial/pl.csv"}]
            
            with pytest.raises(ValueError, match="Both P&L and Balance Sheet documents are required"):
                agent._create_analysis_prompt(documents)
    
    def test_generate_issue_body(self, mock_llm):
        """Test GitHub issue body generation."""
        with patch('autonomous_financial_auditor.agents.financial_agent.get_settings'):
            agent = FinancialAnalysisAgent(llm=mock_llm)
            
            from autonomous_financial_auditor.models import AnalysisResult, FinancialDiscrepancy, DiscrepancySeverity
            from datetime import datetime
            
            # Create mock analysis result with discrepancies
            discrepancy = FinancialDiscrepancy(
                id="test-1",
                title="Balance Sheet Imbalance",
                description="Assets do not equal Liabilities + Equity",
                severity=DiscrepancySeverity.CRITICAL,
                confidence=0.95,
                source_document="balance_sheet",
                recommended_actions=["Review asset accounts", "Check equity calculations"]
            )
            
            result = AnalysisResult(
                analysis_id="test-123",
                repository="test/repo",
                commit_sha="abc123",
                branch="main",
                documents=[],
                discrepancies=[discrepancy],
                summary="Critical issues found",
                completed_at=datetime.utcnow(),
                duration_seconds=45.2
            )
            
            issue_body = agent._generate_issue_body(result)
            
            assert "Financial Audit Report" in issue_body
            assert "test-123" in issue_body
            assert "test/repo" in issue_body
            assert "abc123" in issue_body
            assert "Balance Sheet Imbalance" in issue_body
            assert "CRITICAL" in issue_body
            assert "95%" in issue_body
            assert "Review asset accounts" in issue_body
            assert "45.1 seconds" in issue_body