# camacq [![Build Status](https://github.com/CellProfiling/cam_acq/workflows/Test%20application/badge.svg)](https://github.com/CellProfiling/cam_acq/actions) [![Documentation Status](https://readthedocs.org/projects/cam-acq/badge/?version=latest)](http://cam-acq.readthedocs.io/en/latest/?badge=latest)

Python project to control microscope through client-server program.

## Install

- Install the camacq package. Python version 3.10+ is supported.

    ```sh
    # Check python version.
    python --version
    # Install package.
    pip install camacq
    # Test that program is callable and show help.
    camacq -h
    ```

## Run

```sh
camacq
```

## Configure

camacq uses a yaml configuration file, config.yml, for configuring
almost all settings in the app. The configuration file is found in the
configuration directory. The default configuration directory is located
in the home directory and called `.camacq`.

The location of the configuration directory can be overridden when
starting camacq.

```sh
camacq --config /my_custom_config_dir
```

When camacq is started it checks the configuration directory for the
configuration file, and if none is found creates a default configuration
file. See below for an example of how to configure the leica api and a
simple automation, in the configuration yaml file.

```yaml
leica:
  host: localhost
  port: 8895
  imaging_dir: '/imaging_dir'

automations:
  - name: start
    trigger:
      - type: event
        id: camacq_start_event
    action:
      - type: command
        id: start_imaging
```

## API

To interact with a microscope camacq needs to connect to an API from a
microscope vendor, which in turn will control the microscope. Currently
camacq can connect to the Computer Aided Microscopy (CAM) interface of
Leica Microsystems' microscopes that have that feature activated. The
design of camacq is built to be able to easily extend to APIs of other
microscope vendors in the future. We welcome pull requests for this and
other improvements. The API interface should be contained within a
separate Python library, that instantiates a client object which camacq
can use.

```yaml
leica:
  host: localhost
  port: 8895
  imaging_dir: '/imaging_dir'
```

## Automations

To tell the microscope what to do, camacq uses automations. Automations
are blocks of yaml consisting of triggers, optional conditions and
actions. A trigger is the notification of an event in camacq, eg a new
image is saved. An action is what camacq should do when the trigger
triggers, eg go to the next well. A condition is a criteria that has to
be true to allow the action to execute, when a trigger has triggered.

As events happen, camacq checks the configured automations to see if any
automation trigger matches the event. If there is a match, it also
checks for possible conditions and if they are true. If both trigger and
conditions matches and resolves to true, the corresponding action(s)
will be executed.

For each automation block, it is possible to have multiple triggers,
multiple conditions and multiple actions. Eg we can configure an
automation with two triggers and two actions. If any of the triggers
matches an event, both actions will be executed, in sequence.

```yaml
automations:
  name: image_next_well
  trigger:
    - type: event
      id: camacq_start_event
    - type: event
      id: well_event
      data:
        well_img_ok: true
  action:
    - type: sample
      id: set_sample
      data:
        plate_name: plate_1
        well_x: 1
        well_y: >
          {{ trigger.event.well_y + 1 }}
    - type: command
      id: start_imaging
```

### Trigger

Let us look more closely at the trigger section of the above automation.

```yaml
trigger:
  - type: event
    id: camacq_start_event
  - type: event
    id: well_event
    data:
      well_img_ok: true
```

