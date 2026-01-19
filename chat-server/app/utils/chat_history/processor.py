from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolCall,
)
from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from app.core.config import settings
from app.core.constants import (
    DATASETS_USED,
    DATASETS_USED_ARG,
    SQL_QUERIES_GENERATED,
    SQL_QUERIES_GENERATED_ARG,
    VISUALIZATION_RESULT,
    VISUALIZATION_RESULT_ARG,
)
from app.utils.model_registry.model_selection import get_chat_history

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
        self.sql_queries_mapping = {}

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

    def get_datasets_used(self) -> list[str]:
        if "datasets_used" not in self._context_cache:
            datasets_used = []
            for tool_call in self.get_all_tool_calls():
                if tool_call.get("name") == DATASETS_USED:
                    args = tool_call.get("args", {})
                    datasets_used.extend(args.get(DATASETS_USED_ARG, []))
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

    @traceable(run_type="tool", name="ids_to_sql_queries")
    def ids_to_sql_queries(self, ids: list[int]) -> list[str]:
        """
        Convert IDs to SQL queries, returned sorted by ID descending (most recent first).
        """
        id_query_pairs = [
            (id, self.sql_queries_mapping.get(id, ""))
            for id in ids
            if self.sql_queries_mapping.get(id)
        ]
        id_query_pairs.sort(key=lambda x: x[0], reverse=True)
        return [q for _, q in id_query_pairs]

    def _format_tool_call(self, tool_call: dict, sql_counter: int) -> tuple[list[str], int]:
        """
        Format a single tool call and return formatted lines and updated SQL counter.
        """
        lines = []
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})

        if tool_name == SQL_QUERIES_GENERATED:
            for query in tool_args.get(SQL_QUERIES_GENERATED_ARG, []):
                sql_counter += 1
                self.sql_queries_mapping[sql_counter] = query
                lines.append(f"\n[id:{sql_counter}]\n{query}\n")
        elif tool_name == "tool_messages":
            lines.append(tool_args.get("content", "").strip())
        elif tool_name:
            lines.append(f"{tool_name}: {tool_args.get('content', tool_args)}")

        return lines, sql_counter

    def format_chat_history(self) -> str:
        """
        Format chat history with SQL queries inline (with IDs for selection).
        """
        if "formatted_history" in self._context_cache:
            return self._context_cache["formatted_history"]

        if not self.filtered_history:
            self._context_cache["formatted_history"] = ""
            return ""

        lines = []
        sql_counter = 0
        query_num = 0

        for msg in self.filtered_history:
            if isinstance(msg, HumanMessage):
                query_num += 1
                if query_num > 1:
                    lines.append("")
                lines.append(f"--- Query {query_num} ---\nUser: {(msg.content or '').strip()}")

            elif isinstance(msg, AIMessage):
                for tc in getattr(msg, "tool_calls", []) or []:
                    tc_lines, sql_counter = self._format_tool_call(tc, sql_counter)
                    lines.extend(tc_lines)

                lines.append(f"Assistant: {(msg.content or '').strip()}")

        self._context_cache["formatted_history"] = "\n".join(lines)
        return self._context_cache["formatted_history"]

    def get_context_summary(self) -> dict:
        """
        Get a complete summary of all context extracted from chat history.

        Returns:
            Dictionary containing all extracted context
        """
        return {
            "formatted_history": self.format_chat_history(),
            "datasets_used": self.get_datasets_used(),
            "vizpaths": self.get_vizpaths(),
        }

    def has_history(self) -> bool:
        return len(self.raw_history) > 0
