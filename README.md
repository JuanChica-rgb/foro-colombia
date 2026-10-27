# Foro Colombia

Foro regional sencillo: registro, publicaciones, comentarios y votos.

## Stack

Python · Flask · SQLite · Jinja

## Desarrollo

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set SECRET_KEY=una-clave-local
python app.py
```

La base `foro_colombia.db` se crea sola y no se versiona.

## API

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/` | UI |
| POST | `/api/registro` | Crear cuenta |
| POST | `/api/login` | Entrar |
| GET/POST | `/api/publicaciones` | Listar / crear |
| POST | `/api/comentarios` | Comentar |
| POST | `/api/reacciones` | Voto +1 / -1 |

## Licencia

Uso privado del autor. El código está publicado como portafolio.
