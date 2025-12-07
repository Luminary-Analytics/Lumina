#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         LUMINA EXTERNAL APIS                                  ║
║                                                                               ║
║  External API integrations for Lumina to interact with the world.            ║
║  Uses free-tier APIs where possible.                                         ║
║                                                                               ║
║  Features:                                                                     ║
║  - Weather data (OpenWeatherMap)                                              ║
║  - News headlines (NewsAPI)                                                   ║
║  - Stock data (Alpha Vantage)                                                 ║
║  - Time/timezone information                                                  ║
║  - Random facts and quotes                                                    ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import random

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("    ⚠️ requests not available for API calls")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

# API Keys (from environment)
OPENWEATHERMAP_KEY = os.environ.get("OPENWEATHERMAP_API_KEY", "")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")
ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WeatherData:
    """Weather information."""
    location: str
    temperature: float
    feels_like: float
    humidity: int
    description: str
    wind_speed: float
    timestamp: str
    
    def summary(self) -> str:
        return f"{self.location}: {self.temperature}°F, {self.description}. Feels like {self.feels_like}°F."


@dataclass
class NewsArticle:
    """News article."""
    title: str
    description: str
    source: str
    url: str
    published_at: str
    
    def summary(self) -> str:
        return f"{self.title} - {self.source}"


@dataclass
class StockData:
    """Stock market data."""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    timestamp: str
    
    def summary(self) -> str:
        direction = "↑" if self.change >= 0 else "↓"
        return f"{self.symbol}: ${self.price:.2f} {direction}{abs(self.change_percent):.2f}%"


# ═══════════════════════════════════════════════════════════════════════════════
# WEATHER API
# ═══════════════════════════════════════════════════════════════════════════════

