# Box Packing Service

A FastAPI service that provides the configured shipping box catalogue.
The box values are currently stored in code in `app/boxes.py`; they are not
persisted in a database.

## Run locally

Requires Python 3.12 or newer.

```powershell
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to explore and call the endpoint in Swagger UI.

## API

### `GET /v1/get_boxes`

Returns the available box types, including their dimensions and maximum weight.

Example response:

```json
[
  {
    "name": "A",
    "width": 150,
    "height": 150,
    "length": 150,
    "maxWeight": 1000
  },
  {
    "name": "B",
    "width": 100,
    "height": 200,
    "length": 100,
    "maxWeight": 1000
  },
  {
    "name": "C",
    "width": 300,
    "height": 400,
    "length": 300,
    "maxWeight": 3000
  }
]
```

## Project layout

```text
app/
  __init__.py
  boxes.py     In-code box catalogue
  main.py      FastAPI application and routes
  schemas.py   Box response model
requirements.txt
README.md
```
