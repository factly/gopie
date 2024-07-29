# Project Documentation

## Overview

Gopie is a query engine for csv and parquet files which uses DuckDB under the hood.

## Prerequisites

- Go (version 1.22 or higher)
- Docker and Docker Compose
- Air (for hot reloading)

## Configuration

### Air Configuration

The project uses Air for hot reloading during development. The configuration is stored in the `.air.toml` file at the root of the project. Key settings include:

- Build command: `go build -o ./tmp/main .`
- Binary to run: `./tmp/main serve`
- Directories to exclude: `assets`, `tmp`, `vendor`, `testdata`

### Environment Variables

The project requires a set of environment variables. These are stored in a `config.env` file. To set up:

1. Copy `config.env.example` to `config.env`
2. Modify the values in `config.env` as needed

Key environment variables include:

- `DUCKDB_DSN`: Path to the DuckDB database file
- `LOG_LEVEL`: Logging level (e.g., debug)
- `SERVER_PORT`: Port on which the server runs
- `MASTER_KEY`: Master key for authentication
- `OPEN_AI_API_KEY`: For natural language to text endpoint
- `S3_ACCESS_KEY` and `S3_SECRET_ACCESS_KEY`: Credentials for S3 (Minio) access
- `PORT_KEY_API_KEY` and `PORT_KEY_AI_MODEL`: Settings for PortKey AI integration

## Database

The project uses DuckDB as its database. The database file is stored at the path specified by `DUCKDB_DSN` in the config.

## File Storage

MinIO is used for S3-compatible object storage. It's set up using Docker Compose.

To start MinIO:

```
docker-compose up minio
```

MinIO will be accessible at `http://localhost:9000`.

## Running the Project

1. Ensure all configurations are set up correctly.
2. Start MinIO using Docker Compose.
3. Run the project using Air:

```
air
```

This will start the server with hot reloading enabled.

## Working
Here's a detailed explanation of its workflow:

1. File Upload:
   - Users upload a CSV or Parquet file from their S3 storage using the /source/s3 API endpoint.


2. File Conversion and Storage:

   - Gopie converts the uploaded file into DuckDB format.
   - The converted files are stored in the path specified by the DUCKDB_DSN environment variable (e.g., ./test/main.db).
   - Gopie assigns a unique alphanumeric name to each uploaded file (e.g., gp_hw9NPJ4qX60c).


3. Directory Structure:

   - For each uploaded file, Gopie creates a new folder in the specified path.
   - The folder name matches the assigned alphanumeric name (e.g., gp_hw9NPJ4qX60c).
   - Inside this folder, Gopie creates:
      a) A version.txt file containing the version number of the uploaded file.
      b) A DuckDB file named {version_number}.db (e.g., 178932892971.db), which is the actual converted database.
   - The /source/s3 endpoint returns a table_name to the user, which corresponds to the assigned alphanumeric name.


4. Querying:
   - Users can query the uploaded data using the provided table_name.
   - The directory with table_name specified in query is attached to duckdb main.db if not attached before(this is done because attaching serveral files at the startup, the application is taking a lot of time to start)
   - Queries are sent through Gopie's API, using the table_name to specify which data to query.


## API Endpoints

### Auth Endpoints:
  1. POST `/auth/apikey`:
      - creates an apikey for gopie query apis
      - body:
         ```
           description: string (optional) 
           name: string 
           meta: object (optional)
           expiry: string (optional, valid timestamp)
         ```
      - sample curl request:
         ```bash
            curl --location 'localhost:8000/auth/apikey' \
            --header 'Authorization: Bearer masterkey' \
            --header 'Content-Type: application/json' \
            --data '{
               "name": "testing",
               "expiry": "1731456549"
            }'
         ```
   2. PATCH `/auth/apikey`:
      - update apikey info
      - body:
         ```
           key: api token
           delta:
              description: string
              name: string 
              meta: object 
         ```
      - sample curl request:
         ```
            curl --location --request PATCH 'localhost:8000/auth/apikey' \
            --header 'Authorization: Bearer masterkey' \
            --header 'Content-Type: application/json' \
            --data '{
               "key": "{apikey}",
               "delta": {
                  "name": "update",
                  "meta": {
                     "org_id": 2
                  }
               }
            }'
         ```
   3. DELETE `/auth/apikey`:
      - delete apikey
      - body:
         ```
            key: api token
         ```
      - sample curl request:
         ```
            curl --location --request DELETE 'localhost:8000/auth/apikey' \
            --header 'Authorization: Bearer masterkey' \
            --header 'Content-Type: application/json' \
            --data '{
               "key": "{apikey}",
            }'
         ```
   4. GET `/auth/apikey`
      - get list of apikeys based on metadata
      - pass each field of meta data as query param
      - sample curl request:
         ```
            curl --location --request GET 'localhost:8000/auth/apikey?org_id=1' \
            --header 'Authorization: Bearer masterkey' \
            --header 'Content-Type: application/json' \
         ```
   5. GET `/auth/apikey/details`
      - get apikey info
      - pass api token in API_KEY header
      - sample curl request:
         ```
            curl --location --request GET 'localhost:8000/auth/apikey?org_id=1' \
            --header 'Authorization: Bearer masterkey' \
            --header 'API_KEY: {api token}' \
            --header 'Content-Type: application/json' \
         ```
   6. POST `/auth/apikey/invalidate`:
      - invalidate an api token
      - body:
         ```
            key: api token
         ```
      - sample curl request:
         ```
            curl --location 'localhost:8000/auth/apikey' \
            --header 'Authorization: Bearer masterkey' \
            --header 'Content-Type: application/json' \
            --data '{
               "key": "{apikey}",
            }'
         ```
