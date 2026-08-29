"""Streamlit 기반 krforest API 디버그 UI."""
# ruff: noqa: E402,I001

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
for module_name, module in list(sys.modules.items()):
    if module_name != "krforest" and not module_name.startswith("krforest."):
        continue
    module_file = getattr(module, "__file__", None)
    if module_file is not None and not Path(module_file).resolve().is_relative_to(SRC):
        del sys.modules[module_name]

try:
    import pandas as pd
    import streamlit as st
except ModuleNotFoundError as exc:  # pragma: no cover - 선택 실행 도구
    raise SystemExit('Streamlit UI를 쓰려면 `pip install -e ".[debug-ui]"`를 실행하세요.') from exc

from krforest import CatalogEntry, DebugRun, ForestClient, api_catalog, jsonable, save_fixture
from krforest.config import DEFAULT_ENV_NAME


@dataclass(frozen=True)
class ParameterSpec:
    """디버그 UI에서 요청 파라미터 입력 폼을 만들기 위한 최소 명세."""

    name: str
    required: bool
    label: str
    placeholder: str = ""
    help: str = ""
    default: str = ""


def _param(
    name: str,
    *,
    required: bool,
    label: str | None = None,
    placeholder: str = "",
    help: str = "",
    default: str = "",
) -> ParameterSpec:
    return ParameterSpec(
        name=name,
        required=required,
        label=label or name,
        placeholder=placeholder,
        help=help,
        default=default,
    )


def main() -> None:
    st.set_page_config(page_title="krforest Debug UI", layout="wide")
    st.title("krforest Debug UI")

    entries = list(api_catalog())
    labels = [entry.display_name for entry in entries]

    # 1. Data source 선택 — API 17개(50개 미만)라 단일 API selectbox로 충분하다.
    selected_label = st.sidebar.selectbox("API", labels)
    entry = entries[labels.index(selected_label)]

    # 2. 선택한 API 설명 2줄: 무엇을 하는 API인지 + 어떤 데이터를 반환하는지.
    st.sidebar.caption(f"{entry.display_name} — `{entry.service}/{entry.operation}` 호출")
    st.sidebar.caption(entry.description)

    # 3. Environment: 실제 서비스가 읽는 env var 사용 vs 수동 입력.
    st.sidebar.subheader("Environment")
    env_value = os.getenv(DEFAULT_ENV_NAME)
    env_available = bool(env_value and env_value.strip())
    environment = st.sidebar.radio(
        "Service key source",
        ["env", "manual"],
        index=0 if env_available else 1,
        horizontal=True,
        key="environment",
    )
    if environment == "env":
        if env_available:
            st.sidebar.caption(f"`{DEFAULT_ENV_NAME}` 환경변수 값을 사용합니다.")
        else:
            st.sidebar.warning(
                f"`{DEFAULT_ENV_NAME}` 환경변수가 비어 있습니다. manual로 전환하세요."
            )
    else:
        st.sidebar.caption("아래 Auth에 직접 입력한 값을 사용합니다 (환경변수 미사용).")

    # 4. Auth: 이 API가 실제로 쓰는 쿼리 파라미터명으로 입력창을 만든다.
    st.sidebar.subheader("Auth")
    auth_param = entry.service_key_param or "ServiceKey"
    manual_key = st.sidebar.text_input(
        auth_param,
        value="",
        type="password",
        disabled=environment == "env",
        help=f"이 API의 실제 인증 쿼리 파라미터명은 `{auth_param}`입니다.",
    )
    effective_api_key = (env_value or "") if environment == "env" else manual_key

    # 5. 서비스키 발급 링크 버튼: 카탈로그의 service_key_url을 그대로 사용.
    if entry.service_key_url:
        st.sidebar.link_button(
            "서비스키 발급 / 활용신청",
            entry.service_key_url,
            use_container_width=True,
        )
    if entry.service_key_account_url:
        st.sidebar.link_button(
            "내 인증키 확인",
            entry.service_key_account_url,
            use_container_width=True,
        )

    # 6. Timeout.
    timeout = st.sidebar.number_input(
        "Timeout (seconds)",
        min_value=1.0,
        max_value=120.0,
        value=20.0,
        step=1.0,
        help="API 요청 timeout seconds입니다.",
    )

    # 7. Fixture 저장 기준 디렉터리.
    fixture_base_dir = _fixture_base_dir_sidebar()

    tabs = st.tabs(
        [
            "Raw Response",
            "Pydantic Model",
            "Processed Result",
            "Validation Errors",
            "Debug Trace",
            "Fixture / Testcase",
        ]
    )

    with tabs[0]:
        _raw_response_tab(entry, effective_api_key, timeout=float(timeout))
    with tabs[1]:
        _pydantic_model_tab(entry)
    with tabs[2]:
        _processed_result_tab(entry)
    with tabs[3]:
        _validation_errors_tab(entry)
    with tabs[4]:
        _debug_trace_tab(entries, entry)
    with tabs[5]:
        _fixture_tab(fixture_base_dir, entry)


