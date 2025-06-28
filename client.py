import asyncio
import aiohttp
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from typing import Optional, List
import pandas as pd
from datetime import datetime

app = typer.Typer()
console = Console()

class StockClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_stock_info(self, symbol: str) -> dict:
        async with self.session.post(
            f"{self.base_url}/stock",
            json={"symbol": symbol}
        ) as response:
            return await response.json()

    async def get_multiple_stocks(self, symbols: List[str]) -> List[dict]:
        tasks = [self.get_stock_info(symbol) for symbol in symbols]
        return await asyncio.gather(*tasks)

def format_currency(value: float) -> str:
    return f"${value:,.2f}" if value else "N/A"

def create_stock_table(data: List[dict]) -> Table:
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Symbol")
    table.add_column("Current Price")
    table.add_column("Volume")
    table.add_column("Market Cap")
    table.add_column("50 Day Avg")

    for stock in data:
        symbol = stock['symbol']
        stock_data = stock['data']
        
        table.add_row(
            symbol,
            format_currency(stock_data.get('current_price')),
            f"{stock_data.get('volume'):,}" if stock_data.get('volume') else "N/A",
            format_currency(stock_data.get('market_cap')),
            format_currency(stock_data.get('fifty_day_average'))
        )
    
    return table

@app.command()
def watch(symbols: List[str] = typer.Argument(..., help="Stock symbols to watch"),
          interval: int = typer.Option(60, help="Refresh interval in seconds"),
          output: str = typer.Option(None, help="Output file for CSV export")):
    """
    Watch Canadian stock prices in real-time with periodic updates
    """
    async def watch_stocks():
        df_list = []
        try:
            while True:
                async with StockClient() as client:
                    with Progress() as progress:
                        task = progress.add_task("[cyan]Fetching stock data...", total=len(symbols))
                        
                        stock_data = await client.get_multiple_stocks(symbols)
                        progress.update(task, advance=len(symbols))

                    console.clear()
                    console.print(create_stock_table(stock_data))
                    
                    if output:
                        # Create DataFrame for export
                        current_data = {
                            'timestamp': datetime.now(),
                            'symbol': [],
                            'price': [],
                            'volume': [],
                            'market_cap': [],
                            'fifty_day_avg': []
                        }
                        
                        for stock in stock_data:
                            current_data['symbol'].append(stock['symbol'])
                            current_data['price'].append(stock['data'].get('current_price'))
                            current_data['volume'].append(stock['data'].get('volume'))
                            current_data['market_cap'].append(stock['data'].get('market_cap'))
                            current_data['fifty_day_avg'].append(stock['data'].get('fifty_day_average'))
                        
                        df = pd.DataFrame(current_data)
                        df_list.append(df)
                        
                        # Export to CSV
                        pd.concat(df_list).to_csv(output, index=False)
                        console.print(f"\nData exported to {output}")

                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping stock watch...[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")

    asyncio.run(watch_stocks())

@app.command()
def analyze(symbol: str = typer.Argument(..., help="Stock symbol to analyze"),
            days: int = typer.Option(30, help="Number of days for analysis")):
    """
    Analyze a single stock's performance
    """
    async def analyze_stock():
        async with StockClient() as client:
            try:
                stock_data = await client.get_stock_info(symbol)
                
                console.print(f"\n[bold]Analysis for {symbol}[/bold]")
                
                # Create detailed analysis table
                table = Table(show_header=True, header_style="bold blue")
                table.add_column("Metric")
                table.add_column("Value")
                
                data = stock_data['data']
                current_price = data.get('current_price', 0)
                fifty_day_avg = data.get('fifty_day_average', 0)
                
                if current_price and fifty_day_avg:
                    price_diff = ((current_price - fifty_day_avg) / fifty_day_avg) * 100
                    trend = "🔺" if price_diff > 0 else "🔻"
                    
                    table.add_row(
                        "Price vs 50-day Average",
                        f"{trend} {abs(price_diff):.2f}%"
                    )
                
                table.add_row(
                    "Current Price",
                    format_currency(current_price)
                )
                
                table.add_row(
                    "50 Day Average",
                    format_currency(fifty_day_avg)
                )
                
                table.add_row(
                    "Market Cap",
                    format_currency(data.get('market_cap'))
                )
                
                console.print(table)
                
            except Exception as e:
                console.print(f"[red]Error analyzing {symbol}: {str(e)}[/red]")

    asyncio.run(analyze_stock())

if __name__ == "__main__":
    app()