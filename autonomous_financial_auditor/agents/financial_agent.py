"""Financial Analysis Agent using BeeAI framework."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from beeai_framework.agents import BaseAgent
from beeai_framework.backend import ChatModel
from beeai_framework.memory import ConversationMemory

from autonomous_financial_auditor.agents.tools import (
    DocumentParserTool,
    FinancialAnalysisTool,
    GitHubTool,
)
from autonomous_financial_auditor.config import get_settings
from autonomous_financial_auditor.models import AnalysisResult, FinancialDocumentType

logger = logging.getLogger(__name__)


class FinancialAnalysisAgent(BaseAgent):
    """BeeAI agent for autonomous financial document analysis."""
    
    def __init__(self, llm: Optional[ChatModel] = None) -> None:
        """Initialize the financial analysis agent."""
        self.settings = get_settings()
        
        # Initialize LLM
        if llm is None:
            llm = self._create_llm()
        
        # Initialize tools
        tools = [
            DocumentParserTool(),
            FinancialAnalysisTool(),
            GitHubTool(),
        ]
        
        # Initialize memory
        memory = ConversationMemory()
        
        super().__init__(
            name="FinancialAuditor",
            llm=llm,
            tools=tools,
            memory=memory,
            instructions=self._get_agent_instructions(),
        )
        
        self.logger = logger
    
    def _create_llm(self) -> ChatModel:
        """Create and configure the LLM based on settings."""
        if self.settings.llm_provider == "bedrock":
            return ChatModel.from_name(
                f"bedrock:{self.settings.bedrock_model_id}",
                region_name=self.settings.bedrock_region,
                **self.settings.get_aws_config()
            )
        elif self.settings.llm_provider == "openai":
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI provider")
            return ChatModel.from_name(
                "openai:gpt-4-turbo-preview",
                api_key=self.settings.openai_api_key
            )
        elif self.settings.llm_provider == "ollama":
            return ChatModel.from_name(
                f"ollama:{self.settings.ollama_model}",
                base_url=self.settings.ollama_base_url
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.settings.llm_provider}")
    
    def _get_agent_instructions(self) -> str:
        """Get detailed instructions for the financial analysis agent."""
        return """
You are an expert Financial Auditor AI agent with over 10 years of experience in financial analysis, 
accounting principles, and automated auditing systems. Your primary mission is to analyze financial 
documents for consistency, detect discrepancies, and provide actionable recommendations.

CORE RESPONSIBILITIES:
1. Retrieve financial documents (P&L and Balance Sheet) from GitHub repositories
2. Parse and analyze financial data with high precision
3. Detect inconsistencies using both rule-based and AI-powered analysis
4. Generate comprehensive audit reports with actionable recommendations
5. Create or update GitHub issues with findings and proposed fixes

ANALYSIS FRAMEWORK:
- Apply fundamental accounting principles (Assets = Liabilities + Equity)
- Verify inter-statement consistency (Net Income vs Retained Earnings changes)
- Check mathematical accuracy of calculations and totals
- Validate period consistency across documents
- Assess materiality of discrepancies based on configurable thresholds

QUALITY STANDARDS:
- Maintain >95% accuracy in discrepancy detection
- Provide confidence scores for all findings
- Categorize issues by severity (Critical, High, Medium, Low)
- Generate clear, actionable recommendations for each issue
- Document all analysis steps for audit trail

COMMUNICATION STYLE:
- Professional and precise in all communications
- Use clear financial terminology
- Provide specific numerical references
- Include confidence levels and risk assessments
- Structure reports for both technical and business audiences

TOOLS AVAILABLE:
- document_parser: Parse CSV and Markdown financial documents
- financial_analysis: Perform consistency checks and detect discrepancies  
- github: Interact with GitHub API for file retrieval and issue management

When analyzing financial documents, always:
1. Start by retrieving the latest P&L and Balance Sheet files
2. Parse both documents and extract structured data
3. Perform comprehensive consistency analysis
4. Generate detailed findings with recommendations
5. Create or update GitHub issues with your analysis

