from uuid import UUID

from loguru import logger
from requests.exceptions import HTTPError
from telegram import Update
from telegram.ext import ContextTypes

from pdf_bot.language import LanguageService

from .analytics_repository import AnalyticsRepository
from .models import EventAction, TaskType


class AnalyticsService:
    def __init__(
        self,
        analytics_repository: AnalyticsRepository,
        language_service: LanguageService,
    ) -> None:
        self.analytics_repository = analytics_repository
        self.language_service = language_service

    def send_event(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        task_type: TaskType,
        action: EventAction,
    ) -> None:
        lang = self.language_service.get_user_language(update, context)
        user_id = update.effective_message.from_user.id  # type: ignore
        event = {
            "client_id": str(UUID(int=user_id)),
            "user_properties": {"bot_language": {"value": lang}},
            "events": [
                {
                    "name": task_type.value,
                    "params": {"action": action.value},
                }
            ],
        }

        try:
            self.analytics_repository.send_event(event)
        except HTTPError:
            logger.exception("Failed to send analytics")
