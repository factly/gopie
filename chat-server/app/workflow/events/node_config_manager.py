from app.models.chat import NodeConfig, Role


class NodeConfigManager:
    def __init__(self):
        self._configs = {}
        self._setup_configs()

    def _setup_configs(self):
        self._configs = {
            "generate_subqueries": NodeConfig(
                streams_ai_content=False,
                role=Role.INTERMEDIATE,
                progress_message=(
                    "Breaking down your query into manageable parts..."
                ),
            ),
            "identify_datasets": NodeConfig(
                streams_ai_content=False,
                role=Role.INTERMEDIATE,
                progress_message="Identifying relevant datasets...",
            ),
            "analyze_datasets": NodeConfig(
                streams_ai_content=False,
                role=Role.INTERMEDIATE,
                progress_message="Analyzing datasets...",
            ),
            "plan_query": NodeConfig(
                streams_ai_content=False,
                role=Role.INTERMEDIATE,
                progress_message="Planning the database query...",
            ),
            "process_query": NodeConfig(
                streams_ai_content=False,
                role=Role.INTERMEDIATE,
                progress_message="Processing your query...",
            ),
            "generate_result": NodeConfig(
                streams_ai_content=True, role=Role.AI, progress_message=""
            ),
            "stream_updates": NodeConfig(
                streams_ai_content=True, role=Role.AI, progress_message=""
            ),
            "response": NodeConfig(
                streams_ai_content=True, role=Role.AI, progress_message="."
            ),
            "tools": NodeConfig(
                streams_ai_content=False,
                role=Role.SYSTEM,
                progress_message="Executing tool...",
            ),
            "unknown": NodeConfig(
                streams_ai_content=False,
                role=Role.INTERMEDIATE,
            ),
        }

    def get_config(self, node_name: str) -> NodeConfig:
        return self._configs.get(node_name, NodeConfig())

    def is_valid_node(self, node_name: str) -> bool:
        return node_name in self._configs

    def get_all_nodes(self) -> list[str]:
        return list(self._configs.keys())

    def list_streaming_nodes(self) -> list[str]:
        return [
            node_name
            for node_name, config in self._configs.items()
            if config.streams_ai_content
        ]

    def list_nodes_by_role(self, role: Role) -> list[str]:
        return [
            node_name
            for node_name, config in self._configs.items()
            if config.role == role
        ]

    def get_progress_message(self, node_name: str) -> str:
        return self.get_config(node_name).progress_message


node_config_manager = NodeConfigManager()
