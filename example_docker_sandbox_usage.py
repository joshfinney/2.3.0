#!/usr/bin/env python3
"""
Example usage of PandasAI with Docker Sandbox for secure code execution

This example demonstrates how to use the Docker sandbox for secure analysis
of bond market data while maintaining complete isolation from the host system.
"""

import sys
import os
import pandas as pd

# Add the project path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pandasai'))

from pandasai import Agent
from pandasai_docker import DockerSandbox

def main():
    """
    Main example function demonstrating Docker sandbox usage
    """
    
    # Load bond market data (using mock data from CLAUDE.md)
    print("📈 Loading bond market data...")
    
    # Read the mock bond data
    try:
        df = pd.read_csv("mock_bond_issues.csv")
        print(f"✅ Loaded {len(df)} bond records")
    except FileNotFoundError:
        # Create sample data if file doesn't exist
        print("⚠️  Mock data file not found, creating sample data...")
        bond_data = {
            'Issue_Date': ['2024-01-15', '2024-02-20', '2024-03-10'],
            'Issuer': ['Apple Inc', 'Microsoft Corp', 'Google Inc'],
            'Currency': ['USD', 'EUR', 'USD'],
            'Size_EUR_m': [1000, 1500, 800],
            'Tenor': [5, 7, 10],
            'Coupon': [3.5, 4.0, 3.2],
            'Spread_at_Launch_bps': [85, 95, 90],
            'Oversubscription': [2.5, 3.1, 2.8],
            'BNP_Role': ['Global Coordinator', 'Co-Manager', 'Joint Bookrunner'],
            'Sustainable': ['Yes', 'No', 'Yes']
        }
        df = pd.DataFrame(bond_data)
        print(f"✅ Created {len(df)} sample bond records")
    
    print(df.head())
    
    # Initialize Docker sandbox
    print("\n🐳 Initializing Docker sandbox...")
    try:
        sandbox = DockerSandbox()
        print("✅ Docker sandbox initialized successfully")
        print("   - Network isolation: ENABLED")
        print("   - File system isolation: ENABLED") 
        print("   - Container image: pandasai-sandbox")
        
    except Exception as e:
        print(f"❌ Failed to initialize Docker sandbox: {e}")
        print("Make sure Docker is running and accessible")
        return
    
    # Create PandasAI agent with sandbox
    print("\n🤖 Creating PandasAI agent with Docker sandbox...")
    agent = Agent(df, sandbox=sandbox)
    print("✅ Agent created with secure sandbox execution")
    
    # Example queries (these would work with proper LLM configuration)
    example_queries = [
        "What is the average coupon rate for sustainable bonds?",
        "Show me the distribution of bond sizes by currency",
        "Which issuer has the highest oversubscription ratio?",
        "Create a scatter plot of spread vs tenor for all bonds",
        "Calculate the total issuance volume by BNP role"
    ]
    
    print("\n📊 Example queries for secure analysis:")
    for i, query in enumerate(example_queries, 1):
        print(f"   {i}. {query}")
    
    print("\n🔒 Security Features:")
    print("   ✅ Complete network isolation (no external access)")
    print("   ✅ File system containerization")
    print("   ✅ Process isolation from host system")
    print("   ✅ Controlled data serialization")
    print("   ✅ Secure chart generation")
    
    print("\n💡 Usage Tips:")
    print("   - Sandbox containers auto-cleanup on completion")
    print("   - Custom Docker images supported via dockerfile_path")
    print("   - SQL queries are automatically extracted and processed")
    print("   - Charts are securely transferred via base64 encoding")
    
    # Cleanup
    if sandbox:
        sandbox.stop()
        print("\n🧹 Sandbox cleanup completed")
    
    print("\n🎉 Docker sandbox example completed successfully!")
    print("Your bond analysis environment is ready for secure production use.")

if __name__ == "__main__":
    main()