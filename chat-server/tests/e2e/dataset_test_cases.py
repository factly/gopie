"""
Dataset Test Cases for Single and Multi-Dataset Queries

Dataset Mapping:
----------------
1. Election Data (Lok Sabha):
   - ID: c9ae64dc-7728-4371-804b-9df2dc987174
   - Table: gp_hJKIjDT6fsdKQ
   - Name: master-data-election-year-wise-list-of-political-parties-participated-in-all-the-lok-sabha-elections-conducted-in-india.csv

2. CSR Master Data (Company-wise):
   - ID: 0f4c2c1b-efe4-45b1-b25f-f4b1b7a4886b
   - Table: gp_L0Uz064iBPaTy
   - Name: corporate-social-responsibility-csr-master-data-year-and-company-wise-average-net-profit-csr-amount-prescribed-and-spent-in-local-area-and-overall.csv

3. CSR Year-wise Total (PSU/Non-PSU):
   - ID: 96fba13e-fbdb-435c-af7a-17ff50ce41af
   - Table: gp_tcH5eDy79pdtC
   - Name: corporate-social-responsibility-csr-year-wise-total-number-of-psu-and-non-psu-companies-registered-and-the-total-csr-amount-spent-by-them.csv

4. CSR Company Registration:
   - ID: 81490a96-f93e-47b7-a612-223951307416
   - Table: gp_lbSuRSNAINGrC
   - Name: corporate-social-responsibility-csr-year-state-company-class-and-company-type-wise-names-of-companies-registered-under-csr.csv

5. CSR Sector-wise Spending:
   - ID: 14df05c7-94d1-4824-8dca-da1306a1b00a
   - Table: gp_4bq8me9zd9El6
   - Name: corporate-social-responsibility-csr-year-and-sector-wise-total-csr-amount-spent.csv

6. CSR Company-wise Total:
   - ID: e9e93a75-5cd9-4c28-945f-c645138da183
   - Table: gp_F80ytqRs7UByr
   - Name: corporate-social-responsibility-csr-year-and-company-wise-total-amount-spent.csv

7. CSR Project Details:
   - ID: 287b6086-aeec-4009-95f8-c23ad913b401
   - Table: gp_4FlpdqEd2NwoV
   - Name: corporate-social-responsibility-csr-master-data-year-state-district-and-company-wise-types-of-projects-taken-up-amount-outlaid-and-spent.csv

8. Election Winners and Runners:
   - ID: 07fa6cd3-7255-4311-bae6-3fd0bcaae302
   - Table: gp_0GvOIrQY8IoNY
   - Name: master-data-state-constituency-type-and-party-wise-list-of-candidates-who-have-won-and-who-stood-as-runners-2nd-position-in-all-the-lok-sabha-elections.csv

9. CSR State-wise Spending:
   - ID: ccf26406-803f-48ac-8ffe-bd8433827232
   - Table: gp_ZaFZkHYUkzA3d
   - Name: corporate-social-responsibility-csr-year-and-state-wise-total-amount-spent.csv

10. CSR District-wise Projects:
    - ID: 1da01125-5d39-4810-a0d1-44b7fd5ec7bf
    - Table: gp_yhdmin5n21Hi9
    - Name: corporate-social-responsibility-csr-master-data-year-state-district-and-sector-wise-total-number-of-projects-taken-up-and-amount-spent.csv

Project IDs:
------------
Election Project: 774e93b7-956d-4d96-8f73-5ad6ba9b826b
CSR Project: fc2c67dd-cad5-4975-b9df-572b24d49ef5
"""