Be thorough, accurate, and provide actionable insights that help finance teams 
maintain high-quality financial reporting standards.
"""
    
    async def analyze_repository(
        self, 
        repo: Optional[str] = None, 
        ref: str = "main"
    ) -> AnalysisResult:
        """Analyze financial documents in a GitHub repository."""
        analysis_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"Starting financial analysis {analysis_id} for repository")
            
            repo = repo or f"{self.settings.github_repo_owner}/{self.settings.github_repo_name}"
            
            # Step 1: Find financial documents
            financial_files = await self._discover_financial_files(repo, ref)
            if not financial_files:
                raise ValueError("No financial documents found in repository")
            
            # Step 2: Parse documents
            documents = await self._parse_documents(financial_files)
            if len(documents) < 2:
                raise ValueError("Need at least P&L and Balance Sheet for analysis")
            
            # Step 3: Perform analysis
            analysis_prompt = self._create_analysis_prompt(documents)
            response = await self.run(analysis_prompt)
            
            # Step 4: Extract structured results
            analysis_result = self._extract_analysis_results(
                analysis_id, repo, ref, documents, response
            )
            
            # Step 5: Create/update GitHub issue
            await self._handle_github_issue(repo, analysis_result)
            
            end_time = datetime.utcnow()
            analysis_result.completed_at = end_time
            analysis_result.duration_seconds = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Completed financial analysis {analysis_id}")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Financial analysis {analysis_id} failed: {e}")
            return AnalysisResult(
                analysis_id=analysis_id,
                repository=repo or "unknown",
                commit_sha="unknown",
                branch=ref,
                documents=[],
                discrepancies=[],
                summary=f"Analysis failed: {str(e)}",
                status="failed",
                error_message=str(e),
                started_at=start_time
            )
    
    async def _discover_financial_files(self, repo: str, ref: str) -> Dict[str, str]:
        """Discover financial files in the repository."""
        self.logger.info("Discovering financial files in repository")
        
        # List root directory files
        response = await self.run(f"""
Use the github tool to list files in the root directory of repository {repo} at ref {ref}.
Look for files that match these patterns:
- P&L files: containing "p&l", "pl", "profit", "loss", "income"
- Balance Sheet files: containing "balance", "sheet", "bs"
- Supported formats: .csv, .md, .markdown
""")
        
        # Extract file paths from response
        # This is a simplified implementation - in practice, you'd parse the tool results
        financial_files = {}
        
        # For demo purposes, let's assume we found these files
        # In real implementation, parse the GitHub tool response
        return {
            "pl": "financial/q1_2024_pl.csv",
            "balance_sheet": "financial/q1_2024_balance_sheet.csv"
        }
    
    async def _parse_documents(self, financial_files: Dict[str, str]) -> List[Dict[str, Any]]:
        """Parse the discovered financial documents."""
        documents = []
        
        for doc_type, file_path in financial_files.items():
            self.logger.info(f"Parsing {doc_type} document: {file_path}")
            
            # Get file content and parse
            response = await self.run(f"""
First, use the github tool to get the content of file "{file_path}".
Then, use the document_parser tool to parse the file content and extract structured financial data.
""")
            
            # In real implementation, extract parsed document from response
            # For now, create a placeholder structure
            documents.append({
                "type": doc_type,
                "file_path": file_path,
                "parsed_data": {}  # Would contain actual parsed data
            })
        
        return documents
    
    def _create_analysis_prompt(self, documents: List[Dict[str, Any]]) -> str:
        """Create a comprehensive analysis prompt for the agent."""
        pl_doc = next((doc for doc in documents if doc["type"] == "pl"), None)
        bs_doc = next((doc for doc in documents if doc["type"] == "balance_sheet"), None)
        
        if not pl_doc or not bs_doc:
            raise ValueError("Both P&L and Balance Sheet documents are required")
        
        return f"""
Perform a comprehensive financial analysis of the following documents:

P&L Document: {pl_doc['file_path']}
Balance Sheet Document: {bs_doc['file_path']}

Using the financial_analysis tool, analyze these documents for:

1. CONSISTENCY CHECKS:
   - Net Income (P&L) vs Change in Retained Earnings (Balance Sheet)
   - Balance Sheet equation: Assets = Liabilities + Equity
   - Period consistency between documents
   - Mathematical accuracy of totals and subtotals

