import io
from tkinter.font import Font
import bcrypt
import openpyxl
import psycopg2
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle  # Importación corregida
from reportlab.pdfgen import canvas
from flask import Flask, render_template, request, redirect, send_file, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2


load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

UPLOAD_FOLDER = 'static/images'  # Carpeta para guardar imágenes
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#pdf y excel
def obtener_datos_tabla(nombre_tabla):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f'SELECT * FROM {nombre_tabla};')
        datos = cur.fetchall()
        encabezados = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
        return encabezados, datos

def generar_reporte_excel(encabezados, datos, nombre_archivo):
        libro = openpyxl.Workbook()
        hoja = libro.active

        # Encabezados
        hoja.append(encabezados)

        # Datos
        for fila in datos:
            hoja.append(fila)

        # Eliminar esto:
        # Estilo de encabezados (opcional)
        # fuente = Font(bold=True)
        # for celda in hoja[1]:
        #     celda.font = fuente

        libro.save(nombre_archivo)
        
def generar_reporte_pdf(encabezados, datos, nombre_archivo):
        doc = SimpleDocTemplate(nombre_archivo, pagesize=letter)
        elementos = []

        # Datos
        data = [encabezados]
        data.extend(datos)

        tabla_pdf = Table(data)
        tabla_pdf.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elementos.append(tabla_pdf)
        doc.build(elementos)

@app.route('/reporte/<nombre_tabla>/<formato>')
def reporte(nombre_tabla, formato):
        encabezados, datos = obtener_datos_tabla(nombre_tabla)

        if formato == 'excel':
            nombre_archivo = f'reporte_{nombre_tabla}.xlsx'
            generar_reporte_excel(encabezados, datos, nombre_archivo)
            return send_file(nombre_archivo, as_attachment=True)
        elif formato == 'pdf':
            nombre_archivo = f'reporte_{nombre_tabla}.pdf'
            generar_reporte_pdf(encabezados, datos, nombre_archivo)
            return send_file(nombre_archivo, as_attachment=True)
        else:
            return 'Formato no válido'

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

    # Clase de Usuario para Flask-Login
class Usuario(UserMixin):
        def __init__(self, id, nombre, apellido, correo, contrasena, rol, local_id):
            self.id = id
            self.nombre = nombre
            self.apellido = apellido
            self.correo = correo
            self.contrasena = contrasena
            self.rol = rol
            self.local_id = local_id

    # Función para cargar usuario
@login_manager.user_loader
def load_user(user_id):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM Usuarios WHERE Cod_Usuario = %s;', (user_id,))
        usuario = cur.fetchone()
        cur.close()
        conn.close()
        if usuario:
            return Usuario(usuario[0], usuario[1], usuario[2], usuario[3], usuario[4], usuario[5], usuario[6])
        return None

    # Formulario de Login
class LoginForm(FlaskForm):
        correo = StringField('Correo', validators=[DataRequired(), Email()])
        contrasena = PasswordField('Contraseña', validators=[DataRequired()])
        submit = SubmitField('Iniciar Sesión')

@app.route('/registrar_vendedor', methods=['GET', 'POST'])
def registrar_vendedor():
        if current_user.rol != 'admin':
            flash('No tienes permiso para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT local_id, Nombre FROM Locales;')
        locales = cur.fetchall()
        cur.close()
        if request.method == 'POST':
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            correo = request.form['correo']
            contrasena = request.form['contrasena']
            local_id = request.form['local_id']
            error = None

            if not nombre:
                error = 'Nombre es requerido.'
            elif not apellido:
                error = 'Apellido es requerido.'
            elif not correo:
                error = 'Correo es requerido.'
            elif not contrasena:
                error = 'Contraseña es requerida.'
            elif not local_id:
                error = 'Local es requerido.'

            if error is None:
                try:
                    cur = conn.cursor()
                    # Hashear la contraseña usando bcrypt
                    contrasena_bytes = contrasena.encode('utf-8')
                    hash_bytes = bcrypt.hashpw(contrasena_bytes, bcrypt.gensalt())
                    hash_str = hash_bytes.decode('utf-8')

                    cur.execute(
                        "INSERT INTO Usuarios (Nombre, Apellido, Correo, Contrasena, Rol, local_id) VALUES (%s, %s, %s, %s, %s, %s);",
                        (nombre, apellido, correo, hash_str, 'vendedor', local_id),
                    )
                    conn.commit()
                except psycopg2.IntegrityError:
                    error = f"El usuario {correo} ya está registrado."
                else:
                    return redirect(url_for("login"))
                finally:
                    cur.close()
            flash(error)
        return render_template('registrar_vendedor.html', locales=locales)

