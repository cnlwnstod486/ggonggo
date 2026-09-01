from playwright.sync_api import sync_playwright
from datetime import datetime, timezone, timedelta
import json
import html

BASE_URL = "https://jasoseol.com"
OUTPUT_FILE = "index.html"


# ================================================================
# 상세 채용공고 수집
# ================================================================

def collect_detail(page, url):
    try:
        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        page.wait_for_timeout(500)

        return page.evaluate("""
        () => {
            const section = [...document.querySelectorAll("section")]
                .find(s => {
                    const h2 = s.querySelector("h2");
                    return h2 && h2.innerText.trim() === "모집 직무";
                });

            if (!section) return [];

            const result = [];

            const types = [
                "신입",
                "경력",
                "인턴",
                "신입/경력",
                "경력무관",
                "계약직",
                "정규직"
            ];

            section.querySelectorAll("li").forEach(item => {

                const elements = [...item.querySelectorAll("span, div")]
                    .map(el => el.innerText.trim())
                    .filter(Boolean);

                let employmentType = "";
                let applicants = null;
                let job = "";

                for (const text of elements) {

                    if (types.includes(text)) {
                        employmentType = text;
                    }

                    const match =
                        text.match(/^([\\d,]+)\\s*명\\s*작성$/);

                    if (match) {
                        applicants = parseInt(
                            match[1].replace(/,/g, ""),
                            10
                        );
                    }
                }

                for (const text of elements) {

                    if (types.includes(text)) continue;

                    if (
                        /^[\\d,]+\\s*명\\s*작성$/.test(text)
                    ) {
                        continue;
                    }

                    if (text === "자소서 문항 보기") {
                        continue;
                    }

                    if (
                        text.length >= 2 &&
                        text.length <= 150 &&
                        !text.includes("\\n")
                    ) {
                        job = text;
                        break;
                    }
                }

                if (job) {

                    result.push({
                        employment_type: employmentType,
                        job: job,
                        applicants: applicants
                    });

                }
            });

            const unique = [];
            const seen = new Set();

            for (const item of result) {

                const key =
                    item.employment_type +
                    "|" +
                    item.job;

                if (!seen.has(key)) {

                    seen.add(key);
                    unique.push(item);

                }
            }

            return unique;
        }
        """)

    except Exception as e:

        print(
            f"      상세 페이지 오류: {e}"
        )

        return []


# ================================================================
# 채용 달력 수집
# ================================================================

def collect_calendar(page):

    page.goto(
        f"{BASE_URL}/recruit",
        wait_until="networkidle",
        timeout=30000
    )

    page.wait_for_selector(
        '[data-testid="employment-item"]',
        state="attached",
        timeout=15000
    )

    return page.evaluate("""
    () => {

        const result = {};

        const cells = document.querySelectorAll(
            '[data-testid="week-row"] > div[class*="CalendarCell_cell"]'
        );

        cells.forEach(cell => {

            const time =
                cell.querySelector("time[datetime]");

            if (!time) return;

            const date =
                time.getAttribute("datetime");

            cell.querySelectorAll(
                '[data-testid="employment-item"]'
            ).forEach(item => {

                const link =
                    item.querySelector(
                        'a[href*="/recruit/"]'
                    );

                if (!link) return;

                const href =
                    link.getAttribute("href");

                const companyElement =
                    item.querySelector(
                        ".company-name"
                    );

                if (!companyElement) return;

                const company =
                    companyElement.innerText.trim();

                const statusElement =
                    item.querySelector(
                        ".EmploymentHeader_label__uIxZW"
                    );

                let status = "";

                if (statusElement) {

                    const aria =
                        statusElement.getAttribute(
                            "aria-label"
                        );

                    const text =
                        statusElement.innerText.trim();

                    if (
                        aria === "시작" ||
                        text === "시작"
                    ) {
                        status = "시작";

                    } else if (
                        aria === "마감" ||
                        text === "마감"
                    ) {
                        status = "마감";

                    } else if (
                        aria === "수시" ||
                        text === "수시" ||
                        text === "수"
                    ) {
                        status = "수시";
                    }
                }

                const url =
                    href.startsWith("http")
                        ? href
                        : location.origin + href;

                if (!result[date]) {
                    result[date] = [];
                }

                if (
                    !result[date].some(
                        x => x.url === url
                    )
                ) {

                    result[date].push({

                        status: status,

                        company: company,

                        url: url,

                        jobs: []

                    });

                }

            });

        });

        return result;
    }
    """)


