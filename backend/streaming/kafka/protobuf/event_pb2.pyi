from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Coordinate(_message.Message):
    __slots__ = ("latitude", "longitude")
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    latitude: float
    longitude: float
    def __init__(self, latitude: _Optional[float] = ..., longitude: _Optional[float] = ...) -> None: ...

class Geometry(_message.Message):
    __slots__ = ("points",)
    POINTS_FIELD_NUMBER: _ClassVar[int]
    points: _containers.RepeatedCompositeFieldContainer[Coordinate]
    def __init__(self, points: _Optional[_Iterable[_Union[Coordinate, _Mapping]]] = ...) -> None: ...

class EventEnvelope(_message.Message):
    __slots__ = ("type", "timestamp", "topic", "weather", "river", "sensor", "emergency", "gps", "traffic", "road_failure", "resource", "shelter", "payload_json")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    WEATHER_FIELD_NUMBER: _ClassVar[int]
    RIVER_FIELD_NUMBER: _ClassVar[int]
    SENSOR_FIELD_NUMBER: _ClassVar[int]
    EMERGENCY_FIELD_NUMBER: _ClassVar[int]
    GPS_FIELD_NUMBER: _ClassVar[int]
    TRAFFIC_FIELD_NUMBER: _ClassVar[int]
    ROAD_FAILURE_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    SHELTER_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_JSON_FIELD_NUMBER: _ClassVar[int]
    type: str
    timestamp: str
    topic: str
    weather: WeatherPayload
    river: RiverPayload
    sensor: SensorPayload
    emergency: EmergencyPayload
    gps: GpsPayload
    traffic: TrafficPayload
    road_failure: RoadFailurePayload
    resource: ResourcePayload
    shelter: ShelterPayload
    payload_json: str
    def __init__(self, type: _Optional[str] = ..., timestamp: _Optional[str] = ..., topic: _Optional[str] = ..., weather: _Optional[_Union[WeatherPayload, _Mapping]] = ..., river: _Optional[_Union[RiverPayload, _Mapping]] = ..., sensor: _Optional[_Union[SensorPayload, _Mapping]] = ..., emergency: _Optional[_Union[EmergencyPayload, _Mapping]] = ..., gps: _Optional[_Union[GpsPayload, _Mapping]] = ..., traffic: _Optional[_Union[TrafficPayload, _Mapping]] = ..., road_failure: _Optional[_Union[RoadFailurePayload, _Mapping]] = ..., resource: _Optional[_Union[ResourcePayload, _Mapping]] = ..., shelter: _Optional[_Union[ShelterPayload, _Mapping]] = ..., payload_json: _Optional[str] = ...) -> None: ...

class WeatherPayload(_message.Message):
    __slots__ = ("rainfall_mm", "temperature_c", "humidity_pct", "wind_speed_kmh", "source", "timestamp")
    RAINFALL_MM_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_C_FIELD_NUMBER: _ClassVar[int]
    HUMIDITY_PCT_FIELD_NUMBER: _ClassVar[int]
    WIND_SPEED_KMH_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    rainfall_mm: float
    temperature_c: float
    humidity_pct: float
    wind_speed_kmh: float
    source: str
    timestamp: str
    def __init__(self, rainfall_mm: _Optional[float] = ..., temperature_c: _Optional[float] = ..., humidity_pct: _Optional[float] = ..., wind_speed_kmh: _Optional[float] = ..., source: _Optional[str] = ..., timestamp: _Optional[str] = ...) -> None: ...

class RiverPayload(_message.Message):
    __slots__ = ("station_id", "water_level", "rise_rate", "source", "timestamp")
    STATION_ID_FIELD_NUMBER: _ClassVar[int]
    WATER_LEVEL_FIELD_NUMBER: _ClassVar[int]
    RISE_RATE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    station_id: str
    water_level: float
    rise_rate: float
    source: str
    timestamp: str
    def __init__(self, station_id: _Optional[str] = ..., water_level: _Optional[float] = ..., rise_rate: _Optional[float] = ..., source: _Optional[str] = ..., timestamp: _Optional[str] = ...) -> None: ...

