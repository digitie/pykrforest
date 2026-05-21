"""python-krforest-api 디버그 UI."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from krforest import (  # noqa: E402
    ForestClient,
    api_catalog,
    catalog_entries,
    jsonable,
    save_fixture,
)
from krforest.debug import DebugRun  # noqa: E402
from krforest.exceptions import ForestApiError  # noqa: E402

DEFAULT_ENV_NAME = "DATA_GO_KR_SERVICE_KEY"


st.set_page_config(page_title="krforest Debug UI", layout="wide")
st.title("krforest Debug UI")


def service_key_from_env() -> str | None:
    return os.getenv(DEFAULT_ENV_NAME)


def parse_params(value: str) -> dict[str, Any]:
    text = value.strip()
    if not text:
        return {}
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Input parameters must be a JSON object")
    return parsed


def to_dataframe_rows(value: Any) -> list[dict[str, Any]]:
    data = jsonable(value)
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [row if isinstance(row, dict) else {"value": row} for row in data]
    return [{"value": data}]


def show_json_or_table(value: Any) -> None:
    data = jsonable(value)
    if isinstance(data, list) and data and all(isinstance(row, dict) for row in data):
        st.dataframe(pd.json_normalize(data, sep="."), use_container_width=True)
    elif isinstance(data, dict):
        st.json(data)
    else:
        st.write(data)


api_entries = api_catalog()
all_catalog_entries = catalog_entries()

with st.sidebar:
    st.header("Run")
    selected_entry = st.selectbox(
        "Function",
        api_entries,
        format_func=lambda entry: entry.display_name,
    )
    st.caption(f"`{selected_entry.key}` · data.go.kr `{selected_entry.dataset_id}`")
    if selected_entry.service_key_url:
        st.link_button(
            "서비스키 받기 / 활용신청",
            selected_entry.service_key_url,
            use_container_width=True,
        )
        st.caption(selected_entry.service_key_url)
    if selected_entry.service_key_account_url:
        st.link_button(
            "내 인증키 확인",
            selected_entry.service_key_account_url,
            use_container_width=True,
        )
        st.caption(selected_entry.service_key_account_url)

    env_key = service_key_from_env()
    key_help = "환경변수 키를 사용하려면 비워두세요." if env_key else "서비스키를 입력하세요."
    service_key = st.text_input("Service key", type="password", help=key_help)
    timeout = st.number_input("Timeout seconds", min_value=1, max_value=120, value=20)
    page_no = st.number_input("pageNo", min_value=1, value=1)
    num_of_rows = st.number_input("numOfRows", min_value=1, max_value=1000, value=10)

    default_params = "{}"
    if selected_entry.key == "national_recreation_forest_reservations":
        default_params = json.dumps({"goodsNm": "숲속의집"}, ensure_ascii=False, indent=2)
    if selected_entry.key == "standard_recreation_forests":
        default_params = json.dumps({"ctprvnNm": "강원특별자치도"}, ensure_ascii=False, indent=2)
    params_raw = st.text_area("Input parameters (JSON)", value=default_params, height=150)
    run_button = st.button("Run", type="primary", use_container_width=True)

catalog_df = pd.json_normalize([entry.model_dump(mode="json") for entry in all_catalog_entries])

if "debug_run" not in st.session_state:
    st.session_state.debug_run = None

if run_button:
    try:
        params = parse_params(params_raw)
        async def run_debug() -> DebugRun:
            async with ForestClient(api_key=service_key or None, timeout=float(timeout)) as client:
                return await client.debug_endpoint(
                    selected_entry.key,
                    params,
                    page_no=int(page_no),
                    num_of_rows=int(num_of_rows),
                )

        st.session_state.debug_run = asyncio.run(run_debug())
    except (ForestApiError, ValueError, json.JSONDecodeError) as exc:
        st.session_state.debug_run = DebugRun(
            function=selected_entry.key,
            input={"params": params_raw},
            request={},
            response={},
            parsed=None,
            processed=None,
            trace=["failed"],
            catalog=selected_entry.model_dump(mode="json"),
            error={"type": type(exc).__name__, "message": str(exc), "metadata": {}},
        )

run: DebugRun | None = st.session_state.debug_run

tabs = st.tabs(
    [
        "Raw Response",
        "Pydantic Model",
        "Processed Result",
        "Validation Errors",
        "Debug Trace",
        "Fixture / Testcase",
        "Catalog",
    ]
)

with tabs[0]:
    if run is None:
        st.info("Run an API call to see the raw response.")
    else:
        show_json_or_table(run.response)

with tabs[1]:
    if run is None:
        st.info("Run an API call to see parsed Pydantic output.")
    else:
        show_json_or_table(run.parsed)

with tabs[2]:
    if run is None:
        st.info("Run an API call to see processed output.")
    else:
        show_json_or_table(run.processed)

with tabs[3]:
    if run is None:
        st.info("No run yet.")
    elif run.error:
        st.error(run.error["message"])
        st.json(run.error)
    else:
        st.success("No validation or request errors.")

with tabs[4]:
    if run is None:
        st.info("Run an API call to see debug trace.")
    else:
        st.subheader("Trace")
        st.json(run.trace)
        st.subheader("Catalog Entry")
        catalog_data = run.catalog or selected_entry.model_dump(mode="json")
        st.dataframe(pd.json_normalize([catalog_data], sep="."), use_container_width=True)
        st.json(catalog_data)

with tabs[5]:
    if run is None:
        st.info("Run an API call before saving a fixture.")
    else:
        with st.expander("Save as fixture", expanded=True):
            case_name = st.text_input("Case name", value=f"{run.function}_case")
            description = st.text_area("Description", value="")
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
            fixture_dir = st.text_input(
                "Fixture base dir",
                value=str(PROJECT_ROOT / "tests" / "fixtures"),
            )

            assertion = {
                "mode": assertion_mode,
                "exclude_fields": [
                    item.strip() for item in exclude_fields_raw.split(",") if item.strip()
                ],
                "required_fields": [
                    item.strip() for item in required_fields_raw.split(",") if item.strip()
                ],
            }
            st.subheader("Fixture preview")
            st.json(
                {
                    "function": run.function,
                    "input": run.input,
                    "request": run.request,
                    "response": run.response,
                    "parsed": jsonable(run.parsed),
                    "processed": jsonable(run.processed),
                    "assertion": assertion,
                    "catalog": run.catalog,
                }
            )

            if st.button("Save as fixture"):
                saved_path = save_fixture(
                    base_dir=fixture_dir,
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
                st.success(f"Saved: {saved_path}")

with tabs[6]:
    st.dataframe(catalog_df, use_container_width=True)
    st.caption("dataset_name/display_name columns are human-readable dataset titles.")
