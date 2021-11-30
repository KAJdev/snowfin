from typing import Union, List

from .interaction import Option
from .enums import ButtonStyle, ComponentType

__all__ = (
    'Components',
    'Button',
    'Select',
    'ActionRow'
)

class Button:
    def __init__(
        self,
        label: str,
        custom_id: str,
        disabled: bool = False,
        style: ButtonStyle = ButtonStyle.PRIMARY,
        emoji: Union[str, dict] = None,
        url: str = None
    ) -> None:
        self.weight = 1
        self.type = ComponentType.BUTTON
        self.label = label
        self.custom_id = custom_id
        self.disabled = disabled
        self.style = style
        self.emoji = emoji
        self.url = url

        if self.style is ButtonStyle.URL and self.url is None:
            raise ValueError("URL button requires a URL")
        
        if self.url is not None:
            self.style = ButtonStyle.URL

    def to_dict(self):
        return {
            "type": self.type.value,
            "label": self.label,
            "custom_id": self.custom_id,
            "disabled": self.disabled,
            "style": self.style.value,
            "emoji": self.emoji,
            "url": self.url
        }

class Select:
    def __init__(
        self,
        custom_id: str,
        placeholder: str = None,
        disabled: bool = False,
        emoji: Union[str, dict] = None,
        options: List[Option] = None,
        min_values: int = 1,
        max_values: int = 1,
    ) -> None:
        self.weight = 5
        self.type = ComponentType.SELECT
        self.custom_id = custom_id
        self.placeholder = placeholder
        self.disabled = disabled
        self.emoji = emoji

        self.options = [x.asdict() for x in options]
        if len(self.options) == 0:
            raise ValueError("Select requires at least one option")
        elif len(self.options) > 25:
            raise ValueError("Select cannot have more than 25 options")

        self.min_values = min_values
        self.max_values = max_values

        if self.min_values > self.max_values:
            raise ValueError("min_values cannot be greater than max_values")

        if self.min_values < 0:
            self.min_values = 0
        if self.max_values > 25:
            self.max_values = 25

    def to_dict(self):
        return {
            "type": self.type.value,
            "custom_id": self.custom_id,
            "placeholder": self.placeholder,
            "disabled": self.disabled,
            "emoji": self.emoji,
            "options": self.options,
            "min_values": self.min_values,
            "max_values": self.max_values
        }


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

    def remove_component(self, index: int):
        self.weights -= self.components[index].weight
        del self.components[index]

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

    def add_component(self, component: Union[Button, Select], row: int = None):
        if row is None:
            for _row in self.rows:
                if _row.weights + component.weight <= 5:
                    _row.add_component(component)
                    return

            raise ValueError("Cannot add component, weight limit exceeded")
        else:
            if row > len(self.rows):
                raise ValueError("Row does not exist")
            if self.rows[row].weights + component.weight <= 5:
                self.rows[row].add_component(component)
                return
            raise ValueError("Cannot add component, weight limit exceeded")

    def to_dict(self):
        data = []
        for row in self.rows:
            if row.weights == 0:
                continue
            data.append(row.to_dict())
        return data