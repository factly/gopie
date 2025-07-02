CSR_MASTER_DATA_CASES = [
    {
        "messages": [
            {
                "role": "user",
                "content": "What was the average net profit of companies during 2022-23?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "5eb6f370-8515-4cca-b527-d2b4517591f0",
            "dataset_id_1": "9975bec1-1133-4b94-8ab2-179bba9ba887",
        },
        "stream": True,
        "expected_result": {
            "sql_query_count": 1,
            "visualization_needed": False,
        },
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Show me a bar chart of the top 10 companies by CSR spent in 2021-22",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "5eb6f370-8515-4cca-b527-d2b4517591f0",
            "dataset_id_1": "9975bec1-1133-4b94-8ab2-179bba9ba887",
        },
        "stream": True,
        "expected_result": {
            "sql_query_count": 1,
            "visualization_needed": True,
            "visualization_type": "bar chart",
        },
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "What's the correlation between average net profit and CSR spent for 2022-23? Visualize it with a scatter plot.",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "5eb6f370-8515-4cca-b527-d2b4517591f0",
            "dataset_id_1": "9975bec1-1133-4b94-8ab2-179bba9ba887",
        },
        "stream": True,
        "expected_result": {
            "sql_query_count": 1,
            "visualization_needed": True,
            "visualization_type": "scatter plot",
        },
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "List the companies with zero CSR spent despite having high average net profits (top 20)",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "5eb6f370-8515-4cca-b527-d2b4517591f0",
            "dataset_id_1": "9975bec1-1133-4b94-8ab2-179bba9ba887",
        },
        "stream": True,
        "expected_result": {
            "sql_query_count": 1,
            "visualization_needed": False,
        },
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Compare the trend of prescribed CSR expenditure vs actual CSR spent from 2016 to 2023 with a line chart",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "5eb6f370-8515-4cca-b527-d2b4517591f0",
            "dataset_id_1": "9975bec1-1133-4b94-8ab2-179bba9ba887",
        },
        "stream": True,
        "expected_result": {
            "sql_query_count": 1,
            "visualization_needed": True,
            "visualization_type": "line chart",
        },
    },
]

LOK_SABHA_CANDIDATES_CASES = [
    {
        "messages": [
            {
                "role": "user",
                "content": "How many female candidates contested in the 2019 Lok Sabha elections?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "b26ad6ba-9c23-4c32-ac34-3fc8a6aa86a1",
            "dataset_id_1": "e4301feb-a92b-4971-9e8d-ec62ccbe17a6",
        },
        "stream": True,
        "expected_result": {
            "dataset_identified": "Lok Sabha Candidates Master Data",
            "sql_query_count": 1,
            "visualization_needed": False,
        },
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Show me a pie chart of the gender distribution of candidates in 2019 elections",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "b26ad6ba-9c23-4c32-ac34-3fc8a6aa86a1",
            "dataset_id_1": "e4301feb-a92b-4971-9e8d-ec62ccbe17a6",
        },
        "stream": True,
        "expected_result": {
            "dataset_identified": "Lok Sabha Candidates Master Data",
            "sql_query_count": 1,
            "visualization_needed": True,
            "visualization_type": "pie chart",
        },
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Compare the number of nominations filed versus nominations rejected across states in 2019 using a grouped bar chart",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "b26ad6ba-9c23-4c32-ac34-3fc8a6aa86a1",
            "dataset_id_1": "e4301feb-a92b-4971-9e8d-ec62ccbe17a6",
        },
        "stream": True,
        "expected_result": {
            "dataset_identified": "Lok Sabha Candidates Master Data",
            "sql_query_count": 2,
            "visualization_needed": True,
            "visualization_type": "grouped bar chart",
        },
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "What's the trend of forfeited deposits by gender from 1971 to 2019? Show as a stacked area chart",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "b26ad6ba-9c23-4c32-ac34-3fc8a6aa86a1",
            "dataset_id_1": "e4301feb-a92b-4971-9e8d-ec62ccbe17a6",
        },
        "stream": True,
        "expected_result": {
            "dataset_identified": "Lok Sabha Candidates Master Data",
            "sql_query_count": 1,
            "visualization_needed": True,
            "visualization_type": "stacked area chart",
        },
    },
]