def _raw_response_tab(entry: CatalogEntry, api_key: str, *, timeout: float) -> None:
    st.subheader(entry.display_name)
    st.caption(f"{entry.provider} · `{entry.service}/{entry.operation}`")
    if entry.notes:
        st.caption(f"참고: {entry.notes}")

    try:
        submitted, params, request_options, missing = _request_form(entry)
    except ValueError as exc:
        st.error(str(exc))
        return

    preview = {
        **params,
        "pageNo": request_options["page_no"],
        "numOfRows": request_options["num_of_rows"],
        "response_format": request_options["response_format"] or "(카탈로그 기본값)",
    }
    st.subheader("Request params preview")
    st.json(preview)

    if not submitted:
        return
    if missing:
        st.error("필수 파라미터를 입력하세요: " + ", ".join(missing))
        return

    async def _run() -> DebugRun:
        async with ForestClient(api_key=api_key or None, timeout=timeout) as client:
            return await client.debug_endpoint(
                entry.key,
                params,
                page_no=request_options["page_no"],
                num_of_rows=request_options["num_of_rows"],
                response_format=request_options["response_format"],
            )

    try:
        run = asyncio.run(_run())
    except Exception as exc:  # pragma: no cover - UI 표시
        st.error(str(exc))
        return

    _store_run(entry, run)
    if run.error:
        st.error(run.error["message"])
    st.json(jsonable(run.response))


def _request_form(
    entry: CatalogEntry,
) -> tuple[bool, dict[str, Any], dict[str, Any], list[str]]:
    specs = _parameter_specs(entry)
    required_specs = [spec for spec in specs if spec.required]
    optional_specs = [spec for spec in specs if not spec.required]
    key_prefix = f"api:{entry.key}"

    with st.form(f"request-form:{key_prefix}"):
        st.subheader("Required parameters")
        if required_specs:
            required_values = _render_param_grid(required_specs, key_prefix=key_prefix)
        else:
            st.caption("이 API에는 필수 파라미터가 없습니다.")
            required_values = {}

        st.subheader("Optional parameters")
        if optional_specs:
            optional_values = _render_param_grid(optional_specs, key_prefix=key_prefix)
        else:
            st.caption(
                "카탈로그에 등록된 선택 파라미터가 없습니다. Extra params JSON을 사용하세요."
            )
            optional_values = {}

        page_no, num_of_rows, response_format = _render_common_options(key_prefix)

        extra_text = st.text_area(
            "Extra params JSON",
            value="{}",
            height=110,
            help="폼에 없는 provider 파라미터를 JSON object로 추가합니다.",
            key=f"{key_prefix}:extra",
        )
        submitted = st.form_submit_button("Run selected API")

    params = {**required_values, **optional_values, **_parse_extra_params(extra_text, entry)}
    missing = [spec.name for spec in required_specs if not str(params.get(spec.name, "")).strip()]
    return (
        submitted,
        {key: value for key, value in params.items() if str(value).strip()},
        {"page_no": page_no, "num_of_rows": num_of_rows, "response_format": response_format},
        missing,
    )


