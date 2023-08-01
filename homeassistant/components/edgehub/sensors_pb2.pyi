from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import (
    ClassVar as _ClassVar,
    Optional as _Optional,
    Union as _Union,
)

from google.protobuf import (
    descriptor as _descriptor,
    message as _message,
    timestamp_pb2 as _timestamp_pb2,
)
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class ExternalSensorAvailability(_message.Message):
    __slots__ = ["id", "is_available", "metrics", "type"]
    ID_FIELD_NUMBER: _ClassVar[int]
    IS_AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    id: str
    is_available: bool
    metrics: _containers.RepeatedScalarFieldContainer[str]
    type: str
    def __init__(
        self,
        metrics: _Optional[_Iterable[str]] = ...,
        type: _Optional[str] = ...,
        id: _Optional[str] = ...,
        is_available: bool = ...,
    ) -> None: ...

class SensorChannel(_message.Message):
    __slots__ = ["name", "type", "unit"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    UNIT_FIELD_NUMBER: _ClassVar[int]
    name: str
    type: str
    unit: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        unit: _Optional[str] = ...,
        type: _Optional[str] = ...,
    ) -> None: ...

class SensorConfig(_message.Message):
    __slots__ = ["sensors"]
    SENSORS_FIELD_NUMBER: _ClassVar[int]
    sensors: _containers.RepeatedCompositeFieldContainer[SensorInfo]
    def __init__(
        self, sensors: _Optional[_Iterable[_Union[SensorInfo, _Mapping]]] = ...
    ) -> None: ...

class SensorDatapoint(_message.Message):
    __slots__ = [
        "additional_details",
        "channel",
        "dimensions",
        "is_anomaly_enabled",
        "is_sensor_enabled",
        "sensor_id",
        "timestamp",
        "value",
    ]
    ADDITIONAL_DETAILS_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    DIMENSIONS_FIELD_NUMBER: _ClassVar[int]
    IS_ANOMALY_ENABLED_FIELD_NUMBER: _ClassVar[int]
    IS_SENSOR_ENABLED_FIELD_NUMBER: _ClassVar[int]
    SENSOR_ID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    additional_details: bytes
    channel: SensorChannel
    dimensions: _containers.RepeatedCompositeFieldContainer[SensorDimension]
    is_anomaly_enabled: bool
    is_sensor_enabled: bool
    sensor_id: str
    timestamp: _timestamp_pb2.Timestamp
    value: float
    def __init__(
        self,
        timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...,
        value: _Optional[float] = ...,
        channel: _Optional[_Union[SensorChannel, _Mapping]] = ...,
        is_sensor_enabled: bool = ...,
        is_anomaly_enabled: bool = ...,
        additional_details: _Optional[bytes] = ...,
        dimensions: _Optional[_Iterable[_Union[SensorDimension, _Mapping]]] = ...,
        sensor_id: _Optional[str] = ...,
    ) -> None: ...

class SensorDimension(_message.Message):
    __slots__ = ["key", "value"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    key: str
    value: str
    def __init__(
        self, key: _Optional[str] = ..., value: _Optional[str] = ...
    ) -> None: ...

class SensorInfo(_message.Message):
    __slots__ = [
        "file_name",
        "id",
        "metrics",
        "port",
        "sensor_class",
        "settings",
        "type",
    ]

    class SensorMetric(_message.Message):
        __slots__ = ["max_range", "metric_name", "min_range"]
        MAX_RANGE_FIELD_NUMBER: _ClassVar[int]
        METRIC_NAME_FIELD_NUMBER: _ClassVar[int]
        MIN_RANGE_FIELD_NUMBER: _ClassVar[int]
        max_range: float
        metric_name: str
        min_range: float
        def __init__(
            self,
            metric_name: _Optional[str] = ...,
            min_range: _Optional[float] = ...,
            max_range: _Optional[float] = ...,
        ) -> None: ...
    FILE_NAME_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    SENSOR_CLASS_FIELD_NUMBER: _ClassVar[int]
    SETTINGS_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    file_name: str
    id: str
    metrics: _containers.RepeatedCompositeFieldContainer[SensorInfo.SensorMetric]
    port: str
    sensor_class: str
    settings: SensorSettings
    type: str
    def __init__(
        self,
        id: _Optional[str] = ...,
        type: _Optional[str] = ...,
        sensor_class: _Optional[str] = ...,
        file_name: _Optional[str] = ...,
        port: _Optional[str] = ...,
        metrics: _Optional[_Iterable[_Union[SensorInfo.SensorMetric, _Mapping]]] = ...,
        settings: _Optional[_Union[SensorSettings, _Mapping]] = ...,
    ) -> None: ...

class SensorSettings(_message.Message):
    __slots__ = ["is_anomaly_enabled", "is_sensor_enabled", "upload_rate"]
    IS_ANOMALY_ENABLED_FIELD_NUMBER: _ClassVar[int]
    IS_SENSOR_ENABLED_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_RATE_FIELD_NUMBER: _ClassVar[int]
    is_anomaly_enabled: bool
    is_sensor_enabled: bool
    upload_rate: int
    def __init__(
        self,
        is_sensor_enabled: bool = ...,
        is_anomaly_enabled: bool = ...,
        upload_rate: _Optional[int] = ...,
    ) -> None: ...
