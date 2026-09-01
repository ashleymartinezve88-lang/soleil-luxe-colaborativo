# Soleil Luxe — Sistema de gestión local
Prototipo funcional basado en el documento "Solución Tecnológica para Soleil Luxe (final doc)".
Paleta visual: blanco, negro y dorado.

## Funciones
- Dashboard
- Inventario con stock mínimo
- Registro de ventas y sincronización automática del stock
- Clientes y canal de contacto
- Contabilidad básica (ingresos/egresos)
- Reportes y metas del proyecto
- Base de datos SQLite local

## Ejecutar
1. Instalar Python 3.10+.
2. En la carpeta del proyecto: `pip install -r requirements.txt`
3. Ejecutar: `python app.py`
4. Abrir: `http://127.0.0.1:5000`

La base de datos `soleil_luxe.db` se crea automáticamente al iniciar por primera vez.

## Lucy — asistente virtual
Lucy es un asistente pequeño y local integrado en la interfaz. Es contextual y consulta datos actuales de SQLite para orientar al usuario sobre Inventario, Ventas, Clientes, Contabilidad y Reportes, sin necesitar una API ni una clave externa. Puede detectar stock bajo, explicar procesos y ofrecer un acceso directo a la sección correspondiente.


## Nuevo: portal cliente y espacio colaborativo
- `/cliente`: catálogo interactivo con las fotografías entregadas, selector de cantidades, presupuesto, indicadores y Lucy como asistente de decisión.
- `/colaborativo`: panel del equipo Soleil Luxe para recibir propuestas en vivo, revisar totales y cambiar el estado.
- Las dos vistas usan la misma base SQLite. El panel colaborativo consulta nuevas propuestas automáticamente cada 3 segundos.
- Las propuestas se guardan en `collab_orders` y `collab_items`, de modo que la simulación puede demostrarse abriendo ambas vistas en pestañas simultáneas.
