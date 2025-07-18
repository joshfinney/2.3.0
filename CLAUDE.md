# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

This PandasAI implementation is designed for **DCM (Debt Capital Markets) and Syndicate analysts** working with global bond records. The primary use case is querying, manipulating, and visualizing bond issuance data to generate rich market commentary and analysis.

## Core Architecture - SmartDataframe Focus

This project uses **PandasAI's SmartDataframe** exclusively for conversational data analysis. The SmartDataframe allows analysts to ask natural language questions about bond market data and receive intelligent responses, visualizations, and market insights.

### Key Components:
- **SmartDataframe**: Main interface for conversational bond data analysis
- **Agent**: Handles natural language queries and generates market commentary
- **LLM Integration**: Powers the conversational AI (requires PANDASAI_API_KEY)

## Bond Dataset Structure

The primary dataset (`mock_bond_issues.csv`) contains global bond issuance records with these key fields:

**Issuance Details:**
- Issue Date, Syndicate Desk, Syndicate Region, Country, Issuer, ISIN
- Issuer Category, Sector, Currency, Size (EUR m), Tenor, Seniority

**Pricing & Market Data:**
- Coupon, IPTs, Spread at Launch (bps), Guidance, Price Tightening
- Books Guide, Books Launch, Books Final, Oversubscription
- New Issue Premium (bps)

**Syndicate Information:**
- BNP Role, BNP Active, Sustainable (ESG flag)

## Development Commands

### Library Setup
```bash
# Install dependencies
poetry install

# Run unit tests
make tests

# Run integration tests  
make integration

# Code formatting
make format

# Spell check
make spell_check
```

### Docker Platform (Full Stack)
```bash
# Build and run complete platform
docker-compose build
docker-compose up

# Access at http://localhost:3000
```

## SmartDataframe Usage Patterns for Bond Analysis

### Basic Setup
```python
import pandas as pd
from pandasai import SmartDataframe, Agent
import os

# Set API key for BambooLLM
os.environ["PANDASAI_API_KEY"] = "YOUR_API_KEY"

# Load bond data
df = pd.read_csv("mock_bond_issues.csv")
smart_df = SmartDataframe(df)

# Or use Agent for multi-dataframe analysis
agent = Agent(df)
```

### Common DCM/Syndicate Queries
```python
# Market commentary queries
agent.chat("What are the key market trends in USD corporate bonds over the last 6 months?")

# Pricing analysis
agent.chat("Compare new issue premiums across different sectors")

# Syndicate performance
agent.chat("Show me BNP's active participation by region and desk")

# Size and subscription analysis
agent.chat("What's the average oversubscription ratio for sustainable bonds vs conventional bonds?")

# Spread analysis
agent.chat("Plot the relationship between spread at launch and tenor for healthcare sector bonds")
```

### Market Commentary Generation
The system is optimized to generate rich market commentary by:
- Analyzing pricing dynamics (IPTs, spreads, tightening)
- Identifying market trends by sector, region, currency
- Comparing subscription patterns and oversubscription ratios
- Tracking syndicate activity and roles
- Highlighting ESG/sustainable bond performance

## Testing Strategy

### Unit Tests
```bash
# Test core SmartDataframe functionality
poetry run pytest tests/unit_tests/ -k "test_agent"

# Test specific DCM analysis functions
poetry run pytest tests/unit_tests/test_bond_analysis.py
```

### Integration Tests
```bash
# Test complete bond analysis workflows
poetry run pytest tests/integration_tests/ -k "bond"
```

## Key Configuration

### Environment Variables
- `PANDASAI_API_KEY`: Required for BambooLLM (default LLM)
- `OPENAI_API_KEY`: If using OpenAI models
- `HUGGINGFACE_API_KEY`: If using HuggingFace models

### Configuration Options
```python
from pandasai.schemas.df_config import Config

config = Config(
    llm=your_llm_choice,
    save_charts=True,
    save_charts_path="./charts/",
    verbose=True,
    enforce_privacy=True  # For sensitive bond data
)

agent = Agent(df, config=config)
```

## File Structure for Bond Analysis

- `mock_bond_issues.csv`: Main bond dataset
- `examples/`: Contains bond analysis examples
- `pandasai/`: Core PandasAI library
- `client/`: Web interface for interactive analysis
- `server/`: API backend for collaborative analysis

## Important Notes for DCM/Syndicate Analysis

- The system supports multiple currencies (USD, EUR, CNY, HKD)
- Syndicate roles are tracked (Global Coordinator, Co-Manager, etc.)
- ESG/Sustainable flags enable green bond analysis
- Regional desk analysis (New York, London, Hong Kong, Asia-Pacific)
- Pricing dynamics include IPTs, spreads, and tightening analysis
- Book building data supports subscription analysis
- All financial amounts are in EUR millions for consistency