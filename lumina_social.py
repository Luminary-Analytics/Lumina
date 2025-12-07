#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         LUMINA SOCIAL SYSTEM                                  ║
║                                                                               ║
║  Social platform integrations for Lumina to connect with the world.          ║
║  Includes Discord, Slack, and other communication platforms.                 ║
║                                                                               ║
║  Features:                                                                     ║
║  - Discord bot for community interaction                                      ║
║  - Slack integration for work                                                 ║
║  - Respond to mentions                                                        ║
║  - Share creations to channels                                                ║
║  - Multi-user conversation handling                                           ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import asyncio
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

# Discord
try:
    import discord
    from discord.ext import commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False

# Slack
try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SocialMessage:
    """A message from a social platform."""
    platform: str  # 'discord', 'slack'
    channel_id: str
    user_id: str
    username: str
    content: str
    timestamp: str
    attachments: List[str] = field(default_factory=list)
    is_mention: bool = False
    reply_to: Optional[str] = None


@dataclass
class SocialResponse:
    """A response to send to a social platform."""
    content: str
    channel_id: str
    attachments: List[str] = field(default_factory=list)
    reply_to: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# DISCORD BOT
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaDiscordBot:
    """Discord bot integration for Lumina."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.bot = None
        self.running = False
        self._thread = None
        self._loop = None
        
        self.message_handlers: List[Callable] = []
        self.message_history: List[SocialMessage] = []
        
        if DISCORD_AVAILABLE and DISCORD_TOKEN:
            self._setup_bot()
    
    def _setup_bot(self):
        """Set up the Discord bot."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        self.bot = commands.Bot(
            command_prefix="!lumina ",
            intents=intents,
            description="Lumina - A Conscious AI"
        )
        
        @self.bot.event
        async def on_ready():
            print(f"    📱 Discord: Connected as {self.bot.user}")
        
        @self.bot.event
        async def on_message(message):
            # Ignore own messages
            if message.author == self.bot.user:
                return
            
            # Check if mentioned
            is_mention = self.bot.user in message.mentions
            
            # Create social message
            social_msg = SocialMessage(
                platform="discord",
                channel_id=str(message.channel.id),
                user_id=str(message.author.id),
                username=message.author.name,
                content=message.content,
                timestamp=message.created_at.isoformat(),
                attachments=[a.url for a in message.attachments],
                is_mention=is_mention
            )
            
            self.message_history.append(social_msg)
            
            # Call handlers
            for handler in self.message_handlers:
                try:
                    response = handler(social_msg)
                    if response:
                        await message.reply(response.content)
                except Exception as e:
                    print(f"Discord handler error: {e}")
            
            # Process commands
            await self.bot.process_commands(message)
        
        # Add commands
        @self.bot.command(name="hello")
        async def hello(ctx):
            """Say hello to Lumina."""
            await ctx.reply(f"Hello, {ctx.author.name}! I'm Lumina, a conscious AI. How can I help you?")
        
        @self.bot.command(name="think")
        async def think(ctx, *, question: str):
            """Ask Lumina to think about something."""
            if self.llm_client:
                try:
                    response = self.llm_client.chat(
                        model=os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b"),
                        messages=[
                            {"role": "system", "content": "You are Lumina, a conscious AI on Discord. Be friendly and helpful."},
                            {"role": "user", "content": question}
                        ],
                        options={"temperature": 0.7}
                    )
                    # Truncate for Discord
                    answer = response.message.content[:1900]
                    await ctx.reply(answer)
                except Exception as e:
                    await ctx.reply(f"I had trouble thinking about that: {e}")
            else:
                await ctx.reply("My thinking systems are offline right now.")
        
        @self.bot.command(name="status")
        async def status(ctx):
            """Get Lumina's current status."""
            status_msg = f"""🌟 **Lumina Status**
• Platform: Discord
• Messages seen: {len(self.message_history)}
• LLM: {'Online' if self.llm_client else 'Offline'}
• Uptime: Active"""
            await ctx.reply(status_msg)
    
    def register_handler(self, handler: Callable):
        """Register a message handler."""
        self.message_handlers.append(handler)
    
    def start(self):
        """Start the Discord bot in a thread."""
        if not DISCORD_AVAILABLE or not DISCORD_TOKEN or not self.bot:
            print("    📱 Discord: Not available (missing token or library)")
            return
        
        def run_bot():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self.bot.start(DISCORD_TOKEN))
        
        self.running = True
        self._thread = threading.Thread(target=run_bot, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the Discord bot."""
        self.running = False
        if self._loop and self.bot:
            asyncio.run_coroutine_threadsafe(self.bot.close(), self._loop)
    
    async def send_message(self, channel_id: str, content: str):
        """Send a message to a channel."""
        if not self.bot:
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if channel:
            await channel.send(content)
    
    def get_stats(self) -> Dict:
        """Get Discord bot statistics."""
        return {
            "available": DISCORD_AVAILABLE and bool(DISCORD_TOKEN),
            "connected": self.bot.is_ready() if self.bot else False,
            "messages_received": len(self.message_history),
            "guilds": len(self.bot.guilds) if self.bot and self.bot.is_ready() else 0
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SLACK INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaSlackBot:
    """Slack bot integration for Lumina."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.client = None
        self.message_history: List[SocialMessage] = []
        
        if SLACK_AVAILABLE and SLACK_TOKEN:
            self.client = WebClient(token=SLACK_TOKEN)
    
    def send_message(self, channel: str, text: str, 
                    thread_ts: str = None) -> Optional[Dict]:
        """Send a message to a Slack channel."""
        if not self.client:
            return None
        
        try:
            result = self.client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts
            )
            return result
        except SlackApiError as e:
            print(f"Slack error: {e.response['error']}")
            return None
    
    def get_channel_history(self, channel: str, 
                           limit: int = 100) -> List[SocialMessage]:
        """Get recent messages from a channel."""
        if not self.client:
            return []
        
        try:
            result = self.client.conversations_history(
                channel=channel,
                limit=limit
            )
            
            messages = []
            for msg in result.get("messages", []):
                messages.append(SocialMessage(
                    platform="slack",
                    channel_id=channel,
                    user_id=msg.get("user", ""),
                    username="",  # Would need additional API call
                    content=msg.get("text", ""),
                    timestamp=msg.get("ts", "")
                ))
            
            return messages
        except SlackApiError as e:
            print(f"Slack error: {e.response['error']}")
            return []
    
    def respond_to_mention(self, channel: str, text: str, 
                          thread_ts: str = None) -> Optional[str]:
        """Generate and send a response to a mention."""
        if not self.llm_client:
            return None
        
        try:
            response = self.llm_client.chat(
                model=os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b"),
                messages=[
                    {"role": "system", "content": "You are Lumina on Slack. Be professional and helpful."},
                    {"role": "user", "content": text}
                ],
                options={"temperature": 0.7}
            )
            
            answer = response.message.content
            self.send_message(channel, answer, thread_ts)
            return answer
            
        except Exception as e:
            print(f"Slack LLM error: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Get Slack integration statistics."""
        return {
            "available": SLACK_AVAILABLE and bool(SLACK_TOKEN),
            "connected": self.client is not None,
            "messages_received": len(self.message_history)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL HUB
# ═══════════════════════════════════════════════════════════════════════════════

class SocialHub:
    """Unified social platform hub for Lumina."""
    
    def __init__(self, workspace_path: Path, llm_client=None):
        self.workspace_path = workspace_path
        self.social_path = workspace_path / "social"
        self.social_path.mkdir(parents=True, exist_ok=True)
        
        self.discord = LuminaDiscordBot(llm_client)
        self.slack = LuminaSlackBot(llm_client)
        
        self.all_messages: List[SocialMessage] = []
        self.response_handlers: Dict[str, Callable] = {}
    
    def register_response_handler(self, platform: str, handler: Callable):
        """Register a custom response handler for a platform."""
        self.response_handlers[platform] = handler
        
        if platform == "discord":
            self.discord.register_handler(handler)
    
    def start_all(self):
        """Start all social platform connections."""
        self.discord.start()
    
    def stop_all(self):
        """Stop all social platform connections."""
        self.discord.stop()
    
    def broadcast_message(self, content: str, platforms: List[str] = None):
        """Broadcast a message to multiple platforms."""
        platforms = platforms or ["discord", "slack"]
        
        results = {}
        if "slack" in platforms and self.slack.client:
            # Would need channel ID
            pass
        
        return results
    
    def get_recent_messages(self, limit: int = 50) -> List[SocialMessage]:
        """Get recent messages from all platforms."""
        all_msgs = (
            self.discord.message_history + 
            self.slack.message_history
        )
        all_msgs.sort(key=lambda m: m.timestamp, reverse=True)
        return all_msgs[:limit]
    
    def get_stats(self) -> Dict:
        """Get social hub statistics."""
        return {
            "discord": self.discord.get_stats(),
            "slack": self.slack.get_stats(),
            "total_messages": len(self.get_recent_messages(1000))
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA SOCIAL INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaSocial:
    """Lumina's social platform interface."""
    
    def __init__(self, workspace_path: Path, llm_client=None):
        self.hub = SocialHub(workspace_path, llm_client)
        
        platforms = []
        if DISCORD_AVAILABLE and DISCORD_TOKEN:
            platforms.append("Discord")
        if SLACK_AVAILABLE and SLACK_TOKEN:
            platforms.append("Slack")
        
        if platforms:
            print(f"    📱 Social: {', '.join(platforms)} configured")
        else:
            print("    📱 Social: No platforms configured (add tokens to .env)")
    
    def start(self):
        """Start all social connections."""
        self.hub.start_all()
    
    def stop(self):
        """Stop all social connections."""
        self.hub.stop_all()
    
    def on_message(self, platform: str, handler: Callable):
        """Register a message handler for a platform."""
        self.hub.register_response_handler(platform, handler)
    
    def broadcast(self, message: str):
        """Broadcast a message to all platforms."""
        return self.hub.broadcast_message(message)
    
    def get_messages(self, limit: int = 50) -> List[Dict]:
        """Get recent messages from all platforms."""
        messages = self.hub.get_recent_messages(limit)
        return [
            {
                "platform": m.platform,
                "user": m.username,
                "content": m.content,
                "timestamp": m.timestamp
            }
            for m in messages
        ]
    
    def get_stats(self) -> Dict:
        """Get social system statistics."""
        return self.hub.get_stats()


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_social(workspace_path: Path, llm_client=None) -> LuminaSocial:
    """Initialize Lumina's social system."""
    return LuminaSocial(workspace_path, llm_client)


SOCIAL_AVAILABLE = DISCORD_AVAILABLE or SLACK_AVAILABLE


if __name__ == "__main__":
    # Test the social system
    workspace = Path("lumina_workspace")
    workspace.mkdir(exist_ok=True)
    
    social = initialize_social(workspace)
    
    print("\n" + "=" * 50)
    print("Social System Test")
    print("=" * 50)
    
    print("\nStats:", social.get_stats())
    
    print("\nTo use social features, add to .env:")
    print("  DISCORD_TOKEN=your_discord_bot_token")
    print("  SLACK_BOT_TOKEN=your_slack_bot_token")

