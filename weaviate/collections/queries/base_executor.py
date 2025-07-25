import datetime
import uuid as uuid_lib
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
    Union,
    cast,
)

from typing_extensions import is_typeddict

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.grpc import (
    METADATA,
    PROPERTIES,
    REFERENCES,
    MetadataQuery,
    QueryNested,
    _MetadataQuery,
    _QueryReference,
)
from weaviate.collections.classes.internal import (
    CrossReferences,
    GenerativeGroup,
    GenerativeGroupByReturn,
    GenerativeGrouped,
    GenerativeMetadata,
    GenerativeObject,
    GenerativeReturn,
    GenerativeSingle,
    Group,
    GroupByMetadataReturn,
    GroupByObject,
    GroupByReturn,
    MetadataReturn,
    Object,
    QueryReturn,
    ReturnProperties,
    ReturnReferences,
    WeaviateProperties,
    _CrossReference,
    _extract_properties_from_data_model,
    _extract_references_from_data_model,
    _QueryOptions,
)
from weaviate.collections.classes.types import GeoCoordinate, TReferences, _PhoneNumber
from weaviate.collections.grpc.query import _QueryGRPC
from weaviate.collections.grpc.shared import _ByteOps, _Unpack
from weaviate.connect.v4 import ConnectionType
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1 import base_pb2, generative_pb2, properties_pb2, search_get_pb2
from weaviate.types import INCLUDE_VECTOR
from weaviate.util import (
    _datetime_from_weaviate_str,
    _WeaviateUUIDInt,
)
from weaviate.validator import _validate_input, _ValidateArgument
from weaviate.warnings import _Warnings


