"""Protobuf wire format for ERDOS events.

Contains the ``event.proto`` schema and its generated ``event_pb2`` bindings.
The docs specify Protobuf as the serialization used by the Weather/River/
Simulator producers when publishing into Kafka.  Codecs live in
``backend/streaming/kafka/codec``; this package only holds the schema and the
generated message classes.
"""