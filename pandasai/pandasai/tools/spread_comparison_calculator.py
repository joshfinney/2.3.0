"""
Spread Comparison Calculator Tool

Atomic tool for bond spread statistical analysis following pandas AI framework patterns.
Provides focused spread comparison with standardized output schema and minimal complexity.

Author: PandasAI Tools Team
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from pandasai.tools.base import Tool, ToolParameter


class SpreadComparisonCalculator(Tool):
    """
    Atomic spread comparison calculator for bond market analysis.
    
    Calculates core spread statistics, percentiles, and basic comparisons
    with standardized output format. Designed for composability with other tools.
    
    Philosophy: Small, transparent, fast, composable, testable, maintainable.
    """
    
    @property
    def name(self) -> str:
        return "spread_comparison_calculator"
    
    @property
    def description(self) -> str:
        return (
            "Calculate spread statistics and percentiles for bond market analysis. "
            "Provides median, mean, percentiles, and basic distribution metrics "
            "with optional sector/currency filtering."
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="df",
                type="pd.DataFrame",
                description="Bond dataset with spread data",
                required=True,
                examples=["dfs[0]", "bond_data"]
            ),
            ToolParameter(
                name="spread_column",
                type="str",
                description="Column name containing spread values in basis points",
                required=False,
                default="Spread at Launch (bps)",
                examples=["'Spread at Launch (bps)'", "'Credit Spread'"]
            ),
            ToolParameter(
                name="sector_filter",
                type="str",
                description="Optional sector to filter by",
                required=False,
                default=None,
                examples=["'Technology'", "'Healthcare'", "'Financial Services'"]
            ),
            ToolParameter(
                name="currency_filter",
                type="str",
                description="Optional currency to filter by",
                required=False,
                default=None,
                examples=["'USD'", "'EUR'", "'GBP'"]
            ),
            ToolParameter(
                name="percentiles",
                type="List[float]",
                description="List of percentiles to calculate",
                required=False,
                default=[25, 50, 75, 90],
                examples=["[25, 50, 75]", "[10, 25, 50, 75, 90]"]
            )
        ]
    
    @property
    def use_cases(self) -> List[str]:
        return [
            "Calculate median spread for technology sector bonds",
            "Compare USD vs EUR spread distributions",
            "Get 25th and 75th percentile spread benchmarks",
            "Analyze spread statistics for investment grade bonds",
            "Generate spread summary for peer group analysis"
        ]
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "median_spread": {
                "type": "float",
                "description": "Median spread value in basis points",
                "range": "0.0 to 2000.0 typically for investment grade bonds"
            },
            "mean_spread": {
                "type": "float", 
                "description": "Arithmetic mean spread value in basis points",
                "range": "0.0 to 2000.0 typically for investment grade bonds"
            },
            "percentiles": {
                "type": "Dict[str, float]",
                "description": "Dictionary of percentile values keyed by percentile number",
                "example": "{'p25': 85.5, 'p50': 125.0, 'p75': 180.2, 'p90': 250.0}",
                "keys": "String format 'p{percentile}' where percentile is integer",
                "values": "Float spread values in basis points"
            },
            "std_deviation": {
                "type": "float",
                "description": "Standard deviation of spread values in basis points",
                "range": "0.0 to 500.0 typically, higher indicates more dispersion"
            },
            "min_spread": {
                "type": "float",
                "description": "Minimum spread value in basis points",
                "range": "Can be negative for premium bonds, typically 0.0+ for credit"
            },
            "max_spread": {
                "type": "float",
                "description": "Maximum spread value in basis points",
                "range": "Can exceed 1000.0 for distressed or high-yield bonds"
            },
            "sample_size": {
                "type": "int",
                "description": "Number of bonds included in analysis",
                "range": "1 to unlimited, minimum 3 recommended for statistics"
            },
            "filters_applied": {
                "type": "Dict[str, str]",
                "description": "Dictionary of applied filters",
                "example": "{'sector': 'Technology', 'currency': 'USD'}",
                "keys": "Filter type: 'sector', 'currency'",
                "values": "String values of applied filters, null if not applied"
            },
            "interquartile_range": {
                "type": "float",
                "description": "Difference between 75th and 25th percentiles in basis points",
                "range": "0.0 to 500.0 typically, measures spread dispersion"
            },
            "coefficient_of_variation": {
                "type": "float",
                "description": "Ratio of standard deviation to mean, dimensionless",
                "range": "0.0 to 2.0 typically, higher indicates more relative variability"
            }
        }
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute spread comparison calculation.
        
        Returns:
            Dict with spread statistics following output schema
            
        Raises:
            ValueError: For invalid inputs or missing required columns
            RuntimeError: For calculation errors with context
        """
        # Extract parameters
        df = kwargs.get('df')
        spread_column = kwargs.get('spread_column', 'Spread at Launch (bps)')
        sector_filter = kwargs.get('sector_filter')
        currency_filter = kwargs.get('currency_filter')
        percentiles = kwargs.get('percentiles', [25, 50, 75, 90])
        
        # Validate inputs
        self._validate_inputs(df, spread_column, percentiles)
        
        # Apply filters
        filtered_df = self._apply_filters(df, sector_filter, currency_filter)
        
        # Extract spread values
        spread_values = self._extract_spread_values(filtered_df, spread_column)
        
        # Calculate statistics
        return self._calculate_statistics(spread_values, percentiles, sector_filter, currency_filter)
    
    def _validate_inputs(self, df: pd.DataFrame, spread_column: str, percentiles: List[float]) -> None:
        """Validate input parameters."""
        if df is None:
            raise ValueError("DataFrame cannot be None")
        
        if df.empty:
            raise ValueError("DataFrame cannot be empty")
        
        if spread_column not in df.columns:
            available_columns = list(df.columns)
            raise ValueError(
                f"Spread column '{spread_column}' not found in DataFrame. "
                f"Available columns: {available_columns}"
            )
        
        if not isinstance(percentiles, list) or len(percentiles) == 0:
            raise ValueError("Percentiles must be a non-empty list")
        
        for p in percentiles:
            if not isinstance(p, (int, float)) or not (0 <= p <= 100):
                raise ValueError(f"Percentile {p} must be between 0 and 100")
    
    def _apply_filters(self, df: pd.DataFrame, sector_filter: Optional[str], 
                      currency_filter: Optional[str]) -> pd.DataFrame:
        """Apply sector and currency filters."""
        filtered_df = df.copy()
        
        if sector_filter is not None:
            if 'Sector' not in df.columns:
                raise ValueError("Sector filter specified but 'Sector' column not found")
            filtered_df = filtered_df[filtered_df['Sector'] == sector_filter]
        
        if currency_filter is not None:
            if 'Currency' not in df.columns:
                raise ValueError("Currency filter specified but 'Currency' column not found")
            filtered_df = filtered_df[filtered_df['Currency'] == currency_filter]
        
        if filtered_df.empty:
            raise ValueError("No data remains after applying filters")
        
        return filtered_df
    
    def _extract_spread_values(self, df: pd.DataFrame, spread_column: str) -> np.ndarray:
        """Extract and validate spread values."""
        # Get non-null values
        spread_series = df[spread_column].dropna()
        
        if spread_series.empty:
            raise ValueError(f"No valid (non-null) values found in column '{spread_column}'")
        
        # Convert to numpy array
        spread_values = spread_series.values
        
        # Check for numeric values
        if not np.issubdtype(spread_values.dtype, np.number):
            raise ValueError(f"Column '{spread_column}' contains non-numeric values")
        
        # Remove infinite values
        finite_mask = np.isfinite(spread_values)
        if not np.all(finite_mask):
            infinite_count = np.sum(~finite_mask)
            spread_values = spread_values[finite_mask]
            if len(spread_values) == 0:
                raise ValueError("No finite values found in spread column")
        
        return spread_values
    
    def _calculate_statistics(self, spread_values: np.ndarray, percentiles: List[float],
                            sector_filter: Optional[str], currency_filter: Optional[str]) -> Dict[str, Any]:
        """Calculate spread statistics."""
        if len(spread_values) == 0:
            raise RuntimeError("No spread values available for calculation")
        
        # Basic statistics
        median_spread = float(np.median(spread_values))
        mean_spread = float(np.mean(spread_values))
        std_deviation = float(np.std(spread_values, ddof=1)) if len(spread_values) > 1 else 0.0
        min_spread = float(np.min(spread_values))
        max_spread = float(np.max(spread_values))
        
        # Percentiles
        percentile_dict = {}
        for p in percentiles:
            percentile_dict[f"p{int(p)}"] = float(np.percentile(spread_values, p))
        
        # Derived statistics
        p25 = np.percentile(spread_values, 25)
        p75 = np.percentile(spread_values, 75)
        interquartile_range = float(p75 - p25)
        
        coefficient_of_variation = float(std_deviation / mean_spread) if mean_spread != 0 else 0.0
        
        # Applied filters
        filters_applied = {}
        if sector_filter is not None:
            filters_applied["sector"] = sector_filter
        if currency_filter is not None:
            filters_applied["currency"] = currency_filter
        
        return {
            "median_spread": median_spread,
            "mean_spread": mean_spread,
            "percentiles": percentile_dict,
            "std_deviation": std_deviation,
            "min_spread": min_spread,
            "max_spread": max_spread,
            "sample_size": len(spread_values),
            "filters_applied": filters_applied,
            "interquartile_range": interquartile_range,
            "coefficient_of_variation": coefficient_of_variation
        }