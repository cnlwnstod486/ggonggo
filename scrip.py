from playwright.sync_api import sync_playwright
from html import escape
from datetime import datetime
import json

BASE_URL = "https://jasoseol.com"


def collect_detail(page, url):
    try:
        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        page.wait_for_timeout(300)

        return page.evaluate("""
            () => {
                const section = [...document.querySelectorAll("section")]
                    .find(s => {
                        const h2 = s.querySelector("h2");
                        return h2 &&
                            h2.innerText.trim() === "모집 직무";
                    });

                if (!section) {
                    return [];
                }

                const result = [];

                section.querySelectorAll("li").forEach(item => {
                    const lines = item.innerText
                        .split("\\n")
                        .map(x => x.trim())
                        .filter(Boolean);

                    if (!lines.length) {
                        return;
                    }

                    let applicants = null;

                    const applicantMatch =
                        item.innerText.match(
                            /(\\d[\\d,]*)\\s*명\\s*작성/
                        );

                    if (applicantMatch) {
                        applicants = parseInt(
                            applicantMatch[1].replace(/,/g, ""),
                            10
                        );
                    }

                    const types = [
                        "신입/경력",
                        "경력무관",
                        "계약직",
                        "정규직",
                        "인턴",
                        "신입",
                        "경력"
                    ];

                    let employmentType = "";

                    for (const line of lines) {
                        if (types.includes(line)) {
                            employmentType = line;
                            break;
                        }
                    }

                    let job = "";

                    for (const line of lines) {
                        if (types.includes(line)) {
                            continue;
                        }

                        if (
                            /\\d[\\d,]*\\s*명\\s*작성/.test(line)
                        ) {
                            continue;
                        }

                        if (
                            line.includes("자소서 문항")
                        ) {
                            continue;
                        }

                        if (
                            line.length >= 1 &&
                            line.length <= 100
                        ) {
                            job = line;
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

                result.forEach(item => {
                    const key =
                        item.employment_type +
                        "|" +
                        item.job;

                    if (!unique.some(x =>
                        x.employment_type +
                        "|" +
                        x.job === key
                    )) {
                        unique.push(item);
                    }
                });

                return unique;
            }
        """)

    except Exception as e:
        print(f"      상세 페이지 오류: {e}")
        return []


def make_html(calendar_data):

    data_json = json.dumps(
        calendar_data,
        ensure_ascii=False
    )

    today = datetime.now().strftime("%Y-%m-%d")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>자소설닷컴 채용 달력</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background: #f4f6f8;
    color: #222;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        "Noto Sans KR",
        sans-serif;
}}

.container {{
    width: min(1200px, calc(100% - 30px));
    margin: 30px auto 60px;
}}

.header {{
    background: white;
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,.05);
}}

.header h1 {{
    margin: 0;
    font-size: 25px;
}}

.header p {{
    margin: 8px 0 0;
    color: #777;
    font-size: 14px;
}}

.calendar {{
    background: white;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0,0,0,.05);
}}

.calendar-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px;
    border-bottom: 1px solid #eee;
}}

.month-title {{
    font-size: 21px;
    font-weight: 700;
}}

.month-button {{
    border: 0;
    background: #f1f3f5;
    width: 38px;
    height: 38px;
    border-radius: 8px;
    font-size: 20px;
    cursor: pointer;
}}

.month-button:hover {{
    background: #e5e7eb;
}}

.weekdays {{
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    border-bottom: 1px solid #eee;
}}

.weekday {{
    text-align: center;
    padding: 12px 0;
    color: #777;
    font-size: 13px;
    font-weight: 600;
}}

.weekday:first-child {{
    color: #e05252;
}}

.weekday:last-child {{
    color: #4776d0;
}}

.days {{
    display: grid;
    grid-template-columns: repeat(7, 1fr);
}}

.day {{
    min-height: 105px;
    border-right: 1px solid #eee;
    border-bottom: 1px solid #eee;
    padding: 8px;
    cursor: pointer;
    transition: background .15s;
}}

.day:hover {{
    background: #f8fafc;
}}

.day.empty {{
    background: #fafafa;
    cursor: default;
}}

