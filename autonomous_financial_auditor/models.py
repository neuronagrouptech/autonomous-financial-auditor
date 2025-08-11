"""Data models for financial documents and analysis."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class FinancialDocumentType(str, Enum):
    """Types of financial documents."""
    
    PROFIT_LOSS = "profit_loss"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"
    UNKNOWN = "unknown"


class DiscrepancySeverity(str, Enum):
    """Severity levels for financial discrepancies."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FinancialLineItem(BaseModel):
    """A single line item in a financial document."""
    
    name: str = Field(..., description="Name of the line item")
    value: Union[Decimal, float] = Field(..., description="Monetary value")
    category: Optional[str] = Field(None, description="Category or section")
    subcategory: Optional[str] = Field(None, description="Subcategory")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator("value", pre=True)
    @classmethod
    def convert_to_decimal(cls, v: Any) -> Decimal:
        """Convert value to Decimal for precise calculations."""
        if isinstance(v, str):
            # Remove common formatting characters
            v = v.replace(",", "").replace("$", "").replace("(", "-").replace(")", "").strip()
        try:
            return Decimal(str(v))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert {v} to Decimal: {e}") from e


class FinancialDocument(BaseModel):
    """A parsed financial document."""
    
    document_type: FinancialDocumentType = Field(..., description="Type of financial document")
    file_path: str = Field(..., description="Path to the source file")
    period: Optional[str] = Field(None, description="Financial period (e.g., Q1 2024)")
    line_items: List[FinancialLineItem] = Field(..., description="List of line items")
    totals: Dict[str, Decimal] = Field(default_factory=dict, description="Calculated totals")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    parsed_at: datetime = Field(default_factory=datetime.utcnow, description="When document was parsed")
    
    def get_line_item(self, name: str, case_sensitive: bool = False) -> Optional[FinancialLineItem]:
        """Get a line item by name."""
        for item in self.line_items:
            if case_sensitive:
                if item.name == name:
                    return item
            else:
                if item.name.lower() == name.lower():
                    return item
        return None
    
    def get_line_items_by_category(self, category: str) -> List[FinancialLineItem]:
        """Get all line items in a specific category."""
        return [item for item in self.line_items if item.category == category]
    
    def calculate_total(self, category: Optional[str] = None) -> Decimal:
        """Calculate total for all items or items in a specific category."""
        if category:
            items = self.get_line_items_by_category(category)
        else:
            items = self.line_items
        return sum(item.value for item in items)


class FinancialDiscrepancy(BaseModel):
    """A detected financial discrepancy."""
    
    id: str = Field(..., description="Unique identifier for the discrepancy")
    title: str = Field(..., description="Brief title of the discrepancy")
    description: str = Field(..., description="Detailed description")
    severity: DiscrepancySeverity = Field(..., description="Severity level")
    confidence: float = Field(..., description="AI confidence score (0-1)")
    
    # Source information
    source_document: FinancialDocumentType = Field(..., description="Primary document type")
    related_document: Optional[FinancialDocumentType] = Field(None, description="Related document type")
    
    # Financial details
    expected_value: Optional[Decimal] = Field(None, description="Expected value")
    actual_value: Optional[Decimal] = Field(None, description="Actual value found")
    difference: Optional[Decimal] = Field(None, description="Difference amount")
    difference_percentage: Optional[float] = Field(None, description="Difference as percentage")
    
    # Line item references
    line_items: List[str] = Field(default_factory=list, description="Related line item names")
    
    # AI analysis
    root_cause_analysis: Optional[str] = Field(None, description="AI analysis of potential root causes")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended actions")
    
    # Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="When discrepancy was detected")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence score."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class AnalysisResult(BaseModel):
    """Result of financial document analysis."""
    
    analysis_id: str = Field(..., description="Unique identifier for this analysis")
    repository: str = Field(..., description="GitHub repository analyzed")
    commit_sha: str = Field(..., description="Git commit SHA")
    branch: str = Field(default="main", description="Git branch")
    
    # Documents analyzed
    documents: List[FinancialDocument] = Field(..., description="Documents that were analyzed")
    
    # Analysis results
    discrepancies: List[FinancialDiscrepancy] = Field(..., description="Detected discrepancies")
    summary: str = Field(..., description="Analysis summary")
    
    # Metrics
    total_discrepancies: int = Field(..., description="Total number of discrepancies")
    critical_discrepancies: int = Field(..., description="Number of critical discrepancies")
    high_discrepancies: int = Field(..., description="Number of high severity discrepancies")
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Analysis start time")
    completed_at: Optional[datetime] = Field(None, description="Analysis completion time")
    duration_seconds: Optional[float] = Field(None, description="Analysis duration in seconds")
    
    # Status
    status: str = Field(default="completed", description="Analysis status")
    error_message: Optional[str] = Field(None, description="Error message if analysis failed")
    
    def __init__(self, **data: Any) -> None:
        """Initialize and calculate derived fields."""
        super().__init__(**data)
        self.total_discrepancies = len(self.discrepancies)
        self.critical_discrepancies = len([d for d in self.discrepancies if d.severity == DiscrepancySeverity.CRITICAL])
        self.high_discrepancies = len([d for d in self.discrepancies if d.severity == DiscrepancySeverity.HIGH])
    
    def get_discrepancies_by_severity(self, severity: DiscrepancySeverity) -> List[FinancialDiscrepancy]:
        """Get discrepancies by severity level."""
        return [d for d in self.discrepancies if d.severity == severity]
    
    def has_critical_issues(self) -> bool:
        """Check if analysis found critical issues."""
        return self.critical_discrepancies > 0 or self.high_discrepancies > 0


class GitHubIssue(BaseModel):
    """GitHub issue representation."""
    
    number: Optional[int] = Field(None, description="Issue number (null for new issues)")
    title: str = Field(..., description="Issue title")
    body: str = Field(..., description="Issue body")
    labels: List[str] = Field(default_factory=list, description="Issue labels")
    assignees: List[str] = Field(default_factory=list, description="Issue assignees")
    state: str = Field(default="open", description="Issue state")
    
    # Analysis metadata
    analysis_id: str = Field(..., description="Associated analysis ID")
    repository: str = Field(..., description="Repository name")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update time")


class WebhookPayload(BaseModel):
    """GitHub webhook payload."""
    
    action: str = Field(..., description="Webhook action")
    repository: Dict[str, Any] = Field(..., description="Repository information")
    head_commit: Optional[Dict[str, Any]] = Field(None, description="Head commit information")
    ref: Optional[str] = Field(None, description="Git reference")
    pusher: Optional[Dict[str, Any]] = Field(None, description="Pusher information")
    
    def get_repo_full_name(self) -> str:
        """Get repository full name."""
        return self.repository["full_name"]
    
    def get_commit_sha(self) -> Optional[str]:
        """Get commit SHA."""
        if self.head_commit:
            return self.head_commit["id"]
        return None
    
    def is_main_branch(self) -> bool:
        """Check if this is a push to main branch."""
        return self.ref == "refs/heads/main"