"""Handle automations."""

# Copyright 2013-2017 The Home Assistant Authors
# https://github.com/home-assistant/home-assistant/blob/master/LICENSE.md
# This file was modified by The Camacq Authors.
import logging
from collections import deque
from functools import partial

import voluptuous as vol

from camacq.exceptions import TemplateError
from camacq.helper import BASE_ACTION_SCHEMA, get_module, has_at_least_one_key
from camacq.helper.template import make_template, render_template
from camacq.const import CAMACQ_STOP_EVENT, CONF_DATA, CONF_ID

_LOGGER = logging.getLogger(__name__)

CONF_AUTOMATIONS = "automations"
CONF_ACTION = "action"
CONF_CONDITION = "condition"
CONF_CONDITIONS = "conditions"
CONF_NAME = "name"
CONF_TRIGGER = "trigger"
CONF_TYPE = "type"
ENABLED = "enabled"
NAME = "name"
ACTION_DELAY = "delay"
ACTION_TOGGLE = "toggle"
DATA_AUTOMATIONS = "automations"

TRIGGER_ACTION_SCHEMA = vol.Schema(
    [
        {
            vol.Required(CONF_TYPE): vol.Coerce(str),
            vol.Required(CONF_ID): vol.Coerce(str),
            vol.Optional(CONF_DATA, default={}): dict,
        }
    ],
)

CONDITION_SCHEMA = vol.All(
    has_at_least_one_key(CONF_TYPE, CONF_CONDITION),
    {
        # pylint: disable=no-value-for-parameter
        vol.Inclusive(CONF_TYPE, "condition"): vol.All(
            vol.Upper, vol.In(["AND", "OR"])
        ),
        vol.Inclusive(CONF_CONDITIONS, "condition"): [
            # pylint: disable=unnecessary-lambda
            lambda value: CONDITION_SCHEMA(value)
        ],
        vol.Exclusive(CONF_CONDITION, "condition"): vol.Coerce(str),
    },
)

CONFIG_SCHEMA = vol.Schema(
    [
        {
            vol.Required(CONF_NAME): vol.Coerce(str),
            vol.Required(CONF_TRIGGER): TRIGGER_ACTION_SCHEMA,
            vol.Required(CONF_ACTION): TRIGGER_ACTION_SCHEMA,
            vol.Optional(
                CONF_CONDITION, default={CONF_CONDITION: "true"}
            ): CONDITION_SCHEMA,
        }
    ]
)


async def setup_module(center, config):
    """Set up automations package.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    """
    _process_automations(center, config)
    automations = center.data[DATA_AUTOMATIONS]

    async def handle_action(**kwargs):
        """Enable or disable an automation."""
        name = kwargs[NAME]
        automation = automations[name]
        enabled = kwargs.get(ENABLED, not automation.enabled)
        if enabled:
            automation.enable()
        else:
            automation.disable()

    toggle_action_schema = BASE_ACTION_SCHEMA.extend(
        {
            vol.Required(NAME): vol.All(vol.Coerce(str), vol.In(automations)),
            ENABLED: vol.Boolean(),  # pylint: disable=no-value-for-parameter
        }
    )

    # register action to enable/disable automation
    center.actions.register(
        "automations", ACTION_TOGGLE, handle_action, toggle_action_schema
    )


def _process_automations(center, config):
    """Process automations from config."""
    automations = center.data.setdefault(DATA_AUTOMATIONS, {})
    conf = config[CONF_AUTOMATIONS]
    for block in conf:
        name = block[CONF_NAME]
        _LOGGER.debug("Setting up automation %s", name)
        action_sequence = _get_actions(center, block[CONF_ACTION])
        cond_func = _process_condition(center, block[CONF_CONDITION])
        # use partial to get a function with args to call later
        attach_triggers = partial(_process_trigger, center, block[CONF_TRIGGER])
        automations[name] = Automation(
            center, name, attach_triggers, cond_func, action_sequence
        )


def _get_actions(center, config_block):
    """Return actions."""
    actions = (TemplateAction(center, action_conf) for action_conf in config_block)

    return ActionSequence(center, actions)


def _process_condition(center, config_block):
    """Return a function that parses the condition."""
    if CONF_TYPE in config_block:
        checks = []
        condition_type = config_block[CONF_TYPE]
        conditions = config_block[CONF_CONDITIONS]
        for cond in conditions:
            check = _process_condition(center, cond)
            checks.append(check)
        return make_checker(condition_type, checks)

    data = config_block[CONF_CONDITION]
    template = make_template(center, data)
    return partial(render_template, template)


def make_checker(condition_type, checks):
    """Return a function to check condition."""

    def check_condition(variables):
        """Return True if all or any condition(s) pass."""
        if condition_type.lower() == "and":
            return all(template_check(check(variables)) for check in checks)
        if condition_type.lower() == "or":
            return any(template_check(check(variables)) for check in checks)
        return False

    return check_condition