.day.selected {{
    background: #eef5ff;
    box-shadow: inset 0 0 0 2px #3478f6;
}}

.day-number {{
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 8px;
}}

.day.today .day-number {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #3478f6;
    color: white;
    width: 25px;
    height: 25px;
    border-radius: 50%;
}}

.badges {{
    display: flex;
    flex-direction: column;
    gap: 3px;
}}

.badge {{
    font-size: 11px;
    padding: 3px 5px;
    border-radius: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.badge.start {{
    background: #e8f7ed;
    color: #16843a;
}}

.badge.end {{
    background: #fff0f0;
    color: #d93025;
}}

.badge.rolling {{
    background: #edf4ff;
    color: #2768c7;
}}

.more {{
    font-size: 11px;
    color: #888;
    padding-left: 4px;
}}

.detail {{
    margin-top: 20px;
}}

.detail-header {{
    background: white;
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,.05);
}}

.detail-date {{
    font-size: 21px;
    font-weight: 700;
}}

.detail-count {{
    margin-top: 6px;
    color: #777;
    font-size: 14px;
}}

.recruit-card {{
    background: white;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,.04);
}}

.card-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}}

.company {{
    font-size: 17px;
    font-weight: 700;
}}

.status {{
    font-size: 12px;
    font-weight: 700;
    padding: 5px 8px;
    border-radius: 6px;
}}

.status.start {{
    color: #16843a;
    background: #e8f7ed;
}}

.status.end {{
    color: #d93025;
    background: #fff0f0;
}}

.status.rolling {{
    color: #2768c7;
    background: #edf4ff;
}}

.link {{
    display: inline-block;
    margin: 10px 0 12px;
    color: #2867d8;
    text-decoration: none;
    font-size: 13px;
}}

.link:hover {{
    text-decoration: underline;
}}

.jobs {{
    border-top: 1px solid #eee;
}}

.job {{
    display: grid;
    grid-template-columns: 110px 1fr 100px;
    gap: 10px;
    padding: 10px 4px;
    border-bottom: 1px solid #f0f0f0;
    align-items: center;
}}

.job:last-child {{
    border-bottom: none;
}}

.employment {{
    color: #666;
    font-size: 13px;
}}

.job-name {{
    font-size: 14px;
}}

.applicants {{
    text-align: right;
    color: #e65b00;
    font-size: 13px;
    font-weight: 600;
}}

.no-job {{
    padding: 12px 4px;
    color: #999;
    font-size: 13px;
}}

@media (max-width: 700px) {{

    .container {{
        width: calc(100% - 16px);
        margin-top: 10px;
    }}

    .day {{
        min-height: 75px;
        padding: 5px;
    }}

    .badge {{
        font-size: 9px;
    }}

    .job {{
        grid-template-columns: 70px 1fr 65px;
        gap: 5px;
    }}

    .company {{
        font-size: 15px;
    }}

}}

</style>

</head>

<body>

<div class="container">

    <div class="header">
        <h1>📋 자소설닷컴 채용 달력</h1>
        <p>
            날짜를 클릭하면 해당 날짜의 채용공고를 확인할 수 있습니다.
        </p>
    </div>

    <div class="calendar">

        <div class="calendar-header">

            <button
                class="month-button"
                onclick="changeMonth(-1)"
            >
                ‹
            </button>

            <div
                id="monthTitle"
                class="month-title"
            ></div>

            <button
                class="month-button"
                onclick="changeMonth(1)"
            >
                ›
            </button>

        </div>

        <div class="weekdays">

            <div class="weekday">일</div>
            <div class="weekday">월</div>
            <div class="weekday">화</div>
            <div class="weekday">수</div>
            <div class="weekday">목</div>
            <div class="weekday">금</div>
            <div class="weekday">토</div>

        </div>

        <div
            id="days"
            class="days"
        ></div>

    </div>

    <div
        id="detail"
        class="detail"
    ></div>

</div>


<script>

const calendarData = {data_json};

const today = "{today}";

let currentDate = new Date();

let selectedDate = today;


function parseDate(dateString) {{

    const parts = dateString.split("-");

    return new Date(
        Number(parts[0]),
        Number(parts[1]) - 1,
        Number(parts[2])
    );
}}


