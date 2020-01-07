"""Test the control module."""
import asynctest
import pytest
import voluptuous as vol

from camacq.const import CAMACQ_START_EVENT, CAMACQ_STOP_EVENT

# pylint: disable=redefined-outer-name
# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio  # pylint: disable=invalid-name


async def test_center_start(center):
    """Test start of Center."""
    events = []
    exit_code = 0

    async def handle_event(center, event):
        """Stop the task that listens to the client socket."""
        events.append(event)

    center.bus.register(CAMACQ_START_EVENT, handle_event)
    center._track_tasks = False  # pylint: disable=protected-access
    task = center.create_task(center.start())
    await center.wait_for()
    await center.end(exit_code)
    await center.wait_for()

    assert len(events) == 1
    assert task.result() == exit_code


async def test_center_end(center):
    """Test end of Center."""
    events = []

    async def handle_event(center, event):
        """Stop the task that listens to the client socket."""
        events.append(event)

    center.bus.register(CAMACQ_STOP_EVENT, handle_event)

    await center.end(0)

    assert len(events) == 1
    assert events[0].exit_code == 0


async def test_add_executor_job(center):
    """Test create task."""

    def exec_fun(one, two):
        """Test executor function."""
        return one + two

    result = await center.add_executor_job(exec_fun, 1, 2)

    assert result == 3


async def test_create_task(center):
    """Test create task."""
    coro_fun = asynctest.CoroutineMock()
    task = center.create_task(coro_fun())
    await task

    assert coro_fun.awaited
    assert task.done()


async def test_wait_for(center):
    """Test wait for tracked tasks."""
    sec_coro_fun = asynctest.CoroutineMock()

    async def schedule_task(center):
        """Schedule a new task."""
        center.create_task(sec_coro_fun())

    task = center.create_task(schedule_task(center))
    await center.wait_for()

    assert sec_coro_fun.awaited
    assert task.done()


async def test_register_call_action(center):
    """Test register and call an action."""
    action_type = "command"
    action_id = "test"
    result = []

    async def test_action(**kwargs):
        """Test the action handler."""
        result.append(kwargs["one"] + kwargs["two"])

    schema = vol.Schema({"one": int, "two": int})
    center.actions.register(action_type, action_id, test_action, schema)
    await center.actions.call(action_type, action_id, one=1, two=2)

    assert len(center.actions.actions) == 1
    assert action_type in center.actions.actions
    assert action_id in center.actions.actions[action_type]
    assert len(result) == 1
    assert result[0] == 3


async def test_register_non_coroutine(center, caplog):
    """Test register an action with non coroutine function as handler."""
    action_type = "command"
    action_id = "test"

    def test_action(**kwargs):
        """Test the action handler as non coroutine function."""

    schema = vol.Schema({"one": int, "two": int})
    center.actions.register(action_type, action_id, test_action, schema)
    assert not center.actions.actions
    assert (
        f"Action handler function {test_action} is not a coroutine function"
        in caplog.text
    )


async def test_call_non_action(center, caplog):
    """Test call a non registered action."""
    action_type = "command"
    action_id = "test"

    await center.actions.call(action_type, action_id)

    assert not center.actions.actions
    assert (
        f"No action registered for type {action_type} or id {action_id}" in caplog.text
    )


async def test_call_invalid_args(center, caplog):
    """Test register and call an action."""
    action_type = "command"
    action_id = "test"
    result = []

    async def test_action(**kwargs):
        """Test the action handler."""
        result.append(kwargs["one"] + kwargs["two"])

    schema = vol.Schema({"one": int, "two": int})
    center.actions.register(action_type, action_id, test_action, schema)
    await center.actions.call(action_type, action_id, bad=1, two="str")

    assert len(center.actions.actions) == 1
    assert action_type in center.actions.actions
    assert action_id in center.actions.actions[action_type]
    assert not result
    assert "Invalid action call parameters" in caplog.text
