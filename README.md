# Box Packing Service

A FastAPI service that provides the configured shipping box catalogue.
The box values are currently stored in code in `app/services/boxes.py`; they are not
persisted in a database.

## Run locally

Requires Python 3.12 or newer.

```powershell
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to explore and call the endpoint in Swagger UI.

## API

### `POST /v1/packages/box-count`

Provide a JSON array of packages. Each package must have a unique integer `id`
and positive `width`, `height`, `length`, and `weight` values. Dimensions are
checked in any orientation, and both box size and maximum weight are considered.

Example request:

```json
[
  {
    "id": 123,
    "width": 10,
    "height": 10,
    "length": 10,
    "weight": 5
  }
]
```

Example response:

```json
{
  "boxCount": 1,
  "boxes": [
    {
      "type": "B",
      "packageIds": [123],
      "totalWeight": 5
    }
  ]
}
```

Invalid package data, duplicate IDs, and packages that do not fit return a
`422` error with a `code`, `message`, and `details` field.

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
  errors.py    API error responses
  main.py      API endpoints
  schemas.py   Request and response models
  services/
    __init__.py
    box_service.py  Box lookup and package packing
    boxes.py        In-code box catalogue
    packing.py      Package fitting and box assignment
requirements.txt
README.md
```