@app.route('/')
def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))
    
# Ruta de Login
@app.route('/login', methods=['GET', 'POST'])
def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        form = LoginForm()
        if form.validate_on_submit():
            correo = form.correo.data
            contrasena = form.contrasena.data
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM Usuarios WHERE Correo = %s;', (correo,))
            usuario = cur.fetchone()
            cur.close()
            conn.close()
            if usuario:
                contrasena_db = usuario[4].encode('utf-8') # Obtener el hash de la base de datos
                contrasena_ingresada = contrasena.encode('utf-8') # convertir a bytes
                if bcrypt.checkpw(contrasena_ingresada, contrasena_db): # usar bcrypt.checkpw
                    user = Usuario(usuario[0], usuario[1], usuario[2], usuario[3], usuario[4], usuario[5], usuario[6])
                    login_user(user)
                    return redirect(url_for('dashboard'))
                else:
                    flash('Correo o contraseña incorrectos', 'danger')
            else:
                flash('Correo o contraseña incorrectos', 'danger')
        return render_template('login.html', form=form)

    # Ruta de Logout
@app.route('/logout')
@login_required
def logout():
        logout_user()
        return redirect(url_for('login'))

    # Ruta de Registro de Vendedor (Solo para administradores)
@app.route('/registro_vendedor', methods=['GET', 'POST'])
@login_required
def registro_vendedor():
        if current_user.rol != 'admin':
            flash('No tienes permiso para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        form = RegistroVendedorForm()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT local_id, Nombre FROM Locales;')
        locales = cur.fetchall()
        cur.close()
        conn.close()
        form.local_id.choices = [(local[0], local[1]) for local in locales]
        if form.validate_on_submit():
            nombre = form.nombre.data
            apellido = form.apellido.data
            correo = form.correo.data
            contrasena = generate_password_hash(form.contrasena.data)
            local_id = form.local_id.data
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO Usuarios (Nombre, Apellido, Correo, Contrasena, Rol, local_id) VALUES (%s, %s, %s, %s, %s, %s);', (nombre, apellido, correo, contrasena, 'vendedor', local_id))
            conn.commit()
            cur.close()
            conn.close()
            flash('Vendedor registrado exitosamente', 'success')
            return redirect(url_for('dashboard'))
        return render_template('registro_vendedor.html', form=form)

    # Ruta de Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
        return render_template('dashboard.html')


    # ... (rutas y funciones para cada tabla) ...

    
#usuarios
@app.route('/usuarios')
@login_required
def usuarios():
        if current_user.rol != 'admin':
            flash('No tienes permiso para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT Usuarios.Cod_Usuario, Usuarios.Nombre, Usuarios.Apellido, Usuarios.Correo, Usuarios.Rol, Locales.Nombre
            FROM Usuarios
            LEFT JOIN Locales ON Usuarios.local_id = Locales.local_id;
        ''')
        usuarios = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('usuarios.html', usuarios=usuarios)
#proveedores
@app.route('/proveedores')
def proveedores():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM Proveedores;')
        proveedores = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('proveedores.html', proveedores=proveedores)
#agregar proveedor
@app.route('/agregar_proveedor', methods=['GET', 'POST'])
def agregar_proveedor():
        if request.method == 'POST':
            proveedor = request.form['proveedor']
            empresa = request.form['empresa']
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO Proveedores (Proveedor, Empresa)
                VALUES (%s, %s);
            ''', (proveedor, empresa))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('proveedores'))
        return render_template('agregar_proveedor.html')
    #editar proveedor
@app.route('/editar_proveedor/<int:cod_prov>', methods=['GET', 'POST'])
def editar_proveedor(cod_prov):
        conn = get_db_connection()
        cur = conn.cursor()
        if request.method == 'POST':
            proveedor = request.form['proveedor']
            empresa = request.form['empresa']
            cur.execute('''
                UPDATE Proveedores
                SET Proveedor = %s, Empresa = %s
                WHERE Cod_Prov = %s;
            ''', (proveedor, empresa, cod_prov))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('proveedores'))
        cur.execute('SELECT * FROM Proveedores WHERE Cod_Prov = %s;', (cod_prov,))
        proveedor = cur.fetchone()
        cur.close()
        conn.close()
        return render_template('editar_proveedor.html', proveedor=proveedor)
    
    #eliminar proveedor
