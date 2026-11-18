# Cakewala Bakery & Sweets – Website
Flask + SQLAlchemy backend, vanilla HTML/CSS/JS frontend. Shop, cart, checkout (COD / manual UPI), WhatsApp ordering, admin panel (`/admin.html`).

## Run locally
```
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env   # then set the values below in your shell / host
python app.py            # http://127.0.0.1:5000
pytest
```
Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` once to create the owner account. `WHATSAPP_NUMBER` (country code, no +) is the only place the number is stored.

## API
GET /api/products, /api/products/<id>, /api/config · POST /api/orders · GET /api/orders/<order_number>
Admin (session + `X-CSRF-Token`): POST /api/admin/login, /logout · GET /api/admin/orders, /stats · PATCH /api/admin/orders/<id> · POST/PUT/DELETE /api/admin/products

## Deploy (Render / Railway)
`gunicorn app:app`, set `PRODUCTION=1`, `SECRET_KEY`, `ADMIN_*`, `WHATSAPP_NUMBER`. Use a hosted **PostgreSQL** `DATABASE_URL` (cloud disks are temporary). Uploaded images also need a persistent disk (`UPLOAD_DIR`) or Cloudinary. Serve over HTTPS.

## Notes
Seed products are SAMPLE data; only the Chocolate Decadence, Red Velvet and Caramel Crunch prices came from the shop's public listing. Update the rest in the admin panel. Opening WhatsApp never marks an order confirmed or paid; only the owner sets paid.
