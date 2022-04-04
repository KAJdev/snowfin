from typing import Union, List
from .enums import ButtonStyle, ComponentType, TextStyleTypes

__all__ = (
    'Components',
    'Emoji',
    'Button',
    'Select',
    'SelectOption',
    'ActionRow',
    'TextInput',
    'is_component',
)


class Emoji:
    def __init__(self, name: str, id: int, animated: bool = False):
        self.name = name
        self.id = id
        self.animated = animated

    @classmethod
    def from_str(cls, emoji_string: str):
        if len(emoji_string) == 1:
            return cls(name=emoji_string, id=None)

        emoji_string = emoji_string.strip('<>')
        data = emoji_string.split(':')
        if len(data) == 3:
            return cls(data[1], str(data[2]), animated='a' in data[0])
        elif len(data) == 2:
            return cls(data[0], str(data[1]))
        else:
            raise ValueError(f"Invalid emoji string: {emoji_string}")

    def __str__(self):
        return f"<{'a' if self.animated else ''}:{self.name}:{self.id}>"

    def __repr__(self):
        return f"<Emoji {self.name=} {self.id=} {self.animated=}>"

    def to_dict(self):
        d = {
            'name': self.name,
            'id': self.id
        }

        if self.animated:
            d['animated'] = True

        return d

class Button:
    def __init__(
        self,
        label: str,
        custom_id: str = None,
        disabled: bool = False,
        style: ButtonStyle = ButtonStyle.PRIMARY,
        emoji: Union[str, Emoji] = None,
        url: str = None,
        **kwargs
    ) -> None:
        self.weight = 1
        self.type = ComponentType.BUTTON
        self.label = label
        self.custom_id = custom_id
        self.disabled = disabled
        self.style = ButtonStyle(style)

        if isinstance(emoji, str):
            self.emoji = Emoji.from_str(emoji)
        else:
            self.emoji = emoji

        self.url = url

        if self.style is ButtonStyle.URL and self.url is None:
            raise ValueError("URL button requires a URL")
        
        if self.url is not None:
            self.style = ButtonStyle.URL
            self.custom_id = None

    def to_dict(self):
        d = {
            "type": self.type.value,
            "label": self.label,
            "disabled": self.disabled,
            "style": self.style.value,
        }

        if self.style is ButtonStyle.URL:
            d['url'] = self.url
        else:
            d['custom_id'] = self.custom_id

        if self.style is not ButtonStyle.URL and self.custom_id is None:
            raise ValueError("Button requires a custom_id")

        if self.emoji is not None:
            d['emoji'] = self.emoji.to_dict()

        return d

class SelectOption:
    def __init__(self, label: str, value: str, description: str = None, emoji: str = None, default: bool = False) -> None:
        self.label = label
        self.value = value
        self.description = description
        self.default = default

        if isinstance(emoji, str):
            self.emoji = Emoji.from_str(emoji)
        elif isinstance(emoji, dict):
            self.emoji = Emoji(**emoji)
        else:
            self.emoji = emoji

    def to_dict(self):
        d = {
            "label": self.label,
            "value": self.value,
            "default": self.default,
        }

        if self.emoji is not None:
            d["emoji"] = self.emoji.to_dict()

        if self.description is not None:
            d["description"] = self.description

        return d

class Select:
    def __init__(
        self,
        custom_id: str,
        placeholder: str = None,
        disabled: bool = False,
        options: List[SelectOption] = None,
        min_values: int = 1,
        max_values: int = 1,
        **kwargs
    ) -> None:
        self.weight = 5
        self.type = ComponentType.SELECT
        self.custom_id = custom_id
        self.placeholder = placeholder
        self.disabled = disabled

        if len(options) == 0:
            raise ValueError("Select requires at least one option")
        elif len(options) > 25:
            raise ValueError("Select cannot have more than 25 options")
        self.options = [SelectOption(**x) if not isinstance(x, SelectOption) else x for x in options]

        self.min_values = min_values
        self.max_values = max_values

        if self.min_values > self.max_values:
            raise ValueError("min_values cannot be greater than max_values")

        if self.min_values < 0:
            self.min_values = 0
        if self.max_values > 25:
            self.max_values = 25

    def add_option(self, option: SelectOption) -> None:
        if len(self.options) >= 25:
            raise ValueError("Select cannot have more than 25 options")
        self.options.append(option)

        return self

    def remove_option(self, option: Union[int, SelectOption]) -> None:
        if isinstance(option, int):
            self.options.pop(option)
        elif isinstance(option, SelectOption):
            self.options.remove(option)
        else:
            raise ValueError("option must be an int or SelectOption")

        return self

    def to_dict(self):
        return {
            "type": self.type.value,
            "custom_id": self.custom_id,
            "placeholder": self.placeholder,
            "disabled": self.disabled,
            "options": [x.to_dict() for x in self.options],
            "min_values": self.min_values,
            "max_values": self.max_values
        }