class _BaseExecutor(Generic[ConnectionType]):
    def __init__(
        self,
        connection: ConnectionType,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        properties: Optional[Type[WeaviateProperties]],
        references: Optional[Type[Optional[Mapping[str, Any]]]],
        validate_arguments: bool,
    ) -> None:
        self._connection = connection
        self._name = name
        self.__tenant = tenant
        self.__consistency_level = consistency_level
        self._properties = properties
        self._references = references
        self._validate_arguments = validate_arguments

        self.__uses_125_api = connection._weaviate_version.is_at_least(1, 25, 0)
        self.__uses_127_api = connection._weaviate_version.is_at_least(1, 27, 0)
        self._query = _QueryGRPC(
            connection._weaviate_version,
            self._name,
            self.__tenant,
            self.__consistency_level,
            validate_arguments=self._validate_arguments,
            uses_125_api=self.__uses_125_api,
            uses_127_api=self.__uses_127_api,
        )

    def __retrieve_timestamp(
        self,
        timestamp: int,
    ) -> datetime.datetime:
        # Handle the case in which last_update_time_unix is in nanoseconds or milliseconds, issue #958
        if len(str(timestamp)) <= 13:
            return datetime.datetime.fromtimestamp(timestamp / 1000, tz=datetime.timezone.utc)
        else:
            return datetime.datetime.fromtimestamp(timestamp / 1e9, tz=datetime.timezone.utc)

    def __extract_metadata_for_object(
        self,
        add_props: "search_get_pb2.MetadataResult",
    ) -> MetadataReturn:
        meta = MetadataReturn(
            distance=add_props.distance if add_props.distance_present else None,
            certainty=add_props.certainty if add_props.certainty_present else None,
            creation_time=(
                self.__retrieve_timestamp(add_props.creation_time_unix)
                if add_props.creation_time_unix_present
                else None
            ),
            last_update_time=(
                self.__retrieve_timestamp(add_props.last_update_time_unix)
                if add_props.last_update_time_unix_present
                else None
            ),
            score=add_props.score if add_props.score_present else None,
            explain_score=(add_props.explain_score if add_props.explain_score_present else None),
            is_consistent=(add_props.is_consistent if add_props.is_consistent_present else None),
            rerank_score=(add_props.rerank_score if add_props.rerank_score_present else None),
        )
        return meta

    def __extract_metadata_for_group_by_object(
        self,
        add_props: "search_get_pb2.MetadataResult",
    ) -> GroupByMetadataReturn:
        meta = GroupByMetadataReturn(
            distance=add_props.distance if add_props.distance_present else None,
        )
        return meta

    def __extract_id_for_object(
        self,
        add_props: "search_get_pb2.MetadataResult",
    ) -> uuid_lib.UUID:
        return _WeaviateUUIDInt(int.from_bytes(add_props.id_as_bytes, byteorder="big"))

    def __extract_vector_for_object(
        self,
        add_props: "search_get_pb2.MetadataResult",
    ) -> Dict[str, Union[List[float], List[List[float]]]]:
        if (
            len(add_props.vector_bytes) == 0
            and len(add_props.vector) == 0
            and len(add_props.vectors) == 0
        ):
            return {}

        if len(add_props.vector_bytes) > 0:
            vec = _ByteOps.decode_float32s(add_props.vector_bytes)
            return {"default": vec}

        vecs: Dict[str, Union[List[float], List[List[float]]]] = {}
        for vec in add_props.vectors:
            if vec.type == base_pb2.Vectors.VECTOR_TYPE_SINGLE_FP32:
                vecs[vec.name] = _Unpack.single(vec.vector_bytes)
            elif vec.type == base_pb2.Vectors.VECTOR_TYPE_MULTI_FP32:
                vecs[vec.name] = _Unpack.multi(vec.vector_bytes)
            else:
                vecs[vec.name] = _Unpack.single(vec.vector_bytes)
        return vecs

    def __extract_generated_from_metadata(
        self,
        add_props: search_get_pb2.MetadataResult,
    ) -> Optional[str]:
        return add_props.generative if add_props.generative_present else None

    def __extract_generated_from_generative(
        self, generative: generative_pb2.GenerativeResult
    ) -> Optional[str]:
        return generative.values[0].result if len(generative.values) > 0 else None

    def __extract_generated_from_reply(self, res: search_get_pb2.SearchReply) -> Optional[str]:
        if (
            res.generative_grouped_result != ""
        ):  # for BC, is deprecated in favour of generative_grouped_results
            return res.generative_grouped_result
        if len(res.generative_grouped_results.values) > 0:
            return res.generative_grouped_results.values[0].result
        return None

    def __extract_generative_metadata(
        self, metadata: generative_pb2.GenerativeMetadata
    ) -> Optional[GenerativeMetadata]:
        if metadata.HasField("anthropic"):
            return metadata.anthropic
        if metadata.HasField("anyscale"):
            return metadata.anyscale
        if metadata.HasField("aws"):
            return metadata.aws
        if metadata.HasField("cohere"):
            return metadata.cohere
        if metadata.HasField("databricks"):
            return metadata.databricks
        if metadata.HasField("dummy"):
            return metadata.dummy
        if metadata.HasField("friendliai"):
            return metadata.friendliai
        if metadata.HasField("google"):
            return metadata.google
        if metadata.HasField("mistral"):
            return metadata.mistral
        if metadata.HasField("nvidia"):
            return metadata.nvidia
        if metadata.HasField("ollama"):
            return metadata.ollama
        if metadata.HasField("openai"):
            return metadata.openai
        return None

    def __extract_generative_single_from_generative(
        self, result: generative_pb2.GenerativeResult
    ) -> Optional[GenerativeSingle]:
        if len(vs := result.values) > 0:
            generative = vs[0]
            return GenerativeSingle(
                debug=generative.debug if generative.debug.full_prompt != "" else None,
                metadata=self.__extract_generative_metadata(generative.metadata),
                text=generative.result,
            )
        return None

    def __extract_generative_grouped_from_generative(
        self, result: generative_pb2.GenerativeResult
    ) -> Optional[GenerativeGrouped]:
        if len(vs := result.values) > 0:
            generative = vs[0]
            return GenerativeGrouped(
                metadata=self.__extract_generative_metadata(generative.metadata),
                text=generative.result,
            )
        return None

    def __deserialize_list_value_prop_125(
        self, value: properties_pb2.ListValue
    ) -> Optional[List[Any]]:
        if value.HasField("bool_values"):
            return list(value.bool_values.values)
        if value.HasField("date_values"):
            return [_datetime_from_weaviate_str(val) for val in value.date_values.values]
        if value.HasField("int_values"):
            return _ByteOps.decode_int64s(value.int_values.values)
        if value.HasField("number_values"):
            return _ByteOps.decode_float64s(value.number_values.values)
        if value.HasField("text_values"):
            return list(value.text_values.values)
        if value.HasField("uuid_values"):
            return [uuid_lib.UUID(val) for val in value.uuid_values.values]
        if value.HasField("object_values"):
            return [
                self.__parse_nonref_properties_result(val) for val in value.object_values.values
            ]
        _Warnings.unknown_type_encountered(value.WhichOneof("value"))
        return None

    def __deserialize_list_value_prop_123(self, value: properties_pb2.ListValue) -> List[Any]:
        return [self.__deserialize_non_ref_prop(val) for val in value.values]

    def __deserialize_non_ref_prop(self, value: properties_pb2.Value) -> Any:
        if value.HasField("uuid_value"):
            return uuid_lib.UUID(value.uuid_value)
        if value.HasField("date_value"):
            return _datetime_from_weaviate_str(value.date_value)
        if value.HasField("string_value"):
            return str(value.string_value)
        if value.HasField("text_value"):
            return str(value.text_value)
        if value.HasField("int_value"):
            return int(value.int_value)
        if value.HasField("number_value"):
            return float(value.number_value)
        if value.HasField("bool_value"):
            return bool(value.bool_value)
        if value.HasField("list_value"):
            return (
                self.__deserialize_list_value_prop_125(value.list_value)
                if self._connection._weaviate_version.is_at_least(1, 25, 0)
                else self.__deserialize_list_value_prop_123(value.list_value)
            )
        if value.HasField("object_value"):
            return self.__parse_nonref_properties_result(value.object_value)
        if value.HasField("geo_value"):
            return GeoCoordinate(
                latitude=value.geo_value.latitude, longitude=value.geo_value.longitude
            )
        if value.HasField("blob_value"):
            return value.blob_value
        if value.HasField("phone_value"):
            return _PhoneNumber(
                country_code=value.phone_value.country_code,
                default_country=value.phone_value.default_country,
                international_formatted=value.phone_value.international_formatted,
                national=value.phone_value.national,
                national_formatted=value.phone_value.national_formatted,
                number=value.phone_value.input,
                valid=value.phone_value.valid,
            )
        if value.HasField("null_value"):
            return None

        _Warnings.unknown_type_encountered(value.WhichOneof("value"))
        return None

    def __parse_nonref_properties_result(
        self,
        properties: properties_pb2.Properties,
    ) -> dict:
        return {
            name: self.__deserialize_non_ref_prop(value)
            for name, value in properties.fields.items()
        }

    def __parse_ref_properties_result(
        self,
        properties: search_get_pb2.PropertiesResult,
    ) -> Optional[dict]:
        if len(properties.ref_props) == 0:
            return {} if properties.ref_props_requested else None

        return {
            ref_prop.prop_name: _CrossReference._from(
                [
                    self.__result_to_query_object(
                        prop,
                        prop.metadata,
                        _QueryOptions(True, True, True, True, False),
                    )
                    for prop in ref_prop.properties
                ]
            )
            for ref_prop in properties.ref_props
        }

    def __result_to_query_object(
        self,
        props: search_get_pb2.PropertiesResult,
        meta: search_get_pb2.MetadataResult,
        options: _QueryOptions,
    ) -> Object[Any, Any]:
        return Object(
            collection=props.target_collection,
            properties=(
                self.__parse_nonref_properties_result(props.non_ref_props)
                if options.include_properties
                else {}
            ),
            metadata=(
                self.__extract_metadata_for_object(meta)
                if options.include_metadata
                else MetadataReturn()
            ),
            references=(
                self.__parse_ref_properties_result(props) if options.include_references else None
            ),
            uuid=self.__extract_id_for_object(meta),
            vector=(self.__extract_vector_for_object(meta) if options.include_vector else {}),
        )

    def __result_to_generative_object(
        self,
        props: search_get_pb2.PropertiesResult,
        meta: search_get_pb2.MetadataResult,
        gen: generative_pb2.GenerativeResult,
        options: _QueryOptions,
    ) -> GenerativeObject[Any, Any]:
        return GenerativeObject(
            collection=props.target_collection,
            properties=(
                self.__parse_nonref_properties_result(props.non_ref_props)
                if options.include_properties
                else {}
            ),
            metadata=(
                self.__extract_metadata_for_object(meta)
                if options.include_metadata
                else MetadataReturn()
            ),
            references=(
                self.__parse_ref_properties_result(props) if options.include_references else None
            ),
            uuid=self.__extract_id_for_object(meta),
            vector=(self.__extract_vector_for_object(meta) if options.include_vector else {}),
            generated=(
                self.__extract_generated_from_generative(gen)
                if self.__uses_127_api
                else self.__extract_generated_from_metadata(meta)
            ),
            generative=self.__extract_generative_single_from_generative(gen),
        )

    def __result_to_group(
        self,
        res: search_get_pb2.GroupByResult,
        options: _QueryOptions,
    ) -> Group[Any, Any]:
        return Group(
            objects=[
                self.__result_to_group_by_object(obj.properties, obj.metadata, options, res.name)
                for obj in res.objects
            ],
            name=res.name,
            number_of_objects=res.number_of_objects,
            min_distance=res.min_distance,
            max_distance=res.max_distance,
            rerank_score=res.rerank.score if res.rerank is not None else None,
        )

    def __result_to_generative_group(
        self,
        res: search_get_pb2.GroupByResult,
        options: _QueryOptions,
    ) -> GenerativeGroup[Any, Any]:
        return GenerativeGroup(
            objects=[
                self.__result_to_group_by_object(obj.properties, obj.metadata, options, res.name)
                for obj in res.objects
            ],
            name=res.name,
            number_of_objects=res.number_of_objects,
            min_distance=res.min_distance,
            max_distance=res.max_distance,
            rerank_score=res.rerank.score if res.rerank is not None else None,
            generated=res.generative.result if res.generative is not None else None,
        )

    def __result_to_group_by_object(
        self,
        props: search_get_pb2.PropertiesResult,
        meta: search_get_pb2.MetadataResult,
        options: _QueryOptions,
        group_name: str,
    ) -> GroupByObject[Any, Any]:
        return GroupByObject(
            collection=props.target_collection,
            properties=(
                self.__parse_nonref_properties_result(props.non_ref_props)
                if options.include_properties
                else {}
            ),
            metadata=(
                self.__extract_metadata_for_group_by_object(meta)
                if options.include_metadata
                else GroupByMetadataReturn()
            ),
            references=(
                self.__parse_ref_properties_result(props) if options.include_references else None
            ),
            uuid=self.__extract_id_for_object(meta),
            vector=(self.__extract_vector_for_object(meta) if options.include_vector else {}),
            belongs_to_group=group_name,
        )

    def _result_to_query_return(
        self,
        res: search_get_pb2.SearchReply,
        options: _QueryOptions,
    ) -> QueryReturn[WeaviateProperties, CrossReferences]:
        return QueryReturn(
            objects=[
                self.__result_to_query_object(obj.properties, obj.metadata, options)
                for obj in res.results
            ]
        )

    def _result_to_generative_query_return(
        self,
        res: search_get_pb2.SearchReply,
        options: _QueryOptions,
    ) -> GenerativeReturn[WeaviateProperties, CrossReferences]:
        return GenerativeReturn(
            generated=self.__extract_generated_from_reply(res),
            objects=[
                self.__result_to_generative_object(
                    obj.properties, obj.metadata, obj.generative, options
                )
                for obj in res.results
            ],
            generative=self.__extract_generative_grouped_from_generative(
                res.generative_grouped_results
            ),
        )

    def _result_to_generative_return(
        self,
        res: search_get_pb2.SearchReply,
        options: _QueryOptions,
    ) -> Union[
        GenerativeReturn[WeaviateProperties, CrossReferences],
        GenerativeGroupByReturn[WeaviateProperties, CrossReferences],
    ]:
        return (
            self._result_to_generative_query_return(res, options)
            if options.is_group_by is False
            else self._result_to_generative_groupby_return(res, options)
        )

    def _result_to_groupby_return(
        self,
        res: search_get_pb2.SearchReply,
        options: _QueryOptions,
    ) -> GroupByReturn[WeaviateProperties, CrossReferences]:
        groups = {
            group.name: self.__result_to_group(group, options) for group in res.group_by_results
        }
        objects_group_by: List[GroupByObject] = [
            obj for group in groups.values() for obj in group.objects
        ]
        return GroupByReturn(objects=objects_group_by, groups=groups)

    def _result_to_generative_groupby_return(
        self,
        res: search_get_pb2.SearchReply,
        options: _QueryOptions,
    ) -> GenerativeGroupByReturn[WeaviateProperties, CrossReferences]:
        groups = {
            group.name: self.__result_to_generative_group(group, options)
            for group in res.group_by_results
        }
        objects_group_by: List[GroupByObject] = [
            GroupByObject(
                collection=obj.collection,
                properties=obj.properties,
                references=obj.references,
                metadata=obj.metadata,
                belongs_to_group=group.name,
                uuid=obj.uuid,
                vector=obj.vector,
            )
            for group in groups.values()
            for obj in group.objects
        ]
        return GenerativeGroupByReturn(
            objects=objects_group_by,
            groups=groups,
            generated=(
                res.generative_grouped_result if res.generative_grouped_result != "" else None
            ),
        )

    def _result_to_query_or_groupby_return(
        self,
        res: search_get_pb2.SearchReply,
        options: _QueryOptions,
    ) -> Union[
        QueryReturn[WeaviateProperties, CrossReferences],
        GroupByReturn[WeaviateProperties, CrossReferences],
    ]:
        return (
            self._result_to_query_return(res, options)
            if not options.is_group_by
            else self._result_to_groupby_return(res, options)
        )

    def _parse_return_properties(
        self,
        return_properties: Optional[ReturnProperties[WeaviateProperties]],
    ) -> Union[PROPERTIES, bool, None]:
        if (
            return_properties is not None and not return_properties
        ):  # fast way to check if it is an empty list or False
            return []

        if (
            isinstance(return_properties, Sequence)
            or isinstance(return_properties, str)
            or isinstance(return_properties, QueryNested)
            or (
                (return_properties is None or return_properties is True)
                and self._properties is None
            )
        ):
            # return self.__parse_properties(return_properties)
            return cast(
                Union[PROPERTIES, bool, None], return_properties
            )  # is not sourced from any generic
        elif (
            return_properties is None or return_properties is True
        ) and self._properties is not None:
            if not is_typeddict(self._properties):
                return return_properties
            return _extract_properties_from_data_model(
                self._properties
            )  # is sourced from collection-specific generic
        else:
            assert return_properties is not None
            assert return_properties is not True
            if not is_typeddict(return_properties):
                raise WeaviateInvalidInputError(
                    f"return_properties must only be a TypedDict or PROPERTIES within this context but is {type(return_properties)}"
                )
            return _extract_properties_from_data_model(
                return_properties
            )  # is sourced from query-specific generic

    def _parse_return_metadata(
        self, return_metadata: Optional[METADATA], include_vector: INCLUDE_VECTOR
    ) -> Optional[_MetadataQuery]:
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(
                        [Sequence[str], MetadataQuery, None],
                        "return_metadata",
                        return_metadata,
                    ),
                    _ValidateArgument([bool, str, Sequence], "include_vector", include_vector),
                ]
            )
        if return_metadata is None:
            ret_md = None
        elif hasattr(return_metadata, "creation_time"):
            # cheaper than isinstance(), needs to be MetadataQuery
            ret_md = cast(MetadataQuery, return_metadata)
        else:
            ret_md = MetadataQuery(**{str(prop): True for prop in return_metadata})
        return _MetadataQuery.from_public(ret_md, include_vector)

    def _parse_return_references(
        self, return_references: Optional[ReturnReferences[TReferences]]
    ) -> Optional[REFERENCES]:
        if (
            (return_references is None and self._references is None)
            or isinstance(return_references, Sequence)
            or isinstance(return_references, _QueryReference)
        ):
            return return_references
        elif return_references is None and self._references is not None:
            if not is_typeddict(self._references):
                return return_references
            refs = _extract_references_from_data_model(self._references)
            return refs
        else:
            assert return_references is not None
            if not is_typeddict(return_references):
                raise WeaviateInvalidInputError(
                    f"return_references must only be a TypedDict or ReturnReferences within this context but is {type(return_references)}"
                )
            return _extract_references_from_data_model(return_references)