def template_check(value):
    """Check if a rendered template string equals true.

    If value is not a string, return value as is.
    """
    if isinstance(value, str):
        return value.lower() == "true"
    return value


def _process_trigger(center, config_block, trigger):
    """Process triggers for an automation."""
    remove_funcs = []

    for conf in config_block:
        trigger_id = conf[CONF_ID]
        trigger_type = conf[CONF_TYPE]
        trigger_mod = get_module(__name__, trigger_type)
        if not trigger_mod:
            continue
        _LOGGER.debug("Setting up trigger %s", trigger_id)

        remove = trigger_mod.handle_trigger(center, conf, trigger)
        if not remove:
            _LOGGER.error("Setting up trigger %s failed", trigger_id)
            continue

        remove_funcs.append(remove)

    if not remove_funcs:
        return None

    def remove_triggers():
        """Remove attached triggers."""
        for remove in remove_funcs:
            remove()

    return remove_triggers


class Automation:
    """Automation class."""

    # pylint: disable=too-many-arguments

    def __init__(
        self, center, name, attach_triggers, cond_func, action_sequence, enabled=True
    ):
        """Set up instance."""
        self._center = center
        self.name = name
        self.enabled = False
        self._action_sequence = action_sequence
        self._attach_triggers = attach_triggers
        self._detach_triggers = None
        self._cond_func = cond_func
        if enabled:
            self.enable()

    def __repr__(self):
        """Return the representation."""
        return (
            f"Automation(center={self._center}, name={self.name}, "
            f"attach_triggers={self._attach_triggers}, cond_func={self._cond_func}, "
            f"action_sequence={self._action_sequence}, enabled={self.enabled})"
        )

    def enable(self):
        """Enable automation."""
        if self.enabled:
            return
        self._detach_triggers = self._attach_triggers(self.trigger)
        self.enabled = True

    def disable(self):
        """Disable automation."""
        if not self.enabled:
            return
        if self._detach_triggers is not None:
            self._detach_triggers()
        self._detach_triggers = None
        self.enabled = False

    async def trigger(self, variables):
        """Run actions of this automation."""
        variables["samples"] = self._center.samples
        _LOGGER.debug("Triggered automation %s", self.name)
        try:
            cond = self._cond_func(variables)
        except TemplateError as exc:
            _LOGGER.error("Failed to render condition for %s: %s", self.name, exc)
            return
        if cond:
            _LOGGER.debug("Condition passed for %s", self.name)
            await self._action_sequence(variables)


class ActionSequence:
    """Represent a sequence of actions."""

    # pylint: disable=too-few-public-methods

    def __init__(self, center, actions):
        """Set up instance."""
        self._center = center
        self.actions = list(actions)  # copy to list to make sure it's a list

    async def __call__(self, variables):
        """Start action sequence."""
        waiting = deque(self.actions)
        while waiting:
            action = waiting.popleft()

            if action.action_type == "automations" and action.action_id == ACTION_DELAY:
                rendered_kwargs = action.render(variables)
                seconds = rendered_kwargs.get("seconds")
                self.delay(float(seconds), variables, waiting)

            else:
                _LOGGER.debug(
                    "Calling action %s.%s", action.action_type, action.action_id
                )
                await action(variables)

    def delay(self, seconds, variables, waiting):
        """Delay action sequence.

        Parameters
        ----------
        seconds : float
            A time interval to delay the pending action sequence.
        variables : dict
            A dict of template variables.
        """
        sequence = ActionSequence(self._center, waiting)
        callback = partial(self._center.create_task, sequence(variables))
        waiting.clear()
        _LOGGER.info("Action delay for %s seconds", seconds)
        callback = self._center.loop.call_later(seconds, callback)

        async def cancel_pending_actions(center, event):
            """Cancel pending actions."""
            callback.cancel()

        self._center.bus.register(CAMACQ_STOP_EVENT, cancel_pending_actions)


class TemplateAction:
    """Representation of an action with template data."""

    # pylint: disable=too-few-public-methods

    def __init__(self, center, action_conf):
        """Set up instance."""
        self._center = center
        self.action_id = action_conf[CONF_ID]
        self.action_type = action_conf[CONF_TYPE]
        action_data = action_conf[CONF_DATA]
        self.template = make_template(center, action_data)

    async def __call__(self, variables=None):
        """Execute action with optional template variables."""
        try:
            rendered = self.render(variables)
        except TemplateError:
            return
        await self._center.actions.call(self.action_type, self.action_id, **rendered)

    def render(self, variables):
        """Render the template with the kwargs for the action."""
        variables = variables or {}
        try:
            rendered = render_template(self.template, variables)
        except TemplateError as exc:
            _LOGGER.error(
                "Failed to render variables for %s.%s: %s",
                self.action_type,
                self.action_id,
                exc,
            )
            raise
        return rendered
