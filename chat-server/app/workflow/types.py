from typing import TypedDict


class FuzzyValue(TypedDict):
    name: str
    exact_values: list[str]
    fuzzy_values: list[str]


class ColumnAssumptions(TypedDict):
    dataset: str
    columns: list[FuzzyValue]