class TextInput:
    def __init__(
        self,
        custom_id: str,
        label: str = None,
        style: TextStyleTypes = TextStyleTypes.SHORT,
        placeholder: str = None,
        min_length: int = None,
        max_length: int = None,
        **kwargs
    ) -> None:
        self.weight = 5
        self.type = ComponentType.INPUT_TEXT
        self.custom_id = custom_id
        self.label = label
        self.style = TextStyleTypes(style)
        self.placeholder = placeholder
        self.min_length = min_length
        self.max_length = max_length

    def to_dict(self):
        d = {
            "type": self.type.value,
            "custom_id": self.custom_id,
            "style": self.style.value,
            "label": self.label,
        }

        if self.placeholder is not None:
            d["placeholder"] = self.placeholder

        if self.min_length is not None:
            d["min_length"] = self.min_length

        if self.max_length is not None:
            d["max_length"] = self.max_length

        return d


class ActionRow:
    def __init__(self, *components) -> None:
        self.components = []
        self.weights = 0
        self.type = ComponentType.ACTION_ROW

        for component in components:
            self.add_component(component)

    def add_component(self, component: Union[Button, Select]):
        if self.weights + component.weight > 5:
            raise ValueError("Cannot add component, weight limit exceeded")
        self.components.append(component)
        self.weights += component.weight

        return self

    def remove_component(self, index: int):
        self.weights -= self.components[index].weight
        del self.components[index]

        return self

    def to_dict(self):
        return {
            "type": self.type.value,
            "components": [x.to_dict() for x in self.components]
        }

class Components:

    def __init__(self, *components) -> None:
        self.rows = [ActionRow() for _ in range(5)]

        for component in components:
            self.add_component(component)

    def add_component(self, component: Union[Button, Select, TextInput], row: int = None):
        if row is None:
            for _row in self.rows:
                if _row.weights + component.weight <= 5:
                    _row.add_component(component)
                    return self

            raise ValueError("Cannot add component, weight limit exceeded")
        else:
            if row > len(self.rows):
                raise ValueError("Row does not exist")
            if self.rows[row].weights + component.weight <= 5:
                self.rows[row].add_component(component)
                return self
            raise ValueError("Cannot add component, weight limit exceeded")

    def add_component_raw(self, component: dict, row: int = None):
        if component.get('type') == ComponentType.BUTTON.value:
            component = Button(**component)
        elif component.get('type') == ComponentType.SELECT.value:
            component = Select(**component)
        elif component.get('type') == ComponentType.INPUT_TEXT.value:
            component = TextInput(**component)
        else:
            raise ValueError("Component type not supported")

        return self.add_component(component, row)

    def replace_component(self, component: Union[Button, Select, str], new_component: Union[Button, Select]):
        if isinstance(component, str):
            for row in self.rows:
                for index, _component in enumerate(row.components):
                    if _component.custom_id == component and _component.type == new_component.type:
                        row[index] = new_component
                        return self
            raise ValueError("Component does not exist")
        elif isinstance(component, (Button, Select)):
            for row in self.rows:
                for index, _component in enumerate(row.components):
                    if _component == component:
                        row[index] = new_component
                        return self
            raise ValueError("Component does not exist")
        else:
            raise ValueError("component must be a custom_id, Button or Select")

    def remove_component(self, component: Union[Button, Select, str]):
        if isinstance(component, str):
            for row in self.rows:
                for index, _component in enumerate(row.components):
                    if _component.custom_id == component:
                        row.remove_component(index)
                        return self
        elif isinstance(component, (Button, Select)):
            for row in self.rows:
                for index, _component in enumerate(row.components):
                    if _component == component:
                        row.remove_component(index)
                        return self
        else:
            raise ValueError("component must be a custom_id, Button or Select")

    def to_dict(self):
        data = []
        for row in self.rows:
            if row.weights > 0:
                data.append(row.to_dict())
        return data

    @classmethod
    def from_list(cls, data: list[dict]):
        components = cls()
        for row,action_row in enumerate(data):
            for component in action_row.get('components', []):
                components.add_component_raw(component, row)
            
        return components

def is_component(obj) -> bool:
    return isinstance(obj, (Button, Select, TextInput))