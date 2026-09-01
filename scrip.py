from playwright.sync_api import sync_playwright
from datetime import datetime
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

                section.querySelectorAll("li").forEach(item => {
                    const elements = item.querySelectorAll("span, div");

                    let employmentType = "";
                    let job = "";
                    let applicants = null;

                    for (const el of elements) {
                        const text = el.innerText.trim();

                        if (
                            text === "신입" ||
                            text === "경력" ||
                            text === "인턴" ||
                            text === "신입/경력" ||
                            text === "경력무관" ||
                            text === "계약직" ||
                            text === "정규직"
                        ) {
                            employmentType = text;
                        }

                        const applicantMatch =
                            text.match(/^([\\d,]+)\\s*명\\s*작성$/);

                        if (applicantMatch) {
                            applicants = parseInt(
                                applicantMatch[1].replace(/,/g, ""),
                                10
                            );
                        }
                    }

                    const textElements = [...elements]
                        .map(el => el.innerText.trim())
                        .filter(Boolean);

                    for (const text of textElements) {
                        if (
                            text === "신입" ||
                            text === "경력" ||
                            text === "인턴" ||
                            text === "신입/경력" ||
                            text === "경력무관" ||
                            text === "계약직" ||
                            text === "정규직"
                        ) {
                            continue;
                        }

                        if (/^[\\d,]+\\s*명\\s*작성$/.test(text)) {
                            continue;
                        }

                        if (text === "자소서 문항 보기") {
                            continue;
                        }

                        if (
                            text.length >= 2 &&
                            text.length <= 100 &&
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

                for (const item of result) {
                    const key =
                        item.employment_type + "|" + item.job;

                    if (!unique.some(x =>
                        x.employment_type + "|" + x.job === key
                    )) {
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

                    const company =
                        companyElement.innerText.trim();

                    const statusElement = item.querySelector(
                        ".EmploymentHeader_label__uIxZW"
                    );

                    let status = "";

                    if (statusElement) {
                        const aria =
                            statusElement.getAttribute("aria-label");

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
                            : `${location.origin}${href}`;

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
    calendar = data["calendar"]
    updated_at = data["updated_at"]

    calendar_json = str(calendar)
    calendar_json = calendar_json.replace("'", '"')

    dates = sorted(calendar.keys())

    if dates:
        first_date = datetime.strptime(
            dates[0],
            "%Y-%m-%d"
        )
    else:
        first_date = datetime.now()

    year = first_date.year
    month = first_date.month

    html_content = f"""<!DOCTYPE html>
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
    margin: 0 auto;
    padding: 30px 20px 60px;
}}

.header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
}}

.title {{
    font-size: 28px;
    font-weight: 800;
}}

.updated {{
    color: #777;
    font-size: 13px;
}}

.calendar {{
    background: white;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    overflow: hidden;
}}

.weekdays {{
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    background: #fafafa;
    border-bottom: 1px solid #eee;
}}

.weekday {{
    padding: 14px 10px;
    text-align: center;
    font-weight: 700;
    color: #555;
}}

.days {{
    display: grid;
    grid-template-columns: repeat(7, 1fr);
}}

.day {{
    min-height: 125px;
    padding: 10px;
    border-right: 1px solid #eee;
    border-bottom: 1px solid #eee;
    cursor: pointer;
    transition: background 0.15s;
}}

.day:hover {{
    background: #f5f8ff;
}}

.day.selected {{
    background: #eaf2ff;
    box-shadow: inset 0 0 0 2px #4285f4;
}}

.day-number {{
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 8px;
}}

.sunday {{
    color: #e53935;
}}

.saturday {{
    color: #1976d2;
}}

.counts {{
    display: flex;
    flex-direction: column;
    gap: 4px;
}}

.badge {{
    display: inline-block;
    width: fit-content;
    padding: 3px 7px;
    border-radius: 5px;
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

.empty {{
    color: #aaa;
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
    margin-bottom: 20px;
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
    gap: 8px;
    padding: 6px 0;
    border-bottom: 1px solid #f1f1f1;
    font-size: 14px;
}}

.job:last-child {{
    border-bottom: 0;
}}

.job-type {{
    color: #666;
    min-width: 65px;
}}

.applicants {{
    color: #777;
    margin-left: auto;
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
    padding: 20px 0;
}}

@media (max-width: 700px) {{
    .container {{
        padding: 15px 10px 40px;
    }}

    .header {{
        display: block;
    }}

    .updated {{
        margin-top: 8px;
    }}

    .title {{
        font-size: 22px;
    }}

    .day {{
        min-height: 70px;
        padding: 6px;
    }}

    .badge {{
        font-size: 9px;
        padding: 2px 4px;
    }}

    .detail {{
        padding: 16px;
    }}

    .recruit-header {{
        align-items: flex-start;
    }}
}}
</style>
</head>

<body>

<div class="container">

    <div class="header">
        <div class="title">
            📅 {year}년 {month}월 채용 달력
        </div>

        <div class="updated">
            마지막 업데이트: {html.escape(updated_at)}
        </div>
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
            날짜를 선택해주세요
        </div>

        <div id="details">
            <div class="no-data">
                달력에서 날짜를 클릭하면 해당 날짜의 채용공고가 표시됩니다.
            </div>
        </div>

    </div>

</div>

<script>
const recruitmentData = {calendar_json};

const calendarElement =
    document.getElementById("calendar");

const detailsElement =
    document.getElementById("details");

const detailTitle =
    document.getElementById("detailTitle");

const year = {year};
const month = {month};

const firstDay =
    new Date(year, month - 1, 1).getDay();

const lastDay =
    new Date(year, month, 0).getDate();

for (let i = 0; i < firstDay; i++) {{
    const empty = document.createElement("div");
    empty.className = "day empty";
    calendarElement.appendChild(empty);
}}

for (let day = 1; day <= lastDay; day++) {{

    const date =
        `${{year}}-${{String(month).padStart(2, "0")}}-${{String(day).padStart(2, "0")}}`;

    const cell =
        document.createElement("div");

    cell.className = "day";

    const dateObject =
        new Date(year, month - 1, day);

    const week =
        dateObject.getDay();

    if (week === 0) {{
        cell.classList.add("sunday");
    }}

    if (week === 6) {{
        cell.classList.add("saturday");
    }}

    let htmlText =
        `<div class="day-number">${{day}}</div>`;

    const items =
        recruitmentData[date] || [];

    const startCount =
        items.filter(x => x.status === "시작").length;

    const endCount =
        items.filter(x => x.status === "마감").length;

    const ongoingCount =
        items.filter(x => x.status === "수시").length;

    htmlText += `<div class="counts">`;

    if (startCount > 0) {{
        htmlText +=
            `<span class="badge start">🟢 시작 ${{startCount}}</span>`;
    }}

    if (endCount > 0) {{
        htmlText +=
            `<span class="badge end">🔴 마감 ${{endCount}}</span>`;
    }}

    if (ongoingCount > 0) {{
        htmlText +=
            `<span class="badge ongoing">🟡 수시 ${{ongoingCount}}</span>`;
    }}

    htmlText += `</div>`;

    cell.innerHTML = htmlText;

    cell.addEventListener("click", () => {{
        showDetails(date);
    }});

    calendarElement.appendChild(cell);
}}

function showDetails(date) {{

    document
        .querySelectorAll(".day")
        .forEach(x => x.classList.remove("selected"));

    const dateObjects =
        document.querySelectorAll(".day");

    const targetDay =
        parseInt(date.substring(8, 10), 10);

    for (const cell of dateObjects) {{
        const number =
            cell.querySelector(".day-number");

        if (
            number &&
            parseInt(number.innerText, 10) === targetDay
        ) {{
            cell.classList.add("selected");
            break;
        }}
    }}

    detailTitle.innerText =
        `${{date}} 채용공고`;

    const items =
        recruitmentData[date] || [];

    if (items.length === 0) {{
        detailsElement.innerHTML =
            `<div class="no-data">해당 날짜의 채용공고가 없습니다.</div>`;
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

        if (item.jobs && item.jobs.length > 0) {{

            item.jobs.forEach(job => {{

                const applicant =
                    job.applicants === null ||
                    job.applicants === undefined
                        ? "작성자 수 확인 안 됨"
                        : `${{job.applicants}}명 작성`;

                jobsHtml += `
                    <div class="job">
                        <span class="job-type">
                            ${{job.employment_type || "-"}}
                        </span>

                        <span>
                            ${{escapeHtml(job.job)}}
                        </span>

                        <span class="applicants">
                            ${{applicant}}
                        </span>
                    </div>
                `;
            }});

        }} else {{

            jobsHtml =
                `<div class="no-data">모집 직무 정보 없음</div>`;
        }}

        output += `
            <div class="recruit">

                <div class="recruit-header">

                    <div class="company">
                        ${{escapeHtml(item.company)}}
                    </div>

                    <div class="status ${{statusClass}}">
                        ${{item.status || "확인"}}
                    </div>

                </div>

                <div class="jobs">
                    ${{jobsHtml}}
                </div>

                <a
                    class="link"
                    href="${{item.url}}"
                    target="_blank"
                    rel="noopener"
                >
                    공고 보기 →
                </a>

            </div>
        `;
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
</script>

</body>
</html>
"""

    return html_content


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

        for date, items in calendar_data.items():

            for item in items:

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

        data = {
            "updated_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "recruit_count": total,
            "calendar": calendar_data
        }

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
