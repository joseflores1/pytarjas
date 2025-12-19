# scripts/create_users.py
from pytarjas import create_app
from pytarjas.models.user_models import db, User

app = create_app()

with app.app_context():
    # Recreate tables after delete_tables.sql runs
    db.create_all()
    print("Database schema created successfully.")

    # Create Admin
    admin = User(
        username="admin",
        email="admin@example.com",
        role="admin"
    )
    # Corrected method name based on your user_models.py
    admin.reset_password("admin123") 
    db.session.add(admin)

    # Create Worker
    worker = User(
        username="worker",
        email="worker@example.com",
        role="worker"
    )
    worker.reset_password("worker123")
    db.session.add(worker)

    # Create Planner
    planner = User(
        username="planner",
        email="planner@example.com",
        role="planner"
    )
    planner.reset_password("planner123")
    db.session.add(planner)

    # Create Client
    client = User(
        username="client",
        email="client@example.com",
        role="client"
    )
    client.reset_password("client123")
    db.session.add(client)

    db.session.commit()
    print(f"Created users: {admin.username}, {worker.username}, {planner.username}, {client.username}")