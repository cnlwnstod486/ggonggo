from playwright.sync_api import sync_playwright
from datetime import datetime
import json
import html

BASE_URL = "https://jasoseol.com"
OUTPUT_FILE = "index.html"


def collect_detail(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
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

                    const match = text.match(/^([\\d,]+)\\s*명\\s*작성$/);

                    if (match) {
                        applicants = parseInt(
                            match[1].replace(/,/g, ""),
                            10
                        );
                    }
                }

                for (const text of elements) {
                    if (types.includes(text)) continue;
                    if (/^[\\d,]+\\s*명\\s*작성$/.test(text)) continue;
                    if (text === "자소서 문항 보기") continue;

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
                const key = item.employment_type + "|" + item.job;

                if (!seen.has(key)) {
                    seen.add(key);
                    unique.push(item);
                }
            }

            return unique;
        }
        """)

    except Exception as e:
        print(f"      상세 페이지 오류: {e}")
        return []


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
            const time = cell.querySelector("time[datetime]");

            if (!time) return;

            const date = time.getAttribute("datetime");

            cell.querySelectorAll(
                '[data-testid="employment-item"]'
            ).forEach(item => {
                const link = item.querySelector(
                    'a[href*="/recruit/"]'
                );

                if (!link) return;

                const href = link.getAttribute("href");

                const companyElement = item.querySelector(
                    ".company-name"
                );

                if (!companyElement) return;

                const company = companyElement.innerText.trim();

                const statusElement = item.querySelector(
                    ".EmploymentHeader_label__uIxZW"
                );

                let status = "";

                if (statusElement) {
                    const aria = statusElement.getAttribute("aria-label");
                    const text = statusElement.innerText.trim();

                    if (aria === "시작" || text === "시작") {
                        status = "시작";
                    } else if (aria === "마감" || text === "마감") {
                        status = "마감";
                    } else if (
                        aria === "수시" ||
                        text === "수시" ||
                        text === "수"
                    ) {
                        status = "수시";
                    }
                }

                const url = href.startsWith("http")
                    ? href
                    : location.origin + href;

                if (!result[date]) {
                    result[date] = [];
                }

                if (!result[date].some(x => x.url === url)) {
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
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>자소설닷컴 채용 달력</title>

<style>
* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background: #f5f7fb;
    color: #202124;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        "Noto Sans KR",
        sans-serif;
}}

.container {{
    max-width: 1400px;
    margin: auto;
    padding: 25px 20px 60px;
}}

.header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    gap: 15px;
}}

.title {{
    font-size: 28px;
    font-weight: 800;
}}

.updated {{
    color: #777;
    font-size: 13px;
}}

.month-nav {{
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 20px;
    margin-bottom: 18px;
}}

.month-title {{
    min-width: 180px;
    text-align: center;
    font-size: 24px;
    font-weight: 800;
}}

.nav-btn {{
    border: 0;
    background: #4285f4;
    color: white;
    border-radius: 8px;
    padding: 9px 15px;
    font-size: 16px;
    font-weight: 700;
    cursor: pointer;
}}

.nav-btn:hover {{
    background: #3367d6;
}}

.today-btn {{
    border: 1px solid #4285f4;
    background: white;
    color: #4285f4;
    border-radius: 8px;
    padding: 8px 13px;
    font-weight: 700;
    cursor: pointer;
}}

.calendar {{
    background: white;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}}

.weekdays {{
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    background: #fafafa;
    border-bottom: 1px solid #eee;
}}

.weekday {{
    padding: 13px;
    text-align: center;
    font-weight: 700;
}}

.sunday {{
    color: #e53935;
}}

.saturday {{
    color: #1976d2;
}}

.days {{
    display: grid;
    grid-template-columns: repeat(7, 1fr);
}}

.day {{
    min-height: 135px;
    padding: 9px;
    border-right: 1px solid #eee;
    border-bottom: 1px solid #eee;
    cursor: pointer;
    transition: background .15s;
}}

.day:hover {{
    background: #f5f8ff;
}}

.day.selected {{
    background: #eaf2ff;
    box-shadow: inset 0 0 0 2px #4285f4;
}}

.day.today {{
    background: #fff8e1;
}}

.day-number {{
    font-size: 14px;
    font-weight: 800;
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
    font-weight: 700;
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

.detail {{
    margin-top: 25px;
    background: white;
    border-radius: 16px;
    padding: 25px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}}

.detail-title {{
    font-size: 21px;
    font-weight: 800;
    margin-bottom: 18px;
}}

.recruit {{
    border: 1px solid #e5e7eb;
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
    font-weight: 800;
}}

.status {{
    padding: 4px 8px;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 700;
}}

.jobs {{
    margin-top: 12px;
}}

.job {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 0;
    border-bottom: 1px solid #f1f1f1;
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
    color: #1967d2;
    text-decoration: none;
    font-size: 13px;
    font-weight: 700;
}}

.link:hover {{
    text-decoration: underline;
}}

.no-data {{
    color: #999;
    padding: 15px 0;
}}

@media (max-width: 700px) {{
    .container {{
        padding: 15px 8px 40px;
    }}

    .header {{
        display: block;
    }}

    .updated {{
        margin-top: 7px;
    }}

    .title {{
        font-size: 21px;
    }}

    .month-title {{
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

<div class="container">

    <div class="header">
        <div class="title">📅 자소설닷컴 채용 달력</div>
        <div class="updated">
            마지막 업데이트: {updated_at}
        </div>
    </div>

    <div class="month-nav">
        <button class="nav-btn" onclick="changeMonth(-1)">‹ 이전</button>

        <div class="month-title" id="monthTitle"></div>

        <button class="nav-btn" onclick="changeMonth(1)">다음 ›</button>

        <button class="today-btn" onclick="goToday()">오늘</button>
    </div>

    <div class="calendar">

        <div class="weekdays">
            <div class="weekday sunday">일</div>
            <div class="weekday">월</div>
            <div class="weekday">화</div>
            <div class="weekday">수</div>
            <div class="weekday">목</div>
            <div class="weekday">금</div>
            <div class="weekday saturday">토</div>
        </div>

        <div class="days" id="calendar"></div>

    </div>

    <div class="detail">

        <div class="detail-title" id="detailTitle">
            오늘 날짜를 선택했습니다
        </div>

        <div id="details">
            <div class="no-data">
                날짜를 선택하면 해당 날짜의 채용공고가 표시됩니다.
            </div>
        </div>

    </div>

</div>

<script>
const recruitmentData = {calendar_json};

const calendarElement = document.getElementById("calendar");
const detailsElement = document.getElementById("details");
const detailTitle = document.getElementById("detailTitle");
const monthTitle = document.getElementById("monthTitle");

const today = new Date();

let currentYear = today.getFullYear();
let currentMonth = today.getMonth() + 1;

let selectedDate = formatDate(
    today.getFullYear(),
    today.getMonth() + 1,
    today.getDate()
);


function formatDate(year, month, day) {{
    return (
        year +
        "-" +
        String(month).padStart(2, "0") +
        "-" +
        String(day).padStart(2, "0")
    );
}}


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


function goToday() {{
    currentYear = today.getFullYear();
    currentMonth = today.getMonth() + 1;
    selectedDate = formatDate(
        today.getFullYear(),
        today.getMonth() + 1,
        today.getDate()
    );

    renderCalendar();
    showDetails(selectedDate);
}}


function renderCalendar() {{
    calendarElement.innerHTML = "";

    monthTitle.innerText =
        currentYear + "년 " + currentMonth + "월";

    const firstDay =
        new Date(currentYear, currentMonth - 1, 1).getDay();

    const lastDay =
        new Date(currentYear, currentMonth, 0).getDate();

    for (let i = 0; i < firstDay; i++) {{
        const empty = document.createElement("div");
        empty.className = "day";
        empty.style.cursor = "default";
        calendarElement.appendChild(empty);
    }}

    for (let day = 1; day <= lastDay; day++) {{

        const date = formatDate(
            currentYear,
            currentMonth,
            day
        );

        const cell = document.createElement("div");
        cell.className = "day";

        const dateObject =
            new Date(currentYear, currentMonth - 1, day);

        const week = dateObject.getDay();

        if (week === 0) {{
            cell.classList.add("sunday");
        }}

        if (week === 6) {{
            cell.classList.add("saturday");
        }}

        if (date === selectedDate) {{
            cell.classList.add("selected");
        }}

        if (date === formatDate(
            today.getFullYear(),
            today.getMonth() + 1,
            today.getDate()
        )) {{
            cell.classList.add("today");
        }}

        const items = recruitmentData[date] || [];

        const startCount =
            items.filter(x => x.status === "시작").length;

        const endCount =
            items.filter(x => x.status === "마감").length;

        const ongoingCount =
            items.filter(x => x.status === "수시").length;

        let content =
            '<div class="day-number">' + day + "</div>";

        content += '<div class="badges">';

        if (startCount) {{
            content +=
                '<span class="badge start">🟢 시작 ' +
                startCount +
                "</span>";
        }}

        if (endCount) {{
            content +=
                '<span class="badge end">🔴 마감 ' +
                endCount +
                "</span>";
        }}

        if (ongoingCount) {{
            content +=
                '<span class="badge ongoing">🟡 수시 ' +
                ongoingCount +
                "</span>";
        }}

        content += "</div>";

        cell.innerHTML = content;

        cell.addEventListener("click", function() {{
            selectedDate = date;
            showDetails(date);
            renderCalendar();
        }});

        calendarElement.appendChild(cell);
    }}
}}


function showDetails(date) {{
    detailTitle.innerText =
        date + " 채용공고";

    const items =
        recruitmentData[date] || [];

    if (!items.length) {{
        detailsElement.innerHTML =
            '<div class="no-data">해당 날짜의 채용공고가 없습니다.</div>';
        return;
    }}

    let output = "";

    items.forEach(item => {{

        let statusClass = "ongoing";

        if (item.status === "시작") {{
            statusClass = "start";
        }} else if (item.status === "마감") {{
            statusClass = "end";
        }}

        let jobsHtml = "";

        if (item.jobs && item.jobs.length) {{

            item.jobs.forEach(job => {{

                const applicant =
                    job.applicants === null ||
                    job.applicants === undefined
                        ? ""
                        : job.applicants + "명 작성";

                jobsHtml +=
                    '<div class="job">' +
                        '<span class="job-type">' +
                            escapeHtml(
                                job.employment_type || "-"
                            ) +
                        "</span>" +
                        "<span>" +
                            escapeHtml(job.job) +
                        "</span>" +
                        '<span class="applicants">' +
                            escapeHtml(applicant) +
                        "</span>" +
                    "</div>";
            }});

        }} else {{
            jobsHtml =
                '<div class="no-data">모집 직무 정보 없음</div>';
        }}

        output +=
            '<div class="recruit">' +

                '<div class="recruit-header">' +

                    '<div class="company">' +
                        escapeHtml(item.company) +
                    "</div>" +

                    '<div class="status ' +
                        statusClass +
                    '">' +
                        escapeHtml(item.status || "확인") +
                    "</div>" +

                "</div>" +

                '<div class="jobs">' +
                    jobsHtml +
                "</div>" +

                '<a class="link" href="' +
                    escapeAttribute(item.url) +
                    '" target="_blank" rel="noopener">' +
                    "공고 보기 →" +
                "</a>" +

            "</div>";
    }});

    detailsElement.innerHTML = output;
}}


function escapeHtml(value) {{
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}}


function escapeAttribute(value) {{
    return escapeHtml(value);
}}


renderCalendar();
showDetails(selectedDate);
</script>

</body>
</html>
"""


def main():
    print("자소설닷컴 채용공고 수집 시작")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={"width": 1440, "height": 1000},
            locale="ko-KR"
        )

        calendar_data = collect_calendar(page)

        total = sum(
            len(items)
            for items in calendar_data.values()
        )

        print(f"달력 공고 {total}개 발견")

        detail_page = browser.new_page(
            viewport={"width": 1440, "height": 1000},
            locale="ko-KR"
        )

        count = 0

        for date in sorted(calendar_data):
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
                    f"    직무 {len(item['jobs'])}개"
                )

        data = {{
            "updated_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "recruit_count": total,
            "calendar": calendar_data
        }}

        print("HTML 생성 중...")

        html_content = make_html(data)

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            f.write(html_content)

        detail_page.close()
        page.close()
        browser.close()

    print()
    print("=" * 50)
    print("수집 완료")
    print(f"공고 수: {total}")
    print(f"결과: {OUTPUT_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    main()
