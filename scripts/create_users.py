from pytarjas import create_app
from pytarjas.models.user_models import db, Admin, Worker, Planner, Client

app = create_app()

with app.app_context():
    admin=Admin(
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    admin.set_user_password(admin, "admin123")
    db.session.add(admin)

    worker=Worker(
        username="worker",
        email="worker@example.com",
        role="worker",
    )
    admin.set_user_password(worker, "worker123")
    db.session.add(worker)

    planner=Planner(
        username="planner",
        email="planner@example.com",
        role="planner",
    )
    admin.set_user_password(planner, "planner123")
    db.session.add(planner)

    client=Client(
        username="client",
        email="client@example.com",
        role="client",
    )

    admin.set_user_password(client, "client123")
    db.session.add(client)


    db.session.commit()
    print(f"Created admin: {admin.username}")
    print(f"Created worker: {worker.username}")
    print(f"Created planner: {planner.username}")
    print(f"Created client: {client.username}")