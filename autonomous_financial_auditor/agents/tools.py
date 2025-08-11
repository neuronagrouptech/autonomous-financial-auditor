"""Custom BeeAI tools for financial document analysis."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

import httpx
from beeai_framework.tools.base import Tool, ToolResult

from autonomous_financial_auditor.config import get_settings
from autonomous_financial_auditor.models import FinancialDocument
from autonomous_financial_auditor.parsers.factory import parser_factory

logger = logging.getLogger(__name__)


class DocumentParserTool(Tool):
    """Tool for parsing financial documents."""
    
    name = "document_parser"
    description = "Parse financial documents (CSV, Markdown) and extract structured data"
    
    def __init__(self) -> None:
        """Initialize the document parser tool."""
        super().__init__()
        self.parser_factory = parser_factory
        
    async def run(self, file_path: str, content: str) -> ToolResult:
        """Parse a financial document."""
        try:
            logger.info(f"Parsing document: {file_path}")
            
            document = self.parser_factory.parse_file(file_path, content)
            if not document:
                return ToolResult.error(f"Could not parse document: {file_path}")
            
            # Convert to JSON-serializable format
            result = {
                "document_type": document.document_type.value,
                "file_path": document.file_path,
                "period": document.period,
                "line_items": [
                    {
                        "name": item.name,
                        "value": str(item.value),
                        "category": item.category,
                        "metadata": item.metadata
                    }
                    for item in document.line_items
                ],
                "totals": {key: str(value) for key, value in document.totals.items()},
                "metadata": document.metadata
            }
            
            return ToolResult.success(result)
            
        except Exception as e:
            logger.error(f"Error parsing document {file_path}: {e}")
            return ToolResult.error(f"Error parsing document: {str(e)}")


class FinancialAnalysisTool(Tool):
    """Tool for analyzing financial documents and detecting discrepancies."""
    
    name = "financial_analysis"
    description = "Analyze financial documents for consistency and detect discrepancies"
    
    def __init__(self) -> None:
        """Initialize the financial analysis tool."""
        super().__init__()
        self.settings = get_settings()
        
    async def run(
        self, 
        pl_document: Dict[str, Any], 
        balance_sheet_document: Dict[str, Any]
    ) -> ToolResult:
        """Analyze financial documents for consistency."""
        try:
            logger.info("Performing financial analysis")
            
            discrepancies = []
            
            # Convert back to FinancialDocument objects for analysis
            from autonomous_financial_auditor.models import (
                FinancialDocument, 
                FinancialDocumentType, 
                FinancialLineItem
            )
            from decimal import Decimal
            
            # Reconstruct P&L document
            pl_line_items = [
                FinancialLineItem(
                    name=item["name"],
                    value=Decimal(item["value"]),
                    category=item.get("category"),
                    metadata=item.get("metadata", {})
                )
                for item in pl_document["line_items"]
            ]
            
            pl_doc = FinancialDocument(
                document_type=FinancialDocumentType.PROFIT_LOSS,
                file_path=pl_document["file_path"],
                period=pl_document.get("period"),
                line_items=pl_line_items,
                totals={k: Decimal(v) for k, v in pl_document["totals"].items()},
                metadata=pl_document["metadata"]
            )
            
            # Reconstruct Balance Sheet document
            bs_line_items = [
                FinancialLineItem(
                    name=item["name"],
                    value=Decimal(item["value"]),
                    category=item.get("category"),
                    metadata=item.get("metadata", {})
                )
                for item in balance_sheet_document["line_items"]
            ]
            
            bs_doc = FinancialDocument(
                document_type=FinancialDocumentType.BALANCE_SHEET,
                file_path=balance_sheet_document["file_path"],
                period=balance_sheet_document.get("period"),
                line_items=bs_line_items,
                totals={k: Decimal(v) for k, v in balance_sheet_document["totals"].items()},
                metadata=balance_sheet_document["metadata"]
            )
            
            # Perform consistency checks
            consistency_checks = [
                self._check_net_income_consistency(pl_doc, bs_doc),
                self._check_balance_sheet_equation(bs_doc),
                self._check_period_consistency(pl_doc, bs_doc),
                self._check_totals_consistency(pl_doc),
                self._check_totals_consistency(bs_doc),
            ]
            
            # Collect all discrepancies
            for check_result in consistency_checks:
                if check_result:
                    discrepancies.extend(check_result)
            
            result = {
                "discrepancies_count": len(discrepancies),
                "discrepancies": discrepancies,
                "analysis_summary": self._generate_analysis_summary(discrepancies),
                "recommendations": self._generate_recommendations(discrepancies)
            }
            
            return ToolResult.success(result)
            
        except Exception as e:
            logger.error(f"Error in financial analysis: {e}")
            return ToolResult.error(f"Financial analysis failed: {str(e)}")
    
    def _check_net_income_consistency(
        self, 
        pl_doc: FinancialDocument, 
        bs_doc: FinancialDocument
    ) -> List[Dict[str, Any]]:
        """Check if Net Income from P&L matches change in Retained Earnings."""
        discrepancies = []
        
        # Find Net Income in P&L
        net_income_item = pl_doc.get_line_item("net_income")
        if not net_income_item:
            # Try alternative names
            for alt_name in ["net income", "profit", "earnings"]:
                net_income_item = pl_doc.get_line_item(alt_name)
                if net_income_item:
                    break
        
        # Find Retained Earnings in Balance Sheet
        retained_earnings_item = bs_doc.get_line_item("retained_earnings")
        if not retained_earnings_item:
            for alt_name in ["retained earnings", "accumulated earnings"]:
                retained_earnings_item = bs_doc.get_line_item(alt_name)
                if retained_earnings_item:
                    break
        
        if net_income_item and retained_earnings_item:
            # For this analysis, we assume the retained earnings shows the change
            # In a real scenario, you'd compare with previous period
            difference = abs(net_income_item.value - retained_earnings_item.value)
            
            if difference > self.settings.max_discrepancy_amount:
                discrepancies.append({
                    "id": "net_income_retained_earnings_mismatch",
                    "title": "Net Income and Retained Earnings Mismatch",
                    "description": f"Net Income ({net_income_item.value}) does not match change in Retained Earnings ({retained_earnings_item.value})",
                    "severity": "high" if difference > 10000 else "medium",
                    "confidence": 0.9,
                    "expected_value": str(net_income_item.value),
                    "actual_value": str(retained_earnings_item.value),
                    "difference": str(difference),
                    "line_items": [net_income_item.name, retained_earnings_item.name]
                })
        
        return discrepancies
    
    def _check_balance_sheet_equation(self, bs_doc: FinancialDocument) -> List[Dict[str, Any]]:
        """Check if Assets = Liabilities + Equity."""
        discrepancies = []
        
        # Find major balance sheet components
        total_assets = bs_doc.get_line_item("total_assets")
        total_liabilities = bs_doc.get_line_item("total_liabilities")
        shareholders_equity = bs_doc.get_line_item("shareholders_equity")
        
        if total_assets and total_liabilities and shareholders_equity:
            expected_total = total_liabilities.value + shareholders_equity.value
            difference = abs(total_assets.value - expected_total)
            
            if difference > self.settings.max_discrepancy_amount:
                discrepancies.append({
                    "id": "balance_sheet_equation_imbalance",
                    "title": "Balance Sheet Equation Imbalance",
                    "description": f"Assets ({total_assets.value}) ≠ Liabilities ({total_liabilities.value}) + Equity ({shareholders_equity.value})",
                    "severity": "critical",
                    "confidence": 0.95,
                    "expected_value": str(expected_total),
                    "actual_value": str(total_assets.value),
                    "difference": str(difference),
                    "line_items": [total_assets.name, total_liabilities.name, shareholders_equity.name]
                })
        
        return discrepancies
    
    def _check_period_consistency(
        self, 
        pl_doc: FinancialDocument, 
        bs_doc: FinancialDocument
    ) -> List[Dict[str, Any]]:
        """Check if both documents are for the same period."""
        discrepancies = []
        
        if pl_doc.period and bs_doc.period:
            if pl_doc.period != bs_doc.period:
                discrepancies.append({
                    "id": "period_mismatch",
                    "title": "Document Period Mismatch",
                    "description": f"P&L period ({pl_doc.period}) differs from Balance Sheet period ({bs_doc.period})",
                    "severity": "medium",
                    "confidence": 0.8,
                    "expected_value": pl_doc.period,
                    "actual_value": bs_doc.period,
                    "line_items": []
                })
        
        return discrepancies
    
    def _check_totals_consistency(self, doc: FinancialDocument) -> List[Dict[str, Any]]:
        """Check if calculated totals match document totals."""
        discrepancies = []
        
        # This is a placeholder for more sophisticated total validation
        # In practice, you'd check specific subtotals against their components
        
        return discrepancies
    
    def _generate_analysis_summary(self, discrepancies: List[Dict[str, Any]]) -> str:
        """Generate a summary of the analysis."""
        if not discrepancies:
            return "No significant discrepancies found. Financial documents appear consistent."
        
        critical_count = len([d for d in discrepancies if d["severity"] == "critical"])
        high_count = len([d for d in discrepancies if d["severity"] == "high"])
        medium_count = len([d for d in discrepancies if d["severity"] == "medium"])
        
        summary = f"Found {len(discrepancies)} discrepancies: "
        severity_parts = []
        
        if critical_count > 0:
            severity_parts.append(f"{critical_count} critical")
        if high_count > 0:
            severity_parts.append(f"{high_count} high")
        if medium_count > 0:
            severity_parts.append(f"{medium_count} medium")
        
        summary += ", ".join(severity_parts) + " severity issues."
        
        return summary
    
    def _generate_recommendations(self, discrepancies: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on discrepancies."""
        recommendations = []
        
        for discrepancy in discrepancies:
            if discrepancy["id"] == "net_income_retained_earnings_mismatch":
                recommendations.append(
                    "Review the calculation of Net Income and verify the change in Retained Earnings. "
                    "Ensure all dividends and other equity transactions are properly recorded."
                )
            elif discrepancy["id"] == "balance_sheet_equation_imbalance":
                recommendations.append(
                    "Critical: Balance Sheet does not balance. Review all asset, liability, and equity "
                    "accounts for recording errors or missing entries."
                )
            elif discrepancy["id"] == "period_mismatch":
                recommendations.append(
                    "Ensure both P&L and Balance Sheet are for the same financial period. "
                    "Mismatched periods can lead to incorrect analysis."
                )
        
        if not recommendations:
            recommendations.append("Continue monitoring financial statements for consistency.")
        
        return recommendations


