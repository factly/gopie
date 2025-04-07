from typing import Any, Dict, List, Optional, TypedDict, Union


class AnalysisInfo(TypedDict):
    """Information about the analysis"""

    title: str
    date_start: str
    date_end: str


class NumericVariableStats(TypedDict, total=False):
    """Comprehensive schema information for a dataset"""

    n_distinct: int
    p_distinct: float
    is_unique: bool
    n_unique: int
    p_unique: float
    type: str
    hashable: bool
    ordering: bool
    n_missing: int
    n: int
    p_missing: float
    count: int
    memory_size: int
    n_negative: int
    p_negative: float
    n_infinite: int
    n_zeros: int
    mean: float
    std: float
    variance: float
    min: float
    max: float
    kurtosis: float
    skewness: float
    sum: float
    mad: float
    range: float
    iqr: float
    cv: float
    p_zeros: float
    p_infinite: float
    monotonic_increase: bool
    monotonic_decrease: bool
    monotonic_increase_strict: bool
    monotonic_decrease_strict: bool
    monotonic: int
    histogram: List[Optional[Any]]


class TextVariableStats(TypedDict, total=False):
    """Statistics for text variables"""

    n_distinct: int
    p_distinct: float
    is_unique: bool
    n_unique: int
    p_unique: float
    type: str
    hashable: bool
    ordering: bool
    n_missing: int
    n: int
    p_missing: float
    count: int
    memory_size: int


class ColumnSchema(TypedDict):
    """Schema information for a dataset column"""

    name: str
    description: str
    type: str
    sample_values: Any
    non_null_count: Optional[int]


class DatasetSchema(TypedDict):
    """Comprehensive schema information for a dataset"""

    name: str
    dataset_id: str
    file_path: str
    project_id: str
    analysis: AnalysisInfo
    row_count: int
    col_count: int
    # variables: Dict[str, Union[NumericVariableStats, TextVariableStats]]
    columns: List[ColumnSchema]

    # scatter: Optional[Dict[str, Any]]
    # correlations: Optional[Dict[str, Any]]
    # missing: Optional[Dict[str, Any]]
    # alerts: Optional[List[Any]]
    # duplicates: Optional[str]