function formatDate(date) {{

    const y = date.getFullYear();

    const m = String(
        date.getMonth() + 1
    ).padStart(2, "0");

    const d = String(
        date.getDate()
    ).padStart(2, "0");

    return `${{y}}-${{m}}-${{d}}`;
}}


function getStatusClass(status) {{

    if (status === "시작") {{
        return "start";
    }}

    if (status === "마감") {{
        return "end";
    }}

    return "rolling";
}}


function renderCalendar() {{

    const year =
        currentDate.getFullYear();

    const month =
        currentDate.getMonth();

    document.getElementById(
        "monthTitle"
    ).textContent =
        `${{year}}년 ${{month + 1}}월`;

    const days =
        document.getElementById("days");

    days.innerHTML = "";

    const firstDay =
        new Date(year, month, 1).getDay();

    const lastDate =
        new Date(year, month + 1, 0).getDate();


    for (
        let i = 0;
        i < firstDay;
        i++
    ) {{

        const empty =
            document.createElement("div");

        empty.className = "day empty";

        days.appendChild(empty);
    }}


    for (
        let day = 1;
        day <= lastDate;
        day++
    ) {{

        const date =
            `${{year}}-${{String(month + 1).padStart(2, "0")}}-${{String(day).padStart(2, "0")}}`;

        const cell =
            document.createElement("div");

        cell.className = "day";

        if (date === today) {{
            cell.classList.add("today");
        }}

        if (date === selectedDate) {{
            cell.classList.add("selected");
        }}


        const number =
            document.createElement("div");

        number.className =
            "day-number";

        number.textContent = day;

        cell.appendChild(number);


        const badges =
            document.createElement("div");

        badges.className = "badges";


        const items =
            calendarData[date] || [];


        const visible =
            items.slice(0, 3);


        visible.forEach(item => {{

            const badge =
                document.createElement("div");

            badge.className =
                "badge " +
                getStatusClass(item.status);

            badge.textContent =
                `${{item.status || "수시"}} ${{item.company}}`;

            badges.appendChild(badge);
        }});


        if (items.length > 3) {{

            const more =
                document.createElement("div");

            more.className = "more";

            more.textContent =
                `+ ${{items.length - 3}}개`;

            badges.appendChild(more);
        }}


        cell.appendChild(badges);


        if (items.length > 0) {{

            cell.onclick = () => {{
                selectedDate = date;
                renderCalendar();
                renderDetail(date);
            }};

        }}


        days.appendChild(cell);
    }}
}}


function renderDetail(date) {{

    const detail =
        document.getElementById("detail");

    const items =
        calendarData[date] || [];


    if (!items.length) {{

        detail.innerHTML = `
            <div class="detail-header">
                <div class="detail-date">
                    📅 ${{date}}
                </div>
                <div class="detail-count">
                    등록된 채용공고가 없습니다.
                </div>
            </div>
        `;

        return;
    }}


    let cards = "";


    items.forEach(item => {{

        let status =
            item.status || "수시";

        let statusClass =
            getStatusClass(status);


        let jobs = "";


        if (
            item.jobs &&
            item.jobs.length
        ) {{

            item.jobs.forEach(job => {{

                const employment =
                    job.employment_type || "-";

                const jobName =
                    job.job || "-";

                const applicants =
                    job.applicants === null ||
                    job.applicants === undefined
                        ? "-"
                        : `${{Number(job.applicants).toLocaleString()}}명 작성`;


                jobs += `
                    <div class="job">

                        <span class="employment">
                            ${{escapeHtml(employment)}}
                        </span>

                        <span class="job-name">
                            ${{escapeHtml(jobName)}}
                        </span>

                        <span class="applicants">
                            ${{applicants}}
                        </span>

                    </div>
                `;
            }});

        }} else {{

            jobs = `
                <div class="no-job">
                    모집 직무 정보를 찾지 못했습니다.
                </div>
            `;
        }}


        cards += `
            <div class="recruit-card">

                <div class="card-header">

                    <div class="company">
                        ${{escapeHtml(item.company)}}
                    </div>

                    <div class="status ${{statusClass}}">
                        ${{status === "시작" ? "🟢" :
                           status === "마감" ? "🔴" : "🔵"}}
                        ${{status}}
                    </div>

                </div>

                <a
                    class="link"
                    href="${{escapeAttribute(item.url)}}"
                    target="_blank"
                >
                    🔗 공고 바로가기
                </a>

                <div class="jobs">
                    ${{jobs}}
                </div>

            </div>
        `;
    }});


    detail.innerHTML = `
        <div class="detail-header">

            <div class="detail-date">
                📅 ${{date}}
            </div>

            <div class="detail-count">
                총 ${{items.length}}개 공고
            </div>

        </div>

        ${{cards}}
    `;
}}


