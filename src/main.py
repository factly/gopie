import json
import logging

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from src.lib.graph import stream_graph_updates
from src.utils.correct_column_values import correct_column_values

app = FastAPI()
logging.basicConfig(filename="log/agent.log", level=logging.INFO)

print(
    json.dumps(
        correct_column_values(
            [
                {
                    "dataset": "corporate_social_responsibility_csr_master_data_year_state_district_and_company_wise_types_of_projects_taken_up_amount_outlaid_and_spent.csv",
                    "columns": [
                        {
                            "name": "fiscal_year",
                            "expected_values": ["2021-22"],
                            "filter_condition": "equals",
                        },
                        {
                            "name": "sector",
                            "expected_values": ["Health"],
                            "filter_condition": "equals",
                        },
                        {
                            "name": "amount_spent",
                            "expected_values": "range: 0-maximum in dataset",
                            "filter_condition": "none",
                        },
                    ],
                }
            ]
        ),
        indent=2,
    )
)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Dataful Agent API"}


@app.get("/nl2sql")
async def get_nl2sql(user_input: str):
    return StreamingResponse(stream_graph_updates(user_input))