def _parameter_specs(entry: CatalogEntry) -> tuple[ParameterSpec, ...]:
    required = tuple(
        _param(
            name,
            required=True,
            help=f"{entry.display_name} 필수 요청 파라미터입니다.",
        )
        for name in entry.required_params
    )
    optional = tuple(
        _param(
            name,
            required=False,
            help=f"{entry.display_name} 선택 요청 파라미터입니다.",
        )
        for name in entry.optional_params
    )
    return required + optional


def _render_param_grid(specs: tuple[ParameterSpec, ...], *, key_prefix: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for index in range(0, len(specs), 2):
        columns = st.columns(2)
        for column, spec in zip(columns, specs[index : index + 2], strict=False):
            with column:
                values[spec.name] = st.text_input(
                    spec.label,
                    value=spec.default,
                    placeholder=spec.placeholder,
                    help=spec.help or None,
                    key=f"{key_prefix}:param:{spec.name}",
                )
    return values


def _render_common_options(key_prefix: str) -> tuple[int, int, str | None]:
    col1, col2, col3 = st.columns(3)
    with col1:
        page_no = st.number_input(
            "pageNo",
            min_value=1,
            value=1,
            step=1,
            help="공공데이터포털 paging 파라미터입니다.",
            key=f"{key_prefix}:pageNo",
        )
    with col2:
        num_of_rows = st.number_input(
            "numOfRows",
            min_value=1,
            max_value=1000,
            value=10,
            step=1,
            help="한 페이지에 받을 row 수입니다.",
            key=f"{key_prefix}:numOfRows",
        )
    with col3:
        response_format_choice = st.selectbox(
            "response_format",
            ["(카탈로그 기본값)", "json", "xml"],
            index=0,
            help="비워두면 endpoint의 기본 응답 포맷을 그대로 사용합니다.",
            key=f"{key_prefix}:response_format",
        )
    default_label = "(카탈로그 기본값)"
    response_format = None if response_format_choice == default_label else response_format_choice
    return int(page_no), int(num_of_rows), response_format


def _parse_extra_params(text: str, entry: CatalogEntry) -> dict[str, Any]:
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Extra params JSON is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Extra params JSON must be an object")
    reserved = {"pageNo", "numOfRows", "ServiceKey", "serviceKey", entry.service_key_param or ""}
    return {key: value for key, value in payload.items() if key not in reserved}


def _pydantic_model_tab(entry: CatalogEntry) -> None:
    run = _current_run(entry)
    if run is None:
        st.info("Raw Response 탭에서 선택한 API를 실행하면 여기에서 Pydantic 모델을 확인합니다.")
        return
    if run.error:
        st.warning("실행 중 오류가 있습니다. Validation Errors 탭을 확인하세요.")
    st.json(jsonable(run.parsed))


def _processed_result_tab(entry: CatalogEntry) -> None:
    run = _current_run(entry)
    if run is None:
        st.info("Raw Response 탭에서 API를 실행하면 처리된 row preview를 표시합니다.")
        return
    data = jsonable(run.processed)
    if isinstance(data, list) and data:
        st.dataframe(pd.json_normalize(data, sep="."), width="stretch", hide_index=True)
    elif isinstance(data, list):
        st.info("처리된 결과가 0건입니다.")
    else:
        st.json(data)


def _validation_errors_tab(entry: CatalogEntry) -> None:
    run = _current_run(entry)
    if run is None:
        st.info("아직 실행된 API가 없습니다.")
        return
    if not run.error:
        st.success("현재 실행 결과에서 validation error 또는 exception이 없습니다.")
        return
    st.error(run.error["message"])
    st.json(run.error)


def _debug_trace_tab(entries: list[CatalogEntry], entry: CatalogEntry) -> None:
    run = _current_run(entry)

    st.subheader("Catalog")
    st.dataframe(
        pd.json_normalize([item.model_dump(mode="json") for item in entries], sep="."),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Selected API")
    st.json(entry.model_dump(mode="json"))
    st.caption(f"credential env: {DEFAULT_ENV_NAME}")

    if run is None:
        st.info("아직 실행된 API가 없습니다.")
        return

    st.subheader("Trace")
    st.write(run.trace)

    st.subheader("Request (민감정보 마스킹됨)")
    st.json(jsonable(run.request))

    st.subheader("Response (status_code / elapsed_ms)")
    response_data = jsonable(run.response)
    if isinstance(response_data, dict):
        st.json({key: value for key, value in response_data.items() if key != "body"})
    else:
        st.json(response_data)

    if run.catalog is not None:
        st.subheader("Catalog Entry (run 시점 스냅샷)")
        st.dataframe(pd.json_normalize([run.catalog], sep="."), width="stretch", hide_index=True)


def _fixture_tab(fixture_base_dir: str, entry: CatalogEntry) -> None:
    run = _current_run(entry)
    if run is None:
        st.info("Raw Response 탭에서 API를 실행한 뒤 fixture를 저장할 수 있습니다.")
        st.caption("Fixture base dir")
        st.code(fixture_base_dir, language=None)
        return

    with st.expander("Save as fixture", expanded=True):
        case_name = st.text_input("Case name", value=f"{entry.key}_case")
        description = st.text_area("Description", value=f"{entry.display_name} 실행 결과")
        assertion_mode = st.selectbox(
            "Assertion mode",
            ["snapshot", "schema_only", "required_fields", "count"],
        )
        exclude_fields_raw = st.text_input(
            "Exclude fields",
            value="fetched_at, request_id, updated_at",
        )
        required_fields_raw = st.text_input("Required fields", value="")
        overwrite = st.checkbox("Overwrite existing fixture", value=False)

        assertion = {
            "mode": assertion_mode,
            "exclude_fields": [
                value.strip() for value in exclude_fields_raw.split(",") if value.strip()
            ],
            "required_fields": [
                value.strip() for value in required_fields_raw.split(",") if value.strip()
            ],
        }

        st.subheader("Fixture preview")
        st.json(
            {
                "function": run.function,
                "input": jsonable(run.input),
                "request": jsonable(run.request),
                "response": jsonable(run.response),
                "parsed": jsonable(run.parsed),
                "processed": jsonable(run.processed),
                "assertion": assertion,
            }
        )

        if st.button("Save as fixture"):
            try:
                path = save_fixture(
                    base_dir=fixture_base_dir,
                    function_name=run.function,
                    case_name=case_name,
                    description=description,
                    input_data=run.input,
                    request_data=run.request,
                    response_data=run.response,
                    parsed_result=run.parsed,
                    processed_result=run.processed,
                    assertion=assertion,
                    overwrite=overwrite,
                )
            except Exception as exc:  # pragma: no cover - UI 표시
                st.error(str(exc))
            else:
                st.success(f"Saved: {path}")


def _fixture_base_dir_sidebar() -> str:
    st.sidebar.subheader("Fixtures")
    candidates = _fixture_dir_candidates()
    options = [str(path) for path in candidates]
    custom_label = "Custom..."
    selected = st.sidebar.selectbox("Fixture base dir", [*options, custom_label])
    if selected == custom_label:
        selected = st.sidebar.text_input(
            "Custom fixture base dir",
            value=str((ROOT / "tests" / "fixtures").resolve()),
        )
    st.sidebar.caption(selected)
    return selected


def _fixture_dir_candidates() -> list[Path]:
    preferred = [
        ROOT / "tests" / "fixtures",
        ROOT / "tests",
        ROOT / "examples",
        ROOT,
    ]
    candidates: list[Path] = []
    for path in preferred:
        resolved = path.resolve()
        if resolved not in candidates:
            candidates.append(resolved)
    return candidates


def _store_run(entry: CatalogEntry, run: DebugRun) -> None:
    st.session_state["last_run"] = {"selection_key": _selection_key(entry), "run": run}


def _current_run(entry: CatalogEntry) -> DebugRun | None:
    stored = st.session_state.get("last_run")
    if not isinstance(stored, dict):
        return None
    if stored.get("selection_key") != _selection_key(entry):
        return None
    run = stored.get("run")
    return run if isinstance(run, DebugRun) else None


def _selection_key(entry: CatalogEntry) -> str:
    return f"api:{entry.key}"


if __name__ == "__main__":
    main()