This section now holds a sequence of two trigger items, where each has a
type and an id. The second item also has a `data` key. The
`type` key tells camacq what type of trigger it should
configure. Currently only triggers of type `event` are
available. See the [documentation](http://cam-acq.readthedocs.io) for
all available event ids. The `id` key sets the trigger id
which will be the first part of the matching criteria for the trigger.
The second part is optional and is the value of the `data`
key. This key can hold key-value pairs with event data that should match
the attributes of the event for the trigger to trigger. So for the
second item we want the event to have id `well_event` and
to have an attribute called `well_img_ok` which should
return `True`, for the event to trigger our trigger.

### Action

Looking at the action section of our example automation, we see that it
also has two items. And exactly as for the triggers, each action has a
`type` and an `id`, and can optionally specify
a `data` key. Actions can have different types, eg
`sample` or `command`. You will find all of
the action types in the [documentation](http://cam-acq.readthedocs.io).
For an action, the `data` key sets the keyword arguments
that should be provided to the action handler function that executes the
action.

```yaml
action:
  - type: sample
    id: set_sample
    data:
      plate_name: plate_1
      well_x: 1
      well_y: >
        {{ trigger.event.well_y + 1 }}
  - type: command
    id: start_imaging
```

In our example we want to do two things, first set a well, and then
start the imaging. To not have to define this automation for each well
we want to image, automations allow for dynamic rendering of the value
of a data key, via use of the [Jinja2](http://jinja.pocoo.org/docs)
template language. You can recognize this part by the curly brackets.
See the template section below for further details.

### Template

Using templates in automations allows us to build powerful and flexible
pieces of automation configuration code to control the microscope.
Besides having all the standard Jinja2 features, we also have the
trigger event and the full sample state data available as variables when
the template is rendered. Eg if a well event triggered the automation we
can use `trigger.event.container` inside the template and have
access to all the attributes of the well container that triggered the event.
Useful sample attributes are also directly available on the
`trigger.event` eg `trigger.event.well_x`.

```yaml
well_y: >
  {% if trigger.event.container is defined %}
    {{ trigger.event.well_y + 1 }}
  {% else %}
    1
  {% endif %}
```

If we need access to some sample state that isn't part of the trigger,
we can use `samples` directly in the template. Via this
variable the whole sample state data is accessible from inside a
template. See below for the sample attribute structure. Note that only
condition and action values in key-value pairs support rendering a
template. Templates are not supported in the keys of key-value pairs and
not in trigger sections.

### Condition

A condition can be used to check the current sample state and only
execute the action if some criteria is met. Say eg we want to make sure
that channel 3 of well 1:1 of plate 1 is green and that gain is set to
800.

```yaml
condition:
  type: AND
  conditions:
    - condition: >
        {% if samples.leica.data['{"name": "channel", "plate_name": "plate_1", "well_x": 1, "well_y": 1, "channel_id": 3}'].values['channel_name'] == 'green' %}
          true
        {% endif %}
    - condition: >
        {% if samples.leica.data['{"name": "channel", "plate_name": "plate_1", "well_x": 1, "well_y": 1, "channel_id": 3}'].values['gain'] == 800 %}
          true
        {% endif %}
```

The trigger event data is also available in the condition template as a
variable. Below example will evaluate to true if the well that triggered
the event has either 1 or 2 as x coordinate.

```yaml
condition:
  type: OR
  conditions:
    - condition: >
        {% if trigger.event.well_x == 1 %}
          true
        {% endif %}
    - condition: >
        {% if trigger.event.well_x == 2 %}
          true
        {% endif %}
```

Currently each condition must be a template that renders to the string
`true` if the condition criteria is met.

## Sample

The sample state should represent the sample with a representation that
is specific to each implemented microscope api using the `ImageContainer`
api of camacq. An image container has a `name`, a dictionary of `images` and
a dictionary of `values` as attributes. The container also fires a specific
event on container change.

There are two special cases of the image container. The first is the main
sample container of each microscope api, eg the leica container. The main
container has an extra attribute `data` which is a dictionary with all the
containers of the sample. The second special case is the image in the
dictionary of images of an image container. The image is also a container
and has only itself in the images dictionary and a `path` attribute with
the path of the image.

Eg for the leica sample there are plate, well, field, z_slice, channel and
image containers under the main leica sample container.

All implemented sample states are available as a variable `samples` in
templates in automations. The leica sample is available as `samples.leica`.

See below for the leica sample state attribute structure in camacq.
The words in all capital letters are example values. Each image container
has a name, which is either of plate, well, field, z_slice, channel or image.
The different leica containers have different leica specific attributes
that aren't all shown below.

```yaml
samples:
  leica:
    name: leica
    images:
      PATH:
        name: image
        path: PATH
        plate_name: PLATE_NAME
        well_x: WELL_X
        well_y: WELL_Y
        field_x: FIELD_X
        field_y: FIELD_Y
        z_slice_id: Z_SLICE_ID
        channel_id: CHANNEL_ID
        images:
          PATH: self
        values:
          VALUE_KEY: VALUE
    values:
      VALUE_KEY: VALUE
    data:
      CONTAINER_ID:
        name: plate/well/field/z_slice/channel/image
        images:
          PATH:
            name: image
            path: PATH
            plate_name: PLATE_NAME
            well_x: WELL_X
            well_y: WELL_Y
            field_x: FIELD_X
            field_y: FIELD_Y
            z_slice_id: Z_SLICE_ID
            channel_id: CHANNEL_ID
            images:
              PATH: self
            values:
              VALUE_KEY: VALUE
        values:
          VALUE_KEY: VALUE
```

## Plugins

To extend the functionality of camacq and to make it possible to do
automated feedback microscopy, camacq supports plugins. A plugin is a
module or a package in camacq that provides code for a specific task. It
can eg be an image analysis script. See the
[documentation](http://cam-acq.readthedocs.io) for all default available
plugins.

To install a custom plugin, create a Python package with a `setup.py` module that
implements the entry_points interface with key `"camacq.plugins"`.

```py
setup(
    ...
    entry_points={"camacq.plugins": "plugin_a = package_a.plugin_a"},
    ...
)
```

See the packaging [docs](https://packaging.python.org/guides/creating-and-discovering-plugins/#using-package-metadata) for details.

`camacq` will
automatically load installed modules or packages that implement this entry_point.

Add a `setup_module` coroutine function in the module or package. This function
will be awaited with `center` and `config` as arguments.

```py
async def setup_module(center, config):
    """Set up the plugin package."""
```

Each plugin must have its own configuration section at the root of the config.

```yaml
example_plugin:
  ...
```

## Development

Install the packages needed for development.

```sh
pip install -r requirements_dev.txt
```

Use the Makefile to run common development tasks.

```sh
make
```

### Release

See the [release instructions](RELEASE.md).

## Credits

A lot of the inspiration for the architecture of camacq comes from
another open-source Python automation app: [Home
Assistant](https://github.com/home-assistant/home-assistant). This is
also the source for the automations interface in camacq.
