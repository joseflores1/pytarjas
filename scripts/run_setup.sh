#!/bin/bash
# scripts/run_setup.sh

# --- Configuration ---
DB_NAME="pytarjas"
DB_USER="josei"
DB_PASS="03e+_U#hS9AT" 

# File paths
SQL_DELETE="scripts/delete_tables.sql"
PYTHON_USER_CREATE="scripts/create_users.py" 
SQL_FORM_CREATE="scripts/create_form.sql" 

export PGPASSWORD="$DB_PASS"

check_error() {
    if [ $? -ne 0 ]; then
        echo "ERROR: Step $1 failed. Aborting."
        unset PGPASSWORD
        exit 1
    fi
}

echo "--- 1. Cleaning Database (Dropping Tables) ---"
psql -d "$DB_NAME" -U "$DB_USER" -f "$SQL_DELETE" -v ON_ERROR_STOP=1
check_error "Cleanup"

echo "--- 2. Creating Schema and Users ---"
# Ensure you are in the root directory so 'import pytarjas' works
python3 "$PYTHON_USER_CREATE"
check_error "User/Schema Creation"

echo "--- 3. Inserting Demo Versioned Form ---"
psql -d "$DB_NAME" -U "$DB_USER" -f "$SQL_FORM_CREATE" -v ON_ERROR_STOP=1
check_error "Form Creation"

echo "--- Setup finished successfully. ---"
unset PGPASSWORD