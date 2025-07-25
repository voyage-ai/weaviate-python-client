import warnings
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Optional

try:
    __version__ = version("weaviate-client")
except PackageNotFoundError:
    __version__ = "unknown version"


class _Warnings:
    @staticmethod
    def auth_with_anon_weaviate() -> None:
        warnings.warn(
            message="""Auth001: The client is configured to use authentication, but weaviate is configured without
                    authentication. Are you sure this is correct?""",
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def auth_no_refresh_token(auth_len: Optional[int] = None) -> None:
        if auth_len is not None:
            msg = f"The current access token is only valid for {auth_len}s."
        else:
            msg = "Also, no expiration time was given."

        warnings.warn(
            message=f"""Auth002: The token your identity provider returned does not contain a refresh token. {msg}

            Access to your weaviate instance is not possible after the token expires. This client returns an
            authentication exception.

            Things to try:
            - You might need to enable refresh tokens in your authentication provider settings.
            - You might need to send the correct scope. For some providers, the scope needs to include "offline_access".
            """,
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def auth_negative_expiration_time(expires_in: int) -> None:
        msg = f"""Auth003: Access token expiration time is negative: {expires_in}."""

        warnings.warn(message=msg, category=UserWarning, stacklevel=1)

    @staticmethod
    def auth_header_and_auth_secret() -> None:
        msg = """Auth004: Received an authentication header and an auth_client_secret parameter.

        The auth_client_secret takes precedence over the header. The authentication header will be ignored.

        Use weaviate.auth.AuthBearerToken(..) to supply an access token via auth_client_secret parameter and,
        if available with your provider, to supply refresh tokens and token lifetimes.
        """
        warnings.warn(message=msg, category=UserWarning, stacklevel=1)

    @staticmethod
    def auth_cannot_parse_oidc_config(url: str) -> None:
        msg = f"""Auth005: Could not parse Weaviate's OIDC configuration, using unauthenticated access. If you added
        an authorization header yourself it will be unaffected.

        This can happen if weaviate is miss-configured or if you have a proxy between the client and weaviate.
        You can test this by visiting {url}."""
        warnings.warn(message=msg, category=UserWarning, stacklevel=1)

    @staticmethod
    def token_refresh_failed(exc: Exception) -> None:
        warnings.warn(
            message=f"""Con001: Could not reach token issuer for the periodic refresh. This client will automatically
            retry to refresh. If the retry does not succeed, the client will become unauthenticated.

            The cause might be an unstable internet connection or a problem with your authentication provider.
            Exception: {exc}
            """,
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def weaviate_too_old_vs_latest(server_version: str) -> None:
        warnings.warn(
            message=f"""Dep004: You are connected to Weaviate {server_version}.
            Consider upgrading to the latest version. See https://www.weaviate.io/developers/weaviate for details.""",
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def weaviate_client_too_old_vs_latest(client_version: str, latest_version: str) -> None:
        warnings.warn(
            message=f"""Dep005: You are using weaviate-client version {client_version}. The latest version is {latest_version}.
            Consider upgrading to the latest version. See https://weaviate.io/developers/weaviate/client-libraries/python for details.""",
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def root_module_import(name: str, loc: str) -> None:
        warnings.warn(
            f"Dep010: Importing {name} from weaviate is deprecated. "
            f"Import {name} from its module: weaviate.{loc}",
            DeprecationWarning,
            stacklevel=2,  # don't increase stacklevel, as this otherwise writes the auth-secrets into the log
        )

    @staticmethod
    def palm_to_google_t2v() -> None:
        warnings.warn(
            "Dep011: text2vec-palm is deprecated and will be removed in Q2 25. Use text2vec-google instead.",
            DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def palm_to_google_m2v() -> None:
        warnings.warn(
            "Dep012: multi2vec-palm is deprecated and will be removed in Q2 25. Use multi2vec-google instead.",
            DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def palm_to_google_gen() -> None:
        warnings.warn(
            "Dep013: generative.palm is deprecated and will be removed in Q2 25. Use generative.google instead.",
            DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def vector_index_config_in_config_update() -> None:
        warnings.warn(
            message="""Dep017: You are using the `vector_index_config` argument in the `collection.config.update()` method, which is deprecated.
            Use the `vector_config` argument instead.
            """,
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def sharding_actual_count_is_deprecated(argument: str) -> None:
        warnings.warn(
            message=f"""Dep018: You are using the {argument} argument in the `Configure.sharding` method, which is deprecated.
            This field is read-only, the argument has no effect. It will be removed in a future release.""",
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def bit_compression_in_pq_config() -> None:
        warnings.warn(
            message="""Dep019: The `bit_compression` argument in `PQConfig` is deprecated and will be removed by Q4 2024.""",
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def batch_results_objects_all_responses_attribute() -> None:
        warnings.warn(
            message="""Dep020: The `all_responses` attribute in the `BatchResults` object is deprecated and will be removed by Q4 2024. Please instead use the `errors` and `uuids` attributes.""",
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def deprecated_tenant_type(old: str, new: str) -> None:
        warnings.warn(
            message=f"""Dep021: The tenant status {old} is deprecated and will be removed by Q1 2025. Please use {new} instead.""",
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def oidc_with_wcd_deprecated() -> None:
        warnings.warn(
            message="""Dep022: connecting to Weaviate Cloud (WCD) using OIDC is deprecated and will be removed in August 2025. Please use API keys instead.""",
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def vectorizer_config_in_config_update() -> None:
        warnings.warn(
            message="""Dep023: You are using the `vectorizer_config` argument in the `collection.config.update()` method with a collection with named vectors, which is deprecated.
            Use the `vector_config` argument instead.
            """,
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def vectorizer_config_in_config_create() -> None:
        warnings.warn(
            message="""Dep024: You are using the `vectorizer_config` argument in `collection.config.create()`, which is deprecated.
            Use the `vector_config` argument instead.
            """,
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def vector_index_config_in_config_create() -> None:
        warnings.warn(
            message="""Dep025: You are using the `vector_index_config` argument in `collection.config.create()`, which is deprecated.
            Use the `vector_config` argument instead defining `vector_index_config` as a sub-argument.
            """,
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def named_vector_syntax_in_config_add_vector(name: str) -> None:
        warnings.warn(
            message=f"""Dep026: You are using the named vector syntax for vector {name}, e.g. `Configure.NamedVectors` in `collection.config.add_vector()`, which is deprecated.
            Use `Configure.Vectors` or `Configure.MultiVectors` instead.`
            """,
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def encoding_in_multi_vector_config() -> None:
        warnings.warn(
            message="""Dep026: You are using the `encoding` argument in `Configure.VectorIndex.MultiVectors.multi_vector()`, which is deprecated.
            Use the `encoding` argument inside `Configure.MultiVectors.module()` instead.
            """,
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def multi_vector_in_hnsw_config() -> None:
        warnings.warn(
            message="""Dep027: You are using the `multi_vector` argument in `Configure.VectorIndex.hnsw()`, which is deprecated.
            Use the `multi_vector` argument inside `Configure.MultiVectors.module()` instead.
            """,
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def datetime_insertion_with_no_specified_timezone(date: datetime) -> None:
        warnings.warn(
            message=f"""Con002: You are using the datetime object {date} without a timezone. The timezone will be set to UTC.
            To use a different timezone, specify it in the datetime object. For example:
            datetime.datetime(2021, 1, 1, 0, 0, 0, tzinfo=datetime.timezone(-datetime.timedelta(hours=2))).isoformat() = 2021-01-01T00:00:00-02:00
            """,
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def datetime_year_zero(date: str) -> None:
        warnings.warn(
            message=f"""Con004: Received a date {date} with year 0. The year 0 does not exist in the Gregorian calendar
            and cannot be parsed by the datetime library. The year will be set to {datetime.min}.
            See https://en.wikipedia.org/wiki/Year_zero for more information.""",
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def batch_refresh_failed(err: str) -> None:
        warnings.warn(
            message=f"""Bat003: The dynamic batch-size could not be refreshed successfully: error {err}""",
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def batch_rate_limit_reached(msg: str, seconds: int) -> None:
        warnings.warn(
            message=f"""Bat005: Rate limit reached with error {msg}.
            Sleeping for {seconds} seconds.""",
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def unknown_type_encountered(field: str) -> None:
        warnings.warn(
            message=f"""Grpc002: Unknown return type {field} received, skipping value and returning None.""",
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def unclosed_connection() -> None:
        warnings.warn(
            message="""Con004: The connection to Weaviate was not closed properly. This can lead to memory leaks.
            Please make sure to close the connection using `client.close()`.""",
            category=ResourceWarning,
            stacklevel=1,
        )

    @staticmethod
    def grpc_max_msg_size_not_found() -> None:
        warnings.warn(
            message="""Con005: Could not retrieve the maximum GRPC message size from the weaviate server. Using the default
            value of 10mb. If you need a larger message size, please update weaviate.""",
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def unknown_permission_encountered(permission: Any) -> None:
        warnings.warn(
            message=f"""RBAC001: Unknown permission {permission} received, skipping value.""",
            category=UserWarning,
            stacklevel=1,
        )