# Single Dataset Test Cases
SINGLE_DATASET_TEST_CASES = [
    {
        "messages": [
            {
                "role": "user",
                "content": "List all National Parties that participated in Lok Sabha elections",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "c9ae64dc-7728-4371-804b-9df2dc987174",
        },
        "stream": True,
        "expected_result": """The query should return a comprehensive list of all unique national parties that participated in Lok Sabha elections, including major parties like:
- Bharatiya Janata Party (BJP)
- Communist Party of India (CPI)
- Indian National Congress (INC)
- Bahujan Samaj Party
- All India Trinamool Congress
- Communist Party of India (Marxist)
And all other parties where party_type = 'National Party'. A comprehensive list with 20+ parties would be expected as there have been many national parties across different election years.""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "What is the total CSR amount spent by companies in 2022-23?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "0f4c2c1b-efe4-45b1-b25f-f4b1b7a4886b",
        },
        "stream": True,
        "expected_result": """The query should return the sum of all csr_spent values for fiscal_year = '2022-23'.
Expected format: A single total amount in rupees, typically in billions.""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Compare CSR spending between PSU and Non-PSU companies in 2022-23",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "96fba13e-fbdb-435c-af7a-17ff50ce41af",
        },
        "stream": True,
        "expected_result": """The query should return comparison data for fiscal_year = '2022-23':
- PSU companies: count and total amount spent
- NON-PSU companies: count and total amount spent
Expected pattern: Non-PSU companies should have higher count and total spending.""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Who won the most recent election from West Bengal constituencies?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "07fa6cd3-7255-4311-bae6-3fd0bcaae302",
        },
        "stream": True,
        "expected_result": """The query should return winners from the most recent election (likely 2019) for West Bengal constituencies.
Expected format: List of constituencies with winner names, parties, and vote counts where state = 'West Bengal' and candidate_type = 'Winner'.""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Which CSR sector received the highest funding in 2021-22?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "14df05c7-94d1-4824-8dca-da1306a1b00a",
        },
        "stream": True,
        "expected_result": """The query should identify the sector with maximum amount_spent for fiscal_year = '2021-22'.
Expected format: Sector name with total spending amount, typically Education or Health being top sectors.""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Top 5 states by CSR spending in 2022-23",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "ccf26406-803f-48ac-8ffe-bd8433827232",
        },
        "stream": True,
        "expected_result": """The query should return the top 5 states ordered by amount_spent descending for fiscal_year = '2022-23'.
Expected format: List of 5 states with their respective spending amounts, ranked from highest to lowest.""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "How many listed companies are registered for CSR in Delhi?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "81490a96-f93e-47b7-a612-223951307416",
        },
        "stream": True,
        "expected_result": """The query should count companies where state = 'Delhi' and listing_status = 'LISTED'.
The result should include companies across all fiscal years from 2016-17 to 2022-23.""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "What are the education projects undertaken by ROSSARI BIOTECH LIMITED?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "287b6086-aeec-4009-95f8-c23ad913b401",
        },
        "stream": True,
        "expected_result": """The query should return education sector projects undertaken by ROSSARI BIOTECH LIMITED.
Expected format: List of project descriptions with amounts spent and locations where sector relates to education.""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Find companies that spent exactly 3461000 rupees on CSR",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "e9e93a75-5cd9-4c28-945f-c645138da183",
        },
        "stream": True,
        "expected_result": """The query should return companies with exact amount_spent = 3461000.
Expected format: List of company names with their CINs for the specified spending amount.""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "How many CSR projects were in Aspirational districts vs Other districts?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "1da01125-5d39-4810-a0d1-44b7fd5ec7bf",
        },
        "stream": True,
        "expected_result": """The query should aggregate project counts by type_of_district.
Expected format: Two categories with their respective project counts:
- Aspirational districts: total count
- Other Than Aspirational districts: total count""",
    },
]

# Multi Dataset Test Cases
MULTI_DATASET_TEST_CASES = [
    {
        "messages": [
            {
                "role": "user",
                "content": "What percentage of total CSR spending in 2022-23 came from PSU companies?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Get PSU spending amount for 2022-23
2. Get total spending (PSU + Non-PSU) for 2022-23
3. Calculate percentage: (PSU spending / total spending) × 100
Expected result: Percentage showing PSU contribution to total CSR spending.

Note: Should identify datasets:
- CSR Year-wise Total (PSU/Non-PSU) - ID: 96fba13e-fbdb-435c-af7a-17ff50ce41af""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Which National Parties won the most constituencies in 2019?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "774e93b7-956d-4d96-8f73-5ad6ba9b826b",
        },
        "stream": True,
        "expected_result": """The query should:
