#!/bin/bash
# scripts/run_setup.sh

# --- Production Ready Setup Script ---
# This script initializes the database schema and demo data.
# It uses Python to execute SQL files to avoid dependencies on external tools like psql.

# Ensure the root project directory is in the PYTHONPATH
# This prevents ModuleNotFoundError: No module named 'pytarjas'
export PYTHONPATH=$PYTHONPATH:.

# Determine the database connection string
if [ -n "$SQLALCHEMY_DATABASE_URI" ]; then
    echo "Configuring database connection from SQLALCHEMY_DATABASE_URI..."
    DATABASE_URL="$SQLALCHEMY_DATABASE_URI"
else
    echo "WARNING: SQLALCHEMY_DATABASE_URI not set. Using local development defaults."
    DATABASE_URL="postgresql://josei:03e+_U#hS9AT@localhost:5432/pytarjas"
fi

# File paths relative to the project root
SQL_DELETE="scripts/delete_tables.sql"
PYTHON_USER_CREATE="scripts/create_users.py" 
SQL_OBJECTS_CREATE="scripts/create_objects.sql" 

# Helper function to check for errors and halt execution
check_error() {
    if [ $? -ne 0 ]; then
        echo "ERROR: Step $1 failed. Aborting script execution."
        exit 1
    fi
}

# Helper function to execute a SQL file using SQLAlchemy
# This replaces the need for the 'psql' command line tool
execute_sql() {
    local file_path=$1
    echo "Running SQL: $file_path"
    
    python3 - <<EOF
import sys
from sqlalchemy import create_engine, text

db_uri = "$DATABASE_URL"
file_to_run = "$file_path"

if not db_uri:
    print("Error: No database URI provided.")
    sys.exit(1)

try:
    # Initialize engine using the project's URI
    engine = create_engine(db_uri)
    with engine.connect() as connection:
        with open(file_to_run, 'r') as f:
            sql_content = f.read()
            # Wrap in text() to ensure SQLAlchemy handles raw SQL strings correctly
            # especially for DO blocks and complex inserts
            connection.execute(text(sql_content))
            connection.commit()
    print(f"Successfully executed {file_to_run}")
except Exception as e:
    print(f"Failed to execute {file_to_run}: {e}")
    sys.exit(1)
EOF
}

echo "--- 1. Cleaning Database (Dropping Tables) ---"
execute_sql "$SQL_DELETE"
check_error "Cleanup"

echo "--- 2. Creating Schema and Initial Users ---"
# This script uses SQLAlchemy and will pick up the production config automatically
python3 "$PYTHON_USER_CREATE"
check_error "User/Schema Creation"

echo "--- 3. Inserting Demo Forms, Templates, and Objects ---"
execute_sql "$SQL_OBJECTS_CREATE"
check_error "Objects Creation"

echo "--- Setup finished successfully. ---"