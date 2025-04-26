"""
Service for analyzing financial data and generating insights
"""
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from typing import Dict, List, Any, Optional, Tuple
import os
import tempfile

from services.llm_service import LLMService
from services.sheets_service import SheetsService

class AnalysisService:
    """Service for analyzing financial data"""
    
    def __init__(self):
        """Initialize the analysis service"""
        self.llm_service = LLMService()
        self.sheets_service = SheetsService()
    
    async def analyze_spending_categories(self, user_id: Optional[int] = None, 
                                      period_days: int = 30) -> Dict[str, Any]:
        """
        Analyze spending by category
        
        Args:
            user_id: Optional user ID to filter data
            period_days: Number of days to analyze
            
        Returns:
            Dictionary with analysis results
        """
        # Get receipt data from sheets
        receipt_data = await self._get_recent_receipts(period_days)
        
        # Create a DataFrame from the receipts
        df = self._create_dataframe_from_receipts(receipt_data)
        
        # Group by category and sum amounts
        category_spending = df.groupby('Category')['Total'].sum().reset_index()
        category_spending = category_spending.sort_values('Total', ascending=False)
        
        # Convert to dictionary for easier handling
        categories = {}
        for _, row in category_spending.iterrows():
            categories[row['Category']] = f"${row['Total']:.2f}"
        
        # Create a chart
        chart_path = self._create_category_pie_chart(category_spending, period_days)
        
        # Get LLM insights
        insights = await self._get_category_insights(category_spending, period_days)
        
        # Prepare result
        result = {
            "analysis_type": "spending_categories",
            "period_days": period_days,
            "total_spending": f"${df['Total'].sum():.2f}",
            "categories": categories,
            "chart_path": chart_path,
            "insights": insights,
            "analysis": insights.get("summary", "")
        }
        
        return result
    
    async def analyze_spending_trends(self, user_id: Optional[int] = None, 
                                  period_days: int = 90) -> Dict[str, Any]:
        """
        Analyze spending trends over time
        
        Args:
            user_id: Optional user ID to filter data
            period_days: Number of days to analyze
            
        Returns:
            Dictionary with analysis results
        """
        # Get receipt data from sheets
        receipt_data = await self._get_recent_receipts(period_days)
        
        # Create a DataFrame from the receipts
        df = self._create_dataframe_from_receipts(receipt_data)
        
        # Convert Date column to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Group by date and sum amounts
        daily_spending = df.groupby(df['Date'].dt.date)['Total'].sum().reset_index()
        
        # Create a time series analysis
        # Resample to fill in missing dates with zeros
        date_range = pd.date_range(
            start=daily_spending['Date'].min(),
            end=daily_spending['Date'].max()
        )
        daily_spending = daily_spending.set_index('Date')
        daily_spending = daily_spending.reindex(date_range, fill_value=0).reset_index()
        daily_spending.rename(columns={'index': 'Date'}, inplace=True)
        
        # Calculate moving averages
        daily_spending['7_day_ma'] = daily_spending['Total'].rolling(window=7, min_periods=1).mean()
        
        # Create a chart
        chart_path = self._create_trend_line_chart(daily_spending, period_days)
        
        # Get LLM insights
        insights = await self._get_trend_insights(daily_spending, period_days)
        
        # Prepare result
        result = {
            "analysis_type": "spending_trends",
            "period_days": period_days,
            "total_spending": f"${df['Total'].sum():.2f}",
            "average_daily": f"${df['Total'].sum() / len(daily_spending):.2f}",
            "chart_path": chart_path,
            "insights": insights,
            "analysis": insights.get("summary", "")
        }
        
        return result
    
    async def analyze_merchants(self, user_id: Optional[int] = None, 
                            period_days: int = 30) -> Dict[str, Any]:
        """
        Analyze spending by merchant
        
        Args:
            user_id: Optional user ID to filter data
            period_days: Number of days to analyze
            
        Returns:
            Dictionary with analysis results
        """
        # Get receipt data from sheets
        receipt_data = await self._get_recent_receipts(period_days)
        
        # Create a DataFrame from the receipts
        df = self._create_dataframe_from_receipts(receipt_data)
        
        # Group by merchant and sum amounts
        merchant_spending = df.groupby('Merchant')['Total'].sum().reset_index()
        merchant_spending = merchant_spending.sort_values('Total', ascending=False)
        
        # Count transactions per merchant
        merchant_counts = df.groupby('Merchant').size().reset_index(name='Transactions')
        
        # Merge spending and transaction counts
        merchant_analysis = pd.merge(merchant_spending, merchant_counts, on='Merchant')
        
        # Calculate average transaction amount
        merchant_analysis['Average'] = merchant_analysis['Total'] / merchant_analysis['Transactions']
        
        # Convert to dictionary for easier handling
        merchants = {}
        for _, row in merchant_analysis.head(10).iterrows():
            merchants[row['Merchant']] = {
                "total": f"${row['Total']:.2f}",
                "transactions": int(row['Transactions']),
                "average": f"${row['Average']:.2f}"
            }
        
        # Create a chart
        chart_path = self._create_merchant_bar_chart(merchant_analysis, period_days)
        
        # Get LLM insights
        insights = await self._get_merchant_insights(merchant_analysis, period_days)
        
        # Prepare result
        result = {
            "analysis_type": "merchants",
            "period_days": period_days,
            "total_merchants": len(merchant_analysis),
            "top_merchants": merchants,
            "chart_path": chart_path,
            "insights": insights,
            "analysis": insights.get("summary", "")
        }
        
        return result
    
    async def analyze_budget_status(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze budget status
        
        Args:
            user_id: Optional user ID to filter data
            
        Returns:
            Dictionary with analysis results
        """
        # In a real implementation, we would get the user's budget information
        # For now, we'll use some mock data
        
        # Mock budget data
        budgets = {
            "Groceries": 500.00,
            "Dining": 300.00,
            "Entertainment": 200.00,
            "Transportation": 250.00,
            "Other": 400.00
        }
        
        # Get current month's spending
        today = datetime.datetime.now()
        first_day = today.replace(day=1)
        days_in_month = (today - first_day).days + 1
        
        # Get receipt data for current month
        receipt_data = await self._get_recent_receipts(days_in_month)
        
        # Create a DataFrame from the receipts
        df = self._create_dataframe_from_receipts(receipt_data)
        
        # Group by category and sum amounts
        category_spending = df.groupby('Category')['Total'].sum().reset_index()
        
        # Calculate budget status
        budget_status = []
        for category, budget in budgets.items():
            spent = category_spending.loc[category_spending['Category'] == category, 'Total'].sum() if category in category_spending['Category'].values else 0
            remaining = budget - spent
            percent_used = (spent / budget) * 100 if budget > 0 else 0
            status = "On Track" if percent_used <= 80 else "Warning" if percent_used <= 100 else "Over Budget"
            
            budget_status.append({
                "category": category,
                "budget": budget,
                "spent": spent,
                "remaining": remaining,
                "percent_used": percent_used,
                "status": status
            })
        
        # Convert to DataFrame for easier handling
        budget_df = pd.DataFrame(budget_status)
        
        # Create a chart
        chart_path = self._create_budget_chart(budget_df)
        
        # Get LLM insights
        insights = await self._get_budget_insights(budget_df)
        
        # Prepare formatted result
        formatted_status = {}
        for status in budget_status:
            category = status["category"]
            formatted_status[category] = {
                "budget": f"${status['budget']:.2f}",
                "spent": f"${status['spent']:.2f}",
                "remaining": f"${status['remaining']:.2f}",
                "percent_used": f"{status['percent_used']:.1f}%",
                "status": status["status"]
            }
        
        # Prepare result
        result = {
            "analysis_type": "budget_status",
            "month": today.strftime("%B %Y"),
            "days_elapsed": days_in_month,
            "days_remaining": today.replace(day=28).day - today.day,
            "total_budget": f"${sum(budgets.values()):.2f}",
            "total_spent": f"${budget_df['spent'].sum():.2f}",
            "budget_status": formatted_status,
            "chart_path": chart_path,
            "insights": insights,
            "analysis": insights.get("summary", "")
        }
        
        return result
    
    async def _get_recent_receipts(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get recent receipt data from sheets
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of receipt dictionaries
        """
        # In a real implementation, this would fetch data from Google Sheets
        # For now, we'll use mock data
        
        # Calculate the start date
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        
        # This is a stub - in actual implementation, it would call the sheets service
        # receipts = await self.sheets_service.get_receipts_since(start_date)
        
        # Mock receipt data
        receipts = []
        
        # Create some random receipts over the past days
        current_date = datetime.datetime.now()
        
        # Categories and merchants for mock data
        categories = ["Groceries", "Dining", "Entertainment", "Transportation", "Other"]
        merchants = [
            "Whole Foods", "Trader Joe's", "Safeway", "Starbucks", "Chipotle", 
            "Amazon", "Netflix", "Uber", "Shell", "Target"
        ]
        
        # Generate mock receipts
        for i in range(days):
            # Random date within the specified period
            receipt_date = (current_date - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            
            # Generate 1-3 receipts per day
            for j in range(np.random.randint(1, 4)):
                category = np.random.choice(categories)
                merchant = np.random.choice(merchants)
                
                # Amount depends on category
                if category == "Groceries":
                    amount = np.random.uniform(20, 150)
                elif category == "Dining":
                    amount = np.random.uniform(10, 80)
                elif category == "Entertainment":
                    amount = np.random.uniform(15, 100)
                elif category == "Transportation":
                    amount = np.random.uniform(5, 60)
                else:
                    amount = np.random.uniform(10, 200)
                
                # Create receipt
                receipt = {
                    "Date": receipt_date,
                    "Merchant": merchant,
                    "Category": category,
                    "Total": amount,
                    "Tax": amount * 0.08,  # Mock tax amount
                    "Payment Method": np.random.choice(["Credit Card", "Cash", "Debit Card"]),
                    "Items": [],  # Mock item data would go here
                    "Upload Date": receipt_date,
                    "Notes": ""
                }
                
                receipts.append(receipt)
        
        return receipts
    
    def _create_dataframe_from_receipts(self, receipts: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert receipt dictionaries to a DataFrame
        
        Args:
            receipts: List of receipt dictionaries
            
        Returns:
            Pandas DataFrame
        """
        # Create DataFrame
        df = pd.DataFrame(receipts)
        
        # Handle potential type conversion issues
        if 'Date' in df.columns:
            try:
                df['Date'] = pd.to_datetime(df['Date'])
            except:
                # If conversion fails, keep as is
                pass
                
        if 'Total' in df.columns:
            # Ensure Total is numeric
            try:
                df['Total'] = pd.to_numeric(df['Total'])
            except:
                # Try to clean and convert
                df['Total'] = df['Total'].replace('[\$,]', '', regex=True).astype(float)
        
        return df
    
    def _create_category_pie_chart(self, category_data: pd.DataFrame, period_days: int) -> str:
        """
        Create a pie chart of spending by category
        
        Args:
            category_data: DataFrame with category spending data
            period_days: Number of days in the analysis period
            
        Returns:
            Path to the saved chart image
        """
        # Create a figure
        plt.figure(figsize=(10, 8))
        
        # Create pie chart
        plt.pie(
            category_data['Total'],
            labels=category_data['Category'],
            autopct='%1.1f%%',
            startangle=90,
            shadow=True
        )
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        plt.axis('equal')
        
        # Add title
        plt.title(f'Spending by Category (Last {period_days} Days)')
        
        # Save chart to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        plt.savefig(temp_file.name, dpi=100, bbox_inches='tight')
        plt.close()
        
        return temp_file.name
    
    def _create_trend_line_chart(self, daily_data: pd.DataFrame, period_days: int) -> str:
        """
        Create a line chart of spending trends
        
        Args:
            daily_data: DataFrame with daily spending data
            period_days: Number of days in the analysis period
            
        Returns:
            Path to the saved chart image
        """
        # Create a figure
        plt.figure(figsize=(12, 6))
        
        # Plot daily spending
        plt.plot(daily_data['Date'], daily_data['Total'], label='Daily Spending', marker='o', alpha=0.5)
        
        # Plot 7-day moving average
        plt.plot(daily_data['Date'], daily_data['7_day_ma'], label='7-Day Moving Average', linewidth=2)
        
        # Format x-axis
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))
        plt.gcf().autofmt_xdate()
        
        # Add grid
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Add labels and title
        plt.xlabel('Date')
        plt.ylabel('Amount ($)')
        plt.title(f'Daily Spending Trends (Last {period_days} Days)')
        
        # Add legend
        plt.legend()
        
        # Save chart to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        plt.savefig(temp_file.name, dpi=100, bbox_inches='tight')
        plt.close()
        
        return temp_file.name
    
    def _create_merchant_bar_chart(self, merchant_data: pd.DataFrame, period_days: int) -> str:
        """
        Create a bar chart of top merchants
        
        Args:
            merchant_data: DataFrame with merchant spending data
            period_days: Number of days in the analysis period
            
        Returns:
            Path to the saved chart image
        """
        # Get top 10 merchants
        top_merchants = merchant_data.sort_values('Total', ascending=False).head(10)
        
        # Create a figure
        plt.figure(figsize=(12, 8))
        
        # Create horizontal bar chart
        bars = plt.barh(top_merchants['Merchant'], top_merchants['Total'])
        
        # Add data labels
        for bar in bars:
            width = bar.get_width()
            plt.text(width + 5, bar.get_y() + bar.get_height()/2, f'${width:.2f}', 
                    ha='left', va='center')
        
        # Add labels and title
        plt.xlabel('Total Spent ($)')
        plt.ylabel('Merchant')
        plt.title(f'Top Merchants by Spending (Last {period_days} Days)')
        
        # Save chart to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        plt.savefig(temp_file.name, dpi=100, bbox_inches='tight')
        plt.close()
        
        return temp_file.name
    
    def _create_budget_chart(self, budget_data: pd.DataFrame) -> str:
        """
        Create a chart showing budget status
        
        Args:
            budget_data: DataFrame with budget status data
            
        Returns:
            Path to the saved chart image
        """
        # Create a figure
        plt.figure(figsize=(12, 8))
        
        # Create horizontal bar chart
        categories = budget_data['category']
        spent = budget_data['spent']
        remaining = budget_data['remaining'].clip(lower=0)  # Clip negative values to 0
        
        # Create the bars
        plt.barh(categories, spent, label='Spent')
        plt.barh(categories, remaining, left=spent, alpha=0.5, label='Remaining')
        
        # Add budget markers
        for i, (_, row) in enumerate(budget_data.iterrows()):
            plt.plot([row['budget'], row['budget']], [i - 0.4, i + 0.4], 'k--', linewidth=1)
        
        # Add data labels
        for i, (_, row) in enumerate(budget_data.iterrows()):
            # Display spent amount
            plt.text(row['spent'] / 2, i, f'${row["spent"]:.0f}', 
                    ha='center', va='center', color='white')
            
            # Display percent
            plt.text(row['budget'] + 10, i, f'{row["percent_used"]:.1f}%', 
                    ha='left', va='center')
        
        # Add labels and title
        plt.xlabel('Amount ($)')
        plt.ylabel('Category')
        plt.title(f'Budget Status for {datetime.datetime.now().strftime("%B %Y")}')
        
        # Add legend
        plt.legend(loc='upper right')
        
        # Save chart to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        plt.savefig(temp_file.name, dpi=100, bbox_inches='tight')
        plt.close()
        
        return temp_file.name
    
    async def _get_category_insights(self, category_data: pd.DataFrame, period_days: int) -> Dict[str, Any]:
        """
        Get insights about category spending from LLM
        
        Args:
            category_data: DataFrame with category spending data
            period_days: Number of days in the analysis period
            
        Returns:
            Dictionary with insights
        """
        # Prepare data for LLM
        category_info = []
        for _, row in category_data.iterrows():
            category_info.append(f"{row['Category']}: ${row['Total']:.2f}")
        
        # Create prompt for LLM
        prompt = f"""
        Analyze the following spending by category over a {period_days}-day period:
        
        {'\n'.join(category_info)}
        
        Total spending: ${category_data['Total'].sum():.2f}
        
        Provide insights about the spending patterns, focusing on:
        1. Which categories represent the largest portions of spending
        2. Whether the distribution seems reasonable or if any category seems disproportionately high
        3. Actionable recommendations for budget adjustments if needed
        
        Format the response as JSON with the following structure:
        {{
            "summary": "A paragraph summarizing the key insights",
            "top_categories": ["Category 1", "Category 2", "Category 3"],
            "concerning_categories": ["Category X"],
            "recommendations": ["Recommendation 1", "Recommendation 2"]
        }}
        """
        
        # Simulate LLM response for now
        # In a real implementation, this would call the LLM service
        # response = await self.llm_service.analyze_text(prompt)
        
        # Mock LLM response
        insights = {
            "summary": f"Your largest spending categories over the past {period_days} days are {category_data.iloc[0]['Category']} (${category_data.iloc[0]['Total']:.2f}) and {category_data.iloc[1]['Category']} (${category_data.iloc[1]['Total']:.2f}). These two categories account for {(category_data.iloc[0]['Total'] + category_data.iloc[1]['Total']) / category_data['Total'].sum() * 100:.1f}% of your total spending. Your spending distribution appears reasonable across most categories.",
            "top_categories": category_data.head(3)['Category'].tolist(),
            "concerning_categories": [category_data.iloc[0]['Category']] if category_data.iloc[0]['Total'] > category_data['Total'].sum() * 0.4 else [],
            "recommendations": [
                f"Consider setting a budget for {category_data.iloc[0]['Category']} to keep spending in check",
                "Track your spending more regularly to identify patterns and potential savings",
                "Look for ways to reduce costs in your top spending categories"
            ]
        }
        
        return insights
    
    async def _get_trend_insights(self, daily_data: pd.DataFrame, period_days: int) -> Dict[str, Any]:
        """
        Get insights about spending trends from LLM
        
        Args:
            daily_data: DataFrame with daily spending data
            period_days: Number of days in the analysis period
            
        Returns:
            Dictionary with insights
        """
        # Mock LLM response
        insights = {
            "summary": f"Your spending over the past {period_days} days shows some fluctuation with an average daily spend of ${daily_data['Total'].mean():.2f}. There are noticeable peaks on weekends, suggesting higher discretionary spending during these periods. The 7-day moving average reveals a slight upward trend in your spending over time.",
            "peak_days": ["Weekends", "End of month"],
            "patterns": [
                "Higher spending on weekends",
                "Monthly pattern with increased spending at the beginning of the month"
            ],
            "recommendations": [
                "Plan major purchases ahead of time to smooth out spending spikes",
                "Set daily spending limits for weekends to control discretionary spending",
                "Consider using a budgeting app to track spending in real-time"
            ]
        }
        
        return insights
    
    async def _get_merchant_insights(self, merchant_data: pd.DataFrame, period_days: int) -> Dict[str, Any]:
        """
        Get insights about merchant spending from LLM
        
        Args:
            merchant_data: DataFrame with merchant spending data
            period_days: Number of days in the analysis period
            
        Returns:
            Dictionary with insights
        """
        # Mock LLM response
        top_merchant = merchant_data.iloc[0]['Merchant']
        top_amount = merchant_data.iloc[0]['Total']
        top_transactions = merchant_data.iloc[0]['Transactions']
        
        insights = {
            "summary": f"Your top merchant over the past {period_days} days is {top_merchant}, where you spent ${top_amount:.2f} across {top_transactions} transactions (average of ${top_amount/top_transactions:.2f} per visit). This represents {top_amount/merchant_data['Total'].sum()*100:.1f}% of your total spending. You visited {len(merchant_data)} different merchants during this period.",
            "frequent_merchants": merchant_data.sort_values('Transactions', ascending=False).head(3)['Merchant'].tolist(),
            "highest_average_transaction": merchant_data.sort_values('Average', ascending=False).head(3)['Merchant'].tolist(),
            "recommendations": [
                f"Look for loyalty programs at {top_merchant} to maximize value",
                "Consider consolidating purchases to fewer merchants for better rewards",
                "Review subscriptions and recurring payments for potential savings"
            ]
        }
        
        return insights
    
    async def _get_budget_insights(self, budget_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get insights about budget status from LLM
        
        Args:
            budget_data: DataFrame with budget status data
            
        Returns:
            Dictionary with insights
        """
        # Identify over budget categories
        over_budget = budget_data[budget_data['percent_used'] > 100]
        near_budget = budget_data[(budget_data['percent_used'] <= 100) & (budget_data['percent_used'] > 80)]
        
        # Mock LLM response
        if len(over_budget) > 0:
            main_concern = f"You've exceeded your budget in {len(over_budget)} categories: {', '.join(over_budget['category'].tolist())}"
        elif len(near_budget) > 0:
            main_concern = f"You're approaching your budget limit in {len(near_budget)} categories: {', '.join(near_budget['category'].tolist())}"
        else:
            main_concern = "You're within budget across all categories, which is excellent financial management"
        
        insights = {
            "summary": f"{main_concern}. Overall, you've used {budget_data['spent'].sum() / budget_data['budget'].sum() * 100:.1f}% of your total budget for the month.",
            "over_budget_categories": over_budget['category'].tolist(),
            "near_budget_categories": near_budget['category'].tolist(),
            "under_budget_categories": budget_data[budget_data['percent_used'] < 70]['category'].tolist(),
            "recommendations": [
                "Adjust spending in over-budget categories for the remainder of the month",
                "Consider reallocating budget from under-utilized categories to those where you tend to spend more",
                "Review your budget categories to ensure they align with your actual spending patterns"
            ]
        }
        
        return insights