CSR_AMOUNT_SPENT_CASES = [
    {
        "messages": [
            {
                "role": "user",
                "content": "Which companies spent the most on CSR in 2022-23? Show top 15",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "5eb6f370-8515-4cca-b527-d2b4517591f0",
            "dataset_id_1": "e40a87da-ad0b-423d-8325-26351d548bfd",
        },
        "stream": True,
        "expected_result": {
            "dataset_identified": "CSR Total Amount Spent",
            "sql_query_count": 1,
            "visualization_needed": False,
        },
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Create a treemap visualization of the top 20 companies by CSR amount spent in 2021-22",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "5eb6f370-8515-4cca-b527-d2b4517591f0",
            "dataset_id_1": "e40a87da-ad0b-423d-8325-26351d548bfd",
        },
        "stream": True,
        "expected_result": {
            "dataset_identified": "CSR Total Amount Spent",
            "sql_query_count": 1,
            "visualization_needed": True,
            "visualization_type": "treemap",
        },
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "What's the year-over-year growth in CSR spending from 2016 to 2023? Show as a line chart",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "5eb6f370-8515-4cca-b527-d2b4517591f0",
            "dataset_id_1": "e40a87da-ad0b-423d-8325-26351d548bfd",
        },
        "stream": True,
        "expected_result": {
            "dataset_identified": "CSR Total Amount Spent",
            "sql_query_count": 1,
            "visualization_needed": True,
            "visualization_type": "line chart",
        },
    },
]

LOK_SABHA_CONSTITUENCIES_CASES = [
    {
        "messages": [
            {
                "role": "user",
                "content": "Which state had the highest number of Scheduled Caste constituencies in 2019?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "b26ad6ba-9c23-4c32-ac34-3fc8a6aa86a1",
            "dataset_id_1": "db0ee4dc-d75f-4d3d-8672-119a7cf77968",
        },
        "stream": True,
        "expected_result": {
            "dataset_identified": "Lok Sabha Constituencies Master Data",
            "sql_query_count": 1,
            "visualization_needed": False,
        },
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Create a map visualization showing the distribution of different constituency types across states in 2019",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "b26ad6ba-9c23-4c32-ac34-3fc8a6aa86a1",
            "dataset_id_1": "db0ee4dc-d75f-4d3d-8672-119a7cf77968",
        },
        "stream": True,
        "expected_result": {
            "dataset_identified": "Lok Sabha Constituencies Master Data",
            "sql_query_count": 1,
            "visualization_needed": True,
            "visualization_type": "choropleth map",
        },
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Show the trend of Scheduled Tribe constituencies from 1951 to 2019 as a bar chart",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "b26ad6ba-9c23-4c32-ac34-3fc8a6aa86a1",
            "dataset_id_1": "db0ee4dc-d75f-4d3d-8672-119a7cf77968",
        },
        "stream": True,
        "expected_result": {
            "dataset_identified": "Lok Sabha Constituencies Master Data",
            "sql_query_count": 1,
            "visualization_needed": True,
            "visualization_type": "bar chart",
        },
    },
]

EDGE_CASES = [
    {
        "messages": [
            {
                "role": "user",
                "content": "Show me data from companies that have negative average net profit but still spent on CSR",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "5eb6f370-8515-4cca-b527-d2b4517591f0",
            "dataset_id_1": "9975bec1-1133-4b94-8ab2-179bba9ba887",
        },
        "stream": True,
        "expected_result": {
            "dataset_identified": "CSR Master Data",
            "sql_query_count": 1,
            "visualization_needed": False,
        },
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Find the constituencies with NULL or missing data in 2019",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "b26ad6ba-9c23-4c32-ac34-3fc8a6aa86a1",
            "dataset_id_1": "e4301feb-a92b-4971-9e8d-ec62ccbe17a6",
        },
        "stream": True,
        "expected_result": {
            "dataset_identified": "Lok Sabha Candidates Master Data",
            "sql_query_count": 1,
            "visualization_needed": False,
        },
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Create a complex dashboard with multiple charts showing CSR spending trends, correlation with profits, and geographical distribution",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "5eb6f370-8515-4cca-b527-d2b4517591f0",
            "dataset_id_1": "e40a87da-ad0b-423d-8325-26351d548bfd",
        },
        "stream": True,
        "expected_result": {
            "dataset_identified": "CSR Total Amount Spent",
            "sql_query_count": "multiple",
            "visualization_needed": True,
            "visualization_type": "dashboard",
        },
    },
]

SINGLE_DATASET_TEST_CASES = (
    CSR_MASTER_DATA_CASES
    + LOK_SABHA_CANDIDATES_CASES
    + CSR_AMOUNT_SPENT_CASES
    + LOK_SABHA_CONSTITUENCIES_CASES
    + EDGE_CASES
)
