#!/bin/bash
set -e
set -u

echo "Multiple database creation requested: $POSTGRES_MULTIPLE_DATABASES"

for db in $(echo "$POSTGRES_MULTIPLE_DATABASES" | tr ',' ' '); do
    echo "Creating user and database '$db'"
    
    # Create user
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --command "CREATE USER $db WITH PASSWORD '$db' CREATEDB;"
    
    # Create database
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --command "CREATE DATABASE $db OWNER $db;"
    
    echo "Created user and database '$db'"
done

echo "Multiple databases created"