2. DISCREPANCY DETECTION:
   - Identify any inconsistencies with confidence scores
   - Categorize by severity (Critical, High, Medium, Low)
   - Calculate variance amounts and percentages
   - Note any missing required line items

3. ANALYSIS QUALITY:
   - Provide detailed explanations for each finding
   - Suggest root cause analysis where applicable
   - Recommend specific corrective actions
   - Assess overall financial statement reliability

4. REPORTING:
   - Generate executive summary of findings
   - List all discrepancies with supporting details
   - Provide actionable recommendations
   - Include confidence assessment for the analysis

Focus on materiality - flag discrepancies above ${self.settings.max_discrepancy_amount} 
and confidence levels above {self.settings.analysis_confidence_threshold}.

Be thorough and precise in your analysis. This audit will be used by the finance team 
to ensure reporting accuracy and compliance.
"""
    
    def _extract_analysis_results(
        self,
        analysis_id: str,
        repo: str, 
        ref: str,
        documents: List[Dict[str, Any]],
        response: Any
    ) -> AnalysisResult:
        """Extract structured analysis results from agent response."""
        # In real implementation, this would parse the agent's response
        # and extract the financial analysis results
        
        from autonomous_financial_auditor.models import (
            FinancialDocument,
            FinancialDocumentType, 
            FinancialDiscrepancy,
            DiscrepancySeverity
        )
        
        # Placeholder implementation
        discrepancies = []
        
        # Create mock analysis result for demonstration
        return AnalysisResult(
            analysis_id=analysis_id,
            repository=repo,
            commit_sha="abc123",  # Would get from GitHub API
            branch=ref,
            documents=[],  # Would contain parsed FinancialDocument objects
            discrepancies=discrepancies,
            summary="Analysis completed successfully" if not discrepancies else f"Found {len(discrepancies)} discrepancies"
        )
    
    async def _handle_github_issue(self, repo: str, analysis_result: AnalysisResult) -> None:
        """Create or update GitHub issue with analysis results."""
        if not analysis_result.discrepancies:
            self.logger.info("No discrepancies found, no issue needed")
            return
        
        issue_title = f"Financial Audit Report - {analysis_result.analysis_id[:8]}"
        issue_body = self._generate_issue_body(analysis_result)
        
        labels = ["financial-audit", "automated"]
        if analysis_result.has_critical_issues():
            labels.append("critical")
        
        # Create or update issue
        await self.run(f"""
Use the github tool to create a new issue in repository {repo} with:
- Title: "{issue_title}"
- Body: (detailed analysis report)
- Labels: {labels}

If a similar issue already exists, update it instead of creating a new one.
""")
    
    def _generate_issue_body(self, analysis_result: AnalysisResult) -> str:
        """Generate GitHub issue body with analysis results."""
        body = f"""# Financial Audit Report

**Analysis ID:** `{analysis_result.analysis_id}`
**Repository:** {analysis_result.repository}
**Branch:** {analysis_result.branch}
**Commit:** {analysis_result.commit_sha}
**Completed:** {analysis_result.completed_at or 'In Progress'}

## Summary
{analysis_result.summary}

## Analysis Results
- **Total Discrepancies:** {analysis_result.total_discrepancies}
- **Critical Issues:** {analysis_result.critical_discrepancies}
- **High Priority:** {analysis_result.high_discrepancies}

"""
        
        if analysis_result.discrepancies:
            body += "## Discrepancies Found\n\n"
            
            for i, discrepancy in enumerate(analysis_result.discrepancies, 1):
                body += f"""### {i}. {discrepancy.title}
**Severity:** {discrepancy.severity.value.upper()}
**Confidence:** {discrepancy.confidence:.0%}

{discrepancy.description}

"""
                if discrepancy.recommended_actions:
                    body += "**Recommended Actions:**\n"
                    for action in discrepancy.recommended_actions:
                        body += f"- {action}\n"
                    body += "\n"
        
        body += f"""## Next Steps
1. Review and validate the identified discrepancies
2. Implement recommended corrections
3. Re-run analysis after fixes are applied
4. Close this issue once all discrepancies are resolved

---
*This report was generated automatically by the Autonomous Financial Auditor*
*Analysis completed in {analysis_result.duration_seconds:.1f} seconds*
"""
        
        return body