@app.route('/eliminar_proveedor/<int:cod_prov>')
def eliminar_proveedor(cod_prov):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM Facturas_Compra WHERE Cod_Prov = %s;', (cod_prov,))
        cur.execute('DELETE FROM Proveedores WHERE Cod_Prov = %s;', (cod_prov,))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('proveedores'))
    
    #clientes
    
@app.route('/clientes')
def clientes():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM Clientes;')
        clientes = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('clientes.html', clientes=clientes)
    
@app.route('/agregar_cliente', methods=['GET', 'POST'])
def agregar_cliente():
        if request.method == 'POST':
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            telefono = request.form['telefono']
            direccion = request.form['direccion']
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO Clientes (Nombre, Apellido, Telefono, Direccion)
                VALUES (%s, %s, %s, %s);
            ''', (nombre, apellido, telefono, direccion))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('clientes'))
        return render_template('agregar_cliente.html')

@app.route('/editar_cliente/<int:cod_clientes>', methods=['GET', 'POST'])
def editar_cliente(cod_clientes):
        conn = get_db_connection()
        cur = conn.cursor()
        if request.method == 'POST':
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            telefono = request.form['telefono']
            direccion = request.form['direccion']
            cur.execute('''
                UPDATE Clientes
                SET Nombre = %s, Apellido = %s, Telefono = %s, Direccion = %s
                WHERE Cod_Clientes = %s;
            ''', (nombre, apellido, telefono, direccion, cod_clientes))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('clientes'))
        cur.execute('SELECT * FROM Clientes WHERE Cod_Clientes = %s;', (cod_clientes,))
        cliente = cur.fetchone()
        cur.close()
        conn.close()
        return render_template('editar_cliente.html', cliente=cliente)

@app.route('/eliminar_cliente/<int:cod_clientes>')
def eliminar_cliente(cod_clientes):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM Facturas_Venta WHERE Cod_Clientes = %s;', (cod_clientes,))
        cur.execute('DELETE FROM Clientes WHERE Cod_Clientes = %s;', (cod_clientes,))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('clientes'))

#productos
@app.route('/productos')
def productos():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM Productos;')
        productos = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('productos.html', productos=productos)
    
@app.route('/agregar_producto', methods=['GET', 'POST'])
def agregar_producto():
        if request.method == 'POST':
            nombre = request.form['nombre']
            descripcion = request.form['descripcion']
            imagen = request.files['imagen']
            pvp_unit = request.form['pvp_unit']
            pvp_mayor = request.form['pvp_mayor']
            cantidad = request.form['cantidad']
            filename = None

            if imagen and allowed_file(imagen.filename):
                filename = secure_filename(imagen.filename)
                imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO Productos (Nombre, Descripcion, Imagen, PVP_Unit, PVP_Mayor, Cantidad)
                VALUES (%s, %s, %s, %s, %s, %s);
            ''', (nombre, descripcion, filename, pvp_unit, pvp_mayor, cantidad))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('productos'))
        return render_template('agregar_producto.html')

@app.route('/editar_producto/<int:cod_producto>', methods=['GET', 'POST'])
def editar_producto(cod_producto):
        conn = get_db_connection()
        cur = conn.cursor()
        if request.method == 'POST':
            nombre = request.form['nombre']
            descripcion = request.form['descripcion']
            imagen = request.files['imagen']
            pvp_unit = request.form['pvp_unit']
            pvp_mayor = request.form['pvp_mayor']
            cantidad = request.form['cantidad']
            filename = request.form['imagen_actual']

            if imagen and allowed_file(imagen.filename):
                filename = secure_filename(imagen.filename)
                imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            cur.execute('''
                UPDATE Productos
                SET Nombre = %s, Descripcion = %s, Imagen = %s, PVP_Unit = %s, PVP_Mayor = %s, Cantidad = %s
                WHERE Cod_Producto = %s;
            ''', (nombre, descripcion, filename, pvp_unit, pvp_mayor, cantidad, cod_producto))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('productos'))
        cur.execute('SELECT * FROM Productos WHERE Cod_Producto = %s;', (cod_producto,))
        producto = cur.fetchone()
        cur.close()
        conn.close()
        return render_template('editar_producto.html', producto=producto)
    
