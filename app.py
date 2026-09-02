
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
DB = BASE / "soleil_luxe.db"

app = Flask(__name__)
app.secret_key = __import__('os').environ.get('SECRET_KEY', 'soleil-luxe-demo')

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'Fragancia',
        price REAL NOT NULL DEFAULT 75000,
        stock INTEGER NOT NULL DEFAULT 0,
        min_stock INTEGER NOT NULL DEFAULT 5,
        active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        channel TEXT DEFAULT 'WhatsApp'
    );
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        total REAL NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES customers(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    );
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS collab_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT NOT NULL,
        client_company TEXT DEFAULT '',
        budget REAL DEFAULT 0,
        notes TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'Pendiente',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS collab_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES collab_orders(id) ON DELETE CASCADE,
        FOREIGN KEY(product_id) REFERENCES products(id)
    );
    """)
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO products(name,category,price,stock,min_stock) VALUES(?,?,?,?,?)",
            [
                ("Élite Noir", "Fragancia masculina", 75000, 18, 5),
                ("Lumière Femme", "Fragancia femenina", 75000, 12, 5),
                ("Royal Oud", "Fragancia unisex", 75000, 7, 4),
                ("Velvet Bloom", "Fragancia femenina", 75000, 3, 5),
                ("Imperial Essence", "Fragancia masculina", 75000, 9, 4),
            ]
        )

    catalog_seed = [
        ("Marrakech", "Amaderado · Vainilla Bourbon", 89000, 18, 4),
        ("New York", "Fougère aromático · Ambarado Oriental", 95000, 12, 4),
        ("Milan", "Naranja siciliana · Bergamota", 92000, 15, 4),
        ("Rome", "Cítrico · Lavandina", 88000, 10, 3),
        ("Soleil Star", "Haba Tonka · Vanille", 99000, 8, 3),
    ]
    for name,cat,price,stock,min_stock in catalog_seed:
        if not conn.execute("SELECT 1 FROM products WHERE name=?", (name,)).fetchone():
            conn.execute("INSERT INTO products(name,category,price,stock,min_stock) VALUES(?,?,?,?,?)", (name,cat,price,stock,min_stock))
    conn.commit()
    conn.close()

@app.context_processor
def inject_globals():
    return {"now": datetime.now()}

@app.route("/")
def dashboard():
    conn = db()
    products = conn.execute("SELECT * FROM products WHERE active=1 ORDER BY name").fetchall()
    customers = conn.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    sales = conn.execute("""
        SELECT s.*, p.name product_name, COALESCE(c.name,'Cliente ocasional') customer_name
        FROM sales s JOIN products p ON p.id=s.product_id
        LEFT JOIN customers c ON c.id=s.customer_id
        ORDER BY s.id DESC LIMIT 8
    """).fetchall()
    total_sales = conn.execute("SELECT COALESCE(SUM(total),0) FROM sales").fetchone()[0]
    total_expenses = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
    stock_units = conn.execute("SELECT COALESCE(SUM(stock),0) FROM products WHERE active=1").fetchone()[0]
    low_stock = conn.execute("SELECT COUNT(*) FROM products WHERE active=1 AND stock <= min_stock").fetchone()[0]
    conn.close()
    return render_template("dashboard.html", products=products, customers=customers, sales=sales,
                           total_sales=total_sales, total_expenses=total_expenses,
                           stock_units=stock_units, low_stock=low_stock)

@app.route("/inventory", methods=["GET","POST"])
def inventory():
    conn = db()
    if request.method == "POST":
        name = request.form["name"].strip()
        category = request.form.get("category","Fragancia")
        price = float(request.form["price"])
        stock = int(request.form["stock"])
        min_stock = int(request.form.get("min_stock",5))
        conn.execute("INSERT INTO products(name,category,price,stock,min_stock) VALUES(?,?,?,?,?)",
                     (name,category,price,stock,min_stock))
        conn.commit()
        conn.close()
        flash("Producto agregado al inventario.", "success")
        return redirect(url_for("inventory"))
    products = conn.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("inventory.html", products=products)

@app.post("/inventory/update/<int:pid>")
def inventory_update(pid):
    conn = db()
    stock = int(request.form["stock"])
    price = float(request.form["price"])
    min_stock = int(request.form["min_stock"])
    conn.execute("UPDATE products SET stock=?, price=?, min_stock=? WHERE id=?", (stock,price,min_stock,pid))
    conn.commit(); conn.close()
    flash("Inventario actualizado.", "success")
    return redirect(url_for("inventory"))

@app.route("/sales", methods=["GET","POST"])
def sales():
    conn = db()
    if request.method == "POST":
        pid = int(request.form["product_id"])
        qty = int(request.form["quantity"])
        cid = request.form.get("customer_id")
        cid = int(cid) if cid else None
        product = conn.execute("SELECT * FROM products WHERE id=? AND active=1", (pid,)).fetchone()
        if not product:
            flash("Producto no encontrado.", "error")
        elif qty <= 0 or qty > product["stock"]:
            flash(f"Stock insuficiente. Disponible: {product['stock']}.", "error")
        else:
            total = product["price"] * qty
            conn.execute("INSERT INTO sales(customer_id,product_id,quantity,total,created_at) VALUES(?,?,?,?,?)",
                         (cid,pid,qty,total,datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.execute("UPDATE products SET stock=stock-? WHERE id=?", (qty,pid))
            conn.commit()
            flash("Venta registrada y stock sincronizado automáticamente.", "success")
        conn.close()
        return redirect(url_for("sales"))
    products = conn.execute("SELECT * FROM products WHERE active=1 ORDER BY name").fetchall()
    customers = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
    sales = conn.execute("""
        SELECT s.*,p.name product_name,COALESCE(c.name,'Cliente ocasional') customer_name
        FROM sales s JOIN products p ON p.id=s.product_id
        LEFT JOIN customers c ON c.id=s.customer_id ORDER BY s.id DESC
    """).fetchall()
    conn.close()
    return render_template("sales.html", products=products, customers=customers, sales=sales)

@app.route("/customers", methods=["GET","POST"])
def customers():
    conn = db()
    if request.method == "POST":
        conn.execute("INSERT INTO customers(name,phone,channel) VALUES(?,?,?)",
                     (request.form["name"], request.form.get("phone",""), request.form.get("channel","WhatsApp")))
        conn.commit(); conn.close()
        flash("Cliente guardado.", "success")
        return redirect(url_for("customers"))
    customers = conn.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("customers.html", customers=customers)

@app.route("/finance", methods=["GET","POST"])
def finance():
    conn = db()
    if request.method == "POST":
        conn.execute("INSERT INTO expenses(description,amount,created_at) VALUES(?,?,?)",
                     (request.form["description"],float(request.form["amount"]),datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit(); conn.close()
        flash("Egreso registrado.", "success")
        return redirect(url_for("finance"))
    income = conn.execute("SELECT COALESCE(SUM(total),0) FROM sales").fetchone()[0]
    expenses = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
    rows = conn.execute("SELECT * FROM expenses ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("finance.html", income=income, expenses=expenses, balance=income-expenses, rows=rows)

@app.route("/reports")
def reports():
    conn = db()
    sales_by_product = conn.execute("""
        SELECT p.name, SUM(s.quantity) units, SUM(s.total) revenue
        FROM sales s JOIN products p ON p.id=s.product_id
        GROUP BY p.id ORDER BY revenue DESC
    """).fetchall()
    low = conn.execute("SELECT * FROM products WHERE active=1 AND stock <= min_stock ORDER BY stock").fetchall()
    conn.close()
    return render_template("reports.html", sales_by_product=sales_by_product, low=low)



PRODUCT_IMAGES = {
    "Marrakech": "/static/products/marrakech_front.png",
    "New York": "/static/products/new_york.png",
    "Milan": "/static/products/milan.png",
    "Rome": "/static/products/rome.png",
    "Soleil Star": "/static/products/soleil_star.png",
}

@app.route("/cliente")
def client_portal():
    conn=db()
    products=conn.execute("SELECT * FROM products WHERE active=1 ORDER BY id").fetchall()
    conn.close()
    return render_template("client.html", products=products, product_images=PRODUCT_IMAGES)

@app.route("/colaborativo")
def collaborative():
    conn=db()
    orders=conn.execute("""
      SELECT o.*, COALESCE(SUM(i.quantity),0) units, COALESCE(SUM(i.quantity*i.unit_price),0) total
      FROM collab_orders o LEFT JOIN collab_items i ON i.order_id=o.id
      GROUP BY o.id ORDER BY o.id DESC LIMIT 20
    """).fetchall()
    products=conn.execute("SELECT * FROM products WHERE active=1 ORDER BY name").fetchall()
    conn.close()
    return render_template("collaborative.html", orders=orders, products=products)

@app.post("/api/collab/order")
def create_collab_order():
    data=request.get_json(silent=True) or {}
    client=(data.get("client_name") or "").strip()
    company=(data.get("company") or "").strip()
    notes=(data.get("notes") or "").strip()
    budget=float(data.get("budget") or 0)
    items=data.get("items") or []
    if not client or not items:
        return jsonify({"ok":False,"error":"Indica tu nombre y selecciona al menos un producto."}),400
    conn=db(); now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur=conn.execute("INSERT INTO collab_orders(client_name,client_company,budget,notes,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                     (client,company,budget,notes,"Pendiente",now,now))
    oid=cur.lastrowid
    total=0
    for it in items:
        pid=int(it.get("product_id")); qty=int(it.get("quantity",0))
        p=conn.execute("SELECT id,price,stock FROM products WHERE id=? AND active=1",(pid,)).fetchone()
        if p and qty>0:
            conn.execute("INSERT INTO collab_items(order_id,product_id,quantity,unit_price) VALUES(?,?,?,?)",(oid,pid,qty,p['price']))
            total += p['price']*qty
    conn.commit(); conn.close()
    return jsonify({"ok":True,"order_id":oid,"total":total,"status":"Pendiente"})

@app.get("/api/collab/orders")
def collab_orders_api():
    conn=db()
    rows=conn.execute("""
      SELECT o.id,o.client_name,o.client_company,o.budget,o.notes,o.status,o.created_at,o.updated_at,
             COALESCE(SUM(i.quantity),0) units, COALESCE(SUM(i.quantity*i.unit_price),0) total
      FROM collab_orders o LEFT JOIN collab_items i ON i.order_id=o.id
      GROUP BY o.id ORDER BY o.id DESC LIMIT 20
    """).fetchall()
    data=[dict(r) for r in rows]
    conn.close(); return jsonify(data)

@app.post("/api/collab/orders/<int:oid>/status")
def update_collab_status(oid):
    status=(request.get_json(silent=True) or {}).get("status","Pendiente")
    allowed={"Pendiente","En análisis","Propuesta enviada","Aprobado","Cerrado"}
    if status not in allowed: return jsonify({"ok":False}),400
    conn=db(); conn.execute("UPDATE collab_orders SET status=?,updated_at=? WHERE id=?",(status,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),oid)); conn.commit(); conn.close()
    return jsonify({"ok":True})

@app.get("/api/collab/order/<int:oid>")
def collab_order_detail(oid):
    conn=db()
    o=conn.execute("SELECT * FROM collab_orders WHERE id=?",(oid,)).fetchone()
    items=conn.execute("SELECT i.*,p.name,p.category FROM collab_items i JOIN products p ON p.id=i.product_id WHERE i.order_id=?",(oid,)).fetchall()
    conn.close()
    if not o:return jsonify({"ok":False}),404
    return jsonify({"ok":True,"order":dict(o),"items":[dict(x) for x in items]})

@app.post("/api/lucy")
def lucy():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    page = (data.get("page") or "dashboard").strip()
    t = question.lower()
    import unicodedata
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")

    conn = db()

    # Contextual, data-aware help: Lucy can inspect current system data.
    low = conn.execute("SELECT name, stock, min_stock FROM products WHERE active=1 AND stock <= min_stock ORDER BY stock").fetchall()
    products = conn.execute("SELECT name, stock, price FROM products WHERE active=1 ORDER BY name").fetchall()
    recent = conn.execute("""
        SELECT s.id,p.name,s.quantity,s.total,s.created_at
        FROM sales s JOIN products p ON p.id=s.product_id
        ORDER BY s.id DESC LIMIT 5
    """).fetchall()
    income = conn.execute("SELECT COALESCE(SUM(total),0) FROM sales").fetchone()[0]
    expenses = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
    conn.close()

    destination = None
    if any(x in t for x in ["inventario","stock","existencia","producto","agotad"]):
        destination = "/inventory"
        if "bajo" in t or "alerta" in t:
            if low:
                names = ", ".join(f"{r['name']} ({r['stock']} uds.)" for r in low[:4])
                answer = f"Claro. En este momento tienes <b>{len(low)}</b> producto(s) en nivel bajo: <b>{names}</b>. Ve a <a href='/inventory'>Inventario</a> para ajustar existencias o el stock mínimo."
            else:
                answer = "Revisé el inventario y no hay productos por debajo de su stock mínimo. Puedes abrir <a href='/inventory'>Inventario</a> para consultar todos los productos."
        elif "actual" in t or "cuant" in t or "hay" in t:
            total_units = sum(r["stock"] for r in products)
            answer = f"Actualmente hay <b>{total_units}</b> unidades registradas en el inventario. Puedes ver el detalle en <a href='/inventory'>Inventario</a>."
        else:
            answer = "En <a href='/inventory'>Inventario</a> puedes agregar productos, modificar precio y existencias, y definir el stock mínimo. Si una existencia llega al mínimo, Lucy puede ayudarte a identificarla."
    elif any(x in t for x in ["venta","pedido","vender","despacho"]):
        destination = "/sales"
        answer = "Para registrar una venta: <b>1)</b> entra en Ventas, <b>2)</b> selecciona producto y cliente, <b>3)</b> indica cantidad y <b>4)</b> pulsa Registrar venta. Al guardarla, el sistema descuenta automáticamente las unidades del inventario."
    elif any(x in t for x in ["cliente","contacto","whatsapp","instagram"]):
        destination = "/customers"
        answer = "En <a href='/customers'>Clientes</a> puedes centralizar nombre, teléfono y canal principal. Esto ayuda a conservar la información que llega por WhatsApp o Instagram dentro del sistema."
    elif any(x in t for x in ["contabilidad","egreso","gasto","ingreso","resultado","dinero"]):
        destination = "/finance"
        answer = f"En <a href='/finance'>Contabilidad</a> puedes registrar egresos y consultar el resultado. Actualmente el sistema tiene ingresos por <b>${income:,.0f}</b>, egresos por <b>${expenses:,.0f}</b> y resultado de <b>${income-expenses:,.0f}</b>."
    elif any(x in t for x in ["reporte","indicador","meta","estadistica"]):
        destination = "/reports"
        answer = "En <a href='/reports'>Reportes</a> puedes consultar ventas por producto, alertas de inventario y los indicadores objetivo del proyecto."
    elif any(x in t for x in ["dashboard","inicio","principal"]):
        destination = "/"
        answer = "El <a href='/'>Dashboard</a> es el centro de control: resume ventas, inventario, egresos, resultado, últimas ventas y metas del proyecto."
    elif any(x in t for x in ["no entiendo","ayuda","como funciona","que hago","que puedes","hola"]):
        answer = "Estoy aquí para guiarte paso a paso. Puedo ayudarte con <b>Inventario, Ventas, Clientes, Contabilidad y Reportes</b>. También puedo revisar datos actuales del sistema, como productos con stock bajo o el resultado financiero."
    else:
        # Page-aware fallback.
        page_names = {
            "inventory":"Inventario", "sales":"Ventas", "customers":"Clientes",
            "finance":"Contabilidad", "reports":"Reportes", "dashboard":"Dashboard"
        }
        section = page_names.get(page, "esta sección")
        answer = f"Estás en <b>{section}</b>. Puedo explicarte qué hace esta sección, qué botón usar o cómo completar un proceso. Prueba con una pregunta como “¿qué hago aquí?” o “¿cómo registro una venta?”."

    return jsonify({"answer": answer, "destination": destination})

@app.get("/api/products")
def api_products():
    conn = db()
    rows = conn.execute("SELECT id,name,price,stock FROM products WHERE active=1 ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

init_db()

if __name__ == "__main__":
    app.run(debug=True)
