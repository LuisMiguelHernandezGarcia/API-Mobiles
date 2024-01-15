import base64
import http.server
import json
import socketserver
import mysql.connector
from urllib.parse import parse_qs

# Configuración de la base de datos
db_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '030217',
    'database': 'proyecto_mobiles'
}

class MiHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Manejar la ruta /usuarios
        if self.path == '/usuarios':
            try:
                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)
                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor(dictionary=True)
                # Ejecutar consulta para seleccionar todos los usuarios
                cursor.execute("SELECT * FROM usuarios")
                # Obtener todos los resultados
                usuarios = cursor.fetchall()
                # Cerrar cursor y conexión
                cursor.close()
                conexion.close()
                # Convertir los resultados a formato JSON y enviarlos como respuesta
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(usuarios).encode('utf-8'))
            except mysql.connector.Error as err:
                # Enviar mensaje de error si hay un problema con la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error de conexión a la base de datos: {err}".encode('utf-8'))
        # Manejar la ruta /catalogo
        elif self.path == '/catalogo':
            try:
                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)
                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor(dictionary=True)
                # Ejecutar consulta para seleccionar todos los productos del catálogo
                cursor.execute("SELECT * FROM catalogo")
                # Obtener todos los resultados
                productos_catalogo = cursor.fetchall()
                # Cerrar cursor y conexión
                cursor.close()
                conexion.close()

                # Ordenar productos primero por categoría y luego por precio dentro de cada categoría
                productos_ordenados = sorted(productos_catalogo, key=lambda x: (x['categoria'], x['precio']))
                # Convertir los resultados a formato JSON y enviarlos como respuesta
                for producto in productos_ordenados:
                    # Convertir el campo de imágenes a una cadena base64 para serializar a JSON
                    producto['imagenes'] = base64.b64encode(producto['imagenes']).decode('utf-8')

                    # Convertir el campo de precio de Decimal a float
                    producto['precio'] = float(producto['precio'])

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(productos_ordenados).encode('utf-8'))
            except mysql.connector.Error as err:
                # Enviar mensaje de error si hay un problema con la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error de conexión a la base de datos: {err}".encode('utf-8'))
        # Nuevo método para obtener información de un pedido por
        elif self.path.startswith('/pedidos/'):
            try:
                # Obtener el ID del pedido de la URL
                idpedido = int(self.path.split('/')[2])

                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)

                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor(dictionary=True)

                # Ejecutar consulta para obtener la información del pedido
                cursor.execute("""
                    SELECT
                        pedidos.id_pedido,
                        pedidos.id_usuario,
                        pedidos.id_repartidor,
                        pedidos.latitud,
                        pedidos.longitud,
                        pedidos.Estado,
                        pedidos.latitudC,
                        pedidos.longitudC,
                        GROUP_CONCAT(
                            CONCAT(catalogo.nombre_producto, ' (', CAST(catalogo.precio AS CHAR), ')') SEPARATOR ', '
                        ) AS productos
                    FROM pedidos
                    LEFT JOIN detalles_pedido ON pedidos.id_pedido = detalles_pedido.id_pedido
                    LEFT JOIN catalogo ON detalles_pedido.id_producto = catalogo.id
                    WHERE pedidos.id_pedido = %s
                    GROUP BY pedidos.id_pedido;
                """, (idpedido,))

                # Obtener el resultado
                resultado = cursor.fetchone()

                # Convertir los valores Decimal a float
                if resultado:
                    resultado['latitud'] = float(resultado['latitud'])
                    resultado['longitud'] = float(resultado['longitud'])
                    resultado['latitudC'] = float(resultado['latitudC'])
                    resultado['longitudC'] = float(resultado['longitudC'])

                # Cerrar cursor y conexión
                cursor.close()
                conexion.close()

                # Enviar respuesta con la información del pedido
                if resultado:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(resultado).encode('utf-8'))
                else:
                    # Enviar respuesta 404 si no se encuentra el pedido
                    self.send_response(404)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'Pedido no encontrado')

            except (ValueError, mysql.connector.Error) as err:
                # Enviar mensaje de error si hay un problema con los datos o la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error al obtener información del pedido: {err}".encode('utf-8'))

        elif self.path.startswith('/historia_pedido/'):
            try:
                # Obtener el ID del usuario de la URL
                id_usuario = int(self.path.split('/')[2])

                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)

                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor(dictionary=True)

                # Ejecutar consulta para obtener la información de todos los pedidos asociados al usuario
                cursor.execute("""
                    SELECT *
                    FROM pedidos
                    WHERE id_usuario = %s;
                """, (id_usuario,))

                # Obtener todos los resultados
                resultados = cursor.fetchall()

                # Convertir los valores Decimal a float en cada resultado
                for resultado in resultados:
                    # Convertir latitud y longitud a float si existen, de lo contrario, establecer en None
                    resultado['latitud'] = float(resultado['latitud']) if resultado['latitud'] is not None else None
                    resultado['longitud'] = float(resultado['longitud']) if resultado['longitud'] is not None else None
                    # Convertir latitud y longitud a float si existen, de lo contrario, establecer en None
                    resultado['latitudC'] = float(resultado['latitudC']) if resultado['latitudC'] is not None else None
                    resultado['longitudC'] = float(resultado['longitudC']) if resultado['longitudC'] is not None else None

                # Cerrar cursor y conexión
                cursor.close()
                conexion.close()

                # Enviar respuesta con la información de los pedidos
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resultados).encode('utf-8'))

            except (ValueError, mysql.connector.Error) as err:
                # Enviar mensaje de error si hay un problema con los datos o la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error al obtener la historia de pedidos: {err}".encode('utf-8'))

        else:
            # Utilizar el manejador original para otras rutas
            super().do_GET()

    def do_PUT(self):
        # Manejar la actualización de un usuario en la ruta /usuarios
        if self.path.startswith('/usuarios/'):
            # Obtener el ID y el nuevo nombre del usuario de la URL
            usuario_id = int(self.path.split('/')[2])
            nuevo_nombre = self.path.split('/')[3]
            try:
                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)
                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor()
                # Ejecutar consulta para actualizar el usuario
                cursor.execute("UPDATE usuarios SET usuario = %s, contraseña = %s, rol = %s WHERE id = %s",
                            (nuevo_nombre, self.path.split('/')[4], self.path.split('/')[5], usuario_id))
                # Confirmar la transacción y cerrar cursor y conexión
                conexion.commit()
                cursor.close()
                conexion.close()
                # Enviar respuesta exitosa
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Usuario actualizado correctamente')
            except mysql.connector.Error as err:
                # Enviar mensaje de error si hay un problema con la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error al actualizar el usuario: {err}".encode('utf-8'))
        elif self.path.startswith('/pedidos/'):
            try:
                # Obtener los componentes de la URL
                _, _, idpedido, idrepartidor = self.path.split('/')
                idpedido = int(idpedido)
                idrepartidor = int(idrepartidor)

                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)

                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor()

                # Ejecutar consulta para actualizar el repartidor del pedido
                cursor.execute("UPDATE pedidos SET id_repartidor = %s WHERE id_pedido = %s",
                               (idrepartidor, idpedido))

                # Confirmar la transacción
                conexion.commit()

                # Cerrar cursor y conexión
                cursor.close()
                conexion.close()

                # Enviar respuesta exitosa
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Repartidor del pedido actualizado correctamente')

            except (ValueError, mysql.connector.Error) as err:
                # Enviar mensaje de error si hay un problema con los datos o la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error al actualizar el repartidor del pedido: {err}".encode('utf-8'))
        elif self.path.startswith('/Estado_ac/'):
            try:
                # Obtener el ID del pedido de la URL
                id_pedido = int(self.path.split('/')[2])

                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)

                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor()

                # Ejecutar consulta para actualizar el estado del pedido a "activo"
                cursor.execute("UPDATE pedidos SET Estado = 'activo' WHERE id_pedido = %s", (id_pedido,))

                # Confirmar la transacción y cerrar cursor y conexión
                conexion.commit()
                cursor.close()
                conexion.close()

                # Enviar respuesta de éxito
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'ok')

            except (ValueError, mysql.connector.Error) as err:
                # Enviar mensaje de error si hay un problema con los datos o la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error al actualizar el estado del pedido: {err}".encode('utf-8'))
        elif self.path.startswith('/Estado_en/'):
            try:
                # Obtener el ID del pedido de la URL
                id_pedido = int(self.path.split('/')[2])

                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)

                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor()

                # Ejecutar consulta para actualizar el estado del pedido a "activo"
                cursor.execute("UPDATE pedidos SET Estado = 'Entregado' WHERE id_pedido = %s", (id_pedido,))

                # Confirmar la transacción y cerrar cursor y conexión
                conexion.commit()
                cursor.close()
                conexion.close()

                # Enviar respuesta de éxito
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'ok"')

            except (ValueError, mysql.connector.Error) as err:
                # Enviar mensaje de error si hay un problema con los datos o la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error al actualizar el estado del pedido: {err}".encode('utf-8'))
        elif self.path.startswith('/Estado_ab/'):
            try:
                # Obtener el ID del pedido de la URL
                id_pedido = int(self.path.split('/')[2])

                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)

                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor()

                # Ejecutar consulta para actualizar el estado del pedido a "activo"
                cursor.execute("UPDATE pedidos SET Estado = 'Abierto' WHERE id_pedido = %s", (id_pedido,))

                # Confirmar la transacción y cerrar cursor y conexión
                conexion.commit()
                cursor.close()
                conexion.close()

                # Enviar respuesta de éxito
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'ok"')

            except (ValueError, mysql.connector.Error) as err:
                # Enviar mensaje de error si hay un problema con los datos o la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error al actualizar el estado del pedido: {err}".encode('utf-8'))
        else:
            # Utilizar el manejador original para otras rutas PUT
            super().do_PUT()

    def do_DELETE(self):
        if self.path.startswith('/usuarios/'):
            usuario_id = int(self.path.split('/')[-1])
            try:
                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)
                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor()

                # Obtener los pedidos asociados al usuario
                cursor.execute("SELECT id_pedido FROM pedidos WHERE id_usuario = %s", (usuario_id,))
                pedidos_asociados = cursor.fetchall()

                # Eliminar los detalles de los pedidos asociados
                for pedido_id in pedidos_asociados:
                    cursor.execute("DELETE FROM detalles_pedido WHERE id_pedido = %s", (pedido_id[0],))

                # Eliminar el usuario
                cursor.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))

                # Confirmar la transacción y cerrar cursor y conexión
                conexion.commit()
                cursor.close()
                conexion.close()

                # Enviar respuesta exitosa
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Usuario eliminado correctamente')

            except mysql.connector.Error as err:
                # Enviar mensaje de error si hay un problema con la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error de conexión a la base de datos: {err}".encode('utf-8'))
        else:
            # Utilizar el manejador original para otras rutas DELETE
            super().do_DELETE()

    def do_CUSTOM(self):
        if self.path.startswith('/verificar_usuario/'):
            # Obtener el nombre y la contraseña de la URL
            nombre = self.path.split('/')[2]
            contraseña = self.path.split('/')[3]

            try:
                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)

                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor(dictionary=True)

                # Ejecutar consulta para verificar si el usuario existe
                cursor.execute("SELECT * FROM usuarios WHERE usuario = %s", (nombre,))
                usuario = cursor.fetchone()

                # Cerrar cursor y conexión
                cursor.close()
                conexion.close()

                # Enviar respuesta según el resultado
                if usuario:
                    # Verificar si la contraseña coincide
                    if usuario['contraseña'] == contraseña:
                        # Enviar respuesta con la información completa del usuario
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(usuario).encode('utf-8'))
                    else:
                        # Enviar respuesta indicando que la contraseña es incorrecta
                        self.send_response(401)
                        self.send_header('Content-type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(b'Contrasena incorrecta')
                else:
                    # Enviar respuesta indicando que el usuario no está registrado
                    self.send_response(404)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'No se encontro el usuario')

            except mysql.connector.Error as err:
                # Enviar mensaje de error si hay un problema con la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error al verificar el usuario: {err}".encode('utf-8'))

        elif self.path.startswith('/actualizar_estado/'):
            try:
                # Obtener el ID del pedido, latitud y longitud de la URL
                id_pedido = int(self.path.split('/')[2])
                latitud = float(self.path.split('/')[3])
                longitud = float(self.path.split('/')[4])

                try:
                    # Conexión a la base de datos
                    conexion = mysql.connector.connect(**db_config)

                    # Crear un cursor para ejecutar consultas SQL
                    cursor = conexion.cursor()

                    # Actualizar la latitud y longitud del pedido
                    cursor.execute("UPDATE pedidos SET latitud = %s, longitud = %s WHERE id_pedido = %s",
                                (latitud, longitud, id_pedido))

                    # Confirmar la transacción y cerrar cursor y conexión
                    conexion.commit()
                    cursor.close()
                    conexion.close()

                    # Enviar respuesta exitosa
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'OK')

                except mysql.connector.Error as err:
                    # Enviar mensaje de error si hay un problema con la base de datos
                    self.send_response(500)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(f"Error al actualizar la ubicación: {err}".encode('utf-8'))

            except (ValueError, IndexError) as err:
                # Enviar mensaje de error si hay un problema con los datos de la URL
                self.send_response(400)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error en la solicitud: {err}".encode('utf-8'))

        elif self.path.startswith('/mostrar_estado/'):
            # Obtener el ID del pedido de la URL
            id_pedido = int(self.path.split('/')[2])

            try:
                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)

                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor(dictionary=True)

                # Obtener la ubicación del pedido
                cursor.execute("SELECT latitud, longitud FROM pedidos WHERE id_pedido = %s", (id_pedido,))
                ubicacion_pedido = cursor.fetchone()

                # Cerrar cursor y conexión
                cursor.close()
                conexion.close()

                # Verificar si se encontró la ubicación del pedido
                if ubicacion_pedido:
                    # Convertir las coordenadas de Decimal a float antes de serializar
                    ubicacion_pedido['latitud'] = float(ubicacion_pedido['latitud'])
                    ubicacion_pedido['longitud'] = float(ubicacion_pedido['longitud'])

                    # Enviar respuesta con la ubicación del pedido
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(ubicacion_pedido).encode('utf-8'))
                else:
                    # Enviar respuesta indicando que no se encontró la ubicación del pedido
                    self.send_response(404)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'No se encontro la ubicacion del pedido')

            except mysql.connector.Error as err:
                # Enviar mensaje de error si hay un problema con la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error al obtener la ubicación del pedido: {err}".encode('utf-8'))
                
        elif self.path.startswith('/actualizar_estado_c/'):
            try:
                # Obtener el ID del pedido, latitud y longitud de la URL
                id_pedido = int(self.path.split('/')[2])
                latitud = float(self.path.split('/')[3])
                longitud = float(self.path.split('/')[4])

                try:
                    # Conexión a la base de datos
                    conexion = mysql.connector.connect(**db_config)

                    # Crear un cursor para ejecutar consultas SQL
                    cursor = conexion.cursor()

                    # Actualizar la latitud y longitud del pedido
                    cursor.execute("UPDATE pedidos SET latitudC = %s, longitudC = %s WHERE id_pedido = %s",
                                (latitud, longitud, id_pedido))

                    # Confirmar la transacción y cerrar cursor y conexión
                    conexion.commit()
                    cursor.close()
                    conexion.close()

                    # Enviar respuesta exitosa
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'OK')

                except mysql.connector.Error as err:
                    # Enviar mensaje de error si hay un problema con la base de datos
                    self.send_response(500)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(f"Error al actualizar la ubicación: {err}".encode('utf-8'))

            except (ValueError, IndexError) as err:
                # Enviar mensaje de error si hay un problema con los datos de la URL
                self.send_response(400)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error en la solicitud: {err}".encode('utf-8'))

        elif self.path.startswith('/mostrar_estado_c/'):
            # Obtener el ID del pedido de la URL
            id_pedido = int(self.path.split('/')[2])

            try:
                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)

                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor(dictionary=True)

                # Obtener la ubicación del pedido
                cursor.execute("SELECT latitudC, longitudC FROM pedidos WHERE id_pedido = %s", (id_pedido,))
                ubicacion_pedido = cursor.fetchone()

                # Cerrar cursor y conexión
                cursor.close()
                conexion.close()

                # Verificar si se encontró la ubicación del pedido
                if ubicacion_pedido:
                    # Convertir las coordenadas de Decimal a float antes de serializar
                    ubicacion_pedido['latitudC'] = float(ubicacion_pedido['latitudC'])
                    ubicacion_pedido['longitudC'] = float(ubicacion_pedido['longitudC'])

                    # Enviar respuesta con la ubicación del pedido
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(ubicacion_pedido).encode('utf-8'))
                else:
                    # Enviar respuesta indicando que no se encontró la ubicación del pedido
                    self.send_response(404)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'No se encontro la ubicacion del pedido')

            except mysql.connector.Error as err:
                # Enviar mensaje de error si hay un problema con la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error al obtener la ubicación del pedido: {err}".encode('utf-8'))

        else:
            # Utilizar el manejador original para otras rutas CUSTOM
            super().do_CUSTOM()

    def do_POST(self):
        # Manejar la creación de un nuevo usuario en la ruta /usuarios
        if self.path.startswith('/usuarios/'):
            # Obtener los datos del nuevo usuario de la URL
            nuevo_usuario = self.path.split('/')[2]
            nueva_contraseña = self.path.split('/')[3]
            nuevo_rol = self.path.split('/')[4]

            try:
                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)

                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor()

                # Ejecutar consulta para insertar un nuevo usuario
                cursor.execute("INSERT INTO usuarios (usuario, contraseña, rol) VALUES (%s, %s, %s)",
                            (nuevo_usuario, nueva_contraseña, nuevo_rol))

                # Confirmar la transacción y obtener el ID del nuevo usuario
                conexion.commit()
                nuevo_usuario_id = cursor.lastrowid

                # Cerrar cursor y conexión
                cursor.close()
                conexion.close()

                # Enviar respuesta exitosa con el ID del nuevo usuario
                self.send_response(201)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'{nuevo_usuario_id}'.encode('utf-8'))

            except mysql.connector.Error as err:
                # Enviar mensaje de error si hay un problema con la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error al crear el usuario: {err}".encode('utf-8'))
        # Manejar la creación de un nuevo pedido en la ruta /pedidos/idusuario/idrepartidor/idproductos
        elif self.path.startswith('/pedidos/'):
            try:
                # Obtener los componentes de la URL
                _, _, idusuario, idrepartidor, *idproductos = self.path.split('/')
                idusuario = int(idusuario)
                idrepartidor = int(idrepartidor)
                idproductos = [int(id_producto) for id_producto in idproductos]

                # Conexión a la base de datos
                conexion = mysql.connector.connect(**db_config)

                # Crear un cursor para ejecutar consultas SQL
                cursor = conexion.cursor()

                # Ejecutar consulta para insertar un nuevo pedido
                cursor.execute("INSERT INTO pedidos (id_usuario, id_repartidor,Estado) VALUES (%s, %s, 'abierto')",
                               (idusuario, idrepartidor))

                # Obtener el ID del nuevo pedido
                cursor.execute("SELECT LAST_INSERT_ID()")
                nuevo_pedido_id = cursor.fetchone()[0]

                # Insertar detalles de productos en el pedido
                for id_producto in idproductos:
                    cursor.execute("INSERT INTO detalles_pedido (id_pedido, id_producto) VALUES (%s, %s)",
                                   (nuevo_pedido_id, id_producto))

                # Confirmar la transacción
                conexion.commit()

                # Cerrar cursor y conexión
                cursor.close()
                conexion.close()

                # Enviar respuesta exitosa con el ID del nuevo pedido
                self.send_response(201)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'Pedido creado correctamente. ID: {nuevo_pedido_id}'.encode('utf-8'))

            except (ValueError, mysql.connector.Error) as err:
                # Enviar mensaje de error si hay un problema con los datos o la base de datos
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error al crear el pedido: {err}".encode('utf-8'))
        else:
            # Utilizar el manejador original para otras rutas POST
            super().do_POST()

# Crear una instancia de TCPServer con el manejador personalizado
puerto = 8085
with socketserver.TCPServer(("", puerto), MiHandler) as httpd:
    print(f"Sirviendo en el puerto {puerto}")
    httpd.serve_forever()