@app.route('/eliminar_producto/<int:cod_producto>')
def eliminar_producto(cod_producto):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM Detalles_Factura_Compra WHERE Cod_Producto = %s;', (cod_producto,))
        cur.execute('DELETE FROM Detalles_Factura_Venta WHERE Cod_Producto = %s;', (cod_producto,))
        cur.execute('DELETE FROM Inventario WHERE Cod_Producto = %s;', (cod_producto,))
        cur.execute('DELETE FROM Productos WHERE Cod_Producto = %s;', (cod_producto,))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('productos'))
    
    #facturas compra
@app.route('/facturas_compra')
def facturas_compra():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT Facturas_Compra.Cod_Factura_Compra, Proveedores.Proveedor, Facturas_Compra.Fecha, Facturas_Compra.Total
            FROM Facturas_Compra
            JOIN Proveedores ON Facturas_Compra.Cod_Prov = Proveedores.Cod_Prov;
        ''')
        facturas = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('facturas_compra.html', facturas=facturas)

@app.route('/agregar_factura_compra', methods=['GET', 'POST'])
def agregar_factura_compra():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT Cod_Prov, Proveedor FROM Proveedores;')
        proveedores = cur.fetchall()
        cur.execute('SELECT Cod_Producto, Nombre, PVP_Mayor FROM Productos;')
        productos = cur.fetchall()
        if request.method == 'POST':
            cod_prov = request.form['cod_prov']
            fecha = request.form['fecha']
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO Facturas_Compra (Cod_Prov, Fecha, Total)
                VALUES (%s, %s, 0);
            ''', (cod_prov, fecha))
            conn.commit()
            cur.execute('SELECT MAX(Cod_Factura_Compra) FROM Facturas_Compra;')
            cod_factura_compra = cur.fetchone()[0]
            if 'cod_producto' in request.form:
                cod_productos = request.form.getlist('cod_producto')
                precios_compra = request.form.getlist('precio_compra')
                cantidades = request.form.getlist('cantidad')
                for i in range(len(cod_productos)):
                    cur.execute('''
                        INSERT INTO Detalles_Factura_Compra (Cod_Factura_Compra, Cod_Producto, Precio_Compra, Cantidad)
                        VALUES (%s, %s, %s, %s);
                    ''', (cod_factura_compra, cod_productos[i], precios_compra[i], cantidades[i]))
                cur.execute('''
                    UPDATE Facturas_Compra
                    SET Total = (SELECT SUM(Precio_Compra * Cantidad) FROM Detalles_Factura_Compra WHERE Cod_Factura_Compra = %s)
                    WHERE Cod_Factura_Compra = %s;
                ''', (cod_factura_compra, cod_factura_compra))
                conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('facturas_compra'))
        return render_template('agregar_factura_compra.html', proveedores=proveedores, productos=productos)
    
@app.route('/editar_factura_compra/<int:cod_factura_compra>', methods=['GET', 'POST'])
def editar_factura_compra(cod_factura_compra):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT Cod_Prov, Proveedor FROM Proveedores;')
        proveedores = cur.fetchall()
        cur.execute('SELECT * FROM Facturas_Compra WHERE Cod_Factura_Compra = %s;', (cod_factura_compra,))
        factura = cur.fetchone()
        cur.execute('SELECT Cod_Producto, Nombre, PVP_Mayor FROM Productos;')
        productos = cur.fetchall()
        cur.execute('''SELECT Detalles_Factura_Compra.Cod_Producto, Productos.Nombre, Detalles_Factura_Compra.Precio_Compra, Detalles_Factura_Compra.Cantidad FROM Detalles_Factura_Compra JOIN Productos ON Detalles_Factura_Compra.Cod_Producto = Productos.Cod_Producto WHERE Detalles_Factura_Compra.Cod_Factura_Compra = %s;''',(cod_factura_compra,))
        detalles = cur.fetchall()

        if request.method == 'POST':
            cod_prov = request.form['cod_prov']
            fecha = request.form['fecha']
            cur.execute('''
                UPDATE Facturas_Compra
                SET Cod_Prov = %s, Fecha = %s
                WHERE Cod_Factura_Compra = %s;
            ''', (cod_prov, fecha, cod_factura_compra))

            # Elimina los detalles existentes y los vuelve a insertar
            cur.execute('DELETE FROM Detalles_Factura_Compra WHERE Cod_Factura_Compra = %s;',(cod_factura_compra,))
            if 'cod_producto' in request.form:
                cod_productos = request.form.getlist('cod_producto')
                precios_compra = request.form.getlist('precio_compra')
                cantidades = request.form.getlist('cantidad')
                for i in range(len(cod_productos)):
                    cur.execute('''
                        INSERT INTO Detalles_Factura_Compra (Cod_Factura_Compra, Cod_Producto, Precio_Compra, Cantidad)
                        VALUES (%s, %s, %s, %s);
                    ''', (cod_factura_compra, cod_productos[i], precios_compra[i], cantidades[i]))
                cur.execute('''
                    UPDATE Facturas_Compra
                    SET Total = (SELECT SUM(Precio_Compra * Cantidad) FROM Detalles_Factura_Compra WHERE Cod_Factura_Compra = %s)
                    WHERE Cod_Factura_Compra = %s;
                ''', (cod_factura_compra, cod_factura_compra))

            conn.commit()
            cur.close()
            conn.close() # Mueve conn.close() aquí
            return redirect(url_for('facturas_compra'))

        cur.close()
        conn.close()
        return render_template('editar_factura_compra.html', factura=factura, proveedores=proveedores, productos=productos, detalles=detalles)

