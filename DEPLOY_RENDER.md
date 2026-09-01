# Publicar Soleil Luxe en Render

1. Sube el contenido de esta carpeta a un repositorio de GitHub.
2. En Render: New > Web Service.
3. Conecta el repositorio.
4. Si no usas render.yaml, usa:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app`
5. Plan: Free para la demostración.
6. Nombre recomendado: `soleil-luxe-colaborativo`.
7. Pulsa Create Web Service.

Render entregará una URL `https://...onrender.com`.

Nota: el plan Free es ideal para una demo, pero el servicio puede dormirse tras 15 minutos sin actividad y el almacenamiento local no es persistente.