# ================================================================
# HTML 생성
# ================================================================

def make_html(data):

    calendar_json = json.dumps(
        data["calendar"],
        ensure_ascii=False
    )

    updated_at = html.escape(data["updated_at"])

    return f"""<!DOCTYPE html>
<html lang="ko">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>채용달력 | 꽁고</title>

<style>

/* =========================================================
   기본
========================================================= */

* {{
    box-sizing: border-box;
}}

html {{
    scroll-behavior: smooth;
}}

body {{
    margin: 0;

    background: #f5f7fb;

    color: #172033;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        "Noto Sans KR",
        Arial,
        sans-serif;
}}

a {{
    color: inherit;
    text-decoration: none;
}}

button {{
    font-family: inherit;
}}


/* =========================================================
   상단바
========================================================= */

.topbar {{

    position: sticky;

    top: 0;

    z-index: 100;

    background:
        rgba(255, 255, 255, 0.96);

    backdrop-filter: blur(12px);

    border-bottom:
        1px solid #e7ebf2;
}}

.topbar-inner {{

    width:
        min(1180px, calc(100% - 32px));

    height: 72px;

    margin: 0 auto;

    display: flex;

    align-items: center;

    justify-content: space-between;

    gap: 20px;
}}

.logo {{

    font-size: 21px;

    font-weight: 900;

    letter-spacing: -0.8px;

    white-space: nowrap;

    color: #172033;
}}

.logo span {{
    color: #4f46e5;
}}

.main-nav {{

    display: flex;

    align-items: center;

    gap: 6px;
}}

.nav-link {{

    display: inline-flex;

    align-items: center;

    padding: 10px 16px;

    border-radius: 10px;

    font-size: 14px;

    font-weight: 700;

    color: #687386;

    transition: 0.2s;
}}

.nav-link:hover {{

    background: #f1f3f8;

    color: #20283a;
}}

.nav-link.active {{

    background: #eef0ff;

    color: #4f46e5;
}}


/* =========================================================
   컨테이너
========================================================= */

.container {{

    width:
        min(1180px, calc(100% - 32px));

    margin: 0 auto;

    padding: 42px 0 70px;
}}


/* =========================================================
   페이지 제목
========================================================= */

.header {{

    display: flex;

    align-items: center;

    justify-content: space-between;

    gap: 20px;

    margin-bottom: 24px;
}}

.title {{

    margin: 0;

    font-size: 30px;

    font-weight: 900;

    letter-spacing: -1.2px;
}}

.updated {{

    color: #8b94a5;

    font-size: 12px;

    white-space: nowrap;
}}


/* =========================================================
   월 이동
========================================================= */

.month-nav {{

    display: flex;

    justify-content: center;

    align-items: center;

    gap: 12px;

    margin-bottom: 18px;

    flex-wrap: wrap;
}}

.month-title {{

    min-width: 180px;

    text-align: center;

    font-size: 24px;

    font-weight: 900;
}}

.nav-btn {{

    border: 0;

    background: #4f46e5;

    color: white;

    border-radius: 9px;

    padding: 9px 15px;

    font-size: 14px;

    font-weight: 800;

    cursor: pointer;

    transition: 0.2s;
}}

.nav-btn:hover {{
    background: #4338ca;
}}

.today-btn {{

    border: 1px solid #4f46e5;

    background: white;

    color: #4f46e5;

    border-radius: 9px;

    padding: 8px 13px;

    font-weight: 800;

    cursor: pointer;
}}


/* =========================================================
   달력
========================================================= */

.calendar {{

    background: white;

    border:
        1px solid #e8ecf3;

    border-radius: 16px;

    overflow: hidden;

    box-shadow:
        0 4px 18px rgba(31, 41, 55, 0.035);
}}

.weekdays {{

    display: grid;

    grid-template-columns:
        repeat(7, 1fr);

    background: #fafbfc;

    border-bottom:
        1px solid #eee;
}}

.weekday {{

    padding: 13px;

    text-align: center;

    font-weight: 800;

    color: #687386;
}}

.sunday {{
    color: #e53935;
}}

.saturday {{
    color: #1976d2;
}}

.days {{

    display: grid;

    grid-template-columns:
        repeat(7, 1fr);
}}

.day {{

    min-height: 135px;

    padding: 9px;

    border-right:
        1px solid #eee;

    border-bottom:
        1px solid #eee;

    cursor: pointer;

    transition:
        background 0.15s;
}}

.day:hover {{
    background: #f5f8ff;
}}

.day.selected {{

    background: #eaf2ff;

    box-shadow:
        inset 0 0 0 2px #4f46e5;
}}

.day.today {{
    background: #fff8e1;
}}

.day-number {{

    font-size: 14px;

    font-weight: 900;

    margin-bottom: 8px;
}}

.badges {{

    display: flex;

    flex-direction: column;

    gap: 4px;
}}

.badge {{

    width: fit-content;

    border-radius: 5px;

    padding: 3px 7px;

    font-size: 11px;

    font-weight: 800;
}}

.start {{

    background: #e8f5e9;

    color: #2e7d32;
}}

.end {{

    background: #ffebee;

    color: #c62828;
}}

.ongoing {{

    background: #fff8e1;

    color: #f57f17;
}}


/* =========================================================
   상세
========================================================= */

.detail {{

    margin-top: 25px;

    background: white;

    border:
        1px solid #e8ecf3;

    border-radius: 16px;

    padding: 25px;

    box-shadow:
        0 4px 18px rgba(31, 41, 55, 0.035);
}}

.detail-title {{

    font-size: 21px;

    font-weight: 900;

    margin-bottom: 18px;
}}

.recruit {{

    border:
        1px solid #e5e7eb;

    border-radius: 12px;

    padding: 16px;

    margin-bottom: 12px;
}}

.recruit-header {{

    display: flex;

    justify-content: space-between;

    align-items: center;

    gap: 10px;
}}

.company {{

    font-size: 17px;

    font-weight: 900;
}}

.status {{

    padding: 4px 8px;

    border-radius: 5px;

    font-size: 11px;

    font-weight: 800;
}}

.jobs {{
    margin-top: 12px;
}}

.job {{

    display: flex;

    align-items: center;

    gap: 10px;

    padding: 7px 0;

    border-bottom:
        1px solid #f1f1f1;

    font-size: 14px;
}}

.job:last-child {{
    border-bottom: 0;
}}

.job-type {{

    min-width: 70px;

    color: #666;

    font-size: 12px;
}}

.applicants {{

    margin-left: auto;

    color: #777;

    white-space: nowrap;

    font-size: 12px;
}}

.link {{

    display: inline-block;

    margin-top: 12px;

    color: #4f46e5;

    font-size: 13px;

    font-weight: 800;
}}

.link:hover {{
    text-decoration: underline;
}}

.no-data {{

    color: #999;

    padding: 15px 0;
}}


/* =========================================================
   모바일
========================================================= */

@media (max-width: 700px) {{

    .topbar-inner {{

        height: auto;

        min-height: 64px;

        padding: 10px 0;

        align-items: flex-start;

        flex-direction: column;

        gap: 8px;
    }}

    .main-nav {{

        width: 100%;

        overflow-x: auto;

        padding-bottom: 2px;
    }}

    .nav-link {{

        white-space: nowrap;

        padding: 8px 12px;
    }}

    .container {{

        width:
            calc(100% - 16px);

        padding:
            28px 0 40px;
    }}

    .header {{

        display: block;
    }}

    .title {{

        font-size: 24px;
    }}

    .updated {{

        display: block;

        margin-top: 7px;
    }}

    .month-title {{

        min-width: 150px;

        font-size: 20px;
    }}

    .day {{

        min-height: 75px;

        padding: 5px;
    }}

    .badge {{

        font-size: 9px;

        padding: 2px 4px;
    }}

    .detail {{

        padding: 15px;
    }}

    .job {{

        flex-wrap: wrap;
    }}

    .applicants {{

        margin-left: 0;
    }}
}}

</style>

</head>


<body>


<!-- =========================================================
     꽁고 상단 메뉴
========================================================= -->

<header class="topbar">

    <div class="topbar-inner">

        <a
            href="index.html"
            class="logo"
        >
            꽁고<span>·</span>
        </a>


        <nav class="main-nav">

            <a
                href="index.html"
                class="nav-link active"
            >
                📅 채용달력
            </a>


            <a
                href="index2.html"
                class="nav-link"
            >
                📋 채용공고
            </a>

        </nav>

    </div>

</header>


<!-- =========================================================
     메인
========================================================= -->

<div class="container">


    <div class="header">

        <div class="title">
            📅 오늘의 채용달력
        </div>

        <div class="updated">
            마지막 업데이트: {updated_at}
        </div>

    </div>


    <!-- 월 이동 -->

    <div class="month-nav">

        <button
            class="nav-btn"
            onclick="changeMonth(-1)"
        >
            ‹ 이전
        </button>


        <div
            class="month-title"
            id="monthTitle"
        ></div>


        <button
            class="nav-btn"
            onclick="changeMonth(1)"
        >
            다음 ›
        </button>


        <button
            class="today-btn"
            onclick="goToday()"
        >
            오늘
        </button>

    </div>


    <!-- 달력 -->

    <div class="calendar">


        <div class="weekdays">

            <div class="weekday sunday">
                일
            </div>

            <div class="weekday">
                월
            </div>

            <div class="weekday">
                화
            </div>

            <div class="weekday">
                수
            </div>

            <div class="weekday">
                목
            </div>

            <div class="weekday">
                금
            </div>

            <div class="weekday saturday">
                토
            </div>

        </div>


        <div
            class="days"
            id="calendar"
        ></div>

    </div>


    <!-- 상세 -->

    <div class="detail">

        <div
            class="detail-title"
            id="detailTitle"
        >
            오늘 날짜를 선택했습니다
        </div>


        <div id="details">

            <div class="no-data">
                날짜를 선택하면 해당 날짜의
                채용공고가 표시됩니다.
            </div>

        </div>

    </div>


</div>


<script>

const recruitmentData =
    {calendar_json};


const calendarElement =
    document.getElementById("calendar");

const detailsElement =
    document.getElementById("details");

const detailTitle =
    document.getElementById("detailTitle");

const monthTitle =
    document.getElementById("monthTitle");


const today =
    new Date();


let currentYear =
    today.getFullYear();


let currentMonth =
    today.getMonth() + 1;


let selectedDate =
    formatDate(
        today.getFullYear(),
        today.getMonth() + 1,
        today.getDate()
    );


// ============================================================
// 날짜 포맷
// ============================================================

function formatDate(year, month, day) {{

    return (
        year +
        "-" +
        String(month).padStart(2, "0") +
        "-" +
        String(day).padStart(2, "0")
    );

}}


// ============================================================
// 월 변경
// ============================================================

function changeMonth(amount) {{

    currentMonth += amount;


    if (currentMonth < 1) {{

        currentMonth = 12;

        currentYear--;

    }}


    if (currentMonth > 12) {{

        currentMonth = 1;

        currentYear++;

    }}


    renderCalendar();

}}


// ============================================================
// 오늘
// ============================================================

function goToday() {{

    currentYear =
        today.getFullYear();

    currentMonth =
        today.getMonth() + 1;


    selectedDate =
        formatDate(
            today.getFullYear(),
            today.getMonth() + 1,
            today.getDate()
        );


    renderCalendar();

    showDetails(selectedDate);

}}


// ============================================================
// 달력 렌더링
// ============================================================

function renderCalendar() {{

    calendarElement.innerHTML = "";


    monthTitle.innerText =
        currentYear +
        "년 " +
        currentMonth +
        "월";


    const firstDay =
        new Date(
            currentYear,
            currentMonth - 1,
            1
        ).getDay();


    const lastDay =
        new Date(
            currentYear,
            currentMonth,
            0
        ).getDate();


    // 빈 칸

    for (
        let i = 0;
        i < firstDay;
        i++
    ) {{

        const empty =
            document.createElement("div");

        empty.className =
            "day";

        empty.style.cursor =
            "default";

        calendarElement.appendChild(
            empty
        );

    }}


    // 날짜

    for (
        let day = 1;
        day <= lastDay;
        day++
    ) {{

        const date =
            formatDate(
                currentYear,
                currentMonth,
                day
            );


        const cell =
            document.createElement("div");

        cell.className =
            "day";


        const dateObject =
            new Date(
                currentYear,
                currentMonth - 1,
                day
            );


        const week =
            dateObject.getDay();


        if (week === 0) {{
            cell.classList.add("sunday");
        }}


        if (week === 6) {{
            cell.classList.add("saturday");
        }}


        if (date === selectedDate) {{
            cell.classList.add("selected");
        }}


        if (
            date ===
            formatDate(
                today.getFullYear(),
                today.getMonth() + 1,
                today.getDate()
            )
        ) {{

            cell.classList.add("today");

        }}


        const items =
            recruitmentData[date] || [];


        const startCount =
            items.filter(
                x => x.status === "시작"
            ).length;


        const endCount =
            items.filter(
                x => x.status === "마감"
            ).length;


        const ongoingCount =
            items.filter(
                x => x.status === "수시"
            ).length;


        let content =
            '<div class="day-number">' +
            day +
            "</div>";


        content +=
            '<div class="badges">';


        if (startCount) {{

            content +=
                '<span class="badge start">' +
                "🟢 시작 " +
                startCount +
                "</span>";

        }}


        if (endCount) {{

            content +=
                '<span class="badge end">' +
                "🔴 마감 " +
                endCount +
                "</span>";

        }}


        if (ongoingCount) {{

            content +=
                '<span class="badge ongoing">' +
                "🟡 수시 " +
                ongoingCount +
                "</span>";

        }}


        content +=
            "</div>";


        cell.innerHTML =
            content;


        cell.addEventListener(
            "click",
            function() {{

                selectedDate =
                    date;

                showDetails(date);

                renderCalendar();

            }}
        );


        calendarElement.appendChild(
            cell
        );

    }}

}}


// ============================================================
// 상세 표시
// ============================================================

function showDetails(date) {{

    detailTitle.innerText =
        date +
        " 채용공고";


    const items =
        recruitmentData[date] || [];


    if (!items.length) {{

        detailsElement.innerHTML =
            '<div class="no-data">' +
            "해당 날짜의 채용공고가 없습니다." +
            "</div>";

        return;

    }}


    let output = "";


    items.forEach(item => {{

        let statusClass =
            "ongoing";


        if (item.status === "시작") {{

            statusClass =
                "start";

        }} else if (
            item.status === "마감"
        ) {{

            statusClass =
                "end";

        }}


        let jobsHtml = "";


        if (
            item.jobs &&
            item.jobs.length
        ) {{

            item.jobs.forEach(job => {{

                const applicant =
                    job.applicants === null ||
                    job.applicants === undefined
                        ? ""
                        : job.applicants +
                          "명 작성";


                jobsHtml +=

                    '<div class="job">' +

                        '<span class="job-type">' +

                            escapeHtml(
                                job.employment_type ||
                                "-"
                            ) +

                        "</span>" +

                        "<span>" +

                            escapeHtml(
                                job.job
                            ) +

                        "</span>" +

                        '<span class="applicants">' +

                            escapeHtml(
                                applicant
                            ) +

                        "</span>" +

                    "</div>";

            }});

        }} else {{

            jobsHtml =
                '<div class="no-data">' +
                "모집 직무 정보 없음" +
                "</div>";

        }}


        output +=

            '<div class="recruit">' +

                '<div class="recruit-header">' +

                    '<div class="company">' +

                        escapeHtml(
                            item.company
                        ) +

                    "</div>" +

                    '<div class="status ' +
                        statusClass +
                    '">' +

                        escapeHtml(
                            item.status ||
                            "확인"
                        ) +

                    "</div>" +

                "</div>" +

                '<div class="jobs">' +

                    jobsHtml +

                "</div>" +

                '<a class="link" href="' +

                    escapeAttribute(
                        item.url
                    ) +

                    '" target="_blank" rel="noopener">' +

                    "공고 보기 →" +

                "</a>" +

            "</div>";

    }});


    detailsElement.innerHTML =
        output;

}}


// ============================================================
// HTML escape
// ============================================================

function escapeHtml(value) {{

    return String(value)

        .replaceAll(
            "&",
            "&amp;"
        )

        .replaceAll(
            "<",
            "&lt;"
        )

        .replaceAll(
            ">",
            "&gt;"
        )

        .replaceAll(
            '"',
            "&quot;"
        )

        .replaceAll(
            "'",
            "&#039;"
        );

}}


function escapeAttribute(value) {{

    return escapeHtml(value);

}}


// ============================================================
// 시작
// ============================================================

renderCalendar();

showDetails(selectedDate);

</script>


</body>

</html>
"""


