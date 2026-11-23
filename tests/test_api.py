"""Tests for package and box HTTP endpoints."""

import logging

import pytest
from fastapi.testclient import TestClient

BOX_COUNT_URL = "/v1/packages/box-count"
EXAMPLE = [
    {"id": 123, "width": 10, "height": 10, "length": 10, "weight": 5},
    {"id": 125, "width": 5, "height": 5, "length": 10, "weight": 10},
]


def error_of(response) -> dict:
    """Return the standard error body after checking its shape."""
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    return body["error"]


def test_assignment_example_returns_box_count(client: TestClient) -> None:
    """Return one box with the assignment example packages."""
    response = client.post(BOX_COUNT_URL, json=EXAMPLE)

    assert response.status_code == 200
    assert response.json() == {
        "boxCount": 1,
        "boxes": [{"type": "B", "packageIds": [123, 125], "totalWeight": 15.0}],
    }


def test_packing_logs_a_summary(client: TestClient, caplog) -> None:
    """Log the number of input packages and boxes in the result."""
    with caplog.at_level(logging.INFO):
        response = client.post(BOX_COUNT_URL, json=EXAMPLE)

    assert response.status_code == 200
    assert "Packing completed: packages=2 boxes=1" in caplog.text


def test_multiple_boxes_return_all_package_ids(client: TestClient) -> None:
    """Return every package ID when separate boxes are required."""
    package = {"width": 300, "height": 400, "length": 300, "weight": 100}
    response = client.post(
        BOX_COUNT_URL,
        json=[{"id": package_id, **package} for package_id in (1, 2)],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["boxCount"] == 2
    assert sorted(package_id for box in body["boxes"] for package_id in box["packageIds"]) == [1, 2]


def test_empty_package_list_is_rejected(client: TestClient) -> None:
    """Reject an empty list with the standard validation response."""
    response = client.post(BOX_COUNT_URL, json=[])

    assert response.status_code == 422
    assert error_of(response)["code"] == "validation_error"


@pytest.mark.parametrize("field", ["width", "height", "length", "weight"])
@pytest.mark.parametrize("value", [-1, 0])
def test_non_positive_values_are_rejected(
    client: TestClient,
    example_package: dict[str, int | float],
    field: str,
    value: int,
) -> None:
    """Reject zero and negative dimensions or weight with a useful field path."""
    response = client.post(BOX_COUNT_URL, json=[{**example_package, field: value}])

    assert response.status_code == 422
    error = error_of(response)
    assert error["code"] == "validation_error"
    assert error["details"][0]["field"] == f"[0].{field}"


@pytest.mark.parametrize("field", ["id", "width", "height", "length", "weight"])
def test_missing_package_fields_are_rejected(
    client: TestClient,
    example_package: dict[str, int | float],
    field: str,
) -> None:
    """Reject packages missing required fields."""
    package = {key: value for key, value in example_package.items() if key != field}
    response = client.post(BOX_COUNT_URL, json=[package])

    assert response.status_code == 422
    assert error_of(response)["details"][0]["field"] == f"[0].{field}"


def test_wrong_types_are_rejected(
    client: TestClient, example_package: dict[str, int | float]
) -> None:
    """Reject values that cannot be parsed as package measurements."""
    response = client.post(BOX_COUNT_URL, json=[{**example_package, "width": "wide"}])

    assert response.status_code == 422
    assert error_of(response)["code"] == "validation_error"


def test_unknown_package_fields_are_rejected(
    client: TestClient, example_package: dict[str, int | float]
) -> None:
    """Reject fields that are not part of the package schema."""
    response = client.post(BOX_COUNT_URL, json=[{**example_package, "colour": "red"}])

    assert response.status_code == 422


def test_non_list_request_body_is_rejected(
    client: TestClient, example_package: dict[str, int | float]
) -> None:
    """Require a list of packages as the request body."""
    assert client.post(BOX_COUNT_URL, json=example_package).status_code == 422


def test_malformed_json_is_rejected(client: TestClient) -> None:
    """Return a validation response for malformed JSON."""
    response = client.post(
        BOX_COUNT_URL,
        content="{not json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert error_of(response)["code"] == "validation_error"


def test_duplicate_ids_are_rejected(
    client: TestClient, example_package: dict[str, int | float]
) -> None:
    """Reject duplicate IDs and identify the repeated package."""
    response = client.post(BOX_COUNT_URL, json=[example_package, example_package])

    assert response.status_code == 422
    error = error_of(response)
    assert error["code"] == "duplicate_package_ids"
    assert error["details"] == [
        {"package_id": 123, "message": "id appears more than once"}
    ]


def test_more_than_1000_packages_are_rejected(
    client: TestClient, example_package: dict[str, int | float]
) -> None:
    """Enforce the package-list size limit."""
    packages = [{**example_package, "id": package_id} for package_id in range(1001)]

    assert client.post(BOX_COUNT_URL, json=packages).status_code == 422


def test_unfit_package_is_reported_with_its_id(
    client: TestClient, example_package: dict[str, int | float]
) -> None:
    """Return a deliberate packing error instead of a server error."""
    packages = [example_package, {**example_package, "id": 9, "width": 1000}]
    response = client.post(BOX_COUNT_URL, json=packages)

    assert response.status_code == 422
    error = error_of(response)
    assert error["code"] == "unpackable_packages"
    assert [detail["package_id"] for detail in error["details"]] == [9]


def test_overweight_package_is_unpackable(
    client: TestClient, example_package: dict[str, int | float]
) -> None:
    """Reject a package heavier than every configured box allows."""
    response = client.post(BOX_COUNT_URL, json=[{**example_package, "weight": 5000}])

    assert response.status_code == 422
    assert error_of(response)["code"] == "unpackable_packages"


def test_unknown_route_returns_standard_error(client: TestClient) -> None:
    """Use the standard error shape for unknown routes."""
    response = client.get("/nope")

    assert response.status_code == 404
    assert error_of(response)["code"] == "http_error"


def test_wrong_method_returns_standard_error(client: TestClient) -> None:
    """Use the standard error shape when a route receives the wrong method."""
    response = client.get(BOX_COUNT_URL)

    assert response.status_code == 405
    assert error_of(response)["code"] == "http_error"


def test_box_endpoint_returns_catalogue(client: TestClient) -> None:
    """Return all configured box types with their public field names."""
    response = client.get("/v1/get_boxes")

    assert response.status_code == 200
    boxes = response.json()
    assert [box["name"] for box in boxes] == ["A", "B", "C"]
    assert boxes[0]["maxWeight"] == 1000

