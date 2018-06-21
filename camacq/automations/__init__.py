"""Handle automations."""
# Copyright 2013-2017 The Home Assistant Authors
# https://github.com/home-assistant/home-assistant/blob/master/LICENSE.md
# This file was modified by The Camacq Authors.
import logging
from collections import deque
from functools import partial
from threading import Timer

import voluptuous as vol
from jinja2 import Template

from camacq.helper import BASE_ACTION_SCHEMA, get_module
from camacq.const import CAMACQ_STOP_EVENT, CONF_DATA, CONF_ID

_LOGGER = logging.getLogger(__name__)

CONF_AUTOMATION = 'automations'
CONF_ACTION = 'action'
CONF_CONDITION = 'condition'
CONF_CONDITIONS = 'conditions'
CONF_NAME = 'name'
CONF_TRIGGER = 'trigger'
CONF_TYPE = 'type'
ENABLED = 'enabled'
NAME = 'name'
ACTION_DELAY = 'delay'
ACTION_TOGGLE = 'toggle'

TOGGLE_ACTION_SCHEMA = BASE_ACTION_SCHEMA.extend({
    NAME: vol.Coerce(str),
    ENABLED: vol.Boolean(),  # pylint: disable=no-value-for-parameter
})


def setup_package(center, config):
    """Set up automations package.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    """
    _process_automations(center, config)

    def handle_action(**kwargs):
        """Enable or disable an automation."""
        name = kwargs.get(NAME)
        if name is None:
            return
        automation = center.data[__name__].get(name)
        if not automation:
            return
        enabled = kwargs.get(ENABLED, not automation.enabled)
        if enabled:
            automation.enable()
        else:
            automation.disable()

    # register action to enable/disable automation
    center.actions.register(
        'automations', ACTION_TOGGLE, handle_action, TOGGLE_ACTION_SCHEMA)


def make_template(data):
    """Make templated data."""
    if isinstance(data, dict):
        return {key: make_template(val) for key, val in data.items()}

    if isinstance(data, list):
        return [make_template(val) for val in data]

    return Template(str(data))


def render_template(data, variables):
    """Render templated data."""
    if isinstance(data, dict):
        return {
            key: render_template(val, variables) for key, val in data.items()}

    if isinstance(data, list):
        return [render_template(val, variables) for val in data]

    return data.render(variables)


class TemplateAction(object):
    """Representation of an action with template data."""

    # pylint: disable=too-few-public-methods

    def __init__(self, center, action_conf):
        """Set up instance."""
        self._center = center
        self.action_id = action_conf.get(CONF_ID)
        self.action_type = action_conf.get(CONF_TYPE)
        action_data = action_conf.get(CONF_DATA, {})
        self.template = make_template(action_data)

    def __call__(self, variables=None):
        """Execute action with optional template variables."""
        rendered = self.render(variables)
        self._center.actions.call(self.action_type, self.action_id, **rendered)

    def render(self, variables):
        """Render the template with the kwargs for the action."""
        variables = variables or {}
        rendered = render_template(self.template, variables)
        return rendered


class Automation(object):
    """Automation class."""

    # pylint: disable=too-many-arguments

    def __init__(
            self, center, name, attach_triggers, cond_func, action_sequence):
        """Set up instance."""
        self._center = center
        self.name = name
        self.enabled = False
        self._action_sequence = action_sequence
        self._attach_triggers = attach_triggers
        self._detach_triggers = None
        self._cond_func = cond_func
        self.enable()

    def __repr__(self):
        """Return the representation."""
        return "<Automation: name: {}: enabled: {}>".format(
            self.name, self.enabled)

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

    def trigger(self, variables):
        """Run actions of this automation."""
        variables['sample'] = self._center.sample
        if self._cond_func(variables):
            self._action_sequence(variables)