@app.route('/eliminar_factura_compra/<int:cod_factura_compra>')
def eliminar_factura_compra(cod_factura_compra):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM Detalles_Factura_Compra WHERE Cod_Factura_Compra = %s;', (cod_factura_compra,))
        cur.execute('DELETE FROM Facturas_Compra WHERE Cod_Factura_Compra = %s;', (cod_factura_compra,))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('facturas_compra'))
    
@app.route('/ver_detalles_compra/<int:cod_factura_compra>')
def ver_detalles_compra(cod_factura_compra):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT Detalles_Factura_Compra.Cod_Producto, Productos.Nombre, Detalles_Factura_Compra.Precio_Compra, Detalles_Factura_Compra.Cantidad
            FROM Detalles_Factura_Compra
            JOIN Productos ON Detalles_Factura_Compra.Cod_Producto = Productos.Cod_Producto
            WHERE Detalles_Factura_Compra.Cod_Factura_Compra = %s;
        ''', (cod_factura_compra,))
        detalles = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('ver_detalles_compra.html', detalles=detalles, cod_factura_compra=cod_factura_compra)

@app.route('/reporte/FacturaDeCompra/pdf/<int:cod_factura_compra>')
def reporte_factura_pdf(cod_factura_compra):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT Facturas_Compra.Cod_Factura_Compra, Proveedores.Proveedor, Facturas_Compra.Fecha, Facturas_Compra.Total
            FROM Facturas_Compra
            JOIN Proveedores ON Facturas_Compra.Cod_Prov = Proveedores.Cod_Prov
            WHERE Facturas_Compra.Cod_Factura_Compra = %s;
        ''', (cod_factura_compra,))
        factura = cur.fetchone()
        cur.execute('''
            SELECT Productos.Nombre, Detalles_Factura_Compra.Precio_Compra, Detalles_Factura_Compra.Cantidad
            FROM Detalles_Factura_Compra
            JOIN Productos ON Detalles_Factura_Compra.Cod_Producto = Productos.Cod_Producto
            WHERE Detalles_Factura_Compra.Cod_Factura_Compra = %s;
        ''', (cod_factura_compra,))
        detalles = cur.fetchall()
        cur.close()

        output = io.BytesIO()
        c = canvas.Canvas(output, pagesize=letter)
        c.drawString(100, 750, f'Factura de Compra #{factura[0]}')

        # Tabla de datos
        data = [['Proveedor', factura[1]], ['Fecha', factura[2]]]
        table = Table(data)
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                    ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
        table.wrapOn(c, 100, 700)
        table.drawOn(c, 100, 700)

        # Tabla de detalles de productos
        data_detalles = [['Producto', 'Precio', 'Cantidad', 'Subtotal']]
        for detalle in detalles:
            data_detalles.append([detalle[0], f'${detalle[1]:.2f}', detalle[2], f'${detalle[1] * detalle[2]:.2f}'])
        table_detalles = Table(data_detalles)
        table_detalles.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                            ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
        table_detalles.wrapOn(c, 100, 500)
        table_detalles.drawOn(c, 100, 500)

        c.save()
        output.seek(0)
        return send_file(output, download_name=f'Factura_{cod_factura_compra}.pdf', as_attachment=True)
