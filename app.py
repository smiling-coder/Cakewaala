import os, re, uuid, secrets, time
from datetime import datetime, date
from functools import wraps
from flask import Flask, jsonify, request, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()
FRONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
STATUSES = ["Pending", "Confirmed", "Preparing", "Out for delivery", "Delivered", "Cancelled"]

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(20), default="piece")
    image_url = db.Column(db.String(255), default="")
    category = db.Column(db.String(60), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return dict(id=self.id, name=self.name, description=self.description, price=float(self.price),
                    unit=self.unit, image_url=self.image_url, category=self.category, is_available=self.is_available)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    address = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(24), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(10), nullable=False)
    payment_status = db.Column(db.String(10), default="pending")  # only admin sets "paid"
    order_status = db.Column(db.String(20), default="Pending")
    delivery_date = db.Column(db.Date, nullable=False)
    delivery_time = db.Column(db.String(5), nullable=False)
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer = db.relationship("Customer")
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")
    def to_dict(self, full=False):
        d = dict(order_number=self.order_number, total_amount=float(self.total_amount), payment_method=self.payment_method,
                 payment_status=self.payment_status, order_status=self.order_status,
                 delivery_date=self.delivery_date.isoformat(), delivery_time=self.delivery_time, notes=self.notes,
                 created_at=self.created_at.isoformat(), customer_name=self.customer.name,
                 items=[dict(name=i.product_name_snapshot, unit_price=float(i.unit_price), quantity=i.quantity,
                             subtotal=float(i.subtotal)) for i in self.items])
        if full:
            d.update(id=self.id, phone=self.customer.phone, address=self.customer.address)
        return d

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="SET NULL"), nullable=True)
    product_name_snapshot = db.Column(db.String(120), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)

# SAMPLE DATA. Only the starred prices come from the shop's public listing; owner must update the rest in /admin.html
SEED = [
 ("Chocolate Decadence Cake", "Rich layered chocolate cake.", 950, "kg", "/images/display.jpg", "Cakes"),
 ("Red Velvet Gateaux", "Red velvet with cream and chocolate chips.", 1100, "kg", "/images/red-velvet.jpg", "Cakes"),
 ("Caramel Crunch Cake", "Caramel and crunchy praline layers.", 1250, "kg", "/images/cakes-case.jpg", "Cakes"),
 ("Gems KitKat Cake", "Chocolate cake ringed with KitKat, topped with Gems. (sample price)", 1000, "kg", "/images/kitkat-gems.jpg", "Designer Cakes"),
 ("Anniversary Heart Cake", "Heart-shaped cream cake with a custom message. (sample price)", 900, "kg", "/images/heart.jpg", "Designer Cakes"),
 ("Theme Cake (Boss Baby style)", "Fondant theme cake for kids' birthdays. (sample price)", 1500, "kg", "/images/boss-baby.jpg", "Designer Cakes"),
 ("Two-Tier Rose Cake", "Two tiers with buttercream roses. (sample price)", 1400, "kg", "/images/rose-red.jpg", "Designer Cakes"),
 ("Pink Pearl Two-Tier Cake", "Pink finish, silver pearls, sugar flowers. (sample price)", 1600, "kg", "/images/pink-tier.jpg", "Designer Cakes"),
 ("Three-Tier Rose Cake", "Celebration cake for big occasions. (sample price)", 1500, "kg", "/images/rose-tier.jpg", "Designer Cakes"),
 ("White Chocolate Donut", "Soft donut with white chocolate.", 100, "piece", "/images/counter.jpg", "Bakery & Snacks"),
]