class ActionSequence(object):
    """Represent a sequence of actions."""

    # pylint: disable=too-few-public-methods

    def __init__(self, center, actions):
        """Set up instance."""
        self._center = center
        self.actions = list(actions)  # copy to list to make sure it's a list
        self.waiting = None

    def __call__(self, variables):
        """Start action sequence."""
        self.waiting = deque(self.actions)
        while self.waiting:
            action = self.waiting.popleft()

            if (action.action_type == 'automations' and
                    action.action_id == ACTION_DELAY):
                rendered_kwargs = action.render(variables)
                seconds = rendered_kwargs.get('seconds')
                cancel = self.delay(float(seconds), variables)

                def cancel_pending_actions(center, event):
                    """Cancel pending actions."""
                    cancel()

                self._center.bus.register(
                    CAMACQ_STOP_EVENT, cancel_pending_actions)

            else:
                action(variables)

    def delay(self, seconds, variables):
        """Delay action sequence.

        Parameters
        ----------
        seconds : float
            A time interval to delay the pending action sequence.
        variables : dict
            A dict of template variables.

        Returns
        -------
        callable
            Return a funtion to cancel the delay and the pending action.
        """
        sequence = ActionSequence(self._center, self.waiting)
        self.waiting.clear()
        timer = Timer(seconds, sequence, args=(variables, ))
        _LOGGER.debug('Action delay for %s seconds', seconds)
        timer.start()
        return timer.cancel


def _get_actions(center, config_block):
    """Return actions."""
    actions = (
        TemplateAction(center, action_conf) for action_conf in config_block)

    return ActionSequence(center, actions)


def template_check(value):
    """Check if a rendered template string equals true.

    If value is not a string, return value as is.
    """
    if isinstance(value, str):
        return value.lower() == 'true'
    return value


def make_checker(condition_type, checks):
    """Return a function to check condition."""
    def check_condition(variables):
        """Return True if all or any condition(s) pass."""
        if condition_type.lower() == 'and':
            return all(
                template_check(check(variables)) for check in checks)
        elif condition_type.lower() == 'or':
            return any(
                template_check(check(variables)) for check in checks)
        return None
    return check_condition


def _process_condition(config_block):
    """Return a function that parses the condition."""
    if CONF_TYPE in config_block:
        checks = []
        condition_type = config_block[CONF_TYPE]
        conditions = config_block[CONF_CONDITIONS]
        for cond in conditions:
            check = _process_condition(cond)
            checks.append(check)
        return make_checker(condition_type, checks)
    elif CONF_CONDITION in config_block:
        data = config_block[CONF_CONDITION]
        template = make_template(data)
        return partial(render_template, template)
    raise ValueError('Invalid condition: {}'.format(config_block))


def _process_trigger(center, config_block, trigger):
    """Process triggers for an automation."""
    remove_funcs = []

    for conf in config_block:
        trigger_id = conf.get(CONF_ID)
        trigger_type = conf.get(CONF_TYPE)
        trigger_mod = get_module(__name__, trigger_type)
        if not trigger_mod:
            continue
        _LOGGER.info('Setting up trigger %s', trigger_id)

        remove = trigger_mod.handle_trigger(center, conf, trigger)
        if not remove:
            _LOGGER.error('Setting up trigger %s failed', trigger_id)
            continue

        remove_funcs.append(remove)

    if not remove_funcs:
        return None

    def remove_triggers():
        """Remove attached triggers."""
        for remove in remove_funcs:
            remove()

    return remove_triggers


def _process_automations(center, config):
    """Process automations from config."""
    conf = config.get(CONF_AUTOMATION)
    for block in conf:
        name = block[CONF_NAME]
        _LOGGER.info('Setting up automation %s', name)
        action_sequence = _get_actions(center, block.get(CONF_ACTION, []))
        if CONF_CONDITION in block:
            cond_func = _process_condition(block[CONF_CONDITION])
        else:
            def cond_func(variables):
                """Return always True when condition is not used."""
                return True
        # use partial to get a function with args to call later
        attach_triggers = partial(
            _process_trigger, center, block.get(CONF_TRIGGER, []))
        if __name__ not in center.data:
            center.data[__name__] = {}
        center.data[__name__][name] = Automation(
            center, name, attach_triggers, cond_func, action_sequence)