# ================================================================
# 메인
# ================================================================

def main():

    print(
        "자소설닷컴 채용공고 수집 시작"
    )

    with sync_playwright() as p:

        browser = p.chromium.launch(
                headless=True
            )


        page = browser.new_page(
                viewport={
                    "width": 1440,
                    "height": 1000
                },
                locale="ko-KR"
            )


        # --------------------------------------------------------
        # 달력 수집
        # --------------------------------------------------------

        calendar_data = collect_calendar(page)


        total = sum(
                len(items)
                for items in
                calendar_data.values()
            )


        print(
            f"달력 공고 {total}개 발견"
        )


        # --------------------------------------------------------
        # 상세 페이지
        # --------------------------------------------------------

        detail_page = browser.new_page(
                viewport={
                    "width": 1440,
                    "height": 1000
                },
                locale="ko-KR"
            )


        count = 0


        for date in sorted(
            calendar_data
        ):

            for item in calendar_data[date]:

                count += 1


                print(
                    f"[{count}/{total}] "
                    f"{item['company']} "
                    f"({item['status']})"
                )


                item["jobs"] = collect_detail(
                        detail_page,
                        item["url"]
                    )


                print(
                    f"    직무 "
                    f"{len(item['jobs'])}개"
                )


        # --------------------------------------------------------
        # 한국시간
        # --------------------------------------------------------

        korea_time = datetime.now(
                timezone(
                    timedelta(hours=9)
                )
            )


        data = {

            "updated_at":
                korea_time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "recruit_count":
                total,

            "calendar":
                calendar_data

        }


        print(
            "HTML 생성 중..."
        )


        html_content = make_html(data)


        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                html_content
            )


        detail_page.close()

        page.close()

        browser.close()


    print()

    print("=" * 50)

    print("수집 완료")

    print(
        f"공고 수: {total}"
    )

    print(
        f"한국시간: {data['updated_at']}"
    )

    print(
        f"결과: {OUTPUT_FILE}"
    )

    print("=" * 50)


if __name__ == "__main__":
    main()