#facturas venta
@app.route('/facturas_venta')
def facturas_venta():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT Facturas_Venta.Cod_Factura_Venta, Clientes.Nombre, Clientes.Apellido, Facturas_Venta.Fecha, Facturas_Venta.Total
            FROM Facturas_Venta
            JOIN Clientes ON Facturas_Venta.Cod_Clientes = Clientes.Cod_Clientes;
        ''')
        facturas = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('facturas_venta.html', facturas=facturas)

@app.route('/agregar_factura_venta', methods=['GET', 'POST'])
def agregar_factura_venta():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT Cod_Clientes, Nombre, Apellido FROM Clientes;')
        clientes = cur.fetchall()
        cur.execute('SELECT Cod_Producto, Nombre, PVP_Unit FROM Productos;')
        productos = cur.fetchall()
        if request.method == 'POST':
            cod_clientes = request.form['cod_clientes']
            fecha = request.form['fecha']
            cur.execute('''
                INSERT INTO Facturas_Venta (Cod_Clientes, Fecha, Total)
                VALUES (%s, %s, 0);
            ''', (cod_clientes, fecha))
            conn.commit()
            cur.execute('SELECT MAX(Cod_Factura_Venta) FROM Facturas_Venta;')
            cod_factura_venta = cur.fetchone()[0]
            if 'cod_producto' in request.form:
                cod_productos = request.form.getlist('cod_producto')
                precios_venta = request.form.getlist('precio_venta')
                cantidades = request.form.getlist('cantidad')
                for i in range(len(cod_productos)):
                    cur.execute('''
                        INSERT INTO Detalles_Factura_Venta (Cod_Factura_Venta, Cod_Producto, PVP_Unit, Cantidad)
                        VALUES (%s, %s, %s, %s);
                    ''', (cod_factura_venta, cod_productos[i], precios_venta[i], cantidades[i]))
                cur.execute('''
                    UPDATE Facturas_Venta
                    SET Total = (SELECT SUM(PVP_Unit * Cantidad) FROM Detalles_Factura_Venta WHERE Cod_Factura_Venta = %s)
                    WHERE Cod_Factura_Venta = %s;
                ''', (cod_factura_venta, cod_factura_venta))
                conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('facturas_venta'))
        return render_template('agregar_factura_venta.html', clientes=clientes, productos=productos)

@app.route('/editar_factura_venta/<int:cod_factura_venta>', methods=['GET', 'POST'])
def editar_factura_venta(cod_factura_venta):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT Cod_Clientes, Nombre, Apellido FROM Clientes;')
        clientes = cur.fetchall()
        cur.execute('SELECT * FROM Facturas_Venta WHERE Cod_Factura_Venta = %s;', (cod_factura_venta,))
        factura = cur.fetchone()
        cur.execute('SELECT Cod_Producto, Nombre, PVP_Unit FROM Productos;')
        productos = cur.fetchall()
        cur.execute('''SELECT Detalles_Factura_Venta.Cod_Producto, Productos.Nombre, Detalles_Factura_Venta.PVP_Unit, Detalles_Factura_Venta.Cantidad FROM Detalles_Factura_Venta JOIN Productos ON Detalles_Factura_Venta.Cod_Producto = Productos.Cod_Producto WHERE Detalles_Factura_Venta.Cod_Factura_Venta = %s;''',(cod_factura_venta,))
        detalles = cur.fetchall()
        if request.method == 'POST':
            cod_clientes = request.form['cod_clientes']
            fecha = request.form['fecha']
            cur.execute('''
                UPDATE Facturas_Venta
                SET Cod_Clientes = %s, Fecha = %s
                WHERE Cod_Factura_Venta = %s;
            ''', (cod_clientes, fecha, cod_factura_venta))
            cur.execute('DELETE FROM Detalles_Factura_Venta WHERE Cod_Factura_Venta = %s;',(cod_factura_venta,))
            if 'cod_producto' in request.form:
                cod_productos = request.form.getlist('cod_producto')
                precios_venta = request.form.getlist('precio_venta')
                cantidades = request.form.getlist('cantidad')
                for i in range(len(cod_productos)):
                    cur.execute('''
        INSERT INTO Detalles_Factura_Venta (Cod_Factura_Venta, Cod_Producto, PVP_Unit, PVP_Mayor, Cantidad)
        VALUES (%s, %s, %s, %s, %s);
    ''', (cod_factura_venta, cod_productos[i], precios_venta[i], precios_venta[i], cantidades[i]))
                cur.execute('''
                    UPDATE Facturas_Venta
                    SET Total = (SELECT SUM(PVP_Unit * Cantidad) FROM Detalles_Factura_Venta WHERE Cod_Factura_Venta = %s)
                    WHERE Cod_Factura_Venta = %s;
                ''', (cod_factura_venta, cod_factura_venta))
                conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('facturas_venta'))
        cur.close()
        conn.close()
        return render_template('editar_factura_venta.html', factura=factura, clientes=clientes, productos=productos, detalles=detalles)

@app.route('/eliminar_factura_venta/<int:cod_factura_venta>')
def eliminar_factura_venta(cod_factura_venta):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM Detalles_Factura_Venta WHERE Cod_Factura_Venta = %s;', (cod_factura_venta,))
        cur.execute('DELETE FROM Facturas_Venta WHERE Cod_Factura_Venta = %s;', (cod_factura_venta,))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('facturas_venta'))

@app.route('/ver_detalles_venta/<int:cod_factura_venta>')
def ver_detalles_venta(cod_factura_venta):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT Productos.Nombre, Detalles_Factura_Venta.PVP_Unit, Detalles_Factura_Venta.Cantidad
            FROM Detalles_Factura_Venta
            JOIN Productos ON Detalles_Factura_Venta.Cod_Producto = Productos.Cod_Producto
            WHERE Detalles_Factura_Venta.Cod_Factura_Venta = %s;
        ''', (cod_factura_venta,))
        detalles = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('ver_detalles_venta.html', detalles=detalles, cod_factura_venta=cod_factura_venta)

