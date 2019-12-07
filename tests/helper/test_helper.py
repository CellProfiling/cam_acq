"""Test helper module."""
import asynctest
import pytest
import voluptuous as vol

from camacq import helper

# pylint: disable=redefined-outer-name
# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio  # pylint: disable=invalid-name


class MockModule:
    """Represent a mock module."""

    # pylint: disable=too-few-public-methods

    def __init__(self, module_name, setup_module=None, config_schema=None):
        """Set up the mock module."""
        # pylint: disable=invalid-name
        self.__name__ = f"camacq.plugins.{module_name}"
        self.__file__ = f"camacq.plugins/{module_name}"

        if setup_module is not None:
            self.setup_module = setup_module
        else:
            self.setup_module = asynctest.CoroutineMock()

        if config_schema is not None:
            self.CONFIG_SCHEMA = config_schema


@pytest.fixture(name="module")
def module_fixture():
    """Mock a module."""
    return MockModule("test")


@pytest.fixture(name="schema_module")
def schema_module_fixture():
    """Mock a module."""
    schema = vol.Schema({vol.Required("test_option"): True})
    return MockModule("test", config_schema=schema)


async def test_setup_module(center, module):
    """Test set up module."""
    config = {"test": {}}
    await helper.setup_one_module(center, config, module)
    assert module.setup_module.call_count == 1
    _, args, kwargs = module.setup_module.mock_calls[0]
    assert args == (center, config)
    assert kwargs == {}


async def test_setup_schema_module(center, schema_module):
    """Test set up module with config schema."""
    module = schema_module
    config = {"test": {"test_option": True}}
    await helper.setup_one_module(center, config, module)
    assert module.setup_module.call_count == 1
    _, args, kwargs = module.setup_module.mock_calls[0]
    assert args == (center, config)
    assert kwargs == {}


async def test_setup_bad_config(center, schema_module, caplog):
    """Test set up module with config schema and bad config."""
    module = schema_module
    config = {"test": {"test_option": False}}
    await helper.setup_one_module(center, config, module)
    assert module.setup_module.call_count == 0
    assert "Incorrect configuration for module test" in caplog.text


async def test_missing_setup(center, caplog):
    """Test missing setup function."""
    const_module = helper.get_module("camacq", "const")
    assert const_module.__name__ == "camacq.const"
    await helper.setup_one_module(center, {}, const_module)
    assert "Missing setup_module function in module const" in caplog.text


async def test_many_module_matches(center):
    """Test many module matches."""
    with pytest.raises(ValueError):
        helper.get_module("camacq.plugins", "")
