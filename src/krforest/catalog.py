"""data.go.kr 산림청 검색에서 추린 여행·안전 데이터 카탈로그."""

from __future__ import annotations

from .models import ApiEndpoint, FileDataset

DATA_GO_BASE = "https://www.data.go.kr/data"


API_ENDPOINTS: tuple[ApiEndpoint, ...] = (
    ApiEndpoint(
        key="forest_trail_services",
        title="산림청_숲서비스 및 둘레길 정보",
        data_go_id="15002725",
        categories=("travel",),
        provider="forest.go.kr",
        service="trailInfoService",
        operation="getforestservice",
        url="http://api.forest.go.kr/openapi/service/trailInfoService/getforestservice",
        detail_url=f"{DATA_GO_BASE}/15002725/openapi.do",
        description="둘레길 구간, 거리, 소요시간, GPX/SHP 파일 링크를 제공한다.",
    ),
    ApiEndpoint(
        key="mountain_stories",
        title="산림청_산 정보 조회",
        data_go_id="15058682",
        categories=("travel", "safety"),
        provider="forest.go.kr",
        service="trailInfoService",
        operation="getforeststoryservice",
        url="http://api.forest.go.kr/openapi/service/trailInfoService/getforeststoryservice",
        detail_url=f"{DATA_GO_BASE}/15058682/openapi.do",
        description="국내 산의 높이, 위치, 상세 설명, 등산 관련 정보를 제공한다.",
    ),
    ApiEndpoint(
        key="forest_spatial_trails",
        title="산림청_산림공간정보_등산로정보",
        data_go_id="15002734",
        categories=("travel",),
        provider="forest.go.kr",
        service="trailInfoService",
        operation="getforestspatialdataservice",
        url="http://api.forest.go.kr/openapi/service/trailInfoService/getforestspatialdataservice",
        detail_url=f"{DATA_GO_BASE}/15002734/openapi.do",
        description="등산로 공간정보와 산림지도, 파일 링크를 제공한다.",
    ),
    ApiEndpoint(
        key="baekdu_trails",
        title="산림청_백두대간_등산로정보",
        data_go_id="15002731",
        categories=("travel",),
        provider="forest.go.kr",
        service="trailInfoService",
        operation="gettrailservice",
        url="http://api.forest.go.kr/openapi/service/trailInfoService/gettrailservice",
        detail_url=f"{DATA_GO_BASE}/15002731/openapi.do",
        description="백두대간 등산로 구간, 거리, 경유지, 위치 정보를 제공한다.",
    ),
    ApiEndpoint(
        key="famous_mountain_trails",
        title="산림청_명산등산로",
        data_go_id="3071170",
        categories=("travel",),
        provider="forest.go.kr",
        service="cultureInfoService",
        operation="gdTrailInfoImgOpenAPI",
        url="http://api.forest.go.kr/openapi/service/cultureInfoService/gdTrailInfoImgOpenAPI",
        detail_url=f"{DATA_GO_BASE}/3071170/openapi.do",
        description="명산 등산로 검색 및 상세 정보를 제공한다.",
        notes="검색 조건 없이 호출하면 빈 응답이 올 수 있다.",
    ),
    ApiEndpoint(
        key="mountain_weather",
        title="산림청 국립산림과학원_산악기상정보",
        data_go_id="15084696",
        categories=("travel", "safety"),
        provider="data.go.kr",
        service="1400377/mtweather",
        operation="mountListSearch",
        url="http://apis.data.go.kr/1400377/mtweather/mountListSearch",
        detail_url=f"{DATA_GO_BASE}/15084696/openapi.do",
        description="산악기상 관측 지점과 기상 정보를 조회한다.",
        notes="일부 인증키는 별도 활용신청 전 HTTP 403을 반환할 수 있다.",
    ),
    ApiEndpoint(
        key="national_recreation_forest_reservations",
        title="산림청_국립자연휴양림 예약정보",
        data_go_id="15134227",
        categories=("travel",),
        provider="data.go.kr",
        service="1400000/nationalRecreationForestReservationService",
        operation="nationalRecreationForestReservationList",
        url=(
            "http://apis.data.go.kr/1400000/"
            "nationalRecreationForestReservationService/"
            "nationalRecreationForestReservationList"
        ),
        detail_url=f"{DATA_GO_BASE}/15134227/openapi.do",
        description="기관, 상품명, 숙박일자, 예약 상태 기준 국립자연휴양림 예약 현황을 조회한다.",
        notes=(
            "공식 gateway endpoint는 인증 파라미터명을 소문자 serviceKey로 받으며 "
            "XML을 반환한다."
        ),
        service_key_param="serviceKey",
        response_format="xml",
    ),
    ApiEndpoint(
        key="wildfire_risk_forecast",
        title="산림청 국립산림과학원_산불위험예보정보",
        data_go_id="15084817",
        categories=("safety",),
        provider="data.go.kr",
        service="1400377/forestPoint",
        operation="forestPointListGeongugSearch",
        url="http://apis.data.go.kr/1400377/forestPoint/forestPointListGeongugSearch",
        detail_url=f"{DATA_GO_BASE}/15084817/openapi.do",
        description="전국 단위 산불위험 예보지수와 위험등급 통계를 제공한다.",
        notes="3시간 간격 예보 계열이며 일부 인증키는 별도 활용신청이 필요하다.",
    ),
    ApiEndpoint(
        key="wildfire_stats",
        title="산림청_산불발생통계(대국민포털)",
        data_go_id="3070842",
        categories=("safety",),
        provider="data.go.kr",
        service="1400000/forestStusService",
        operation="getfirestatsservice",
        url="http://apis.data.go.kr/1400000/forestStusService/getfirestatsservice",
        detail_url=f"{DATA_GO_BASE}/3070842/openapi.do",
        description="산불 발생 위치, 일자, 시간, 원인 등 통계 정보를 조회한다.",
        notes="tripmate 키 기준 2026-05-08에 HTTP 403이 확인되어 live test는 승인 상태를 구분한다.",
    ),
    ApiEndpoint(
        key="past_landslides",
        title="산림청_과거산사태 정보",
        data_go_id="15074816",
        categories=("safety",),
        provider="data.go.kr",
        service="1400000/pastLndslInfoService",
        operation="pastLndslInfoList",
        url="http://apis.data.go.kr/1400000/pastLndslInfoService/pastLndslInfoList",
        detail_url=f"{DATA_GO_BASE}/15074816/openapi.do",
        description="산사태 재해연도, 재해명, 행정구역, 피해면적 기준 목록을 조회한다.",
    ),
    ApiEndpoint(
        key="landslide_predictions",
        title="산림청_산사태예측정보",
        data_go_id="15074800",
        categories=("safety",),
        provider="data.go.kr",
        service="1400000/predictionInfoService",
        operation="predictionInfoList",
        url="http://apis.data.go.kr/1400000/predictionInfoService/predictionInfoList",
        detail_url=f"{DATA_GO_BASE}/15074800/openapi.do",
        description="시도·시군구 단위 산사태 예측정보와 예보코드를 조회한다.",
    ),
    ApiEndpoint(
        key="landslide_forecast_issues",
        title="산림청_산사태 예보발령 정보",
        data_go_id="15074798",
        categories=("safety",),
        provider="data.go.kr",
        service="1400000/forecastIssueService",
        operation="forecastIssueList",
        url="http://apis.data.go.kr/1400000/forecastIssueService/forecastIssueList",
        detail_url=f"{DATA_GO_BASE}/15074798/openapi.do",
        description="산사태 예보 발령·해제 이력, 기관, 상태 정보를 조회한다.",
    ),
    ApiEndpoint(
        key="roadside_landslides",
        title="산림청_도로변산사태 정보",
        data_go_id="15074812",
        categories=("safety",),
        provider="data.go.kr",
        service="1400000/roadsideLndslInfoService",
        operation="roadsideLndslInfoList",
        url="http://apis.data.go.kr/1400000/roadsideLndslInfoService/roadsideLndslInfoList",
        detail_url=f"{DATA_GO_BASE}/15074812/openapi.do",
        description="도로 인접 산사태 예방·복구 시설과 취약지역 정보를 조회한다.",
    ),
    ApiEndpoint(
        key="erosion_control_dams",
        title="산림청_사방댐 정보",
        data_go_id="15074803",
        categories=("safety",),
        provider="data.go.kr",
        service="1400000/ecndmInfoService",
        operation="ecndmInfoList",
        url="http://apis.data.go.kr/1400000/ecndmInfoService/ecndmInfoList",
        detail_url=f"{DATA_GO_BASE}/15074803/openapi.do",
        description="사방댐 관리번호, 관리주소, 좌표, 관리기관 정보를 조회한다.",
    ),
)


