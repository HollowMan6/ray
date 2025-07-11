import pandas as pd
import pytest

import ray
from ray._private.test_utils import run_string_as_driver
from ray.data.block import BlockMetadata
from ray.data.context import DataContext
from ray.data.datasource import Datasource, ReadTask
from ray.tests.conftest import *  # noqa

# Auto-use `restore_data_context` for each test.
pytestmark = pytest.mark.usefixtures("restore_data_context")


def test_context_saved_when_dataset_created(
    ray_start_regular_shared,
):
    ctx = DataContext.get_current()
    ctx.set_config("foo", 1)
    d1 = ray.data.range(10)
    d2 = ray.data.range(10)
    assert ctx.get_config("foo") == 1
    assert d1.context.get_config("foo") == 1
    assert d2.context.get_config("foo") == 1

    # Changing `d1.context` should not affect `d2.context` or the global context.
    d1.context.set_config("foo", 2)
    assert d1.context.get_config("foo") == 2
    assert d2.context.get_config("foo") == 1
    assert ctx.get_config("foo") == 1

    # Changed value can be propagated to remote tasks.
    @ray.remote(num_cpus=0)
    def check(d1, d2):
        assert d1.context.get_config("foo") == 2
        assert d2.context.get_config("foo") == 1

    ray.get(check.remote(d1, d2))

    # Changing the global context should not affect `d1.context` or `d2.context`.
    ctx.set_config("foo", 3)
    assert ctx.get_config("foo") == 3
    assert d1.context.get_config("foo") == 2
    assert d2.context.get_config("foo") == 1


def test_context_inheritance(ray_start_regular_shared):
    ds = ray.data.range(10)
    ds.context.set_config("foo", 1)
    assert DataContext.get_current().get_config("foo", None) is None

    # Test that applying a new operator to an existing dataset
    # inherits the context.
    ds2 = ds.map_batches(lambda batch: batch)
    assert ds2.context.get_config("foo") == 1

    # Test that materializing a dataset also inherits the context.
    mds = ds.materialize()
    assert mds.context.get_config("foo") == 1

    # Test that the iterator also inherits the context.
    iter = ds.iterator()
    assert iter.get_context().get_config("foo") == 1
    assert iter.materialize().context.get_config("foo") == 1


def _test_updating_context_after_dataset_creation(gen_ds):
    context = DataContext.get_current()
    context.set_config("foo", 1)
    ds = gen_ds()
    assert ds.take_all()[0]["id"] == 1
    # DataContext is supposed to be sealed when a Dataset is created.
    # Test that updating the current DataContext doesn't affect existing Datasets.
    context.set_config("foo", 2)
    assert ds.take_all()[0]["id"] == 1


def test_read(
    ray_start_regular_shared,
):
    class CustomDatasource(Datasource):
        def prepare_read(self, parallelism: int):
            def read_fn():
                value = DataContext.get_current().get_config("foo")
                return [pd.DataFrame({"id": [value]})]

            meta = BlockMetadata(
                num_rows=1, size_bytes=8, input_files=None, exec_stats=None
            )
            return [ReadTask(read_fn, meta)]

    _test_updating_context_after_dataset_creation(
        lambda: ray.data.read_datasource(CustomDatasource()),
    )


def test_map(
    ray_start_regular_shared,
):
    _test_updating_context_after_dataset_creation(
        lambda: ray.data.range(1).map(
            lambda _: {"id": DataContext.get_current().get_config("foo")}
        )
    )


def test_flat_map(
    ray_start_regular_shared,
):
    _test_updating_context_after_dataset_creation(
        lambda: ray.data.range(1).flat_map(
            lambda _: [{"id": DataContext.get_current().get_config("foo")}]
        )
    )


def test_map_batches(
    ray_start_regular_shared,
):
    _test_updating_context_after_dataset_creation(
        lambda: ray.data.range(1).map_batches(
            lambda x: {"id": [DataContext.get_current().get_config("foo")]}
        )
    )


def test_filter(
    ray_start_regular_shared,
):
    _test_updating_context_after_dataset_creation(
        lambda: ray.data.from_items([1])
        .filter(lambda x: x["item"] == DataContext.get_current().get_config("foo"))
        .rename_columns({"item": "id"})
    )


def test_streaming_split(
    ray_start_regular_shared,
):
    # Tests that custom DataContext can be properly propagated
    # when using `streaming_split()`.
    block_size = 123 * 1024 * 1024
    data_context = DataContext.get_current()
    data_context.target_max_block_size = block_size
    data_context.set_config("foo", "bar")

    def f(x):
        assert DataContext.get_current().target_max_block_size == block_size
        assert DataContext.get_current().get_config("foo") == "bar"
        return x

    num_splits = 2
    splits = (
        ray.data.range(10, override_num_blocks=10).map(f).streaming_split(num_splits)
    )

    @ray.remote(num_cpus=0)
    def consume(split):
        for _ in split.iter_rows():
            pass

    assert ray.get([consume.remote(split) for split in splits]) == [None] * num_splits


def test_context_placement_group():
    driver_code = """
import ray
from ray.data.context import DataContext
from ray.util.scheduling_strategies import PlacementGroupSchedulingStrategy
from ray._private.test_utils import placement_group_assert_no_leak

ray.init(num_cpus=1)

context = DataContext.get_current()
# This placement group will take up all cores of the local cluster.
placement_group = ray.util.placement_group(
    name="core_hog",
    strategy="SPREAD",
    bundles=[
        {"CPU": 1},
    ],
)
ray.get(placement_group.ready())
context.scheduling_strategy = PlacementGroupSchedulingStrategy(placement_group)
ds = ray.data.range(100, override_num_blocks=2).map(lambda x: {"id": x["id"] + 1})
assert ds.take_all() == [{"id": x} for x in range(1, 101)]
placement_group_assert_no_leak([placement_group])
ray.shutdown()
    """

    # Successful exit is sufficient to verify this test.
    run_string_as_driver(driver_code)


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main(["-v", __file__]))