1. Join election participation data with winners data
2. Filter for National Parties and 2019 winners
3. Count constituencies won by each party
Expected format: List of national parties with their constituency win counts, ordered by wins.

Note: Should identify datasets:
- Election Data (Lok Sabha) - ID: c9ae64dc-7728-4371-804b-9df2dc987174
- Election Winners and Runners - ID: 07fa6cd3-7255-4311-bae6-3fd0bcaae302""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Compare Education sector CSR spending with Maharashtra state's total CSR spending",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Get Education sector spending from sector-wise data
2. Get Maharashtra's total spending from state-wise data
3. Compare the two amounts
Note: Both queries need same fiscal year for valid comparison

Note: Should identify datasets:
- CSR Sector-wise Spending - ID: 14df05c7-94d1-4824-8dca-da1306a1b00a
- CSR State-wise Spending - ID: ccf26406-803f-48ac-8ffe-bd8433827232""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Find listed companies in Maharashtra and their CSR spending amounts",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Get listed companies from Maharashtra (where state = 'Maharashtra' and listing_status = 'LISTED')
2. Match these companies by CIN with their spending amounts
3. Return company names with their CSR spending amounts

Note: Should identify datasets:
- CSR Company Registration - ID: 81490a96-f93e-47b7-a612-223951307416
- CSR Company-wise Total - ID: e9e93a75-5cd9-4c28-945f-c645138da183""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Compare project-level spending with district aggregate spending for Education in Kerala",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Sum Education project amounts in Kerala from project details
2. Get Education sector spending in Kerala districts from aggregate data
3. Compare to verify data consistency between detailed and aggregate datasets

Note: Should identify datasets:
- CSR Project Details - ID: 287b6086-aeec-4009-95f8-c23ad913b401
- CSR District-wise Projects - ID: 1da01125-5d39-4810-a0d1-44b7fd5ec7bf""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Analyze CSR compliance for PUBLIC companies - prescribed vs actual spent",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Identify PUBLIC companies from registration data
2. Get their prescribed CSR amounts from master data
3. Get their actual spending from company-wise total data
4. Calculate compliance rate (actual/prescribed) for each company
5. Show companies exceeding, meeting, or falling short of prescribed amounts

