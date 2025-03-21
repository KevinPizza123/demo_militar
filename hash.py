import bcrypt

# Generar el hash
contrasena = 'militar25'
contrasena_bytes = contrasena.encode('utf-8')
contrasena_hash_bytes = bcrypt.hashpw(contrasena_bytes, bcrypt.gensalt())
contrasena_hash = contrasena_hash_bytes.decode('utf-8')  # Decodificar a cadena

print(contrasena_hash)  # Mostrar el hash
