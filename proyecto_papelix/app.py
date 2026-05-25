from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

app = Flask(__name__, template_folder='.')
app.secret_key = "papelix_secret"

bcrypt = Bcrypt(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'brawlstarsycrow72@gmail.com'
app.config['MAIL_PASSWORD'] = 'brawlstars'
app.config['MAIL_DEFAULT_SENDER'] = 'brawlstarsycrow72@gmail.com'

mail = Mail(app)

serializer = URLSafeTimedSerializer(app.secret_key)

mongo_uri = 'mongodb+srv://alex1832847_db_user:PdqODxHEa19Qqp6w@cluster0.uxjjqpr.mongodb.net/'

client = MongoClient(mongo_uri)

db = client["papelix_db"]
users = db["usuarios"]
products = db["productos"]

@app.route("/")
def home():
    return render_template("inicio.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if users.find_one({"email": email}):
            flash("El correo ya existe", "error")
            return redirect(url_for("register"))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        users.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password
        })

        msg = Message('Registro en Papelix', recipients=[email], charset='utf-8')
        msg.body = f'Hola {name},\n\nTu cuenta en Papelix se ha creado correctamente. ¡Bienvenido!\n\nSaludos,\nEquipo Papelix'
        try:
            mail.send(msg)
            flash("Usuario creado en Papelix. Revisa tu correo electrónico.", "registered")
        except Exception as e:
            flash("Usuario creado correctamente, pero no se pudo enviar el correo: " + str(e), "error")
        return redirect(url_for("login"))

    return render_template("formulario.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = users.find_one({"email": email})

        if user and bcrypt.check_password_hash(user['password'], password):

            session["user"] = user["name"]
            return redirect(url_for("dashboard"))

        flash("Correo o contraseña incorrectos", "error")

    return render_template("inicio_de_sesion.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    productos_list = list(products.find())
    return render_template("dashboard.html", productos=productos_list, usuario=session.get("user"))

@app.route("/producto", methods=["POST"])
def add_producto():
    if "user" not in session:
        return redirect(url_for("login"))

    nombre = request.form.get("nombre", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    precio = request.form.get("precio", "").strip()
    stock = request.form.get("stock", "").strip()

    if not nombre or not precio or not stock:
        flash("Nombre, precio y stock son obligatorios.", "error")
        return redirect(url_for("dashboard"))

    try:
        producto = {
            "nombre": nombre,
            "descripcion": descripcion,
            "precio": float(precio),
            "stock": int(stock)
        }
        products.insert_one(producto)
        flash("Producto agregado correctamente.", "success")
    except ValueError:
        flash("El precio debe ser un número y el stock un entero.", "error")
    except Exception as e:
        flash("Error al guardar el producto: " + str(e), "error")

    return redirect(url_for("dashboard"))

@app.route("/producto/editar", methods=["POST"])
def editar_producto():
    if "user" not in session:
        return redirect(url_for("login"))

    producto_id = request.form.get("producto_id")
    if not producto_id:
        flash("Seleccione un producto antes de editar.", "error")
        return redirect(url_for("dashboard"))

    nombre = request.form.get("nombre_edit", "").strip()
    descripcion = request.form.get("descripcion_edit", "").strip()
    precio = request.form.get("precio_edit", "").strip()
    stock = request.form.get("stock_edit", "").strip()

    if not nombre or not precio or not stock:
        flash("Nombre, precio y stock son obligatorios.", "error")
        return redirect(url_for("dashboard"))

    try:
        products.update_one(
            {"_id": ObjectId(producto_id)},
            {"$set": {
                "nombre": nombre,
                "descripcion": descripcion,
                "precio": float(precio),
                "stock": int(stock)
            }}
        )
        flash("Producto actualizado correctamente.", "success")
    except ValueError:
        flash("El precio debe ser un número y el stock un entero.", "error")
    except Exception as e:
        flash("Error al actualizar el producto: " + str(e), "error")

    return redirect(url_for("dashboard"))

@app.route("/producto/eliminar/<string:producto_id>", methods=["POST"])
def eliminar_producto(producto_id):
    if "user" not in session:
        return redirect(url_for("login"))

    try:
        products.delete_one({"_id": ObjectId(producto_id)})
        flash("Producto eliminado correctamente.", "success")
    except Exception as e:
        flash("Error al eliminar el producto: " + str(e), "error")

    return redirect(url_for("dashboard"))

@app.route("/recuperar_contraseña/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)  # 1 hora
    except SignatureExpired:
        flash("El enlace de recuperación ha expirado", "error")
        return redirect(url_for("login"))
    except:
        flash("Enlace de recuperación inválido", "error")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        new_password = request.form["password"]
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        users.update_one({"email": email}, {"$set": {"password": hashed_password}})
        flash("Contraseña actualizada exitosamente", "success")
        return redirect(url_for("login"))
    
    return render_template("recuperar_contraseña.html")

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        user = users.find_one({"email": email})
        if user:
            token = serializer.dumps(email, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)
            
            msg = Message('Recuperación de contraseña - Papelix', recipients=[email], charset='utf-8')
            msg.body = f'Haz clic en el siguiente enlace para restablecer tu contraseña: {reset_url}'
            try:
                mail.send(msg)
                flash("Se ha enviado un enlace de recuperación a tu correo electrónico", "success")
            except Exception as e:
                flash("No se pudo enviar el correo de recuperación: " + str(e), "error")
        else:
            flash("No se encontró una cuenta con ese correo electrónico", "error")
        return redirect(url_for("login"))
    return render_template("olvido_contraseña.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)