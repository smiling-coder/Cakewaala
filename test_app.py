from datetime import date, timedelta
import pytest
from app import create_app

@pytest.fixture
def c():
    a = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "ADMIN_USERNAME": "owner", "ADMIN_PASSWORD": "pw12345!"})
    return a.test_client()

def order(c, items, **kw):
    b = dict(name="Asha", phone="9876543210", address="Desai Circle, Jamkhandi", payment_method="COD",
             delivery_date=(date.today() + timedelta(days=2)).isoformat(), delivery_time="16:30", items=items)
    b.update(kw); return c.post("/api/orders", json=b)

def test_products(c):
    assert len(c.get("/api/products").json) >= 5

def test_price_from_db_and_status(c):
    r = order(c, [{"id": 1, "quantity": 2}], price=1, total_amount=1)
    assert r.status_code == 201 and r.json["total_amount"] == 1900 and r.json["payment_status"] == "pending"

def test_invalid_orders(c):
    assert order(c, []).status_code == 400
    assert order(c, [{"id": 1, "quantity": 1}], phone="123").status_code == 400
    assert order(c, [{"id": 1, "quantity": 1}], delivery_date="2020-01-01").status_code == 400
    assert order(c, [{"id": 999, "quantity": 1}]).status_code == 400

def test_admin_auth_and_status(c):
    assert c.get("/api/admin/orders").status_code == 401
    assert c.post("/api/admin/login", json={"username": "owner", "password": "bad"}).status_code == 401
    t = c.post("/api/admin/login", json={"username": "owner", "password": "pw12345!"}).json["csrf"]
    oid = c.get("/api/admin/orders").json
    order(c, [{"id": 1, "quantity": 1}]); oid = c.get("/api/admin/orders").json[0]["id"]
    assert c.patch(f"/api/admin/orders/{oid}", json={"order_status": "Confirmed"}).status_code == 403  # no CSRF
    r = c.patch(f"/api/admin/orders/{oid}", json={"order_status": "Confirmed"}, headers={"X-CSRF-Token": t})
    assert r.json["order_status"] == "Confirmed"
