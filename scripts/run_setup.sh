#!/bin/bash

# --- Configuration ---
# Your provided PostgreSQL credentials
DB_NAME="pytarjas"
DB_USER="josei"
DB_PASS="03e+_U#hS9AT" 

# File paths (CORRECTED: Added 'scripts/' prefix based on file tree)
SQL_DELETE="scripts/delete_tables.sql"
PYTHON_USER_CREATE="scripts/create_users.py" 
SQL_FORM_CREATE="scripts/create_form.sql" 

# Set the PGPASSWORD environment variable for psql
export PGPASSWORD="$DB_PASS"

# Function to check for errors and abort the sequence
check_error() {
    if [ $? -ne 0 ]; then
        echo "ERROR: Step $1 failed. Aborting sequence."
        # Clean up PGPASSWORD before exiting
        unset PGPASSWORD
        exit 1
    fi
}

# ------------------------------------------------------------------
# --- 1. Execute SQL to delete tables (Cleanup) ---
echo "--- 1. Executing SQL: $SQL_DELETE ---"
psql -d "$DB_NAME" -U "$DB_USER" -f "$SQL_DELETE" -v ON_ERROR_STOP=1
check_error 1
echo "Table deletion completed."

# ------------------------------------------------------------------
# --- 2. Execute Python script to create users/initial data ---
echo "--- 2. Executing Python: $PYTHON_USER_CREATE ---"
# Note: You may need to activate your virtual environment (venv) here.
# Example: source /path/to/venv/bin/activate
python3 "$PYTHON_USER_CREATE"
check_error 2
echo "User creation completed."

# ------------------------------------------------------------------
# --- 3. Execute SQL to create template form ---
echo "--- 3. Executing SQL: $SQL_FORM_CREATE ---"
psql -d "$DB_NAME" -U "$DB_USER" -f "$SQL_FORM_CREATE" -v ON_ERROR_STOP=1
check_error 3
echo "Form template creation completed."

# ------------------------------------------------------------------
echo "--- Setup sequence finished successfully. ---"

# Clear PGPASSWORD from the environment
unset PGPASSWORD