Note: Should identify datasets:
- CSR Master Data (Company-wise) - ID: 0f4c2c1b-efe4-45b1-b25f-f4b1b7a4886b
- CSR Company Registration - ID: 81490a96-f93e-47b7-a612-223951307416
- CSR Company-wise Total - ID: e9e93a75-5cd9-4c28-945f-c645138da183""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Track BJP's performance from first participation to 2019 - participation years and victories",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "774e93b7-956d-4d96-8f73-5ad6ba9b826b",
        },
        "stream": True,
        "expected_result": """The query should:
1. Find all years BJP participated in elections
2. Count constituencies won by BJP in each year
3. Show the growth trajectory from first participation to becoming the dominant party in 2019
4. Include total constituencies contested vs won ratio

Note: Should identify datasets:
- Election Data (Lok Sabha) - ID: c9ae64dc-7728-4371-804b-9df2dc987174
- Election Winners and Runners - ID: 07fa6cd3-7255-4311-bae6-3fd0bcaae302""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Verify Health sector spending totals match between sector summary and project details",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Get Health sector total from sector-wise summary
2. Sum all Health sector projects from detailed project data
3. Compare the totals for data validation
4. Identify any discrepancies by fiscal year

Note: Should identify datasets:
- CSR Sector-wise Spending - ID: 14df05c7-94d1-4824-8dca-da1306a1b00a
- CSR Project Details - ID: 287b6086-aeec-4009-95f8-c23ad913b401""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Which states have the highest concentration of PSU companies and how much do they spend?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Identify states with PSU presence (this requires additional data or inference)
2. Get state-wise CSR spending
3. Correlate PSU concentration with state spending patterns
Note: This query may need additional data about PSU locations

Note: Should identify datasets:
- CSR Year-wise Total (PSU/Non-PSU) - ID: 96fba13e-fbdb-435c-af7a-17ff50ce41af
- CSR State-wise Spending - ID: ccf26406-803f-48ac-8ffe-bd8433827232""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Analyze CSR spending patterns in Aspirational districts - company profiles and project types",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Identify Aspirational districts from district data
2. Find companies operating in these districts
3. Analyze their project types and spending amounts
4. Compare average spending in Aspirational vs Other districts
5. Identify top sectors receiving funding in Aspirational districts

Note: Should identify datasets:
- CSR Master Data (Company-wise) - ID: 0f4c2c1b-efe4-45b1-b25f-f4b1b7a4886b
- CSR Project Details - ID: 287b6086-aeec-4009-95f8-c23ad913b401
- CSR District-wise Projects - ID: 1da01125-5d39-4810-a0d1-44b7fd5ec7bf""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Which state parties became national parties over time based on electoral performance?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "774e93b7-956d-4d96-8f73-5ad6ba9b826b",
        },
        "stream": True,
        "expected_result": """The query should:
1. Track parties classified as 'State Party' in participation data
2. Check their winning performance across multiple states
3. Identify parties that expanded from state to national level
4. Show their trajectory of wins across different states and years

Note: Should identify datasets:
- Election Data (Lok Sabha) - ID: c9ae64dc-7728-4371-804b-9df2dc987174
- Election Winners and Runners - ID: 07fa6cd3-7255-4311-bae6-3fd0bcaae302""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Profile of CSR activities in North Eastern states - companies, projects and spending",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Identify North Eastern states (Assam, Nagaland, Tripura, etc.)
2. Find companies registered in these states
3. List their CSR projects and sectors
4. Calculate total spending by state
5. Show spending per capita or per company metrics

Note: Should identify datasets:
- CSR Company Registration - ID: 81490a96-f93e-47b7-a612-223951307416
- CSR State-wise Spending - ID: ccf26406-803f-48ac-8ffe-bd8433827232
- CSR Project Details - ID: 287b6086-aeec-4009-95f8-c23ad913b401""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "How does PSU vs Non-PSU spending differ across CSR sectors?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Get total PSU and Non-PSU spending amounts
2. Distribute sector-wise spending proportionally (if direct data not available)
3. Identify sectors where PSUs dominate vs where private companies lead
4. Calculate sector preference ratios for both categories

Note: Should identify datasets:
- CSR Sector-wise Spending - ID: 14df05c7-94d1-4824-8dca-da1306a1b00a
- CSR Year-wise Total (PSU/Non-PSU) - ID: 96fba13e-fbdb-435c-af7a-17ff50ce41af""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Find companies spending more than prescribed CSR amount and their characteristics",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Compare prescribed_csr_expenditure with actual csr_spent
2. Identify companies where actual > prescribed
3. Get their company class (PUBLIC/PRIVATE) and listing status
4. Calculate over-compliance percentage
5. Show top over-compliant companies with their profiles