@app.route('/reporte/FacturaDeVenta/pdf/<int:cod_factura_venta>')
def reporte_factura_venta_pdf(cod_factura_venta):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT Facturas_Venta.Cod_Factura_Venta, Clientes.Nombre, Clientes.Apellido, Facturas_Venta.Fecha, Facturas_Venta.Total
            FROM Facturas_Venta
            JOIN Clientes ON Facturas_Venta.Cod_Clientes = Clientes.Cod_Clientes
            WHERE Facturas_Venta.Cod_Factura_Venta = %s;
        ''', (cod_factura_venta,))
        factura = cur.fetchone()
        cur.execute('''
            SELECT Productos.Nombre, Detalles_Factura_Venta.PVP_Unit, Detalles_Factura_Venta.Cantidad
            FROM Detalles_Factura_Venta
            JOIN Productos ON Detalles_Factura_Venta.Cod_Producto = Productos.Cod_Producto
            WHERE Detalles_Factura_Venta.Cod_Factura_Venta = %s;
        ''', (cod_factura_venta,))
        detalles = cur.fetchall()
        cur.close()

        output = io.BytesIO()
        c = canvas.Canvas(output, pagesize=letter)
        c.drawString(100, 750, f'Factura de Venta #{factura[0]}')

        # Tabla de datos
        data = [['Cliente', f'{factura[1]} {factura[2]}'], ['Fecha', factura[3]], ['Total', f'${factura[4]:.2f}']]
        table = Table(data)
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                    ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
        table.wrapOn(c, 100, 700)
        table.drawOn(c, 100, 700)

        # Tabla de detalles de productos
        data_detalles = [['Producto', 'Precio', 'Cantidad', 'Subtotal']]
        for detalle in detalles:
            data_detalles.append([detalle[0], f'${detalle[1]:.2f}', detalle[2], f'${detalle[1] * detalle[2]:.2f}'])
        table_detalles = Table(data_detalles)
        table_detalles.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                            ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
        table_detalles.wrapOn(c, 100, 500)
        table_detalles.drawOn(c, 100, 500)

        c.save()
        output.seek(0)
        return send_file(output, download_name=f'Factura_Venta_{cod_factura_venta}.pdf', as_attachment=True)
    
#locales

@app.route('/locales')
@login_required
def locales():
        if current_user.rol != 'admin':
            flash('No tienes permiso para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM Locales;')
        locales = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('locales.html', locales=locales)

# Ruta para agregar un local
@app.route('/agregar_local', methods=['GET', 'POST'])
@login_required
def agregar_local():
        if current_user.rol != 'admin':
            flash('No tienes permiso para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            nombre = request.form['nombre']
            direccion = request.form['direccion']
            telefono = request.form['telefono']
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO Locales (Nombre, Direccion, Telefono) VALUES (%s, %s, %s);', (nombre, direccion, telefono))
            conn.commit()
            cur.close()
            conn.close()
            flash('Local agregado exitosamente', 'success')
            return redirect(url_for('locales'))
        return render_template('agregar_local.html')

    # Ruta para editar un local
@app.route('/editar_local/<int:local_id>', methods=['GET', 'POST'])
@login_required
def editar_local(local_id):
        if current_user.rol != 'admin':
            flash('No tienes permiso para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM Locales WHERE local_id = %s;', (local_id,))
        local = cur.fetchone()
        cur.close()
        conn.close()
        if request.method == 'POST':
            nombre = request.form['nombre']
            direccion = request.form['direccion']
            telefono = request.form['telefono']
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('UPDATE Locales SET Nombre = %s, Direccion = %s, Telefono = %s WHERE local_id = %s;', (nombre, direccion, telefono, local_id))
            conn.commit()
            cur.close()
            conn.close()
            flash('Local editado exitosamente', 'success')
            return redirect(url_for('locales'))
        return render_template('editar_local.html', local=local)

    # Ruta para eliminar un local
@app.route('/eliminar_local/<int:local_id>')
@login_required
def eliminar_local(local_id):
        if current_user.rol != 'admin':
            flash('No tienes permiso para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM Locales WHERE local_id = %s;', (local_id,))
        conn.commit()
        cur.close()
        conn.close()
        flash('Local eliminado exitosamente', 'success')
        return redirect(url_for('locales'))
    
#Inventario
@app.route('/inventario')
@login_required
def inventario():
        if current_user.rol != 'admin':
            flash('No tienes permiso para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT Inventario.cod_inventario, Locales.Nombre, Productos.Nombre, Inventario.cantidad
            FROM Inventario
            JOIN Locales ON Inventario.local_Id = Locales.local_id
            JOIN Productos ON Inventario.cod_producto = Productos.cod_producto;
        ''')
        inventario = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('inventario.html', inventario=inventario)

