camacq |build-status| |docs| |license-badge|
============================================

Python project to control microscope through client-server program.

Install
-------
- Install the camacq package. 3.5 and 3.6 are supported.

::

  # Check python version.
  python --version
  # Clone the repo.
  git clone https://github.com/CellProfiling/cam_acq.git
  # Enter directory.
  cd cam_acq
  # Checkout master branch.
  git checkout master
  # Install package.
  pip install .
  # Test that program is callable and show help.
  camacq -h

Run
---

::

  camacq

Configure
---------
camacq uses a yaml configuration file, config.yml, for configuring almost all settings in the app. The configuration file is found in the configuration directory. The default configuration directory is located in the home directory and called :code:`.camacq`.

The location of the configuration directory can be overridden when starting camacq.

::

  camacq --config /my_custom_config_dir


When camacq is started it checks the configuration directory for the configuration file, and if none is found creates a default configuration file. See below for an example of how to configure the leica api and a simple automation, in the configuration yaml file.

::

  api:
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

API
---
To interact with a microscope camacq needs to connect to an API from a microscope vendor, which in turn will control the microscope. Currently camacq can connect to the Computer Aided Microscopy (CAM) interface of Leica Microsystems' microscopes that have that feature activated. The design of camacq is built to be able to easily extend to APIs of other microscope vendors in the future. We welcome pull requests for this and other improvements. The API interface should be contained within a separate Python library, that instantiates a client object which camacq can use.

::

  api:
    leica:
      host: localhost
      port: 8895
      imaging_dir: '/imaging_dir'

Automations
-----------
To tell the microscope what to do, camacq uses automations. Automations are blocks of yaml consisting of triggers, optional conditions and actions. A trigger is the notification of an event in camacq, eg a new image is saved. An action is what camacq should do when the trigger triggers, eg go to the next well. A condition is a criteria that has to be true to allow the action to execute, when a trigger has triggered.

As events happen, camacq checks the configured automations to see if any automation trigger matches the event. If there is a match, it also checks for possible conditions and if they are true. If both trigger and conditions matches and resolves to true, the corresponding action(s) will be executed.

For each automation block, it is possible to have multiple triggers, multiple conditions and multiple actions. Eg we can configure an automation with two triggers and two actions. If any of the triggers matches an event, both actions will be executed, in sequence.

::

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
        id: set_well
        data:
          plate_name: plate_1
          well_x: 1
          well_y: >
            {% if trigger.event.well is defined %}
              {{ trigger.event.well_y + 1 }}
            {% else %}
              1
            {% endif %}
      - type: command
        id: start_imaging

Trigger
~~~~~~~
Let us look more closely at the trigger section of the above automation.

::

  trigger:
    - type: event
      id: camacq_start_event
    - type: event
      id: well_event
      data:
        well_img_ok: true

This section now holds a sequence of two trigger items, where each has a type and an id. The second item also has a :code:`data` key. The :code:`type` key tells camacq what type of trigger it should configure. Currently only triggers of type :code:`event` are available. See the `documentation`_ for all available event ids. The :code:`id` key sets the trigger id which will be the first part of the matching criteria for the trigger. The second part is optional and is the value of the :code:`data` key. This key can hold key-value pairs with event data that should match the attributes of the event for the trigger to trigger. So for the second item we want the event to have id :code:`well_event` and to have an attribute called :code:`well_img_ok` which should return :code:`True`, for the event to trigger our trigger.

Action
~~~~~~
Looking at the action section of our example automation, we see that it also has two items. And exactly as for the triggers, each action has a :code:`type` and an :code:`id`, and can optionally specify a :code:`data` key. Actions can have different types, eg :code:`sample` or :code:`command`. You will find all of the action types in the `documentation`_. For an action, the :code:`data` key sets the keyword arguments that should be provided to the action handler function that executes the action.

.. _`documentation`: http://cam-acq.readthedocs.io

::

  action:
    - type: sample
      id: set_well
      data:
        plate_name: plate_1
        well_x: 1
        well_y: >
          {% if trigger.event.well is defined %}
            {{ trigger.event.well_y + 1 }}
          {% else %}
            1
          {% endif %}
    - type: command
      id: start_imaging

In our example we want to do two things, first set a well, and then start the imaging. To not have to define this automation for each well we want to image, automations allow for dynamic rendering of the value of a data key, via use of the `Jinja2`_ template language. You can recognize this part by the curly brackets. See the template section below for further details.

.. _`Jinja2`: http://jinja.pocoo.org/docs

Template
~~~~~~~~
Using templates in automations allows us to build powerful and flexible pieces of automation configuration code to control the microscope. Besides having all the standard Jinja2 features, we also have the trigger event and the full sample state data available as variables when the template is rendered. Eg if a well event triggered the automation we can use :code:`trigger.event.well` inside the template and have access to all the attributes of the well that triggered the event. Useful sample attributes are also directly available on the :code:`trigger.event` eg :code:`trigger.event.well_x`.