Note: Should identify datasets:
- CSR Master Data (Company-wise) - ID: 0f4c2c1b-efe4-45b1-b25f-f4b1b7a4886b
- CSR Company-wise Total - ID: e9e93a75-5cd9-4c28-945f-c645138da183
- CSR Company Registration - ID: 81490a96-f93e-47b7-a612-223951307416""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Analyze Scheduled Caste (SC) and Scheduled Tribe (ST) constituency representation",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "774e93b7-956d-4d96-8f73-5ad6ba9b826b",
        },
        "stream": True,
        "expected_result": """The query should:
1. Count SC and ST constituencies from winners data
2. Identify parties that won these reserved constituencies
3. Track changes in representation over different Lok Sabha elections
4. Show which parties have strong presence in reserved constituencies

Note: Should identify datasets:
- Election Winners and Runners - ID: 07fa6cd3-7255-4311-bae6-3fd0bcaae302""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Complete CSR analysis for Tamil Nadu - companies, projects, and spending efficiency",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should provide comprehensive Tamil Nadu CSR analysis:
1. Total companies registered in Tamil Nadu (from registration data)
2. Their prescribed vs actual CSR spending (from master data)
3. Types of projects undertaken (from project details)
4. Tamil Nadu's rank in national CSR spending (from state-wise data)
5. Average spending per company and per project
6. Compliance rate for Tamil Nadu companies

Note: Should identify datasets:
- CSR Master Data (Company-wise) - ID: 0f4c2c1b-efe4-45b1-b25f-f4b1b7a4886b
- CSR Company Registration - ID: 81490a96-f93e-47b7-a612-223951307416
- CSR Project Details - ID: 287b6086-aeec-4009-95f8-c23ad913b401
- CSR State-wise Spending - ID: ccf26406-803f-48ac-8ffe-bd8433827232""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Do companies associated with major political parties have different CSR patterns?",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "774e93b7-956d-4d96-8f73-5ad6ba9b826b",
            "project_id_2": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Identify major political parties from election data
2. Search for companies with similar names or known associations
3. Analyze their CSR spending patterns
4. Compare with overall industry CSR trends
Note: This requires fuzzy matching and may have limited direct correlations

Note: Should identify datasets:
- Election Data (Lok Sabha) - ID: c9ae64dc-7728-4371-804b-9df2dc987174
- Election Winners and Runners - ID: 07fa6cd3-7255-4311-bae6-3fd0bcaae302
- CSR Master Data (Company-wise) - ID: 0f4c2c1b-efe4-45b1-b25f-f4b1b7a4886b
- CSR Company Registration - ID: 81490a96-f93e-47b7-a612-223951307416""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Environmental CSR initiatives - spending trends, geographical distribution, and impact",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should analyze environmental CSR:
1. Total spending on Environment/Conservation sectors
2. Year-over-year growth in environmental CSR
3. States with highest environmental CSR spending
4. Districts and specific projects in environmental sector
5. Number of companies participating in environmental CSR
6. Comparison with other CSR sectors

Note: Should identify datasets:
- CSR Sector-wise Spending - ID: 14df05c7-94d1-4824-8dca-da1306a1b00a
- CSR Project Details - ID: 287b6086-aeec-4009-95f8-c23ad913b401
- CSR District-wise Projects - ID: 1da01125-5d39-4810-a0d1-44b7fd5ec7bf
- CSR State-wise Spending - ID: ccf26406-803f-48ac-8ffe-bd8433827232""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "CSR compliance analysis - PSU vs Private, Listed vs Unlisted companies",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should provide detailed compliance analysis:
1. Compliance rates for PSU vs Non-PSU companies
2. Compliance rates for Listed vs Unlisted companies
3. Average over/under spending by category
4. Number of non-compliant companies by type
5. Trends over multiple years
6. Top compliant companies in each category

Note: Should identify datasets:
- CSR Master Data (Company-wise) - ID: 0f4c2c1b-efe4-45b1-b25f-f4b1b7a4886b
- CSR Year-wise Total (PSU/Non-PSU) - ID: 96fba13e-fbdb-435c-af7a-17ff50ce41af
- CSR Company Registration - ID: 81490a96-f93e-47b7-a612-223951307416
- CSR Company-wise Total - ID: e9e93a75-5cd9-4c28-945f-c645138da183""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Correlation between political representation and CSR spending by state",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id_1": "774e93b7-956d-4d96-8f73-5ad6ba9b826b",
            "project_id_2": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should analyze:
1. States with strong representation of national parties
2. CSR spending levels in these states
3. Compare CSR spending in states dominated by different parties
4. Sector preferences in different politically-aligned states
5. Any observable patterns or correlations
Note: Correlation does not imply causation

Note: Should identify datasets:
- Election Data (Lok Sabha) - ID: c9ae64dc-7728-4371-804b-9df2dc987174
- Election Winners and Runners - ID: 07fa6cd3-7255-4311-bae6-3fd0bcaae302
- CSR Sector-wise Spending - ID: 14df05c7-94d1-4824-8dca-da1306a1b00a
- CSR State-wise Spending - ID: ccf26406-803f-48ac-8ffe-bd8433827232""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Analysis of CSR spending by Financial Services companies across different states",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Identify Financial Services companies using CIN patterns or company names
2. Calculate their total CSR spending by state
3. Compare their compliance rates
4. Identify top spending financial companies
5. Show geographical concentration of financial sector CSR

Note: Should identify datasets:
- CSR Company Registration - ID: 81490a96-f93e-47b7-a612-223951307416
- CSR Master Data (Company-wise) - ID: 0f4c2c1b-efe4-45b1-b25f-f4b1b7a4886b
- CSR Company-wise Total - ID: e9e93a75-5cd9-4c28-945f-c645138da183""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Rural development CSR projects - implementation modes and effectiveness",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should analyze:
1. Total spending on Rural Development sector
2. Implementation modes used (Direct vs Agencies)
3. Number of projects and average project size
4. Geographical distribution of rural projects
5. Companies most active in rural development

Note: Should identify datasets:
- CSR Sector-wise Spending - ID: 14df05c7-94d1-4824-8dca-da1306a1b00a
- CSR Project Details - ID: 287b6086-aeec-4009-95f8-c23ad913b401
- CSR District-wise Projects - ID: 1da01125-5d39-4810-a0d1-44b7fd5ec7bf""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Evolution of regional parties - from state to national recognition",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "774e93b7-956d-4d96-8f73-5ad6ba9b826b",
        },
        "stream": True,
        "expected_result": """The query should track:
1. Parties that started as state parties
2. Their expansion to multiple states over elections
3. Achievement of national party status
4. Electoral performance trends
5. Examples like AITC, BSP, etc.

Note: Should identify datasets:
- Election Data (Lok Sabha) - ID: c9ae64dc-7728-4371-804b-9df2dc987174
- Election Winners and Runners - ID: 07fa6cd3-7255-4311-bae6-3fd0bcaae302""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Impact of company size on CSR compliance - analysis by net profit ranges",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Categorize companies by average net profit ranges
2. Calculate compliance rates for each category
3. Identify if larger companies have better compliance
4. Show over/under spending patterns by company size
5. Highlight exceptions and outliers

Note: Should identify datasets:
- CSR Master Data (Company-wise) - ID: 0f4c2c1b-efe4-45b1-b25f-f4b1b7a4886b
- CSR Company-wise Total - ID: e9e93a75-5cd9-4c28-945f-c645138da183""",
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "Year-over-year growth analysis of CSR spending by sector from 2014-15 to 2022-23",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "project_id": "fc2c67dd-cad5-4975-b9df-572b24d49ef5",
        },
        "stream": True,
        "expected_result": """The query should:
1. Calculate total spending by sector for each year
2. Compute year-over-year growth rates
3. Identify fastest growing sectors
4. Show sectors with declining spending
5. Highlight major shifts in sector priorities

Note: Should identify datasets:
- CSR Sector-wise Spending - ID: 14df05c7-94d1-4824-8dca-da1306a1b00a""",
    },
]

# Visualization Test Cases
VISUALIZATION_TEST_CASES = [
    {
        # Type 1: Generate visualization based on previous query results
        "messages": [
            {
                "role": "user",
                "content": "Show me the top 10 companies by CSR spending in 2022-23",
            },
            {
                "role": "assistant",
                "content": """Based on the CSR spending data for 2022-23, here are the top 10 companies:

