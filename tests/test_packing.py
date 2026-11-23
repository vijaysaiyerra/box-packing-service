"""Tests for the package-to-box packing algorithm."""

import random

import pytest

from app.services.boxes import Box
from app.services.packing import Package, UnpackablePackagesError, fits_in_box, pack


def package(
    package_id: int,
    width: float,
    height: float,
    length: float,
    weight: float = 1,
) -> Package:
    """Create a package from dimensions and weight."""
    return Package(package_id, width, height, length, weight)


def box_names(result) -> list[str]:
    """Return the box names in a packing result."""
    return sorted(box.box.name for box in result)


def test_empty_input_needs_no_boxes(catalogue) -> None:
    """Pack an empty package list without opening boxes."""
    assert pack([], catalogue) == []


def test_small_package_uses_smallest_fitting_box(catalogue) -> None:
    """Put a small package into box B."""
    assert box_names(pack([package(1, 10, 10, 10)], catalogue)) == ["B"]


def test_assignment_example_fits_in_one_box(catalogue) -> None:
    """Pack the assignment's sample packages together."""
    result = pack([package(123, 10, 10, 10, 5), package(125, 5, 5, 10, 10)], catalogue)

    assert len(result) == 1
    assert result[0].package_ids() == [123, 125]


@pytest.mark.parametrize(
    ("dimensions", "weight", "expected_box"),
    [
        ((300, 400, 300), 3000, "C"),
        ((200, 100, 100), 1, "B"),
        ((5, 5, 400), 1, "C"),
    ],
)
def test_exact_or_rotated_dimensions_fit(
    catalogue,
    dimensions: tuple[float, float, float],
    weight: float,
    expected_box: str,
) -> None:
    """Fit packages at box limits or after rotating them."""
    result = pack([package(1, *dimensions, weight)], catalogue)

    assert box_names(result) == [expected_box]


def test_multiple_packages_share_a_box(catalogue) -> None:
    """Fit eight 75-unit cubes in one box."""
    result = pack([package(i, 75, 75, 75) for i in range(8)], catalogue)

    assert len(result) == 1


def test_many_packages_share_one_large_box(catalogue) -> None:
    """Fit 36 packages in the large box using its available space."""
    result = pack([package(i, 100, 100, 100) for i in range(36)], catalogue)

    assert box_names(result) == ["C"]


def test_packages_use_a_second_box_when_space_runs_out() -> None:
    """Open another box when two cubes cannot share box A."""
    only_a = [Box("A", 150, 150, 150, 1000)]

    assert len(pack([package(i, 100, 100, 100) for i in range(2)], only_a)) == 2


def test_weight_limit_is_respected() -> None:
    """Allow weight exactly at the limit and split weight above the limit."""
    only_a = [Box("A", 150, 150, 150, 1000)]

    assert len(pack([package(1, 1, 1, 1, 500), package(2, 1, 1, 1, 500)], only_a)) == 1
    assert len(pack([package(1, 1, 1, 1, 500), package(2, 1, 1, 1, 501)], only_a)) == 2


@pytest.mark.parametrize(
    "item",
    [package(1, 301, 401, 301), package(2, 1, 1, 401), package(3, 1, 1, 1, 3001)],
)
def test_unfit_packages_are_reported(catalogue, item: Package) -> None:
    """Report a package that exceeds every box's dimensions or weight."""
    with pytest.raises(UnpackablePackagesError) as error:
        pack([item], catalogue)

    assert error.value.packages == [item]


def test_all_unfit_packages_are_reported(catalogue) -> None:
    """Report all packages that cannot fit any box."""
    packages = [package(1, 1, 1, 1), package(2, 999, 1, 1), package(3, 1, 1, 1, 9999)]

    with pytest.raises(UnpackablePackagesError) as error:
        pack(packages, catalogue)

    assert [item.id for item in error.value.packages] == [2, 3]


def test_fit_check_checks_dimensions_and_weight(catalogue) -> None:
    """Check individual package dimensions and weight against a box."""
    box_a = next(box for box in catalogue if box.name == "A")

    assert fits_in_box(package(1, 150, 150, 150, 1000), box_a)
    assert not fits_in_box(package(1, 151, 150, 150), box_a)
    assert not fits_in_box(package(1, 1, 1, 1, 1001), box_a)


def test_input_order_does_not_change_box_count(catalogue) -> None:
    """Keep box count stable after shuffling and leave the input unchanged."""
    packages = [package(i, 20 + i % 50, 30 + i % 60, 10 + i % 90, 5 + i) for i in range(40)]
    original = packages.copy()
    shuffled = packages.copy()
    random.Random(1).shuffle(shuffled)

    assert len(pack(packages, catalogue)) == len(pack(shuffled, catalogue))
    assert packages == original


@pytest.mark.parametrize("seed", range(10))
def test_random_packings_preserve_invariants(catalogue, seed: int) -> None:
    """Pack each generated package exactly once within box weight limits."""
    rng = random.Random(seed)
    packages = [
        package(
            package_id,
            rng.randint(1, 150),
            rng.randint(1, 150),
            rng.randint(1, 150),
            rng.randint(1, 400),
        )
        for package_id in range(rng.randint(1, 30))
    ]
    result = pack(packages, catalogue)

    assert sorted(item.id for box in result for item in box.packages) == sorted(
        item.id for item in packages
    )
    assert all(box.total_weight() <= box.box.max_weight for box in result)
    assert all(
        fits_in_box(item, box.box)
        for box in result
        for item in box.packages
    )
    assert all(
        sum(item.volume for item in box.packages) <= box.box.volume
        for box in result
    )