class SensorPayload(_message.Message):
    __slots__ = ("sensor_id", "road_id", "sensor_type", "source", "rainfall_mm", "water_level", "flood_probability", "latitude", "longitude", "timestamp")
    SENSOR_ID_FIELD_NUMBER: _ClassVar[int]
    ROAD_ID_FIELD_NUMBER: _ClassVar[int]
    SENSOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    RAINFALL_MM_FIELD_NUMBER: _ClassVar[int]
    WATER_LEVEL_FIELD_NUMBER: _ClassVar[int]
    FLOOD_PROBABILITY_FIELD_NUMBER: _ClassVar[int]
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    sensor_id: str
    road_id: str
    sensor_type: str
    source: str
    rainfall_mm: float
    water_level: float
    flood_probability: float
    latitude: float
    longitude: float
    timestamp: str
    def __init__(self, sensor_id: _Optional[str] = ..., road_id: _Optional[str] = ..., sensor_type: _Optional[str] = ..., source: _Optional[str] = ..., rainfall_mm: _Optional[float] = ..., water_level: _Optional[float] = ..., flood_probability: _Optional[float] = ..., latitude: _Optional[float] = ..., longitude: _Optional[float] = ..., timestamp: _Optional[str] = ...) -> None: ...

class EmergencyPayload(_message.Message):
    __slots__ = ("incident_id", "incident_type", "geometry", "priority", "status", "description", "reported_people", "severity", "source", "created_at")
    INCIDENT_ID_FIELD_NUMBER: _ClassVar[int]
    INCIDENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    GEOMETRY_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    REPORTED_PEOPLE_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    incident_id: str
    incident_type: str
    geometry: Geometry
    priority: str
    status: str
    description: str
    reported_people: int
    severity: float
    source: str
    created_at: str
    def __init__(self, incident_id: _Optional[str] = ..., incident_type: _Optional[str] = ..., geometry: _Optional[_Union[Geometry, _Mapping]] = ..., priority: _Optional[str] = ..., status: _Optional[str] = ..., description: _Optional[str] = ..., reported_people: _Optional[int] = ..., severity: _Optional[float] = ..., source: _Optional[str] = ..., created_at: _Optional[str] = ...) -> None: ...

class GpsPayload(_message.Message):
    __slots__ = ("resource_id", "latitude", "longitude", "heading", "speed_kmh", "timestamp")
    RESOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    HEADING_FIELD_NUMBER: _ClassVar[int]
    SPEED_KMH_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    resource_id: str
    latitude: float
    longitude: float
    heading: float
    speed_kmh: float
    timestamp: str
    def __init__(self, resource_id: _Optional[str] = ..., latitude: _Optional[float] = ..., longitude: _Optional[float] = ..., heading: _Optional[float] = ..., speed_kmh: _Optional[float] = ..., timestamp: _Optional[str] = ...) -> None: ...

class TrafficPayload(_message.Message):
    __slots__ = ("road_id", "traffic_density", "timestamp")
    ROAD_ID_FIELD_NUMBER: _ClassVar[int]
    TRAFFIC_DENSITY_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    road_id: str
    traffic_density: float
    timestamp: str
    def __init__(self, road_id: _Optional[str] = ..., traffic_density: _Optional[float] = ..., timestamp: _Optional[str] = ...) -> None: ...

class RoadFailurePayload(_message.Message):
    __slots__ = ("road_id", "status", "timestamp")
    ROAD_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    road_id: str
    status: str
    timestamp: str
    def __init__(self, road_id: _Optional[str] = ..., status: _Optional[str] = ..., timestamp: _Optional[str] = ...) -> None: ...

class ResourcePayload(_message.Message):
    __slots__ = ("resource_id", "resource_type", "status", "speed_kmh", "capacity", "geometry", "timestamp")
    RESOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_TYPE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SPEED_KMH_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    GEOMETRY_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    resource_id: str
    resource_type: str
    status: str
    speed_kmh: float
    capacity: int
    geometry: Geometry
    timestamp: str
    def __init__(self, resource_id: _Optional[str] = ..., resource_type: _Optional[str] = ..., status: _Optional[str] = ..., speed_kmh: _Optional[float] = ..., capacity: _Optional[int] = ..., geometry: _Optional[_Union[Geometry, _Mapping]] = ..., timestamp: _Optional[str] = ...) -> None: ...

class ShelterPayload(_message.Message):
    __slots__ = ("shelter_id", "status", "occupancy", "capacity", "geometry", "timestamp")
    SHELTER_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    OCCUPANCY_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    GEOMETRY_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    shelter_id: str
    status: str
    occupancy: int
    capacity: int
    geometry: Geometry
    timestamp: str
    def __init__(self, shelter_id: _Optional[str] = ..., status: _Optional[str] = ..., occupancy: _Optional[int] = ..., capacity: _Optional[int] = ..., geometry: _Optional[_Union[Geometry, _Mapping]] = ..., timestamp: _Optional[str] = ...) -> None: ...