FILE_DATASETS: tuple[FileDataset, ...] = (
    FileDataset(
        data_go_id="15112801",
        title="산림청 국립자연휴양림관리소_숲나들e 숲길 100대명산 정보",
        categories=("travel",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15112801/fileData.do",
        description="100대 명산의 이름, 소재지, 난이도, 산행포인트, 코스, 교통, 좌표 정보.",
    ),
    FileDataset(
        data_go_id="3034022",
        title="산림청_등산로(산림문화·휴양정보)",
        categories=("travel",),
        formats=("SHP",),
        detail_url=f"{DATA_GO_BASE}/3034022/fileData.do",
        description="전국 등산로 위치, 노선, 거리, 소요시간, 난이도 등 공간정보.",
    ),
    FileDataset(
        data_go_id="3034163",
        title="산림청_숲길(산림문화·휴양정보)",
        categories=("travel",),
        formats=("SHP",),
        detail_url=f"{DATA_GO_BASE}/3034163/fileData.do",
        description="전국 숲길 노선, 위치, 거리, 소요시간, 난이도, 주변 경관 정보.",
    ),
    FileDataset(
        data_go_id="15098177",
        title="한국등산트레킹지원센터_산림청 100대명산",
        categories=("travel",),
        formats=("GPX",),
        detail_url=f"{DATA_GO_BASE}/15098177/fileData.do",
        description="산림청 100대명산 POI, 갈림길, 노면정보, 종주코스 GPX.",
    ),
    FileDataset(
        data_go_id="15041973",
        title="산림청_휴양림수목원 위치도",
        categories=("travel",),
        formats=("SHP",),
        detail_url=f"{DATA_GO_BASE}/15041973/fileData.do",
        description="자연휴양림과 수목원의 위치 공간자료.",
    ),
    FileDataset(
        data_go_id="15064415",
        title="산림청 국립자연휴양림관리소_국립자연휴양림 홍보",
        categories=("travel",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15064415/fileData.do",
        description="국립자연휴양림 기본 정보, 주소, 전화번호, 수용인원, 운영시간.",
    ),
    FileDataset(
        data_go_id="15064419",
        title="산림청 국립자연휴양림관리소_국립자연휴양림 시설관련 정보",
        categories=("travel",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15064419/fileData.do",
        description="휴양림 시설, 좌표, 주소, 요금, 판매 가능 여부.",
    ),
    FileDataset(
        data_go_id="15064416",
        title="산림청 국립자연휴양림관리소_국립자연휴양림 예약 정책",
        categories=("travel",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15064416/fileData.do",
        description="선착순, 추첨, 우선예약 등 예약 정책과 일정.",
    ),
    FileDataset(
        data_go_id="15064418",
        title="산림청 국립자연휴양림관리소_국립자연휴양림 예약 정보",
        categories=("travel",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15064418/fileData.do",
        description="숙박 예약 현황과 상품별 예약 정보.",
    ),
    FileDataset(
        data_go_id="15113956",
        title="산림청 국립자연휴양림관리소_명품숲길정보",
        categories=("travel",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15113956/fileData.do",
        description="명품숲길 명칭, 위치, 면적, 유형, 개요, 이미지.",
    ),
    FileDataset(
        data_go_id="15113562",
        title="산림청 국립자연휴양림관리소_숲나들e 숲길정보",
        categories=("travel",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15113562/fileData.do",
        description="숲나들e 예약 가능 숲길의 난이도, 거리, 소요시간, 교통 정보.",
    ),
    FileDataset(
        data_go_id="15110618",
        title="산림청_국가숲길 이용등급 데이터",
        categories=("travel",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15110618/fileData.do",
        description="국가숲길 노선의 상세 정보와 이용 난이도.",
    ),
    FileDataset(
        data_go_id="15141659",
        title="산림청_국가숲길 노선도 데이터(한라산둘레길)",
        categories=("travel",),
        formats=("SHP",),
        detail_url=f"{DATA_GO_BASE}/15141659/fileData.do",
        description="한라산둘레길 노선도 공간정보.",
    ),
    FileDataset(
        data_go_id="15141660",
        title="산림청_국가숲길 노선도 데이터(속리산둘레길)",
        categories=("travel",),
        formats=("SHP",),
        detail_url=f"{DATA_GO_BASE}/15141660/fileData.do",
        description="속리산둘레길 노선도 공간정보.",
    ),
    FileDataset(
        data_go_id="15074817",
        title="산림청_산사태위험지도",
        categories=("safety",),
        formats=("IMG", "XML"),
        detail_url=f"{DATA_GO_BASE}/15074817/fileData.do",
        description="10m 격자 단위 산사태 위험도 공간정보.",
    ),
    FileDataset(
        data_go_id="15121380",
        title="산림청_산불통계데이터",
        categories=("safety",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15121380/fileData.do",
        description="산불 발생 시점, 장소, 원인, 피해 규모 통계.",
    ),
    FileDataset(
        data_go_id="15125006",
        title="산림청_최근 5년간 전국 산사태 발생 이력",
        categories=("safety",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15125006/fileData.do",
        description="전국 산사태 발생 이력, 피해원인, 피해주소, 피해면적.",
    ),
    FileDataset(
        data_go_id="15072172",
        title="산림청_산사태예보발령",
        categories=("safety",),
        formats=("XLS",),
        detail_url=f"{DATA_GO_BASE}/15072172/fileData.do",
        description="산사태 주의보·경보 발령과 해제 이력.",
    ),
    FileDataset(
        data_go_id="15120930",
        title="산림청_산사태정보 실황정보",
        categories=("safety",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15120930/fileData.do",
        description="전국 산사태 실황정보와 예측 데이터.",
    ),
    FileDataset(
        data_go_id="15092027",
        title="산림청 국립산림과학원_대형산불위험예보목록정보",
        categories=("safety",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15092027/fileData.do",
        description="대형산불 위험예보 목록 정보.",
    ),
    FileDataset(
        data_go_id="15092032",
        title="산림청 국립산림과학원_동해안산불위험예보정보",
        categories=("safety",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15092032/fileData.do",
        description="동해안 지역 산불위험 예보 정보.",
    ),
    FileDataset(
        data_go_id="15125648",
        title="산림청 국립산림과학원_산불위험예보분석이미지",
        categories=("safety",),
        formats=("PNG",),
        detail_url=f"{DATA_GO_BASE}/15125648/fileData.do",
        description="예보 기상, 지형, 임상을 활용한 산불위험 예보 분석 이미지.",
    ),
    FileDataset(
        data_go_id="15125640",
        title="산림청 국립산림과학원_산불위험실황분석이미지",
        categories=("safety",),
        formats=("PNG",),
        detail_url=f"{DATA_GO_BASE}/15125640/fileData.do",
        description="실시간 기상과 지형·임상을 활용한 산불위험 실황 분석 이미지.",
    ),
    FileDataset(
        data_go_id="15121208",
        title="산림청_산불상황관제시스템 산불신고 유형별 위험지수",
        categories=("safety",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15121208/fileData.do",
        description="산불 신고 유형별 위험지수.",
    ),
    FileDataset(
        data_go_id="15144785",
        title="산림청_산불상황관제시스템_산불소화시설",
        categories=("safety",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15144785/fileData.do",
        description="산불 초기 대응을 위한 소화시설 현황.",
    ),
    FileDataset(
        data_go_id="15144788",
        title="산림청_산불상황관제시스템_진화대원대기장소",
        categories=("safety",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15144788/fileData.do",
        description="산불 진화대원 대기장소 현황.",
    ),
    FileDataset(
        data_go_id="15144784",
        title="산림청_산불상황관제시스템_담수용사방댐",
        categories=("safety",),
        formats=("CSV",),
        detail_url=f"{DATA_GO_BASE}/15144784/fileData.do",
        description="산불 진화 담수 용도로 활용 가능한 사방댐 정보.",
    ),
)


def api_endpoints(category: str | None = None) -> tuple[ApiEndpoint, ...]:
    """정리된 API endpoint 목록을 반환하고, 필요하면 category로 필터링한다."""

    _validate_category(category)
    if category is None:
        return API_ENDPOINTS
    return tuple(endpoint for endpoint in API_ENDPOINTS if category in endpoint.categories)


def file_datasets(category: str | None = None) -> tuple[FileDataset, ...]:
    """정리된 파일데이터 목록을 반환하고, 필요하면 category로 필터링한다."""

    _validate_category(category)
    if category is None:
        return FILE_DATASETS
    return tuple(dataset for dataset in FILE_DATASETS if category in dataset.categories)


def api_endpoint(key: str) -> ApiEndpoint:
    """key로 API endpoint 하나를 반환한다."""

    for endpoint in API_ENDPOINTS:
        if endpoint.key == key:
            return endpoint
    raise KeyError(key)


def file_dataset(data_go_id: str) -> FileDataset:
    """data.go.kr dataset id로 파일데이터 하나를 반환한다."""

    for dataset in FILE_DATASETS:
        if dataset.data_go_id == data_go_id:
            return dataset
    raise KeyError(data_go_id)


def _validate_category(category: str | None) -> None:
    if category is not None and category not in {"travel", "safety"}:
        raise ValueError("category must be 'travel', 'safety', or None")
