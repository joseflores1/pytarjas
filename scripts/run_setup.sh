#!/bin/bash
# scripts/run_setup.sh

# --- Production Ready Setup Script ---
# This script initializes the database schema and demo data.
# It dynamically extracts credentials from environment variables to avoid hardcoding.

# Function to safely parse the connection URI using Python
get_db_config() {
    python3 <<EOF
from urllib.parse import urlparse, unquote
import os
uri = os.getenv('SQLALCHEMY_DATABASE_URI')
if uri:
    p = urlparse(uri)
    if '$1' == 'username':
        print(unquote(p.username or ''))
    elif '$1' == 'password':
        print(unquote(p.password or ''))
    elif '$1' == 'hostname':
        print(unquote(p.hostname or ''))
    elif '$1' == 'port':
        print(p.port or '5432')
    elif '$1' == 'dbname':
        # Remove the leading slash from the path to get the DB name
        print(unquote(p.path[1:]))
EOF
}

# Determine if we use environment variables or local defaults
if [ -n "$SQLALCHEMY_DATABASE_URI" ]; then
    echo "Configuring database connection from SQLALCHEMY_DATABASE_URI..."
    DB_USER=$(get_db_config "username")
    DB_PASS=$(get_db_config "password")
    DB_HOST=$(get_db_config "hostname")
    DB_PORT=$(get_db_config "port")
    DB_NAME=$(get_db_config "dbname")
else
    echo "WARNING: SQLALCHEMY_DATABASE_URI not set. Using local development defaults."
    DB_NAME="pytarjas"
    DB_USER="josei"
    DB_PASS="03e+_U#hS9AT"
    DB_HOST="localhost"
    DB_PORT="5432"
fi

# File paths relative to the project root
SQL_DELETE="scripts/delete_tables.sql"
PYTHON_USER_CREATE="scripts/create_users.py" 
SQL_OBJECTS_CREATE="scripts/create_objects.sql" 

# Export the password so psql does not prompt for manual input
export PGPASSWORD="$DB_PASS"

# Helper function to check for errors and halt execution
check_error() {
    if [ $? -ne 0 ]; then
        echo "ERROR: Step $1 failed. Aborting script execution."
        unset PGPASSWORD
        exit 1
    fi
}

echo "--- 1. Cleaning Database (Dropping Tables) ---"
# Azure Database for PostgreSQL requires host (-h) and port (-p) flags for remote access
psql -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -U "$DB_USER" -f "$SQL_DELETE" -v ON_ERROR_STOP=1
check_error "Cleanup"

echo "--- 2. Creating Schema and Initial Users ---"
# This script uses SQLAlchemy and will pick up the production config automatically via APP_ENV
python3 "$PYTHON_USER_CREATE"
check_error "User/Schema Creation"

echo "--- 3. Inserting Demo Forms, Templates, and Objects ---"
psql -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -U "$DB_USER" -f "$SQL_OBJECTS_CREATE" -v ON_ERROR_STOP=1
check_error "Objects Creation"

echo "--- Setup finished successfully. ---"

# Security: Remove the sensitive password from the environment variables
unset PGPASSWORD