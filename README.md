# Box Packing Service

A FastAPI service that provides the configured shipping box catalogue.
The box values are currently stored in code in `app/services/boxes.py`; they are not
persisted in a database.

## Run locally

Requires Python 3.12 or newer.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The source app does not need a separate build step. After installing dependencies,
start it with `python -m uvicorn app.main:app --reload`.
Set `DEBUG = True` in `app/main.py` to include full request and response payloads
in the logs. Set it to `False` to show INFO logs only.

Open `http://127.0.0.1:8000/docs` to explore and call the endpoints in Swagger UI.

Run the unit and API tests with:

```powershell
python -m pytest
```

## Run with Docker

Requires Docker with Docker Compose. From the repository root, build the image
and start the service with one command:

```powershell
docker compose up --build
```

Open `http://127.0.0.1:8000/docs` to use the API. Stop the service with `Ctrl+C`;
run `docker compose down` to remove its container.

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
`422` error with a `code`, `message`, and `details` field. Unknown routes return
a consistent `404` error. Unexpected server errors return a generic `500`
response without exposing internal details.

### `GET /v1/boxes`

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

## Packing approach and assumptions

- Package and box dimensions use the same units; packages may be rotated.
- Multiple packages can share a box when they fit in the remaining space and the
  combined weight stays within the box's `maxWeight`.
- Package IDs must be unique. Requests must contain 1 to 1000 packages, with
  positive finite dimensions and weight.
- A package that cannot fit any available box is rejected with a `422`
  `unpackable_packages` response. Empty or invalid requests also receive `422`.
- The packer orders packages by size and tries small-box-first and
  large-box-first strategies. It chooses the better result of those attempts;
  this is a heuristic and is not guaranteed to find the globally minimal count.

With more time, I would expand the packing heuristic and test it against a
broader set of generated package combinations.

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
tests/
  test_api.py       Endpoint and validation tests
  test_packing.py   Packing algorithm tests
requirements.txt
Dockerfile
compose.yaml
.dockerignore
README.md
```
