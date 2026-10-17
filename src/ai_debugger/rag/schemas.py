"""
Milvus collection schemas.

Design notes:
- Only `vector` field holds the embedding of `error_content` (C6).
- Other scalar fields are filter/rank helpers; full payload lives in DocStore (D10).
- "enable_dynamic_field=False"
    => Milvus rejects any field not declared here (C6 enforced at DB level).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from pymilvus import DataType, MilvusClient

EMBEDDING_DIM: Final[int] = 1536


@dataclass(frozen=True)
class StaticSchema:
    """Field names for static_database collection."""

    doc_id: str = "doc_id"
    vector: str = "vector"
    system_name: str = "system_name"
    error_code: str = "error_code"
    tags: str = "tags"
    verified: str = "verified"

    # Output fields returned from a search — deliberately EXCLUDES solution/symptoms (C6).
    search_output_fields: tuple[str, ...] = (
        "doc_id",
        "system_name",
        "error_code",
        "tags",
        "verified",
    )


@dataclass(frozen=True)
class DynamicSchema:
    """Field names for dynamic_database collection. Created now, used in Phase 5."""

    memory_id: str = "memory_id"
    vector: str = "vector"
    confidence_score: str = "confidence_score"
    occurrence_count: str = "occurrence_count"
    tags: str = "tags"

    search_output_fields: tuple[str, ...] = (
        "memory_id",
        "confidence_score",
        "occurrence_count",
        "tags",
    )


STATIC: Final[StaticSchema] = StaticSchema()
DYNAMIC: Final[DynamicSchema] = DynamicSchema()


def build_static_schema() -> object:
    """Create the Milvus CollectionSchema for static_database."""
    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field(
        field_name=STATIC.doc_id,
        datatype=DataType.VARCHAR,
        max_length=64,
        is_primary=True,
    )
    schema.add_field(field_name=STATIC.vector, datatype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)
    schema.add_field(field_name=STATIC.system_name, datatype=DataType.VARCHAR, max_length=128)
    schema.add_field(field_name=STATIC.error_code, datatype=DataType.VARCHAR, max_length=128)
    schema.add_field(
        field_name=STATIC.tags,
        datatype=DataType.ARRAY,
        element_type=DataType.VARCHAR,
        max_capacity=32,
        max_length=64,
    )
    schema.add_field(field_name=STATIC.verified, datatype=DataType.BOOL)
    return schema


def build_dynamic_schema() -> object:
    """Create the Milvus CollectionSchema for dynamic_database."""
    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field(
        field_name=DYNAMIC.memory_id,
        datatype=DataType.VARCHAR,
        max_length=64,
        is_primary=True,
    )
    schema.add_field(field_name=DYNAMIC.vector, datatype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)
    schema.add_field(field_name=DYNAMIC.confidence_score, datatype=DataType.FLOAT)
    schema.add_field(field_name=DYNAMIC.occurrence_count, datatype=DataType.INT64)
    schema.add_field(
        field_name=DYNAMIC.tags,
        datatype=DataType.ARRAY,
        element_type=DataType.VARCHAR,
        max_capacity=32,
        max_length=64,
    )
    return schema
