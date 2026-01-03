# scripts/create_users.py
import os
from pytarjas import create_app
from pytarjas.models.user_models import db, User

app = create_app()

with app.app_context():
    # Recreate tables after delete_tables.sql runs
    db.create_all()
    print("Database schema created successfully.")

    # Fetch initial passwords from environment variables with safe defaults for dev
    admin_pw = os.getenv('INITIAL_ADMIN_PASSWORD', 'admin123')
    worker_pw = os.getenv('INITIAL_WORKER_PASSWORD', 'worker123')
    planner_pw = os.getenv('INITIAL_PLANNER_PASSWORD', 'planner123')
    client_pw = os.getenv('INITIAL_CLIENT_PASSWORD', 'client123')

    # Create Admin
    admin = User(
        username="admin",
        email="joseflores@alumnos.uai.cl",
        role="admin"
    )
    admin.reset_password(admin_pw) 
    db.session.add(admin)

    # Create Worker
    worker = User(
        username="worker",
        email="worker@example.com",
        role="worker"
    )
    worker.reset_password(worker_pw)
    db.session.add(worker)

    # Create Planner
    planner = User(
        username="planner",
        email="planner@example.com",
        role="planner"
    )
    planner.reset_password(planner_pw)
    db.session.add(planner)

    # Create Client
    client = User(
        username="client",
        email="client@example.com",
        role="client"
    )
    client.reset_password(client_pw)
    db.session.add(client)

    try:
        db.session.commit()
        print(f"Created users: {admin.username}, {worker.username}, {planner.username}, {client.username}")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating users: {e}")