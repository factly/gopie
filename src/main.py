from langchain_core.messages import AIMessage
from lib.graph import stream_graph_updates, visualize_graph
from lib.ui.ui import CliUI
from lib.graph.types import ErrorMessage, IntermediateStep

event_types = ["identify_datasets", "plan_query", "execute_query", "generate_result"]

def main():
    ui = CliUI()
    visualize_graph()

    while True:
        user_input = ui.get_user_input()
        if user_input.lower() in ["exit", "quit", "q"]:
            ui.display_exit()
            break

        for event in stream_graph_updates(user_input):
            for event_type in event_types:
                if event_type in event:
                    if "messages" in event[event_type]:
                        message = event[event_type]["messages"][-1]

                        if isinstance(message, IntermediateStep) and message.content:
                            ui.display_intermediate_step(str(message.content))
                        elif isinstance(message, ErrorMessage) and message.content:
                            ui.display_error_message(str(message.content))
                        elif isinstance(message, AIMessage) and message.content:
                            ui.display_assistant_message(str(message.content))

if __name__ == "__main__":
    main()