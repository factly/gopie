import logging

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

from src.lib.graph import stream_graph_updates, visualize_graph

app = FastAPI()
logging.basicConfig(filename="log/agent.log", level=logging.INFO)
visualize_graph()

# df = pd.read_csv(
#     "data/corporate_social_responsibility_csr_master_data_year_and_company_wise_average_net_profit_csr_amount_prescribed_and_spent_in_local_area_and_overall.csv",
#     nrows=1000,
# )
# profile = ProfileReport(df, minimal=True)
# profile.to_file("report.html")

templates = Jinja2Templates(directory="src/test/templates")


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("stream_test.html", {"request": request})


@app.get("/nl2sql")
async def get_nl2sql(user_input: str):
    """Stream the agent's processing events as Server-Sent Events."""

    async def event_generator():
        async for chunk in stream_graph_updates(user_input):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