@app.route('/agregar_inventario', methods=['GET', 'POST'])
@login_required
def agregar_inventario():
        if current_user.rol != 'admin':
            flash('No tienes permiso para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT local_id, Nombre FROM Locales;')
        locales = cur.fetchall()
        cur.execute('SELECT cod_producto, Nombre FROM Productos;')
        productos = cur.fetchall()
        cur.close()
        if request.method == 'POST':
            local_id = request.form['local_id']
            producto_id = request.form['producto_id']
            cantidad = request.form['cantidad']
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO Inventario (local_Id, cod_producto, cantidad) VALUES (%s, %s, %s);', (local_id, producto_id, cantidad))
            conn.commit()
            cur.close()
            conn.close()
            flash('Inventario agregado exitosamente', 'success')
            return redirect(url_for('inventario'))
        return render_template('agregar_inventario.html', locales=locales, productos=productos)

@app.route('/editar_inventario/<int:inventario_id>', methods=['GET', 'POST'])
@login_required
def editar_inventario(inventario_id):
        if current_user.rol != 'admin':
            flash('No tienes permiso para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM Inventario WHERE cod_inventario = %s;', (inventario_id,))
        inventario = cur.fetchone()
        cur.execute('SELECT local_id, Nombre FROM Locales;')
        locales = cur.fetchall()
        cur.execute('SELECT cod_producto, Nombre FROM Productos;')
        productos = cur.fetchall()
        cur.close()
        conn.close()
        if request.method == 'POST':
            local_id = request.form['local_id']
            producto_id = request.form['producto_id']
            cantidad = request.form['cantidad']
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('UPDATE Inventario SET local_Id = %s, cod_producto = %s, cantidad = %s WHERE cod_inventario = %s;', (local_id, producto_id, cantidad, inventario_id))
            conn.commit()
            cur.close()
            conn.close()
            flash('Inventario editado exitosamente', 'success')
            return redirect(url_for('inventario'))
        return render_template('editar_inventario.html', inventario=inventario, locales=locales, productos=productos)

@app.route('/eliminar_inventario/<int:inventario_id>')
@login_required
def eliminar_inventario(inventario_id):
        if current_user.rol != 'admin':
            flash('No tienes permiso para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM Inventario WHERE cod_inventario = %s;', (inventario_id,))
        conn.commit()
        cur.close()
        conn.close()
        flash('Inventario eliminado exitosamente', 'success')
        return redirect(url_for('inventario'))

    


    
if __name__ == '__main__':
        app.run(debug=True)