import re
from typing import Optional
from telegram import Update, Bot
from telegram.constants import ChatAction, ParseMode


class TelegramHandler:
    """Handles Telegram bot message processing and formatting"""

    def __init__(self, bot: Bot, logger, llm_handler, bible_parser, session_manager):
        self.bot = bot
        self.logger = logger
        self.llm_handler = llm_handler
        self.bible_parser = bible_parser
        self.session_manager = session_manager

    async def process_message(self, update: Update) -> None:
        """Process incoming Telegram message"""
        try:
            if not update.message or not update.message.text:
                return

            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            message_text = update.message.text.strip()

            # Update session activity
            self.session_manager.update_activity(user_id)

            # Check if we should send a psalm first (for idle users)
            if self.session_manager.should_send_psalm(user_id):
                await self._send_idle_psalm(chat_id, user_id)
                return

            # Handle commands
            if message_text.startswith("/"):
                await self._handle_command(chat_id, user_id, message_text)
            else:
                # Treat as query
                await self._handle_query(chat_id, user_id, message_text)

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            if update.effective_chat:
                await self._send_error_message(update.effective_chat.id, str(e))

    async def _handle_command(self, chat_id: int, user_id: int, command: str) -> None:
        """Handle bot commands"""
        if command.startswith("/start"):
            await self._send_welcome_message(chat_id)
        elif command.startswith("/psalm"):
            await self._send_random_psalm(chat_id, user_id)
        elif command.startswith("/help"):
            await self._send_help_message(chat_id)
        else:
            # Treat unknown commands as queries (remove the /)
            query = command[1:].strip()
            if query:
                await self._handle_query(chat_id, user_id, query)
            else:
                await self._send_help_message(chat_id)

    async def _handle_query(self, chat_id: int, user_id: int, query: str) -> None:
        """Handle user query through LLM"""
        try:
            # Send typing indicator
            await self.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            # Process query through LLM (simulate session for compatibility)
            session = {"telegram_user_id": user_id}
            result, status_code = self.llm_handler.get_llm_bible_reference(
                session, query
            )

            if status_code != 200:
                # Fallback to random psalm
                self.logger.warning(
                    f"LLM query failed for user {user_id}, falling back to psalm"
                )
                await self._send_random_psalm(chat_id, user_id)
                return

            # Format and send response
            response_text = result.get("response", "No response received.")
            score = result.get("score")

            formatted_text = self._format_response(response_text, score)
            await self._send_typing_response(chat_id, formatted_text)

        except Exception as e:
            self.logger.error(f"Error handling query for user {user_id}: {e}")
            await self._send_error_message(
                chat_id,
                "I encountered an issue processing your request. Please try again.",
            )

    async def _send_random_psalm(self, chat_id: int, user_id: int) -> None:
        """Send a random psalm"""
        try:
            await self.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            passage_text = self.bible_parser.get_random_psalm_passage()
            if passage_text is None:
                fallback_verse = (
                    "For God so loved the world, that he gave his only begotten Son, "
                    "that whosoever believeth in him should not perish, but have everlasting life. – John 3:16"
                )
                passage_text = fallback_verse

            formatted_text = self._format_response(passage_text, None)
            await self._send_typing_response(chat_id, formatted_text)

        except Exception as e:
            self.logger.error(f"Error sending random psalm to user {user_id}: {e}")
            await self._send_error_message(
                chat_id, "Could not retrieve a Psalm at this moment."
            )

    async def _send_idle_psalm(self, chat_id: int, user_id: int) -> None:
        """Send psalm to idle user"""
        self.session_manager.mark_psalm_sent(user_id)
        await self._send_random_psalm(chat_id, user_id)

    async def _send_welcome_message(self, chat_id: int) -> None:
        """Send welcome message"""
        welcome_text = (
            "🕊️ *Welcome to Divine Link*\n\n"
            "I'm here to help you find relevant Bible passages for your spiritual questions.\n\n"
            "*Commands:*\n"
            "• Just type your question or spiritual concern\n"
            "• /psalm - Get a random powerful Psalm\n"
            "• /help - Show this help message\n\n"
            "_Ask me anything about faith, life, or scripture..._"
        )
        await self.bot.send_message(
            chat_id=chat_id, text=welcome_text, parse_mode=ParseMode.MARKDOWN
        )

    async def _send_help_message(self, chat_id: int) -> None:
        """Send help message"""
        help_text = (
            "*How to use Divine Link:*\n\n"
            "🙏 *Ask questions like:*\n"
            '• "I\'m feeling anxious about the future"\n'
            '• "How should I forgive someone who hurt me?"\n'
            '• "I need strength for a difficult time"\n\n'
            "📖 *Commands:*\n"
            "• /psalm - Get a random Psalm\n"
            "• /help - Show this message\n\n"
            "_I'll find relevant Bible passages to guide and comfort you._"
        )
        await self.bot.send_message(
            chat_id=chat_id, text=help_text, parse_mode=ParseMode.MARKDOWN
        )

    async def _send_typing_response(self, chat_id: int, text: str) -> None:
        """Send response with typing simulation"""
        # For now, just send the message
        # Could implement character-by-character typing later
        await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )

    async def _send_error_message(self, chat_id: int, error_text: str) -> None:
        """Send error message to user"""
        try:
            await self.bot.send_message(
                chat_id=chat_id, text=f"❌ {error_text}", parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            self.logger.error(f"Failed to send error message: {e}")

    def _format_response(self, text: str, score: Optional[int]) -> str:
        """Format response text for Telegram"""
        # Escape markdown special characters
        text = self._escape_markdown(text)

        # Convert Bible references to links
        text = self._linkify_verses(text)

        # Handle divine names (LORD, GOD)
        text = self._format_divine_names(text)

        # Add score indicator for perfect matches
        if score == 20:
            text = f"✨ *Perfect Match* ✨\n\n{text}"

        return text

    def _escape_markdown(self, text: str) -> str:
        """Escape markdown special characters"""
        # Escape markdown v2 special characters
        special_chars = [
            "_",
            "*",
            "[",
            "]",
            "(",
            ")",
            "~",
            "`",
            ">",
            "#",
            "+",
            "-",
            "=",
            "|",
            "{",
            "}",
            ".",
            "!",
        ]
        for char in special_chars:
            text = text.replace(char, f"\\{char}")
        return text

    def _linkify_verses(self, text: str) -> str:
        """Convert Bible references to BibleGateway links"""
        # Pattern to match Bible references like "John 3:16" or "1 Corinthians 13:4-7"
        pattern = r"\b((?:[1-3]\s)?[A-Za-z][\w\s\']*?)\s(\d+:\d+(?:[-–]\d+)?)\b"

        def replace_verse(match):
            book = match.group(1)
            verses = match.group(2)
            search_term = f"{book} {verses}".replace(" ", "%20")
            url = f"https://www.biblegateway.com/passage/?search={search_term}&version=NRSVCE"
            return f"[{book} {verses}]({url})"

        return re.sub(pattern, replace_verse, text)

    def _format_divine_names(self, text: str) -> str:
        """Format divine names (LORD, GOD) with emphasis"""
        # Replace common divine name patterns with bold formatting
        text = re.sub(r"\bLORD\b", "*LORD*", text)
        text = re.sub(r"\bGOD\b", "*GOD*", text)
        return text
