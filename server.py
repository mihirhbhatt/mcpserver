from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yfinance as yf
import uvicorn
import asyncio
from typing import Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app initialization
app = FastAPI(title="Stock Market API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StockRequest(BaseModel):
    symbol: str

class StockResponse(BaseModel):
    symbol: str
    data: Dict

async def get_stock_data(symbol: str) -> Dict:
    try:
        # Add .TO suffix for Canadian stocks if not present
        if not symbol.endswith('.TO'):
            symbol = f"{symbol}.TO"
        
        stock = yf.Ticker(symbol)
        info = stock.info
        
        return {
            "current_price": info.get("currentPrice"),
            "volume": info.get("volume"),
            "market_cap": info.get("marketCap"),
            "fifty_day_average": info.get("fiftyDayAverage"),
            "name": info.get("longName"),
            "currency": info.get("currency", "CAD")
        }
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching stock data: {str(e)}")

@app.get("/")
async def root():
    return {"status": "online", "message": "Stock Market API is running"}

@app.post("/stock", response_model=StockResponse)
async def get_stock_info(request: StockRequest):
    try:
        data = await get_stock_data(request.symbol)
        return StockResponse(symbol=request.symbol, data=data)
    except Exception as e:
        logger.error(f"Error processing request for {request.symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def start_server():
    """Function to start the server"""
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise

if __name__ == "__main__":
    start_server()