def create_app(cfg=None):
    app = Flask(__name__, static_folder=None)
    prod = os.environ.get("PRODUCTION") == "1"
    if prod and not os.environ.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is required in production")
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-not-secret"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///cakewala.db").replace("postgres://", "postgresql://"),
        WHATSAPP_NUMBER=os.environ.get("WHATSAPP_NUMBER", "919740730548"),
        ADMIN_USERNAME=os.environ.get("ADMIN_USERNAME"), ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD"),
        UPLOAD_DIR=os.environ.get("UPLOAD_DIR", os.path.join(FRONT, "uploads")),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=prod,
        MAX_CONTENT_LENGTH=4 * 1024 * 1024)
    if cfg: app.config.update(cfg)
    db.init_app(app)
    with app.app_context():
        db.create_all()
        if not Product.query.count():
            for n, d, p, u, i, c in SEED:
                db.session.add(Product(name=n, description=d, price=p, unit=u, image_url=i, category=c))
        u, pw = app.config["ADMIN_USERNAME"], app.config["ADMIN_PASSWORD"]
        if u and pw and not Admin.query.filter_by(username=u).first():
            db.session.add(Admin(username=u, password_hash=generate_password_hash(pw)))
        db.session.commit()

    fails = {}
    def admin_required(f):
        @wraps(f)
        def w(*a, **k):
            if not session.get("admin"): return jsonify(error="unauthorized"), 401
            if request.method != "GET" and request.headers.get("X-CSRF-Token") != session.get("csrf"):
                return jsonify(error="invalid CSRF token"), 403
            return f(*a, **k)
        return w

    @app.get("/api/config")
    def config():
        return jsonify(whatsapp=app.config["WHATSAPP_NUMBER"], shop="Cakewala Bakery & Sweets", phone="+91 97407 30548")

    @app.get("/api/products")
    def products():
        return jsonify([p.to_dict() for p in Product.query.order_by(Product.id)])

    @app.get("/api/products/<int:pid>")
    def product(pid):
        return jsonify(db.get_or_404(Product, pid).to_dict())

    @app.post("/api/orders")
    def create_order():
        d = request.get_json(silent=True) or {}
        name, addr = str(d.get("name", "")).strip(), str(d.get("address", "")).strip()
        phone = re.sub(r"[\s-]", "", str(d.get("phone", "")))
        pm, tm = d.get("payment_method", "COD"), str(d.get("delivery_time", ""))
        errs = []
        if not 2 <= len(name) <= 80: errs.append("name")
        if not re.fullmatch(r"(\+91)?[6-9]\d{9}", phone): errs.append("phone")
        if len(addr) < 5: errs.append("address")
        if pm not in ("COD", "UPI"): errs.append("payment_method")
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", tm): errs.append("delivery_time")
        try:
            dd = datetime.strptime(str(d.get("delivery_date", "")), "%Y-%m-%d").date()
            if dd < date.today(): errs.append("delivery_date")
        except ValueError:
            errs.append("delivery_date")
        qty = {}
        for it in d.get("items") or []:
            try:
                q = int(it["quantity"]); pid = int(it["id"])
            except (KeyError, TypeError, ValueError):
                errs.append("items"); continue
            if not 1 <= q <= 50: errs.append("items")
            qty[pid] = qty.get(pid, 0) + q
        if not qty: errs.append("items")
        if errs: return jsonify(error="invalid input", fields=sorted(set(errs))), 400
        lines, total = [], 0
        for pid, q in qty.items():
            p = db.session.get(Product, pid)
            if not p or not p.is_available: return jsonify(error=f"product {pid} unavailable"), 400
            lines.append((p, q)); total += p.price * q  # price always from DB
        c = Customer(name=name, phone=phone, address=addr); db.session.add(c); db.session.flush()
        o = Order(order_number="CW" + datetime.utcnow().strftime("%y%m%d") + secrets.token_hex(3).upper(),
                  customer_id=c.id, total_amount=total, payment_method=pm, delivery_date=dd,
                  delivery_time=tm, notes=str(d.get("notes", ""))[:500])
        for p, q in lines:
            o.items.append(OrderItem(product_id=p.id, product_name_snapshot=p.name, unit_price=p.price,
                                     quantity=q, subtotal=p.price * q))
        db.session.add(o); db.session.commit()
        return jsonify(o.to_dict()), 201

    @app.get("/api/orders/<number>")
    def get_order(number):
        o = Order.query.filter_by(order_number=number).first_or_404()
        return jsonify(o.to_dict())

    @app.post("/api/admin/login")
    def login():
        ip, now = request.remote_addr, time.time()
        fails[ip] = [t for t in fails.get(ip, []) if now - t < 600]
        if len(fails[ip]) >= 5: return jsonify(error="too many attempts, try later"), 429
        d = request.get_json(silent=True) or {}
        a = Admin.query.filter_by(username=str(d.get("username", ""))).first()
        if not a or not check_password_hash(a.password_hash, str(d.get("password", ""))):
            fails[ip].append(now); return jsonify(error="invalid credentials"), 401
        session.clear(); session["admin"] = a.id; session["csrf"] = secrets.token_hex(16)
        return jsonify(csrf=session["csrf"])

    @app.post("/api/admin/logout")
    @admin_required
    def logout():
        session.clear(); return jsonify(ok=True)

    @app.get("/api/admin/session")
    def sess():
        return (jsonify(csrf=session["csrf"]), 200) if session.get("admin") else (jsonify(error="unauthorized"), 401)

    @app.get("/api/admin/stats")
    @admin_required
    def stats():
        sales = db.session.query(db.func.sum(Order.total_amount)).filter_by(payment_status="paid").scalar() or 0
        return jsonify(total=Order.query.count(), pending=Order.query.filter_by(order_status="Pending").count(),
                       completed=Order.query.filter_by(order_status="Delivered").count(),
                       sales_paid=float(sales), products=Product.query.count())

    @app.get("/api/admin/orders")
    @admin_required
    def a_orders():
        q = Order.query.join(Customer)
        if request.args.get("status"): q = q.filter(Order.order_status == request.args["status"])
        if request.args.get("q"):
            s = f"%{request.args['q']}%"
            q = q.filter(db.or_(Order.order_number.ilike(s), Customer.name.ilike(s), Customer.phone.ilike(s)))
        return jsonify([o.to_dict(True) for o in q.order_by(Order.id.desc()).limit(200)])

    @app.patch("/api/admin/orders/<int:oid>")
    @admin_required
    def a_order_patch(oid):
        o, d = db.get_or_404(Order, oid), request.get_json(silent=True) or {}
        if "order_status" in d:
            if d["order_status"] not in STATUSES: return jsonify(error="bad status"), 400
            o.order_status = d["order_status"]
        if "payment_status" in d:  # manual confirmation by owner only
            if d["payment_status"] not in ("pending", "paid"): return jsonify(error="bad payment status"), 400
            o.payment_status = d["payment_status"]
        db.session.commit(); return jsonify(o.to_dict(True))

    def save_image():
        f = request.files.get("image")
        if not f or not f.filename: return None
        ext = f.filename.rsplit(".", 1)[-1].lower()
        if ext not in ("jpg", "jpeg", "png", "webp"): raise ValueError("image must be jpg, png or webp")
        os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
        fn = uuid.uuid4().hex + "." + ext
        f.save(os.path.join(app.config["UPLOAD_DIR"], fn))
        return "/uploads/" + fn

    def apply(p):
        d = request.form if request.form else (request.get_json(silent=True) or {})
        for k in ("name", "description", "unit", "category"):
            if k in d: setattr(p, k, str(d[k]).strip())
        if "price" in d:
            pr = float(d["price"])
            if pr <= 0: raise ValueError("price must be positive")
            p.price = pr
        if "is_available" in d: p.is_available = str(d["is_available"]).lower() in ("1", "true", "on")
        img = save_image()
        if img: p.image_url = img
        if not p.name or not p.category: raise ValueError("name and category required")

    @app.post("/api/admin/products")
    @admin_required
    def a_prod_add():
        p = Product(price=1, name="", category="")
        try: apply(p)
        except (ValueError, TypeError) as e: return jsonify(error=str(e)), 400
        db.session.add(p); db.session.commit(); return jsonify(p.to_dict()), 201

    @app.put("/api/admin/products/<int:pid>")
    @admin_required
    def a_prod_put(pid):
        p = db.get_or_404(Product, pid)
        try: apply(p)
        except (ValueError, TypeError) as e: return jsonify(error=str(e)), 400
        db.session.commit(); return jsonify(p.to_dict())

    @app.delete("/api/admin/products/<int:pid>")
    @admin_required
    def a_prod_del(pid):
        db.session.delete(db.get_or_404(Product, pid)); db.session.commit()  # order history keeps name/price snapshots
        return jsonify(ok=True)

    @app.errorhandler(404)
    def nf(e): return (jsonify(error="not found"), 404) if request.path.startswith("/api/") else ("Not found", 404)

    @app.get("/uploads/<path:p>")
    def uploads(p): return send_from_directory(app.config["UPLOAD_DIR"], p)

    @app.get("/")
    def home(): return send_from_directory(FRONT, "index.html")

    @app.get("/<path:p>")
    def static_files(p): return send_from_directory(FRONT, p)

    return app

app = create_app() if os.environ.get("FLASK_RUN_FROM_CLI") or __name__ != "__main__" else None
if __name__ == "__main__":
    create_app().run(debug=os.environ.get("PRODUCTION") != "1")
