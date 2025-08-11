"""Application settings and configuration management."""

import os
from functools import lru_cache
from typing import Any, Dict, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application settings
    app_name: str = Field(default="Autonomous Financial Auditor", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # GitHub configuration
    github_token: str = Field(..., description="GitHub API token")
    github_repo_owner: str = Field(..., description="GitHub repository owner")
    github_repo_name: str = Field(..., description="GitHub repository name")
    github_webhook_secret: Optional[str] = Field(None, description="GitHub webhook secret")

    # AWS configuration
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_access_key_id: Optional[str] = Field(None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(None, description="AWS secret access key")
    
    # AWS Bedrock configuration
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0", 
        description="AWS Bedrock model ID"
    )
    bedrock_region: str = Field(default="us-east-1", description="AWS Bedrock region")

    # LLM configuration
    llm_provider: str = Field(default="bedrock", description="LLM provider (bedrock, openai, ollama)")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    ollama_model: str = Field(default="llama3.1", description="Ollama model name")

    # Financial analysis configuration
    analysis_confidence_threshold: float = Field(
        default=0.8, 
        description="Minimum confidence threshold for reporting discrepancies"
    )
    max_discrepancy_amount: float = Field(
        default=1000.0, 
        description="Maximum absolute discrepancy amount to ignore (in currency units)"
    )
    
    # Document processing
    supported_file_formats: list[str] = Field(
        default=["csv", "md", "markdown"], 
        description="Supported file formats for financial documents"
    )
    pl_file_patterns: list[str] = Field(
        default=["*p&l*", "*pl*", "*profit*loss*", "*income*statement*"],
        description="File patterns to identify P&L documents"
    )
    balance_sheet_patterns: list[str] = Field(
        default=["*balance*sheet*", "*bs*", "*balance*"],
        description="File patterns to identify Balance Sheet documents"
    )

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # Monitoring and observability
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    
    # CloudWatch configuration (for AWS deployment)
    cloudwatch_log_group: str = Field(
        default="/aws/ecs/financial-auditor", 
        description="CloudWatch log group name"
    )
    cloudwatch_metrics_namespace: str = Field(
        default="FinancialAuditor", 
        description="CloudWatch metrics namespace"
    )

    @validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    @validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider."""
        valid_providers = ["bedrock", "openai", "ollama"]
        if v.lower() not in valid_providers:
            raise ValueError(f"llm_provider must be one of {valid_providers}")
        return v.lower()

    @validator("analysis_confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, v: float) -> float:
        """Validate confidence threshold."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("analysis_confidence_threshold must be between 0.0 and 1.0")
        return v

    class Config:
        """Pydantic config."""
        
        env_prefix = "FA_"  # Financial Auditor prefix
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_github_headers(self) -> Dict[str, str]:
        """Get GitHub API headers."""
        return {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"{self.app_name}/1.0",
        }

    def get_aws_config(self) -> Dict[str, Any]:
        """Get AWS configuration dictionary."""
        config = {"region_name": self.aws_region}
        
        if self.aws_access_key_id and self.aws_secret_access_key:
            config.update({
                "aws_access_key_id": self.aws_access_key_id,
                "aws_secret_access_key": self.aws_secret_access_key,
            })
        
        return config


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()