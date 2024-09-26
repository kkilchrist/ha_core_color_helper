# Input Color Helper for Home Assistant

### Introduction

The `input_color` helper is a customizable color input entity for Home Assistant. It allows users to manage colors independently of device states, making it possible to incorporate color selection into automations and device control without being tied to a light entity (or a fake light entity). Future work will enable its use in UI themes and cards. This helper enables the user to set and retrieve colors in multiple formats, such as `HEX`, `RGB`, and `HSV`, and to manipulate individual color components like red, green, blue, hue, saturation, and value.

### Motivation

Many Home Assistant users need the ability to select and store colors outside of typical device entities like lights. (See here: https://community.home-assistant.io/t/color-picker-helper/255516/19) Common use cases include changing the color of UI elements, managing LED strips with multiple color zones, and setting colors for non-lighting devices. The `input_color` helper fills this gap by providing a flexible and reusable method to handle color values and integrate them into Home Assistant's automation ecosystem.

### Key Features

- **Color Storage**: Stores colors in `#HEX` format and allows access to RGB and HSV components.
- **Multiple Input Formats**: Set colors via `HEX`, `RGB`, or `HSV`, or manipulate individual components like red, green, blue, hue, saturation, and value.
- **Flexible Automation**: Incorporate color values into Home Assistant automations, independent of device state.
- **Editable Entities**: Colors can be dynamically changed via storage or preset through YAML configuration.

### Installation

To install the `input_color` helper as a custom component in Home Assistant, follow the updated installation steps below:

### Installation as a Custom Component

1. **Download the Custom Component**:
   Obtain the `input_color` custom component zip file and extract it to your local machine.

2. **Create Custom Components Folder**:
   If you haven't already, create a `custom_components` folder in your Home Assistant configuration directory.

   ```bash
   /config/custom_components/
   ```

3. **Move the `input_color` Files**:
   Place the extracted `input_color` folder from the zip file into the `custom_components` directory. Your folder structure should look like this:

   ```
   /config/custom_components/input_color/
       ├── __init__.py
       ├── manifest.json
       ├── services.yaml
   ```

4. **Update `configuration.yaml`**:
   Add the following configuration to your `configuration.yaml` file to define `input_color` entities:

   ```yaml
   input_color:
     my_color_helper:
       name: Today's Color
       initial: "#FF5733"
       icon: mdi:palette
   ```

   This example defines an input color with the name "Today's Color" and an initial color of `#FF5733`.

5. **Restart Home Assistant**:
   Once the custom component is installed and configured, restart Home Assistant for the changes to take effect. You can do this via the Home Assistant UI by navigating to **Configuration > Server Controls > Restart**, or by restarting the service from the command line.

6. **Set up Automations**:
   Now that the `input_color` helper is installed, you can integrate it into your automations or scripts. You can set colors programmatically or retrieve the color value to control devices.

### Configuration Options

The `input_color` helper supports the following configuration options:

- **name**: (Optional) A friendly name for the color entity.
- **initial**: (Optional) The default color value, which can be defined as a HEX, RGB, or HSV value. If no initial value is provided, it defaults to white (`#FFFFFF`). Restoring the color across a restart is not currently done.
- **icon**: (Optional) An icon representing the color input in the UI.

#### Example YAML Configuration

```yaml
input_color:
  led_strip_color:
    name: LED Strip Color
    initial: "#22A7F0"
    icon: mdi:lightbulb
```

### Available Services

#### `input_color.set_color`

This service allows you to set the color of an `input_color` entity. You can use HEX, RGB, HSV, or individual color components to change the color.

**Service Schema:**

- **hex_value**: Set color using a HEX format (e.g., `#FF5733`).
- **rgb_value**: Set color using RGB components (e.g., `{"red": 255, "green": 87, "blue": 51}`).
- **hsv_value**: Set color using HSV components (e.g., `{"h": 0.1, "s": 0.9, "v": 0.8}`).
- **red, green, blue**: Set individual RGB components (0-255).
- **hue, saturation, value**: Set individual HSV components (0-1).

**Example Service Call:**

```yaml
service: input_color.set_color
data:
  entity_id: input_color.living_room_light_color
  hex_value: "#FF5733"
```

Alternatively, you can set the color using RGB or HSV values:

```yaml
service: input_color.set_color
data:
  entity_id: input_color.living_room_light_color
  rgb_value:
    red: 255
    green: 87
    blue: 51
```

### Attributes

The `input_color` helper provides the following attributes for use in automations and scripts:

- **hex_color**: The current color in `#HEX` format.
- **rgb_color**: The current color in RGB format, as a tuple of `(red, green, blue)`.
- **hsv_color**: The current color in HSV format, as a tuple of `(hue, saturation, value)`.
- **red, green, blue**: The individual RGB components of the color.
- **hue, saturation, value**: The individual HSV components of the color.
- **hex_color_without_hash**: The HEX color value without the leading `#`.

### Example Automation

The following automation changes the color of an `input_color` entity and synchronizes it with a light:

```yaml
alias: Test Input Color and Light
sequence:
  - service: input_color.set_color
    target:
      entity_id: input_color.living_room_light_color
    data:
      hex_value: "#FF5733"

  - service: light.turn_on
    target:
      entity_id: light.island_light
    data:
      rgb_color: "{{ state_attr('input_color.living_room_light_color', 'rgb_color') }}"

  - delay: "00:00:01"

  - service: input_color.set_color
    target:
      entity_id: input_color.living_room_light_color
    data:
      rgb_value:
        red: 0
        green: 0
        blue: 255

  - service: light.turn_on
    target:
      entity_id: light.island_light
    data:
      rgb_color: "{{ state_attr('input_color.living_room_light_color', 'rgb_color') }}"

  - delay: "00:00:01"

  - service: input_color.set_color
    target:
      entity_id: input_color.living_room_light_color
    data:
      hsv_value:
        h: 0.6
        s: 1
        v: 1

  - service: light.turn_on
    target:
      entity_id: light.island_light
    data:
      rgb_color: "{{ state_attr('input_color.living_room_light_color', 'rgb_color') }}"
```

### Future Work - Would Love Some Help

- **Frontend Integration**: Add a color picker interface in the Home Assistant UI to allow users to visually select colors and integrate them into automations more easily.
- **UI Helper**: Improve the helper system to allow users to manipulate color values directly from the Home Assistant interface with more intuitive controls, such as sliders for RGB/HSV values.
- **Restoration of State**: Implement persistent storage to automatically restore the last color state after a Home Assistant restart.
- **Add New Helper from UI**: Enable the creation and management of `input_color` entities directly from the Home Assistant UI, similar to other input helpers.
- **Examples Using UI Cards**: Provide examples for integrating `input_color` with Lovelace cards to control elements like themes or devices based on selected colors.
- **More Testing**: Improve test coverage and ensure the component works as expected in various setups and use cases. 

Contributions and feedback are welcome to help improve these areas.