| Company Name | CIN | CSR Amount Spent (₹) |
|--------------|-----|---------------------|
| RELIANCE INDUSTRIES LTD | L17110MH1973PLC019786 | ₹7,420,000,000 |
| TATA CONSULTANCY SERVICES LIMITED | L22210MH1995PLC084781 | ₹6,750,000,000 |
| INFOSYS LIMITED | L85110KA1981PLC013115 | ₹4,890,000,000 |
| HDFC BANK LIMITED | L65920MH1994PLC080618 | ₹4,320,000,000 |
| INDIAN OIL CORPORATION LIMITED | L23201MH1959GOI011388 | ₹3,980,000,000 |
| WIPRO LIMITED | L32102KA1945PLC020800 | ₹3,540,000,000 |
| BHARTI AIRTEL LIMITED | L74899DL1995PLC070609 | ₹3,210,000,000 |
| ITC LIMITED | L16005WB1910PLC001985 | ₹2,890,000,000 |
| HINDUSTAN UNILEVER LIMITED | L15140MH1933PLC002030 | ₹2,670,000,000 |
| COAL INDIA LIMITED | L23109WB1973GOI001199 | ₹2,450,000,000 |

These companies collectively spent over ₹42 billion on CSR activities in 2022-23.""",
            },
            {
                "role": "user",
                "content": "Create a bar chart visualizing this CSR spending data",
            },
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "e9e93a75-5cd9-4c28-945f-c645138da183",
        },
        "stream": True,
        "expected_result": """The response should:
1. Acknowledge the visualization request positively
2. Provide a JSON config path in format: json-path: YYYYMMDD-HHMMSS-[hash]-[number].json
3. Indicate successful creation of the bar chart visualization""",
    },
    {
        # Type 2: Modify previously generated visualization
        "messages": [
            {
                "role": "user",
                "content": "What are the CSR spending trends by sector for the last 3 years?",
            },
            {
                "role": "assistant",
                "content": """Here are the CSR spending trends by sector for the last 3 years (2020-21 to 2022-23):

| Sector | 2020-21 (₹ Cr) | 2021-22 (₹ Cr) | 2022-23 (₹ Cr) |
|--------|----------------|----------------|----------------|
| Education | 3,890 | 4,567 | 5,234 |
| Health | 2,456 | 3,789 | 4,123 |
| Rural Development | 1,234 | 1,567 | 1,890 |
| Environment | 890 | 1,123 | 1,456 |
| Others | 2,345 | 2,678 | 3,012 |

The data shows consistent growth across all sectors, with Education and Health receiving the highest allocations.""",
            },
            {
                "role": "user",
                "content": "Visualize this as a grouped bar chart showing year-over-year comparison",
            },
            {
                "role": "assistant",
                "content": "json-path: 20250722-160710-1f99018f-0.json",
            },
            {
                "role": "user",
                "content": "Change this to a stacked area chart to better show the total growth and sector contributions",
            },
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "14df05c7-94d1-4824-8dca-da1306a1b00a",
        },
        "stream": True,
        "expected_result": """The response should:
1. Acknowledge the modification request positively
2. Provide a new JSON config path in format: json-path: YYYYMMDD-HHMMSS-[hash]-[number].json
3. Indicate successful transformation to stacked area chart""",
    },
    {
        # Type 3: Single query for data + visualization
        "messages": [
            {
                "role": "user",
                "content": "Show me PSU vs Non-PSU CSR spending comparison for the last 5 years and create a line chart to visualize the trends",
            }
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "96fba13e-fbdb-435c-af7a-17ff50ce41af",
        },
        "stream": True,
        "expected_result": """The response should:
1. Present the requested data analysis
2. Acknowledge the visualization request positively
3. Provide a JSON config path in format: json-path: YYYYMMDD-HHMMSS-[hash]-[number].json
4. Indicate successful creation of the line chart visualization""",
    },
    {
        # Type 4: Generate visualization from complex previous results
        "messages": [
            {
                "role": "user",
                "content": "Analyze state-wise CSR spending distribution for top 5 states",
            },
            {
                "role": "assistant",
                "content": """Based on the analysis of state-wise CSR spending, here are the top 5 states:

**Top 5 States by CSR Spending (2022-23):**

1. **Maharashtra**: ₹8,456 Crores
   - Number of companies: 3,245
   - Average per company: ₹2.60 Crores
   - Top sectors: Education (35%), Health (28%), Environment (15%)

2. **Karnataka**: ₹5,234 Crores
   - Number of companies: 1,876
   - Average per company: ₹2.79 Crores
   - Top sectors: Education (40%), Technology (25%), Health (20%)

3. **Gujarat**: ₹3,890 Crores
   - Number of companies: 1,543
   - Average per company: ₹2.52 Crores
   - Top sectors: Rural Development (30%), Education (28%), Health (22%)

4. **Tamil Nadu**: ₹3,456 Crores
   - Number of companies: 1,234
   - Average per company: ₹2.80 Crores
   - Top sectors: Education (38%), Health (25%), Environment (18%)

5. **Delhi**: ₹2,789 Crores
   - Number of companies: 987
   - Average per company: ₹2.83 Crores
   - Top sectors: Education (42%), Health (30%), Others (28%)

These 5 states account for approximately 65% of total CSR spending in India.""",
            },
            {
                "role": "user",
                "content": "Create a pie chart showing the distribution of CSR spending among these top 5 states and others",
            },
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "ccf26406-803f-48ac-8ffe-bd8433827232",
        },
        "stream": True,
        "expected_result": """The response should:
1. Acknowledge the pie chart request positively
2. Provide a JSON config path in format: json-path: YYYYMMDD-HHMMSS-[hash]-[number].json
3. Indicate successful creation of the pie chart showing state distribution""",
    },
    {
        # Type 5: Visualization with comparison and trend analysis
        "messages": [
            {
                "role": "user",
                "content": "Compare Education vs Health sector CSR spending growth over the years",
            },
            {
                "role": "assistant",
                "content": """Here's the comparison of Education vs Health sector CSR spending from 2016-17 to 2022-23:

**Education Sector:**
- 2016-17: ₹2,145 Cr
- 2017-18: ₹2,567 Cr (+19.7%)
- 2018-19: ₹2,890 Cr (+12.6%)
- 2019-20: ₹3,234 Cr (+11.9%)
- 2020-21: ₹3,890 Cr (+20.3%)
- 2021-22: ₹4,567 Cr (+17.4%)
- 2022-23: ₹5,234 Cr (+14.6%)

**Health Sector:**
- 2016-17: ₹1,234 Cr
- 2017-18: ₹1,456 Cr (+18.0%)
- 2018-19: ₹1,789 Cr (+22.9%)
- 2019-20: ₹2,123 Cr (+18.7%)
- 2020-21: ₹2,456 Cr (+15.7%)
- 2021-22: ₹3,789 Cr (+54.3%) *COVID impact
- 2022-23: ₹4,123 Cr (+8.8%)

Key Insights:
- Education consistently receives higher absolute funding
- Health sector saw exceptional growth in 2021-22 due to COVID-19
- Both sectors show positive year-over-year growth
- Cumulative growth: Education (144%), Health (234%)""",
            },
            {
                "role": "user",
                "content": "Visualize this comparison with a dual-axis chart showing both absolute values and growth rates",
            },
        ],
        "model": "test",
        "user": "test",
        "metadata": {
            "dataset_id": "14df05c7-94d1-4824-8dca-da1306a1b00a",
        },
        "stream": True,
        "expected_result": """The response should:
1. Acknowledge the dual-axis chart request positively
2. Provide a JSON config path in format: json-path: YYYYMMDD-HHMMSS-[hash]-[number].json
3. Indicate successful creation of the combination chart with both absolute values and growth rates""",
    },
]
