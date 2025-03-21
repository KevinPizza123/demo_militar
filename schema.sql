-- Tabla de Proveedores
    CREATE TABLE Proveedores (
        Cod_Prov SERIAL PRIMARY KEY,
        Proveedor VARCHAR(255) NOT NULL,
        Empresa VARCHAR(255) NOT NULL
    );

    -- Tabla de Clientes
    CREATE TABLE Clientes (
        Cod_Clientes SERIAL PRIMARY KEY,
        Nombre VARCHAR(255) NOT NULL,
        Apellido VARCHAR(255) NOT NULL,
        Telefono VARCHAR(20),
        Direccion VARCHAR(255)
    );

    -- Tabla de Productos
    CREATE TABLE Productos (
        Cod_Producto SERIAL PRIMARY KEY,
        Nombre VARCHAR(255) NOT NULL,
        Descripcion TEXT,
        Imagen VARCHAR(255),
        PVP_Unit DECIMAL(10, 2),
        PVP_Mayor DECIMAL(10, 2),
        Cantidad INT DEFAULT 0
    );


    -- Tabla de Facturas de Compra
    CREATE TABLE Facturas_Compra (
        Cod_Factura_Compra SERIAL PRIMARY KEY,
        Cod_Prov INT REFERENCES Proveedores(Cod_Prov),
        Fecha DATE NOT NULL,
        Total DECIMAL(10, 2) NOT NULL
    );

    -- Tabla de Detalles de Factura de Compra
    CREATE TABLE Detalles_Factura_Compra (
        Cod_Detalle_Compra SERIAL PRIMARY KEY,
        Cod_Factura_Compra INT REFERENCES Facturas_Compra(Cod_Factura_Compra),
        Cod_Producto INT REFERENCES Productos(Cod_Producto),
        Precio_Compra DECIMAL(10, 2) NOT NULL,
        Cantidad INT NOT NULL
    );

    -- Tabla de Facturas de Venta
    CREATE TABLE Facturas_Venta (
        Cod_Factura_Venta SERIAL PRIMARY KEY,
        Cod_Clientes INT REFERENCES Clientes(Cod_Clientes),
        Fecha DATE NOT NULL,
        Total DECIMAL(10, 2) NOT NULL
    );

    -- Tabla de Detalles de Factura de Venta
    CREATE TABLE Detalles_Factura_Venta (
        Cod_Detalle_Venta SERIAL PRIMARY KEY,
        Cod_Factura_Venta INT REFERENCES Facturas_Venta(Cod_Factura_Venta),
        Cod_Producto INT REFERENCES Productos(Cod_Producto),
        PVP_Unit DECIMAL(10, 2) NOT NULL,
        PVP_Mayor DECIMAL(10, 2) NOT NULL,
        Cantidad INT NOT NULL
    );

    -- Tabla de Locales
    CREATE TABLE Locales (
        local_id SERIAL PRIMARY KEY,
        nombre VARCHAR(255) NOT NULL,
        responsable VARCHAR(255)
    );

    -- Tabla de Inventario
    CREATE TABLE Inventario (
        Cod_Inventario SERIAL PRIMARY KEY,
        Cod_Producto INT REFERENCES Productos(Cod_Producto),
        local_id INT REFERENCES Locales(local_id),
        Cantidad INT NOT NULL
    );