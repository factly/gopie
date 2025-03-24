import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from src.lib.graph import stream_graph_updates

app = FastAPI()
logging.basicConfig(filename="log/agent.log", level=logging.INFO)
# visualize_graph()

# df = pd.read_csv(
#     "data/corporate_social_responsibility_csr_master_data_year_and_company_wise_average_net_profit_csr_amount_prescribed_and_spent_in_local_area_and_overall.csv",
#     nrows=1000,
# )
# profile = ProfileReport(df, minimal=True)
# profile.to_file("report.html")


# @app.get("/")
# def read_root():
#     return {"message": "Welcome to the Dataful Agent API"}

os.makedirs("src/api/templates", exist_ok=True)

templates = Jinja2Templates(directory="src/api/templates")

@app.get("/", response_class=HTMLResponse)
async def test_page(request: Request):
    return templates.TemplateResponse(
        "test_events.html",
        {"request": request}
    )

@app.get("/stream_events")
async def stream_events(query: str):
    return StreamingResponse(
        stream_graph_updates(query),
    )

@app.get("/nl2sql")
async def get_nl2sql(user_input: str):
    return StreamingResponse(stream_graph_updates(user_input))