### S3 File uploads

   1. POST `/source/s3`:
      - upload a csv/parquet
      - body:
         ```
            path: string
         ```
      - valid pat: s3://{bucket_name}/{path_to_file}
      - sample request:
         ```
         curl --location 'localhost:8000/source/s3' \
         --header 'Authorization: Bearer masterkey' \
         --header 'Content-Type: application/json' \
         --data '{
             "path": "s3://gopie/aqi.csv",
             "table_name":"gp_WcMmocuYox1k"
         }'
         ```
   2. POST `/source/s3`
      - update a table (uploaded file)
      - this is an upsert operation.
         - if exists deletes and replaces it with new file
         - else creates an new file with give table_name
      - body:
         ```
            path: string (path to new file)
            table_name: string
         ```
      - sample curl request:
         ```
            curl --location --request PUT 'localhost:8000/source/s3' \
            --header 'Authorization: Bearer masterkey' \
            --header 'Content-Type: application/json' \
            --data '{
                "path": "s3://gopie/aqi.csv",
                "table_name":"gp_WcMmocuYox1k"
            }'
         ```
         
   3. DELETE `/source/s3`
      - delete a table
      - body:
         ```
            table_name: string
         ```
      - sample curl request:
         ```
            curl --location --request DELETE 'localhost:8000/source/s3' \
            --header 'Authorization: Bearer masterkey' \
            --header 'Content-Type: application/json' \
            --data '{
                "table_name":"gp_WcMmocuYox1k"
            }'
         ```
### Gopie query apis

   1. GET `/api/{table_name}`:

      - To query a dataset using query parameters in gopie, you can send a GET request to the /api/tables/{table_name} endpoint, where table_name is the name of the dataset you want to query. You can then specify the query operators in the URL query parameters.
      - For example, the following request will return the first 10 rows of the customers dataset, sorted in ascending order by the last_name column:
      ```
         /api/tables/customers?sort=last_name&limit=10"
      ```

      - You can also use the filter parameter to specify a filter condition. For example, the following request will return all rows from the customers dataset where the first_name column is equal to John:
      ```
         /api/tables/customers?filter[first_name]=John"
      ```

      - You can use the page and limit parameters to paginate the results. For example, the following request will return the second page of results, where each page contains 10 rows:
      ```
         /api/tables/customers?page=2&limit=10"
      ```


      - The /api/tables/{table_name} endpoint supports the following query parameters:
          1. columns: specifies which columns of the dataset to include in the response.

          2. sort: specifies the order in which the rows of the dataset should be sorted. This parameter can be used to sort the rows in ascending or descending order by one or more columns.

          3. limit: specifies the maximum number of rows to include in the response.

          4. filter: specifies a condition that rows must satisfy in order to be included in the response.

          5. page: specifies which page of the dataset to include in the response, when pagination is used. For example, to sort the rows of the dataset by the col1 and col2 columns in ascending and descending order, respectively, and return only the first 100 rows, the query might look like this:

      - Sample for sorting and limiting
      ```
         /api/tables/{table_name}?sort=col1,-col2&limit=100
      ```

      - These query parameters can be combined in various ways to retrieve the desired subset of the dataset.
      - sample curl request: 
         ```
            curl --location --globoff 'localhost:8003/api/tables/gp_hw9NPJ4qX60c?filter[aqi_value]=214' \
            --header 'Authorization: Bearer gpWGhScTNSVXhickZJUFg.cjYLHkBb5JtjY6rqQBDVN2cwZYWoRj3EonNl_A'
         ```
   2. POST `/api/sql`:
      - query a dataset with sql
      - body: 
         ```
            query: "select * from {table_name}"
         ```
      - sample curl request:
         ```
            curl --location 'localhost:8000/api/sql' \
            --header 'Authorization: Bearer gpMktybXZURU0zc2N3YWs.xXkhQDoZT9YDT5RWRsZ1bKH9Ldl8tFBjycHv8g' \
            --header 'Content-Type: application/json' \
            --data '{

                "query":"select * from {table_name}"
            }'
         ```
   3. GET `/api/schema/{table_name}`
      - returns the schema of the dataset
      - sample curl request:
         ```
            curl --location 'localhost:8003/api/schema/gp_hw9NPJ4qX60c' \
            --header 'Authorization: Bearer gpWGhScTNSVXhickZJUFg.cjYLHkBb5JtjY6rqQBDVN2cwZYWoRj3EonNl_A'
         ```
   4. POST `/api/nl2sql`:
      - returns a sql for the passed natural language query
      - body: 
         ```
            query: string
            table_name: string
         ```
      - sample curl request:
         ```
            curl --location 'localhost:8000/api/nl2sql' \
            --header 'Authorization: Bearer gpMktybXZURU0zc2N3YWs.xXkhQDoZT9YDT5RWRsZ1bKH9Ldl8tFBjycHv8g' \
            --header 'Content-Type: application/json' \
            --data '{

                "query":"get all data",
                "table_name":"gp_olOdJwwhdoSg"
            }'
         ```
   5. GET `/api/health`:
      - check health of the application

## Troubleshooting

- If you encounter issues with database connections, ensure the `DUCKDB_DSN` path is correct and the directory exists.
- For S3 storage issues, verify that MinIO is running and the S3 credentials in `config.env` are correct.

## Additional Notes

- The server can be set to read-only mode by setting `SERVER_READ_ONLY=true` in the config.
- Adjust the `DUCKDB_MEMORY_LIMIT` as needed for your system's capabilities.
