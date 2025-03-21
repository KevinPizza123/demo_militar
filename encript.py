import bcrypt

password = 'herbye25'
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
print(hashed_password.decode('utf-8'))