function escapeHtml(value) {{

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}}


function escapeAttribute(value) {{
    return escapeHtml(value);
}}


function changeMonth(offset) {{

    currentDate.setMonth(
        currentDate.getMonth() + offset
    );

    renderCalendar();

    const year =
        currentDate.getFullYear();

    const month =
        String(
            currentDate.getMonth() + 1
        ).padStart(2, "0");

    const firstDate =
        `${{year}}-${{month}}-01`;

    const dates =
        Object.keys(calendarData)
            .filter(date => date.startsWith(
                `${{year}}-${{month}}`
            ))
            .sort();

    if (dates.length) {{
        selectedDate = dates[0];
        renderDetail(selectedDate);
    }} else {{
        document.getElementById(
            "detail"
        ).innerHTML = "";
    }}

    renderCalendar();
}}


// 처음 열었을 때
const todayDate = parseDate(today);

currentDate =
    new Date(
        todayDate.getFullYear(),
        todayDate.getMonth(),
        1
    );

renderCalendar();

if (calendarData[today]) {{
    renderDetail(today);
}} else {{

    const currentMonth =
        today.slice(0, 7);

    const dates =
        Object.keys(calendarData)
            .filter(date =>
                date.startsWith(currentMonth)
            )
            .sort();

    if (dates.length) {{
        selectedDate = dates[0];
        renderCalendar();
        renderDetail(selectedDate);
    }} else {{
        renderDetail(today);
    }}
}}

</script>

</body>
</html>
"""


def main():

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

        print("자소설닷컴 채용 달력 수집 중...")

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

        calendar_data = page.evaluate("""
            () => {

                const result = {};

                const cells =
                    document.querySelectorAll(
                        '[data-testid="week-row"] > div[class*="CalendarCell_cell"]'
                    );

                cells.forEach(cell => {

                    const time =
                        cell.querySelector(
                            "time[datetime]"
                        );

                    if (!time) return;

                    const date =
                        time.getAttribute(
                            "datetime"
                        );

                    const items =
                        cell.querySelectorAll(
                            '[data-testid="employment-item"]'
                        );

                    items.forEach(item => {

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
                            }
                            else if (
                                aria === "마감" ||
                                text === "마감"
                            ) {
                                status = "마감";
                            }
                            else {
                                status = "수시";
                            }

                        }
                        else {
                            status = "수시";
                        }

                        const url =
                            href.startsWith("http")
                                ? href
                                : `${location.origin}${href}`;

                        if (!result[date]) {
                            result[date] = [];
                        }

                        if (!result[date].some(
                            x => x.url === url
                        )) {

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

        total = sum(
            len(items)
            for items in calendar_data.values()
        )

        print(
            f"달력 공고 {total}개 발견"
        )

        detail_page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 1000
            },
            locale="ko-KR"
        )

        count = 0

        for date, items in calendar_data.items():

            for item in items:

                count += 1

                print(
                    f"[{count}/{total}] "
                    f"{item['company']}"
                )

                item["jobs"] = collect_detail(
                    detail_page,
                    item["url"]
                )

        print("HTML 생성 중...")

        html = make_html(
            calendar_data
        )

        with open(
            "jasoseol_recruit.html",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(html)

        print()
        print("=" * 60)
        print("수집 완료!")
        print(f"총 공고: {total}개")
        print("결과: jasoseol_recruit.html")
        print("=" * 60)

        detail_page.close()
        page.close()
        browser.close()


if __name__ == "__main__":
    main()
