"""Handle automations."""
# Copyright 2013-2017 The Home Assistant Authors
# https://github.com/home-assistant/home-assistant/blob/master/LICENSE.md
# This file was modified by The Camacq Authors.
import logging
from functools import partial

from jinja2 import Template

from camacq.helper import get_module
from camacq.const import CONF_DATA, CONF_ID, PACKAGE

_LOGGER = logging.getLogger(__name__)

CONF_AUTOMATION = __name__.split('.')[-1]
CONF_ACTION = 'action'
CONF_NAME = 'name'
CONF_TRIGGER = 'trigger'
CONF_TYPE = 'type'
ENABLED = 'enabled'
NAME = 'name'
ACTION_TOGGLE = 'toggle'


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
    center.actions.register(__name__, ACTION_TOGGLE, handle_action)


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
        action_type = action_conf.get(CONF_TYPE, '')
        self.module = '{}.{}'.format(PACKAGE, action_type)
        action_data = action_conf.get(CONF_DATA, {})
        self.template = make_template(action_data)

    def __call__(self, variables=None):
        """Execute action with optional template variables."""
        variables = variables or {}
        rendered = render_template(self.template, variables)
        self._center.actions.call(self.module, self.action_id, **rendered)


class Automation(object):
    """Automation class."""

    def __init__(self, center, name, attach_triggers, actions):
        """Set up instance."""
        self._center = center
        self.name = name
        self.enabled = False
        self._actions = actions
        self._attach_triggers = attach_triggers
        self._detach_triggers = None
        self.enable()

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
        for action in self._actions:
            action(variables)


def _get_actions(center, config_block):
    """Return actions."""
    actions = []

    for action_conf in config_block:
        actions.append(TemplateAction(center, action_conf))

    return actions


def _process_trigger(center, config_block, trigger):
    """Process triggers for an automation."""
    remove_funcs = []

    for conf in config_block:
        trigger_id = conf.get(CONF_ID)
        trigger_type = conf.get(CONF_TYPE)
        trigger_mod = get_module(__name__, trigger_type)
        if not trigger_mod:
            continue
        remove = trigger_mod.handle_trigger(center, conf, trigger)

        if not remove:
            _LOGGER.error('Setting up trigger %s failed', trigger_id)
            continue

        _LOGGER.info('Set up trigger %s', trigger_id)
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
        actions = _get_actions(center, block.get(CONF_ACTION, []))
        # use partial to get a function with args to call later
        attach_triggers = partial(
            _process_trigger, center, block.get(CONF_TRIGGER, []))
        if __name__ not in center.data:
            center.data[__name__] = {}
        center.data[__name__][name] = Automation(
            center, name, attach_triggers, actions)