class GitHubTool(Tool):
    """Tool for GitHub API operations."""
    
    name = "github"
    description = "Interact with GitHub API for repository operations and issue management"
    
    def __init__(self) -> None:
        """Initialize the GitHub tool."""
        super().__init__()
        self.settings = get_settings()
        
    async def run(
        self, 
        action: str, 
        repo: Optional[str] = None,
        **kwargs: Any
    ) -> ToolResult:
        """Perform GitHub API operations."""
        try:
            repo = repo or f"{self.settings.github_repo_owner}/{self.settings.github_repo_name}"
            
            if action == "get_file":
                return await self._get_file(repo, kwargs.get("path", ""), kwargs.get("ref", "main"))
            elif action == "list_files":
                return await self._list_files(repo, kwargs.get("path", ""), kwargs.get("ref", "main"))
            elif action == "create_issue":
                return await self._create_issue(repo, kwargs)
            elif action == "update_issue":
                return await self._update_issue(repo, kwargs.get("issue_number"), kwargs)
            elif action == "list_issues":
                return await self._list_issues(repo, kwargs)
            else:
                return ToolResult.error(f"Unknown action: {action}")
                
        except Exception as e:
            logger.error(f"GitHub API error: {e}")
            return ToolResult.error(f"GitHub operation failed: {str(e)}")
    
    async def _get_file(self, repo: str, path: str, ref: str) -> ToolResult:
        """Get file content from repository."""
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        params = {"ref": ref}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, 
                headers=self.settings.get_github_headers(),
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("type") == "file":
                    import base64
                    content = base64.b64decode(data["content"]).decode("utf-8")
                    return ToolResult.success({
                        "path": path,
                        "content": content,
                        "sha": data["sha"],
                        "size": data["size"]
                    })
                else:
                    return ToolResult.error(f"Path {path} is not a file")
            else:
                return ToolResult.error(f"Failed to get file: {response.status_code}")
    
    async def _list_files(self, repo: str, path: str, ref: str) -> ToolResult:
        """List files in repository directory."""
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        params = {"ref": ref}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.settings.get_github_headers(),
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    files = [
                        {
                            "name": item["name"],
                            "path": item["path"],
                            "type": item["type"],
                            "size": item.get("size", 0)
                        }
                        for item in data
                    ]
                    return ToolResult.success({"files": files})
                else:
                    return ToolResult.error(f"Path {path} is not a directory")
            else:
                return ToolResult.error(f"Failed to list files: {response.status_code}")
    
    async def _create_issue(self, repo: str, issue_data: Dict[str, Any]) -> ToolResult:
        """Create a new GitHub issue."""
        url = f"https://api.github.com/repos/{repo}/issues"
        
        payload = {
            "title": issue_data.get("title", "Financial Analysis Issue"),
            "body": issue_data.get("body", ""),
            "labels": issue_data.get("labels", []),
            "assignees": issue_data.get("assignees", [])
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self.settings.get_github_headers(),
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                return ToolResult.success({
                    "number": data["number"],
                    "url": data["html_url"],
                    "title": data["title"]
                })
            else:
                return ToolResult.error(f"Failed to create issue: {response.status_code}")
    
    async def _update_issue(self, repo: str, issue_number: int, issue_data: Dict[str, Any]) -> ToolResult:
        """Update an existing GitHub issue."""
        url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
        
        payload = {}
        if "title" in issue_data:
            payload["title"] = issue_data["title"]
        if "body" in issue_data:
            payload["body"] = issue_data["body"]
        if "labels" in issue_data:
            payload["labels"] = issue_data["labels"]
        if "state" in issue_data:
            payload["state"] = issue_data["state"]
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                url,
                headers=self.settings.get_github_headers(),
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return ToolResult.success({
                    "number": data["number"],
                    "url": data["html_url"],
                    "title": data["title"],
                    "state": data["state"]
                })
            else:
                return ToolResult.error(f"Failed to update issue: {response.status_code}")
    
    async def _list_issues(self, repo: str, filters: Dict[str, Any]) -> ToolResult:
        """List issues in repository."""
        url = f"https://api.github.com/repos/{repo}/issues"
        
        params = {
            "state": filters.get("state", "open"),
            "labels": ",".join(filters.get("labels", [])),
            "per_page": filters.get("per_page", 30)
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.settings.get_github_headers(),
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                issues = [
                    {
                        "number": issue["number"],
                        "title": issue["title"],
                        "state": issue["state"],
                        "labels": [label["name"] for label in issue["labels"]],
                        "url": issue["html_url"]
                    }
                    for issue in data
                ]
                return ToolResult.success({"issues": issues})
            else:
                return ToolResult.error(f"Failed to list issues: {response.status_code}")