::

  well_y: >
    {% if trigger.event.well is defined %}
      {{ trigger.event.well_y + 1 }}
    {% else %}
      1
    {% endif %}


If we need access to some sample state that isn't part of the trigger, we can use :code:`sample` directly in the template. Via this variable the whole sample state data is accessible from inside a template. See below for the sample attribute structure. Note that only condition and action values in key-value pairs support rendering a template. Templates are not supported in the keys of key-value pairs and not in trigger sections.

Condition
~~~~~~~~~
A condition can be used to check the current sample state and only execute the action if some criteria is met. Say eg we want to make sure that a well has four channels and that the green channel gain is set to 800.

::

  condition:
    type: AND
    conditions:
      - condition: >
          {% if sample.plate['plate_1'].wells[1, 1].channels | length == 4 %}
            true
          {% endif %}
      - condition: >
          {% if sample.plate['plate_1'].wells[1, 1].channels['green'] == 800 %}
            true
          {% endif %}

The trigger event data is also available in the condition template as a variable. Below example will evaluate to true if the well that triggered the event has either 3 or 4 channels set.

::

  condition:
    type: OR
    conditions:
      - condition: >
          {% if trigger.event.well.channels | length == 3 %}
            true
          {% endif %}
      - condition: >
          {% if trigger.event.well.channels | length == 4 %}
            true
          {% endif %}

Currently each condition must be a template that renders to the string :code:`true` if the condition criteria is met.

Sample
------
The sample state should represent the sample with plate, wells, fields, images etc. See below for the full sample state attribute structure in camacq. This is available as a variable in templates in automations.

::

  sample:
    plates:
      [plate_name]:
        name: [plate_name]
        images:
          [path]:
            path: [path]
            plate_name: [plate_name]
            well_x: [well_x]
            well_y: [well_y]
            field_x: [field_x]
            field_y: [field_y]
            channel_id: [channel_id]
        wells:
          [well_x, well_y]:
            x: [well_x]
            y: [well_y]
            name: [well_name]
            img_ok: [True/False]
            images:
              [path]:
                path: [path]
                plate_name: [plate_name]
                well_x: [well_x]
                well_y: [well_y]
                field_x: [field_x]
                field_y: [field_y]
                channel_id: [channel_id]
            channels:
              [channel_name]:
                gain: [value]
            fields:
              [field_x, field_y]:
                x: [field_x]
                y: [field_y]
                name: [field_name]
                dx: [dx]
                dy: [dy]
                img_ok: [True/False]
                images:
                  [path]:
                    path: [path]
                    plate_name: [plate_name]
                    well_x: [well_x]
                    well_y: [well_y]
                    field_x: [field_x]
                    field_y: [field_y]
                    channel_id: [channel_id]

To allow the user to set up the sample state before starting an experiment, camacq can load the sample state from a file. In the sample configuration section there is an option to specify a path to a csv file.

::

  sample:
    state_file: '/sample_state.csv'

Each row in the csv file should represent a state of a sample container, ie plate, well, field or channel. The csv file should also have a header. See below.

::

  plate_name,well_x,well_y,channel_name,gain
  00,1,1,blue,600

This example will set create a plate '00', a well (1, 1), a blue channel and set the gain of the blue channel to 600.

::

  plate_name,well_x,well_y,field_x,field_y
  00,1,1,1,1

This example will create a plate '00' a well (1, 1) and a field (1, 1) in the sample state.

Plugins
-------
To extend the functionality of camacq and to make it possible to do automated feedback microscopy, camacq supports plugins. A plugin is a module or a package in camacq that provides code for a specific task. It can eg be an image analysis script. See the `documentation`_ for all available plugins.

Plugins have their own configuration section. This is an example of the gain plugin section in the configuration.

::

  plugins:
    gain:
      channels:
        - channel: green
          init_gain: [450, 495, 540, 585, 630, 675, 720, 765, 810, 855, 900]
        - channel: blue
          init_gain: [400, 435, 470, 505, 540, 575, 610]
        - channel: yellow
          init_gain: [550, 585, 620, 655, 690, 725, 760]
        - channel: red
          init_gain: [525, 560, 595, 630, 665, 700, 735]
      save_dir: '/save_dir'

Each plugin should at minimum register an action in the action registry to expose the plugin task as an action available in automations.

Credits
-------
A lot of the inspiration for the architecture of camacq comes from another open-source Python automation app: `Home Assistant`_. This is also the source for the automations interface in camacq.


.. _`Home Assistant`: https://github.com/home-assistant/home-assistant

.. |build-status| image:: https://travis-ci.org/CellProfiling/cam_acq.svg?branch=develop
   :target: https://travis-ci.org/CellProfiling/cam_acq
   :alt: Build Status

.. |docs| image:: https://readthedocs.org/projects/cam-acq/badge/?version=latest
   :target: http://cam-acq.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. |license-badge| image:: http://img.shields.io/badge/license-GPLv3-blue.svg
   :target: https://www.gnu.org/copyleft/gpl.html
   :alt: License
