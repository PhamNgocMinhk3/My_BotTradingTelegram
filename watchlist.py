"""
Watchlist Manager
Manages user's custom watchlist of trading symbols
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class WatchlistManager:
    def __init__(self, filename='watchlist.json'):
        """Initialize watchlist manager"""
        self.filename = filename
        self.watchlist = []
        self.details = {} # Store metadata: {symbol: {'price': float, 'score': int, 'time': ts}}
        self.load()
        logger.info(f"Watchlist initialized with {len(self.watchlist)} symbols")
    
    def load(self):
        """Load watchlist from file"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    self.watchlist = data.get('symbols', [])
                    self.details = data.get('details', {})
                    # Ensure consistency (remove details for non-existent symbols)
                    self.details = {k: v for k, v in self.details.items() if k in self.watchlist}
                    return self.watchlist
            except Exception as e:
                logger.error(f"Error loading watchlist: {e}")
                self.watchlist = []
                self.details = {}
                return []
        return []
    
    def save(self):
        """Save watchlist to file"""
        try:
            data = {
                'symbols': self.watchlist,
                'details': self.details,
                'updated_at': datetime.now().isoformat()
            }
            with open(self.filename, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Watchlist saved: {len(self.watchlist)} symbols")
            return True
        except Exception as e:
            logger.error(f"Error saving watchlist: {e}")
            return False
    
    def add(self, symbol, price=None, score=None):
        """
        Add symbol to watchlist with optional details
        
        Args:
            symbol: Trading symbol
            price: Entry price (optional)
            score: Quality score (optional)
        
        Returns:
            tuple: (success: bool, message: str)
        """
        # Normalize symbol
        symbol = symbol.upper().strip()
        if not symbol.endswith('USDT'):
            symbol = symbol + 'USDT'
        
        # Check if already exists
        if symbol in self.watchlist:
            # Update details if price provided
            if price is not None:
                self.details[symbol] = {
                    'price': float(price),
                    'score': score if score else 0,
                    'time': datetime.now().timestamp(),
                    'entry_time_str': datetime.now().strftime('%H:%M:%S')
                }
                self.save()
                return True, f"🔄 Updated {symbol} details"
            return False, f"⚠️ {symbol} is already in your watchlist"
        
        # Add to watchlist
        self.watchlist.append(symbol)
        
        # Add details if provided
        if price is not None:
            self.details[symbol] = {
                'price': float(price),
                'score': score if score else 0,
                'time': datetime.now().timestamp(),
                'entry_time_str': datetime.now().strftime('%H:%M:%S')
            }
            
        self.save()
        
        return True, f"✅ Added {symbol} to watchlist"
    
    def remove(self, symbol):
        """
        Remove symbol from watchlist
        
        Args:
            symbol: Trading symbol
        
        Returns:
            tuple: (success: bool, message: str)
        """
        # Normalize symbol
        symbol = symbol.upper().strip()
        if not symbol.endswith('USDT'):
            symbol = symbol + 'USDT'
        
        # Check if exists
        if symbol not in self.watchlist:
            return False, f"⚠️ {symbol} is not in your watchlist"
        
        # Remove from watchlist
        self.watchlist.remove(symbol)
        
        # Remove details
        if symbol in self.details:
            del self.details[symbol]
            
        self.save()
        
        return True, f"✅ Removed {symbol} from watchlist"
    
    def get_details(self, symbol):
        """Get details for a symbol"""
        symbol = symbol.upper().strip()
        if not symbol.endswith('USDT'):
            symbol = symbol + 'USDT'
        return self.details.get(symbol, None)

    def get_all(self):
        """Get all symbols in watchlist"""
        return self.watchlist.copy()
    
    def clear(self):
        """Clear entire watchlist"""
        count = len(self.watchlist)
        self.watchlist = []
        self.details = {}
        self.save()
        return count
    
    def count(self):
        """Get number of symbols in watchlist"""
        return len(self.watchlist)
    
    def contains(self, symbol):
        """Check if symbol is in watchlist"""
        symbol = symbol.upper().strip()
        if not symbol.endswith('USDT'):
            symbol = symbol + 'USDT'
        return symbol in self.watchlist
    
    def get_formatted_list(self):
        """Get formatted string of watchlist with details"""
        if not self.watchlist:
            return "📋 <b>Your Watchlist is Empty</b>\n\nUse /watch SYMBOL to add coins."
        
        msg = f"📋 <b>Your Watchlist ({len(self.watchlist)} symbols)</b>\n\n"
        
        for i, symbol in enumerate(self.watchlist, 1):
            # Remove USDT suffix for display
            display_symbol = symbol.replace('USDT', '')
            details = self.details.get(symbol)
            
            detail_str = ""
            if details:
                entry = details.get('price', 0)
                score = details.get('score', 0)
                time_str = details.get('entry_time_str', '')
                if entry > 0:
                    detail_str = f" (Entry: {entry}, Score: {score}, Time: {time_str})"
            
            msg += f"{i}. <b>{display_symbol}</b>{detail_str}\n"
        
        msg += f"\n💡 Use /unwatch SYMBOL to remove"
        msg += f"\n💡 Use /{display_symbol} to analyze"
        
        return msg
