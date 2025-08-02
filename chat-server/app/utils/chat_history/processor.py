from langchain_core.messages import AIMessage, BaseMessage, ToolCall
from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.core.constants import (
    DATASETS_USED,
    DATASETS_USED_ARG,
    SQL_QUERIES_GENERATED,
    SQL_QUERIES_GENERATED_ARG,
    VISUALIZATION_RESULT,
    VISUALIZATION_RESULT_ARG,
)
from app.utils.model_registry.model_provider import get_chat_history

from .sliding_window import apply_sliding_window


class ChatHistoryProcessor:
    """
    Centralized processor for chat history operations.

    This class handles all chat history related operations including:
    - Retrieving and filtering chat history
    - Extracting context (SQL queries, datasets, visualizations)
    - Formatting history for prompts
    """

    def __init__(self, config: RunnableConfig):
        """
        Initialize the processor with configuration.

        Args:
            config: Runnable configuration containing chat history
        """
        self.config = config
        self._raw_history = None
        self._filtered_history = None
        self._context_cache = {}

    @property
    def raw_history(self) -> list[BaseMessage]:
        if self._raw_history is None:
            self._raw_history = get_chat_history(self.config) or []
        return self._raw_history

    @property
    def filtered_history(self) -> list[BaseMessage]:
        if self._filtered_history is None:
            self._filtered_history = apply_sliding_window(
                self.raw_history,
                settings.CHAT_HISTORY_MAX_MESSAGES,
                settings.CHAT_HISTORY_MAX_TOKENS,
            )
        return self._filtered_history

    def get_all_tool_calls(self) -> list[ToolCall]:
        if "tool_calls" not in self._context_cache:
            tool_calls = []
            for message in self.filtered_history:
                if isinstance(message, AIMessage) and message.tool_calls:
                    tool_calls.extend(message.tool_calls)
            self._context_cache["tool_calls"] = tool_calls
        return self._context_cache["tool_calls"]

    def get_sql_queries(self) -> list[str]:
        if "sql_queries" not in self._context_cache:
            sql_queries = []
            for tool_call in self.get_all_tool_calls():
                if tool_call.get("name") == SQL_QUERIES_GENERATED:
                    args = tool_call.get("args", {})
                    sql_queries.extend(args.get(SQL_QUERIES_GENERATED_ARG, []))
            self._context_cache["sql_queries"] = sql_queries
        return self._context_cache["sql_queries"]

    def get_datasets_used(self) -> list[str]:
        if "datasets_used" not in self._context_cache:
            datasets_used = []
            for tool_call in self.get_all_tool_calls():
                if tool_call.get("name") == DATASETS_USED:
                    args = tool_call.get("args", {})
                    datasets_used.append(args.get(DATASETS_USED_ARG, []))
            self._context_cache["datasets_used"] = datasets_used
        return self._context_cache["datasets_used"]

    def get_vizpaths(self) -> list[str]:
        if "vizpaths" not in self._context_cache:
            vizpaths = []
            for tool_call in self.get_all_tool_calls():
                if tool_call.get("name") == VISUALIZATION_RESULT:
                    args = tool_call.get("args", {})
                    vizpaths.extend(args.get(VISUALIZATION_RESULT_ARG, []))
                    break
            self._context_cache["vizpaths"] = vizpaths
        return self._context_cache["vizpaths"]

    def format_chat_history(self) -> str:
        """
        Format chat history for inclusion in prompts.

        Returns:
            Formatted chat history string
        """
        if "formatted_history" not in self._context_cache:
            if not self.filtered_history:
                formatted_history = ""
            else:
                formatted_messages = []
                for message in self.filtered_history:
                    if message.type == "human":
                        formatted_messages.append(f"User: {message.content}")
                    else:
                        formatted_messages.append(f"Assistant: {message.content}")

                formatted_history = "\n".join(formatted_messages)

                sql_queries = self.get_sql_queries()
                if sql_queries:
                    formatted_history += f"\n\nRecent SQL Queries: {sql_queries}\n\n"

            self._context_cache["formatted_history"] = formatted_history

        return self._context_cache["formatted_history"]

    def get_context_summary(self) -> dict:
        """
        Get a complete summary of all context extracted from chat history.

        Returns:
            Dictionary containing all extracted context
        """
        return {
            "formatted_history": self.format_chat_history(),
            "sql_queries": self.get_sql_queries(),
            "datasets_used": self.get_datasets_used(),
            "vizpaths": self.get_vizpaths(),
            "message_count": len(self.filtered_history),
            "original_message_count": len(self.raw_history),
        }

    def has_history(self) -> bool:
        return len(self.raw_history) > 0
