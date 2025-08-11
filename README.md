# Autonomous Financial Auditor

![CI/CD Pipeline](https://github.com/your-org/autonomous-financial-auditor/workflows/CI/CD%20Pipeline/badge.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)

> AI-powered autonomous financial document analysis system that automatically detects discrepancies between P&L statements and Balance Sheets using advanced LLMs and the BeeAI framework.

## 🚀 Key Features

- **🤖 Autonomous Analysis**: Powered by BeeAI framework with advanced LLM reasoning
- **📊 Multi-Format Support**: Parse CSV and Markdown financial documents
- **🔍 Smart Detection**: Identify inconsistencies using rule-based + AI analysis
- **⚡ Real-time Processing**: GitHub webhook integration for automatic auditing
- **🎯 Precise Reporting**: Generate detailed GitHub issues with actionable recommendations
- **☁️ Cloud-Ready**: Production deployment on AWS ECS with full observability
- **🔒 Enterprise Security**: Comprehensive security scanning and audit trails

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Local Development](#-local-development)
- [Production Deployment](#-production-deployment)
- [Configuration](#-configuration)
- [Usage Examples](#-usage-examples)
- [API Reference](#-api-reference)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [Troubleshooting](#-troubleshooting)

## 🏗 Architecture

The system follows a modern, cloud-native architecture designed for scalability and reliability:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub Repo   │    │  GitHub Actions │    │  AWS ECR/ECS    │
│  - P&L.md/csv   │───▶│  - Trigger on   │───▶│  - Docker Image │
│  - Balance.csv  │    │    push to main │    │  - BeeAI Agent  │
│  - .github/     │    │  - Build & Push │    │  - Orchestrator │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  GitHub Issues  │◀───│  Issue Manager  │◀───│  Financial      │
│  - Discrepancy  │    │  - Create/Update│    │  Analyzer Agent │
│    Reports      │    │  - Rich Format  │    │  - LLM Powered  │
│  - Fix Proposals│    │  - Assign Teams │    │  - Rule Engine  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

1. **BeeAI Financial Agent**: Intelligent agent with 10+ years of financial expertise
2. **Document Parsers**: Multi-format support for CSV and Markdown files
3. **Analysis Engine**: Hybrid rule-based + LLM consistency validation
4. **GitHub Integration**: Automated issue creation and repository monitoring
5. **AWS Infrastructure**: Scalable deployment with ECS Fargate

For detailed architecture documentation, see [architecture.md](architecture.md).

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- GitHub personal access token
- LLM provider access (AWS Bedrock, OpenAI, or Ollama)

### 1. Clone and Setup

```bash
git clone https://github.com/your-org/autonomous-financial-auditor.git
cd autonomous-financial-auditor

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
```

### 2. Configure Environment

Edit `.env` file with your settings:

```env
# GitHub Configuration
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO_OWNER=your-organization
GITHUB_REPO_NAME=financial-reports

# LLM Provider (choose one)
LLM_PROVIDER=bedrock  # or openai, ollama
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
```

### 3. Quick Start with Docker

```bash
# Start the complete stack
docker-compose up -d

# Check service health
curl http://localhost:8000/health

# Run analysis manually
curl -X POST http://localhost:8000/analyze
```

### 4. Command Line Usage

```bash
# Install dependencies
pip install .

# Analyze a repository
financial-auditor analyze --repo owner/repo-name --ref main

# Start server mode
financial-auditor server
```

## 🛠 Local Development

### Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install development dependencies
pip install -e .[dev,test]

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/ -v --cov=autonomous_financial_auditor
```

### Development Workflow

1. **Code Quality**: Automatic formatting with `ruff` and `black`
2. **Type Safety**: Full type checking with `mypy`
3. **Testing**: Comprehensive test suite with pytest
4. **Security**: Automated security scanning with bandit

```bash
# Code formatting
ruff format autonomous_financial_auditor tests
ruff check autonomous_financial_auditor tests --fix

# Type checking
mypy autonomous_financial_auditor

# Security scan
bandit -r autonomous_financial_auditor
```

### Local Testing with Sample Data

Create test financial documents:

```bash
mkdir -p test_data

# Create sample P&L
cat > test_data/q1_2024_pl.csv << EOF
Line Item,Amount
Revenue,100000.00
Cost of Goods Sold,40000.00
Gross Profit,60000.00
Operating Expenses,35000.00
Net Income,25000.00
EOF

# Create sample Balance Sheet
cat > test_data/q1_2024_balance_sheet.csv << EOF
Line Item,Amount
Total Assets,200000.00
Total Liabilities,120000.00
Shareholders Equity,80000.00
Retained Earnings,25000.00
EOF

# Test parsing
python -c "
from autonomous_financial_auditor.parsers.factory import ParserFactory
factory = ParserFactory()
doc = factory.parse_file('test_data/q1_2024_pl.csv', open('test_data/q1_2024_pl.csv').read())
print(f'Parsed {len(doc.line_items)} line items from P&L')
"
```

## 🚀 Production Deployment

### AWS ECS Deployment

The system is designed for production deployment on AWS ECS Fargate with the following infrastructure:

#### Infrastructure Requirements

```yaml
# AWS Resources Required
- ECS Cluster: financial-auditor-production
- Task Definition: financial-auditor with 1024 CPU, 2048 Memory
- Service: Auto-scaling from 1-5 tasks
- Load Balancer: Application Load Balancer with health checks
- CloudWatch: Log groups and custom metrics
- IAM Roles: Task execution and task roles with appropriate permissions
```

#### Deployment via GitHub Actions

1. **Setup AWS Credentials** in GitHub Secrets:
   ```
   AWS_ACCESS_KEY_ID
   AWS_SECRET_ACCESS_KEY
   AWS_ACCOUNT_ID
   ```

2. **Configure Parameters** in AWS Parameter Store:
   ```bash
   aws ssm put-parameter --name "/financial-auditor/production/github-token" --value "your-token" --type "SecureString"
   aws ssm put-parameter --name "/financial-auditor/production/github-repo-owner" --value "your-org" --type "String"
   aws ssm put-parameter --name "/financial-auditor/production/github-repo-name" --value "your-repo" --type "String"
   ```

3. **Deploy**: Push to `main` branch triggers automatic deployment

#### Manual Deployment

```bash
# Build and push container
docker build -t financial-auditor:latest .
docker tag financial-auditor:latest your-account.dkr.ecr.us-east-1.amazonaws.com/financial-auditor:latest
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/financial-auditor:latest

# Deploy to ECS
aws ecs update-service --cluster financial-auditor-production --service financial-auditor-service --force-new-deployment
```

### Monitoring and Observability

#### CloudWatch Integration

- **Logs**: Structured JSON logs in `/aws/ecs/financial-auditor-production`
- **Metrics**: Custom metrics for analysis success/failure rates
- **Alarms**: Automated alerts for service health and error rates

#### Health Checks

```bash
# Service health
curl https://your-domain.com/health

# Metrics endpoint (if enabled)
curl https://your-domain.com:9090/metrics
```

### Environment-Specific Configuration

#### Production
- High availability across multiple AZs
- Auto-scaling based on CPU and memory
- Enhanced security with VPC and security groups
- Automated backups and disaster recovery

#### Staging
- Single instance for cost optimization
- Relaxed security for development access
- Debug logging enabled

## ⚙️ Configuration

### Environment Variables

The system uses environment variables with the `FA_` prefix for configuration:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `FA_GITHUB_TOKEN` | GitHub personal access token | - | ✅ |
| `FA_GITHUB_REPO_OWNER` | Repository owner | - | ✅ |
| `FA_GITHUB_REPO_NAME` | Repository name | - | ✅ |
| `FA_LLM_PROVIDER` | LLM provider (bedrock/openai/ollama) | bedrock | ✅ |
| `FA_BEDROCK_MODEL_ID` | AWS Bedrock model ID | claude-3-5-sonnet | ❌ |
| `FA_OPENAI_API_KEY` | OpenAI API key | - | ❌ |
| `FA_ANALYSIS_CONFIDENCE_THRESHOLD` | Minimum confidence for reporting | 0.8 | ❌ |
| `FA_MAX_DISCREPANCY_AMOUNT` | Maximum discrepancy to ignore | 1000.0 | ❌ |

### LLM Provider Setup

#### AWS Bedrock
```env
FA_LLM_PROVIDER=bedrock
FA_BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
FA_AWS_REGION=us-east-1
FA_AWS_ACCESS_KEY_ID=your_key
FA_AWS_SECRET_ACCESS_KEY=your_secret
```

#### OpenAI
```env
FA_LLM_PROVIDER=openai
FA_OPENAI_API_KEY=sk-your_key_here
```

#### Ollama (Local)
```env
FA_LLM_PROVIDER=ollama
FA_OLLAMA_BASE_URL=http://localhost:11434
FA_OLLAMA_MODEL=llama3.1
```

## 💡 Usage Examples

### GitHub Webhook Integration

Set up a webhook in your GitHub repository:

1. Go to **Settings > Webhooks > Add webhook**
2. **Payload URL**: `https://your-domain.com/webhook/github`
3. **Content type**: `application/json`
4. **Events**: Choose "Push" events
5. **Secret**: Your webhook secret (optional)

### Manual Analysis API

```bash
# Analyze specific repository
curl -X POST "https://your-domain.com/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "your-org/financial-repo",
    "ref": "main"
  }'

# Response
{
  "status": "completed",
  "code": 0,
  "analysis_id": "abc123...",
  "discrepancies_found": 2
}
```

### Command Line Examples

```bash
# Basic analysis
financial-auditor analyze --repo microsoft/vscode

# Specific branch
financial-auditor analyze --repo your-org/repo --ref feature-branch

# With custom configuration
FA_ANALYSIS_CONFIDENCE_THRESHOLD=0.9 financial-auditor analyze --repo your-org/repo

# Server mode with custom port
financial-auditor server --host 0.0.0.0 --port 8080
```

### Python SDK Usage

```python
import asyncio
from autonomous_financial_auditor.agents import FinancialAnalysisAgent

async def analyze_repository():
    agent = FinancialAnalysisAgent()
    result = await agent.analyze_repository("your-org/repo", "main")
    
    print(f"Analysis ID: {result.analysis_id}")
    print(f"Status: {result.status}")
    print(f"Discrepancies: {result.total_discrepancies}")
    
    if result.has_critical_issues():
        print("🚨 Critical issues found!")
        for discrepancy in result.get_discrepancies_by_severity("critical"):
            print(f"- {discrepancy.title}: {discrepancy.description}")

# Run analysis
asyncio.run(analyze_repository())
```

## 📚 API Reference

### REST API Endpoints

#### `GET /`
- **Description**: Service status
- **Response**: `{"message": "Autonomous Financial Auditor is running"}`

#### `GET /health`
- **Description**: Health check endpoint
- **Response**: `{"status": "healthy", "service": "financial-auditor"}`

#### `POST /webhook/github`
- **Description**: GitHub webhook handler
- **Content-Type**: `application/json`
- **Body**: GitHub webhook payload
- **Response**: `{"status": "processed", "code": 0}`

#### `POST /analyze`
- **Description**: Manual analysis trigger
- **Body**: 
  ```json
  {
    "repo": "owner/repository-name",
    "ref": "main"
  }
  ```
- **Response**: 
  ```json
  {
    "status": "completed",
    "code": 0,
    "analysis_id": "uuid",
    "duration": 45.2
  }
  ```

### Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | No discrepancies found |
| 1 | Error | Analysis failed due to error |
| 2 | Issues Found | Discrepancies detected and reported |

## 🧪 Testing

### Test Categories

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: BeeAI agent and tool integration
3. **End-to-End Tests**: Complete workflow testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test categories
pytest tests/unit/ -v                    # Unit tests only
pytest tests/integration/ -v             # Integration tests
pytest tests/e2e/ -v                     # End-to-end tests

# With coverage
pytest tests/ --cov=autonomous_financial_auditor --cov-report=html

# Parallel execution
pytest tests/ -n auto
```

### Test Configuration

```bash
# Set test environment variables
export FA_GITHUB_TOKEN=test-token
export FA_LLM_PROVIDER=ollama
export FA_OLLAMA_BASE_URL=http://localhost:11434

# Run with test fixtures
pytest tests/ --fixtures
```

### Sample Test Data

The test suite includes comprehensive sample data:

- Valid P&L and Balance Sheet pairs
- Documents with intentional inconsistencies
- Edge cases and error conditions
- Multi-format examples (CSV, Markdown)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Make** your changes with tests
4. **Run** the full test suite: `pytest tests/`
5. **Commit** using conventional commits: `git commit -m "feat: add amazing feature"`
6. **Push** to your branch: `git push origin feature/amazing-feature`
7. **Create** a Pull Request

### Code Quality Standards

- **100% Type Coverage**: All code must have type hints
- **95%+ Test Coverage**: Comprehensive test coverage required
- **Security First**: All dependencies scanned for vulnerabilities
- **Performance**: Sub-2-minute analysis completion time

## 🔧 Troubleshooting

### Common Issues

#### 1. "No financial documents found"
**Cause**: Repository doesn't contain recognizable financial files
**Solution**: Ensure your repository has files matching these patterns:
- P&L: `*p&l*`, `*pl*`, `*profit*loss*`, `*income*statement*`
- Balance Sheet: `*balance*sheet*`, `*bs*`, `*balance*`

#### 2. "LLM provider authentication failed"
**Cause**: Invalid API credentials
**Solution**: 
```bash
# For AWS Bedrock
aws sts get-caller-identity  # Verify AWS credentials

# For OpenAI
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

#### 3. "GitHub API rate limit exceeded"
**Cause**: Too many API requests
**Solution**: 
- Check rate limit: `curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit`
- Use GitHub App instead of personal token for higher limits

#### 4. Docker build failures
**Cause**: Memory/disk space issues
**Solution**:
```bash
# Clean up Docker resources
docker system prune -a --volumes

# Build with more memory
docker build --memory=4g -t financial-auditor .
```

### Debug Mode

Enable detailed logging:

```bash
# Environment variable
export FA_DEBUG=true
export FA_LOG_LEVEL=DEBUG

# Or in .env file
FA_DEBUG=true
FA_LOG_LEVEL=DEBUG
```

### Performance Optimization

#### For Large Repositories
```env
# Increase processing timeouts
FA_GITHUB_API_TIMEOUT=60
FA_LLM_REQUEST_TIMEOUT=120

# Optimize parsing
FA_MAX_FILE_SIZE=5MB
FA_PARALLEL_PROCESSING=true
```

#### Memory Usage
```bash
# Monitor memory usage
docker stats financial-auditor

# Adjust container resources
docker run --memory=4g --cpus=2 financial-auditor
```

### Getting Help

1. **Check Logs**: Review CloudWatch logs or local logs for error details
2. **GitHub Issues**: [Create an issue](https://github.com/your-org/autonomous-financial-auditor/issues) with:
   - Error message
   - Steps to reproduce
   - Environment details
   - Sample data (if safe to share)
3. **Community**: Join our [Discord server](https://discord.gg/financial-auditor) for real-time help

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **BeeAI Framework**: Core agent framework powering the intelligent analysis
- **AWS Bedrock**: Enterprise-grade LLM infrastructure
- **Open Source Community**: Contributors and feedback providers

---

**Built with ❤️ by the Financial AI Team**

*For enterprise licensing, professional services, or custom integrations, contact us at enterprise@financial-auditor.com*