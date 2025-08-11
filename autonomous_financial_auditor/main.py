"""Main application entry point for the Autonomous Financial Auditor."""

import asyncio
import logging
import sys
from typing import Optional

import structlog
from rich.console import Console
from rich.logging import RichHandler

from autonomous_financial_auditor.agents import FinancialAnalysisAgent
from autonomous_financial_auditor.config import get_settings


def setup_logging() -> None:
    """Set up structured logging with Rich console output."""
    settings = get_settings()
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=Console(stderr=True),
                show_time=True,
                show_path=settings.debug,
                markup=True,
                rich_tracebacks=True
            )
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


async def analyze_repository(
    repo: Optional[str] = None,
    ref: str = "main", 
    manual_trigger: bool = False
) -> int:
    """Analyze a GitHub repository for financial document discrepancies."""
    logger = logging.getLogger(__name__)
    settings = get_settings()
    
    try:
        logger.info(
            "Starting financial analysis",
            extra={
                "repo": repo or f"{settings.github_repo_owner}/{settings.github_repo_name}",
                "ref": ref,
                "manual_trigger": manual_trigger
            }
        )
        
        # Initialize the financial analysis agent
        agent = FinancialAnalysisAgent()
        
        # Perform the analysis
        result = await agent.analyze_repository(repo=repo, ref=ref)
        
        # Log results
        logger.info(
            "Financial analysis completed",
            extra={
                "analysis_id": result.analysis_id,
                "status": result.status,
                "discrepancies": result.total_discrepancies,
                "critical_issues": result.critical_discrepancies,
                "duration": result.duration_seconds
            }
        )
        
        # Print summary to console
        console = Console()
        
        if result.status == "failed":
            console.print(f"[red]❌ Analysis failed: {result.error_message}[/red]")
            return 1
        
        if result.total_discrepancies == 0:
            console.print("[green]✅ No discrepancies found! Financial documents are consistent.[/green]")
        else:
            console.print(f"[yellow]⚠️  Found {result.total_discrepancies} discrepancies[/yellow]")
            
            if result.critical_discrepancies > 0:
                console.print(f"[red]🚨 {result.critical_discrepancies} critical issues require immediate attention![/red]")
            
            console.print(f"\n📋 Summary: {result.summary}")
            console.print(f"🔗 Check GitHub issues for detailed analysis and recommendations")
        
        return 0 if result.total_discrepancies == 0 else 2  # Exit code 2 for discrepancies found
        
    except Exception as e:
        logger.error("Unexpected error during analysis", exc_info=True)
        Console().print(f"[red]💥 Unexpected error: {str(e)}[/red]")
        return 1


async def webhook_handler(payload: dict) -> int:
    """Handle GitHub webhook events."""
    logger = logging.getLogger(__name__)
    
    try:
        from autonomous_financial_auditor.models import WebhookPayload
        
        webhook_data = WebhookPayload(**payload)
        
        # Only process push events to main branch
        if not webhook_data.is_main_branch():
            logger.info("Ignoring webhook - not main branch", extra={"ref": webhook_data.ref})
            return 0
        
        logger.info(
            "Processing webhook event",
            extra={
                "action": webhook_data.action,
                "repo": webhook_data.get_repo_full_name(),
                "commit": webhook_data.get_commit_sha()
            }
        )
        
        # Trigger analysis
        return await analyze_repository(
            repo=webhook_data.get_repo_full_name(),
            ref="main"
        )
        
    except Exception as e:
        logger.error("Error processing webhook", exc_info=True)
        return 1


async def server_mode() -> None:
    """Run in server mode to handle webhooks."""
    logger = logging.getLogger(__name__)
    settings = get_settings()
    
    try:
        from fastapi import FastAPI, Request, HTTPException
        from fastapi.responses import JSONResponse
        import uvicorn
        
        app = FastAPI(
            title="Autonomous Financial Auditor",
            description="AI-powered financial document analysis service",
            version="0.1.0"
        )
        
        @app.get("/")
        async def root():
            return {"message": "Autonomous Financial Auditor is running"}
        
        @app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "financial-auditor"}
        
        @app.post("/webhook/github")
        async def github_webhook(request: Request):
            try:
                payload = await request.json()
                result_code = await webhook_handler(payload)
                
                return JSONResponse(
                    status_code=200 if result_code == 0 else 202,
                    content={"status": "processed", "code": result_code}
                )
                
            except Exception as e:
                logger.error("Webhook processing failed", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/analyze")
        async def manual_analysis(
            repo: Optional[str] = None,
            ref: str = "main"
        ):
            try:
                result_code = await analyze_repository(repo=repo, ref=ref, manual_trigger=True)
                
                return JSONResponse(
                    status_code=200,
                    content={"status": "completed", "code": result_code}
                )
                
            except Exception as e:
                logger.error("Manual analysis failed", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        # Start server
        logger.info(f"Starting server on {settings.host}:{settings.port}")
        
        config = uvicorn.Config(
            app=app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
            access_log=settings.debug
        )
        
        server = uvicorn.Server(config)
        await server.serve()
        
    except ImportError:
        logger.error("FastAPI not available. Install with: pip install fastapi uvicorn")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Autonomous Financial Auditor - AI-powered financial document analysis"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a repository")
    analyze_parser.add_argument(
        "--repo", 
        help="Repository to analyze (owner/name format)"
    )
    analyze_parser.add_argument(
        "--ref", 
        default="main", 
        help="Git reference to analyze (default: main)"
    )
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Run in server mode")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    if args.command == "analyze":
        # Run single analysis
        exit_code = asyncio.run(analyze_repository(
            repo=args.repo,
            ref=args.ref,
            manual_trigger=True
        ))
        sys.exit(exit_code)
        
    elif args.command == "server":
        # Run server mode
        asyncio.run(server_mode())
        
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()