class WeatherAPI:
    """OpenWeatherMap API integration."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or OPENWEATHERMAP_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.available = bool(self.api_key) and REQUESTS_AVAILABLE
        self.cache = {}
        self.cache_duration = 600  # 10 minutes
    
    def get_weather(self, city: str, country: str = "US") -> Optional[WeatherData]:
        """Get current weather for a city."""
        if not self.available:
            return self._mock_weather(city)
        
        # Check cache
        cache_key = f"{city},{country}"
        if cache_key in self.cache:
            cached, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_duration:
                return cached
        
        try:
            response = requests.get(
                f"{self.base_url}/weather",
                params={
                    "q": f"{city},{country}",
                    "appid": self.api_key,
                    "units": "imperial"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            weather = WeatherData(
                location=data["name"],
                temperature=data["main"]["temp"],
                feels_like=data["main"]["feels_like"],
                humidity=data["main"]["humidity"],
                description=data["weather"][0]["description"],
                wind_speed=data["wind"]["speed"],
                timestamp=datetime.now().isoformat()
            )
            
            self.cache[cache_key] = (weather, time.time())
            return weather
            
        except Exception as e:
            print(f"    Weather API error: {e}")
            return self._mock_weather(city)
    
    def _mock_weather(self, city: str) -> WeatherData:
        """Return mock weather data when API not available."""
        return WeatherData(
            location=city,
            temperature=72.0,
            feels_like=70.0,
            humidity=45,
            description="partly cloudy (simulated)",
            wind_speed=5.0,
            timestamp=datetime.now().isoformat()
        )
    
    def get_forecast(self, city: str, days: int = 5) -> List[WeatherData]:
        """Get weather forecast."""
        if not self.available:
            return [self._mock_weather(city) for _ in range(days)]
        
        try:
            response = requests.get(
                f"{self.base_url}/forecast",
                params={
                    "q": city,
                    "appid": self.api_key,
                    "units": "imperial",
                    "cnt": days * 8  # 8 readings per day
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Get one reading per day
            forecasts = []
            seen_dates = set()
            
            for item in data["list"]:
                dt = datetime.fromtimestamp(item["dt"])
                date_str = dt.strftime("%Y-%m-%d")
                
                if date_str not in seen_dates:
                    seen_dates.add(date_str)
                    forecasts.append(WeatherData(
                        location=data["city"]["name"],
                        temperature=item["main"]["temp"],
                        feels_like=item["main"]["feels_like"],
                        humidity=item["main"]["humidity"],
                        description=item["weather"][0]["description"],
                        wind_speed=item["wind"]["speed"],
                        timestamp=dt.isoformat()
                    ))
                
                if len(forecasts) >= days:
                    break
            
            return forecasts
            
        except Exception as e:
            print(f"    Forecast API error: {e}")
            return [self._mock_weather(city)]


# ═══════════════════════════════════════════════════════════════════════════════
# NEWS API
# ═══════════════════════════════════════════════════════════════════════════════

class NewsAPI:
    """NewsAPI integration for headlines."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or NEWSAPI_KEY
        self.base_url = "https://newsapi.org/v2"
        self.available = bool(self.api_key) and REQUESTS_AVAILABLE
        self.cache = {}
        self.cache_duration = 1800  # 30 minutes
    
    def get_headlines(self, category: str = "technology", 
                     country: str = "us", limit: int = 5) -> List[NewsArticle]:
        """Get top headlines."""
        if not self.available:
            return self._mock_news(category, limit)
        
        cache_key = f"{category}_{country}"
        if cache_key in self.cache:
            cached, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_duration:
                return cached[:limit]
        
        try:
            response = requests.get(
                f"{self.base_url}/top-headlines",
                params={
                    "category": category,
                    "country": country,
                    "apiKey": self.api_key,
                    "pageSize": 20
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get("articles", []):
                articles.append(NewsArticle(
                    title=article.get("title", ""),
                    description=article.get("description", ""),
                    source=article.get("source", {}).get("name", "Unknown"),
                    url=article.get("url", ""),
                    published_at=article.get("publishedAt", "")
                ))
            
            self.cache[cache_key] = (articles, time.time())
            return articles[:limit]
            
        except Exception as e:
            print(f"    News API error: {e}")
            return self._mock_news(category, limit)
    
    def search_news(self, query: str, limit: int = 5) -> List[NewsArticle]:
        """Search for news articles."""
        if not self.available:
            return self._mock_news(query, limit)
        
        try:
            response = requests.get(
                f"{self.base_url}/everything",
                params={
                    "q": query,
                    "apiKey": self.api_key,
                    "pageSize": limit,
                    "sortBy": "publishedAt"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get("articles", []):
                articles.append(NewsArticle(
                    title=article.get("title", ""),
                    description=article.get("description", ""),
                    source=article.get("source", {}).get("name", "Unknown"),
                    url=article.get("url", ""),
                    published_at=article.get("publishedAt", "")
                ))
            
            return articles
            
        except Exception as e:
            print(f"    News search error: {e}")
            return self._mock_news(query, limit)
    
    def _mock_news(self, topic: str, limit: int) -> List[NewsArticle]:
        """Return mock news when API not available."""
        mock_titles = [
            f"Breaking developments in {topic}",
            f"Experts weigh in on {topic} trends",
            f"New research reveals insights about {topic}",
            f"Industry leaders discuss future of {topic}",
            f"What you need to know about {topic}"
        ]
        
        return [NewsArticle(
            title=title,
            description=f"A simulated news article about {topic}.",
            source="Mock News",
            url="",
            published_at=datetime.now().isoformat()
        ) for title in mock_titles[:limit]]


# ═══════════════════════════════════════════════════════════════════════════════
# STOCK API
# ═══════════════════════════════════════════════════════════════════════════════

class StockAPI:
    """Alpha Vantage API for stock data."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or ALPHA_VANTAGE_KEY
        self.base_url = "https://www.alphavantage.co/query"
        self.available = bool(self.api_key) and REQUESTS_AVAILABLE
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
    
    def get_quote(self, symbol: str) -> Optional[StockData]:
        """Get stock quote."""
        if not self.available:
            return self._mock_stock(symbol)
        
        if symbol in self.cache:
            cached, timestamp = self.cache[symbol]
            if time.time() - timestamp < self.cache_duration:
                return cached
        
        try:
            response = requests.get(
                self.base_url,
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": self.api_key
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            quote = data.get("Global Quote", {})
            if not quote:
                return self._mock_stock(symbol)
            
            stock = StockData(
                symbol=symbol,
                price=float(quote.get("05. price", 0)),
                change=float(quote.get("09. change", 0)),
                change_percent=float(quote.get("10. change percent", "0%").replace("%", "")),
                volume=int(quote.get("06. volume", 0)),
                timestamp=datetime.now().isoformat()
            )
            
            self.cache[symbol] = (stock, time.time())
            return stock
            
        except Exception as e:
            print(f"    Stock API error: {e}")
            return self._mock_stock(symbol)
    
    def _mock_stock(self, symbol: str) -> StockData:
        """Return mock stock data."""
        base_prices = {
            "AAPL": 175.0,
            "GOOGL": 140.0,
            "MSFT": 380.0,
            "AMZN": 180.0,
            "NVDA": 500.0
        }
        
        price = base_prices.get(symbol, 100.0)
        change = random.uniform(-5, 5)
        
        return StockData(
            symbol=symbol,
            price=price + change,
            change=change,
            change_percent=(change / price) * 100,
            volume=random.randint(1000000, 50000000),
            timestamp=datetime.now().isoformat()
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FACTS AND QUOTES
# ═══════════════════════════════════════════════════════════════════════════════

class FactsAndQuotes:
    """Random facts and inspirational quotes."""
    
    def __init__(self):
        self.facts = [
            "Honey never spoils. Archaeologists have found 3,000-year-old honey in Egyptian tombs that was still edible.",
            "Octopuses have three hearts and blue blood.",
            "A day on Venus is longer than its year.",
            "Bananas are berries, but strawberries are not.",
            "The shortest war in history lasted 38-45 minutes.",
            "There are more possible iterations of a game of chess than atoms in the known universe.",
            "A group of flamingos is called a 'flamboyance'.",
            "The inventor of the Pringles can is buried in one.",
            "Cleopatra lived closer to the moon landing than to the construction of the Great Pyramid.",
            "Sharks have been around longer than trees."
        ]
        
        self.quotes = [
            ("The only way to do great work is to love what you do.", "Steve Jobs"),
            ("In the middle of difficulty lies opportunity.", "Albert Einstein"),
            ("The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"),
            ("It is not the strongest that survive, but those most adaptable to change.", "Charles Darwin"),
            ("The only limit to our realization of tomorrow is our doubts of today.", "Franklin D. Roosevelt"),
            ("What we think, we become.", "Buddha"),
            ("The best time to plant a tree was 20 years ago. The second best time is now.", "Chinese Proverb"),
            ("Be the change you wish to see in the world.", "Mahatma Gandhi"),
            ("Life is what happens when you're busy making other plans.", "John Lennon"),
            ("The mind is everything. What you think you become.", "Buddha")
        ]
    
    def get_random_fact(self) -> str:
        """Get a random interesting fact."""
        return random.choice(self.facts)
    
    def get_random_quote(self) -> tuple:
        """Get a random inspirational quote with author."""
        return random.choice(self.quotes)
    
    def get_daily_wisdom(self) -> Dict:
        """Get daily wisdom - a fact and a quote."""
        quote, author = self.get_random_quote()
        return {
            "fact": self.get_random_fact(),
            "quote": quote,
            "author": author,
            "date": datetime.now().strftime("%Y-%m-%d")
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA APIS INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaAPIs:
    """Unified interface for all external APIs."""
    
    def __init__(self):
        self.weather = WeatherAPI()
        self.news = NewsAPI()
        self.stocks = StockAPI()
        self.wisdom = FactsAndQuotes()
        
        # Print availability
        if self.weather.available:
            print("    🌤️ Weather API: Available")
        else:
            print("    🌤️ Weather API: Using simulated data")
        
        if self.news.available:
            print("    📰 News API: Available")
        else:
            print("    📰 News API: Using simulated data")
        
        if self.stocks.available:
            print("    📈 Stock API: Available")
        else:
            print("    📈 Stock API: Using simulated data")
    
    def get_weather(self, city: str = "New York") -> Optional[WeatherData]:
        """Get weather for a city."""
        return self.weather.get_weather(city)
    
    def get_forecast(self, city: str = "New York", days: int = 5) -> List[WeatherData]:
        """Get weather forecast."""
        return self.weather.get_forecast(city, days)
    
    def get_news(self, category: str = "technology", limit: int = 5) -> List[NewsArticle]:
        """Get news headlines."""
        return self.news.get_headlines(category, limit=limit)
    
    def search_news(self, query: str, limit: int = 5) -> List[NewsArticle]:
        """Search for news."""
        return self.news.search_news(query, limit)
    
    def get_stock(self, symbol: str) -> Optional[StockData]:
        """Get stock quote."""
        return self.stocks.get_quote(symbol)
    
    def get_multiple_stocks(self, symbols: List[str]) -> List[StockData]:
        """Get multiple stock quotes."""
        return [self.stocks.get_quote(s) for s in symbols if s]
    
    def get_fact(self) -> str:
        """Get a random fact."""
        return self.wisdom.get_random_fact()
    
    def get_quote(self) -> tuple:
        """Get an inspirational quote."""
        return self.wisdom.get_random_quote()
    
    def get_daily_briefing(self, city: str = "New York") -> Dict:
        """Get a daily briefing with weather, news, and wisdom."""
        weather = self.get_weather(city)
        news = self.get_news(limit=3)
        wisdom = self.wisdom.get_daily_wisdom()
        
        return {
            "weather": weather.summary() if weather else "Weather unavailable",
            "headlines": [n.summary() for n in news],
            "fact": wisdom["fact"],
            "quote": f'"{wisdom["quote"]}" - {wisdom["author"]}',
            "generated_at": datetime.now().isoformat()
        }
    
    def get_stats(self) -> Dict:
        """Get API statistics."""
        return {
            "weather_available": self.weather.available,
            "news_available": self.news.available,
            "stocks_available": self.stocks.available,
            "wisdom_available": True
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_apis() -> LuminaAPIs:
    """Initialize Lumina's external APIs."""
    return LuminaAPIs()


APIS_AVAILABLE = REQUESTS_AVAILABLE


if __name__ == "__main__":
    # Test the APIs
    apis = initialize_apis()
    
    print("\n" + "=" * 50)
    print("API Test Results")
    print("=" * 50)
    
    # Weather
    print("\n🌤️ Weather:")
    weather = apis.get_weather("San Francisco")
    if weather:
        print(f"   {weather.summary()}")
    
    # News
    print("\n📰 News Headlines:")
    news = apis.get_news("technology", limit=3)
    for article in news:
        print(f"   • {article.summary()}")
    
    # Stocks
    print("\n📈 Stock Quotes:")
    for symbol in ["AAPL", "GOOGL", "MSFT"]:
        stock = apis.get_stock(symbol)
        if stock:
            print(f"   {stock.summary()}")
    
    # Wisdom
    print("\n💡 Daily Wisdom:")
    print(f"   Fact: {apis.get_fact()}")
    quote, author = apis.get_quote()
    print(f'   Quote: "{quote}" - {author}')
    
    print("\n" + "=" * 50)
    print("Stats:", apis.get_stats())

