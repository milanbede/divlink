import time
from typing import Dict


class TelegramSessionManager:
    """Manages user sessions for Telegram bot with idle timeout handling"""

    def __init__(self, logger, idle_timeout: int = 60):
        self.logger = logger
        self.idle_timeout = idle_timeout  # seconds
        self.sessions: Dict[int, Dict] = {}  # In-memory storage for now

    def get_session(self, user_id: int) -> Dict:
        """Get or create session for user"""
        current_time = time.time()

        if user_id not in self.sessions:
            self.sessions[user_id] = {
                "user_id": user_id,
                "last_activity": current_time,
                "psalm_sent": False,
                "conversation_state": {},
            }
            self.logger.info(f"Created new session for user {user_id}")

        return self.sessions[user_id]

    def update_activity(self, user_id: int):
        """Update last activity timestamp for user"""
        session = self.get_session(user_id)
        session["last_activity"] = time.time()
        # Reset psalm_sent flag on activity
        session["psalm_sent"] = False

    def is_idle(self, user_id: int) -> bool:
        """Check if user has been idle beyond timeout"""
        session = self.get_session(user_id)
        current_time = time.time()
        idle_duration = current_time - session["last_activity"]
        return idle_duration > self.idle_timeout

    def should_send_psalm(self, user_id: int) -> bool:
        """Check if we should send a psalm to idle user"""
        session = self.get_session(user_id)
        return self.is_idle(user_id) and not session["psalm_sent"]

    def mark_psalm_sent(self, user_id: int):
        """Mark that psalm has been sent to user"""
        session = self.get_session(user_id)
        session["psalm_sent"] = True

    def get_idle_duration(self, user_id: int) -> float:
        """Get how long user has been idle in seconds"""
        session = self.get_session(user_id)
        current_time = time.time()
        return current_time - session["last_activity"]

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        expired_users = []
        for user_id, session in self.sessions.items():
            if current_time - session["last_activity"] > max_age_seconds:
                expired_users.append(user_id)

        for user_id in expired_users:
            del self.sessions[user_id]
            self.logger.info(f"Cleaned up expired session for user {user_id}")

    def get_session_count(self) -> int:
        """Get total number of active sessions"""
        return len(self.sessions)
