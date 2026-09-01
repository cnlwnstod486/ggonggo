import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
import time
import re
import json
import os


# ============================================================================
# 공통 설정
# ============================================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://job.alio.go.kr/",
}


# ============================================================================
# 한국시간(KST)
# ============================================================================

KST = timezone(timedelta(hours=9))


def now_kst():
    return datetime.now(KST)


# ============================================================================
# 경로
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

JSON_FILE = os.path.join(
    BASE_DIR,
    "jobs.json"
)


# ============================================================================
# 알리오
# ============================================================================

ALIO_BASE_URL = "https://job.alio.go.kr/recruit.do"


def format_date(date_obj):
    return date_obj.strftime("%Y.%m.%d")


def normalize_alio_date(date_text):

    if not date_text:
        return ""

    text = date_text.strip()

    match = re.search(
        r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})",
        text
    )

    if match:

        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))

        return f"{year:04d}.{month:02d}.{day:02d}"

    return text


def get_alio_rows(soup):
    """
    알리오 실제 HTML에서 공고 행을 찾는다.

    헤더 인덱스를 이용하지 않고
    '등록일' 날짜가 들어있는 실제 데이터 행을 찾는다.
    """

    rows = []

    for tr in soup.find_all("tr"):

        tds = tr.find_all(
            "td",
            recursive=False
        )

        if len(tds) < 5:
            continue

        row_text = tr.get_text(
            " ",
            strip=True
        )

        # 실제 공고 행에는 등록일이 들어있음
        if not re.search(
            r"\d{4}\.\d{2}\.\d{2}",
            row_text
        ):
            continue

        # 채용제목 링크가 있는 행만
        links = tr.find_all(
            "a",
            href=True
        )

        if not links:
            continue

        rows.append(tr)

    return rows


def fetch_alio_jobs(
    area_code="R8018"
):
    """
    알리오 채용공고 수집

    한국시간 기준:
    오늘 ~ 3일 전까지 검색

    예:
    현재 KST = 2026.09.02
    s_date = 2026.08.30
    e_date = 2026.09.02
    """

    now = now_kst()

    end_date = now.date()

    start_date = end_date - timedelta(days=3)

    s_date = start_date.strftime(
        "%Y.%m.%d"
    )

    e_date = end_date.strftime(
        "%Y.%m.%d"
    )

    print()
    print("=" * 80)
    print("📡 알리오(Alio) 크롤링 중...")
    print("=" * 80)

    print(
        f"📅 검색기간: {s_date} ~ {e_date}"
    )

    print(
        f"📍 지역코드: {area_code}"
    )

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/131.0.0.0 "
            "Safari/537.36"
        ),

        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,"
            "image/avif,image/webp,"
            "*/*;q=0.8"
        ),

        "Accept-Language":
            "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",

        "Referer":
            "https://job.alio.go.kr/"
    })

    base_url = (
        "https://job.alio.go.kr/recruit.do"
    )

    all_html = []

    page_no = 1

    page_set = 10

    max_pages = 50

    while page_no <= max_pages:

        params = {
            "pageNo": page_no,
            "s_date": s_date,
            "e_date": e_date,
            "area": area_code,
            "org_type": "",
            "org_name": "",
            "search_type": "",
            "keyword": "",
            "order": "REG_DATE",
            "sort": "DESC",
            "pageSet": page_set,
        }

        html_content = None

        for attempt in range(1, 4):

            try:

                print(
                    f"🔄 알리오 페이지 {page_no} "
                    f"요청 ({attempt}/3)"
                )

                response = session.get(
                    base_url,
                    params=params,
                    timeout=(30, 60)
                )

                response.raise_for_status()

                response.encoding = "utf-8"

                html_content = response.text

                if not html_content.strip():
                    raise RuntimeError(
                        "HTML 응답이 비어있습니다."
                    )

                print(
                    f"   HTTP 상태: "
                    f"{response.status_code}"
                )

                print(
                    f"   ✅ 페이지 {page_no} "
                    f"수신 성공"
                )

                break

            except Exception as e:

                print(
                    f"   ⚠️ 요청 실패 "
                    f"({attempt}/3): {e}"
                )

                if attempt < 3:
                    time.sleep(
                        attempt * 2
                    )

        if html_content is None:

            print(
                f"❌ 알리오 페이지 {page_no} "
                f"최종 요청 실패"
            )

            break

        # HTML 저장
        all_html.append(
            html_content
        )

        # 다음 페이지 존재 여부 확인
        soup = BeautifulSoup(
            html_content,
            "html.parser"
        )

        # 실제 공고 행 확인
        rows = []

        for tr in soup.find_all("tr"):

            tds = tr.find_all(
                "td",
                recursive=False
            )

            if len(tds) != 9:
                continue

            cells = [
                td.get_text(
                    " ",
                    strip=True
                )
                for td in tds
            ]

            # 1번 셀 = 번호
            if not cells[1].isdigit():
                continue

            # 2번 셀 = 채용제목
            if not cells[2]:
                continue

            # 제목 링크
            if not tr.find(
                "a",
                href=True
            ):
                continue

            rows.append(tr)

        print(
            f"   📄 페이지 {page_no}: "
            f"{len(rows)}개 공고"
        )

        # 공고가 없으면 종료
        if len(rows) == 0:

            all_html.pop()

            print(
                f"🏁 페이지 {page_no} "
                f"공고 없음 → 종료"
            )

            break

        # 10개보다 적으면 마지막 페이지
        if len(rows) < page_set:

            print(
                f"🏁 마지막 페이지: "
                f"{page_no}페이지"
            )

            break

        page_no += 1

        time.sleep(0.5)

    print()
    print(
        f"📦 알리오 총 "
        f"{len(all_html)}페이지 수집"
    )

    return all_html



def parse_alio_jobs(
    html_contents
):

    if not html_contents:
        return []

    if isinstance(
        html_contents,
        str
    ):
        html_contents = [
            html_contents
        ]

    print()
    print("=" * 80)
    print("🔎 알리오 공고 파싱")
    print("=" * 80)

    jobs = []

    seen = set()

    for page_index, html_content in enumerate(
        html_contents,
        start=1
    ):

        print()
        print(
            f"📄 페이지 {page_index} 파싱"
        )

        soup = BeautifulSoup(
            html_content,
            "html.parser"
        )

        rows = []

        for tr in soup.find_all("tr"):

            tds = tr.find_all(
                "td",
                recursive=False
            )

            if len(tds) != 9:
                continue

            cells = [
                td.get_text(
                    " ",
                    strip=True
                )
                for td in tds
            ]

            if not cells[1].isdigit():
                continue

            if not cells[2]:
                continue

            if not tr.find(
                "a",
                href=True
            ):
                continue

            rows.append(tr)

        print(
            f"   🔎 실제 공고 행: "
            f"{len(rows)}개"
        )

        page_count = 0

        for row in rows:

            try:

                tds = row.find_all(
                    "td",
                    recursive=False
                )

                cells = [
                    td.get_text(
                        " ",
                        strip=True
                    )
                    for td in tds
                ]

                # 알리오 실제 구조
                number = cells[1]
                title = cells[2]
                company = cells[3]
                location = cells[4]
                employment = cells[5]
                reg_date = cells[6]
                deadline = cells[7]
                status = cells[8]

                # 링크
                title_link = row.find(
                    "a",
                    href=True
                )

                link = ""

                if title_link:

                    href = title_link.get(
                        "href",
                        ""
                    )

                    if href:

                        link = urljoin(
                            "https://job.alio.go.kr",
                            href
                        )

                # 중복 제거
                unique_key = (
                    link
                    if link
                    else (
                        company
                        + "|"
                        + title
                        + "|"
                        + reg_date
                    )
                )

                if unique_key in seen:
                    continue

                seen.add(
                    unique_key
                )

                jobs.append({
                    "site": "alio",
                    "site_name": "알리오",
                    "company": company,
                    "title": title,
                    "type": "공공기관 채용",
                    "location": location,
                    "career": "정보 없음",
                    "education": "정보 없음",
                    "employment": employment,
                    "deadline": deadline,
                    "reg_date": reg_date,
                    "status": status,
                    "link": link,
                })

                page_count += 1

                print(
                    f"   ✅ {company} | {title}"
                )

            except Exception as e:

                print(
                    f"   ⚠️ 알리오 행 파싱 오류: "
                    f"{type(e).__name__}: {e}"
                )

        print(
            f"   🎯 페이지 {page_index}: "
            f"{page_count}개"
        )

    print()
    print("=" * 80)
    print(
        f"🎯 알리오 최종 결과: "
        f"{len(jobs)}개"
    )
    print("=" * 80)

    return jobs







# ============================================================================
# 사람인
# ============================================================================

def fetch_saramin_jobs():

    url = (
        "https://www.saramin.co.kr/zf_user/jobs/list/domestic?"
        "loc_mcd=101000%2C102000%2C108000"
        "&cat_mcls=2"
        "&searchType=search"
        "&searchword=%EC%A0%84%EC%82%B0%EC%A7%81"
        "&exp_cd=1"
        "&exp_none=y"
        "&search_optional_item=y"
        "&search_done=y"
        "&panel_count=y"
        "&preview=y"
        "&page=1"
        "&sort=RD"
        "&page_count=50"
    )

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        response.raise_for_status()

        response.encoding = "utf-8"

        return response.text

    except Exception as e:

        print(
            f"❌ 사람인 크롤링 오류: {e}"
        )

        return None


def is_registered_today_saramin(
    reg_date_text
):

    if not reg_date_text:
        return False

    if "등록" not in reg_date_text:
        return False

    if "수정" in reg_date_text:
        return False

    hours_match = re.search(
        r"(\d+)\s*시간\s*전\s*등록",
        reg_date_text
    )

    if hours_match:

        hours = int(
            hours_match.group(1)
        )

        return hours < 24

    days_match = re.search(
        r"(\d+)\s*일\s*전\s*등록",
        reg_date_text
    )

    if days_match:

        days = int(
            days_match.group(1)
        )

        return days == 0

    return False


def parse_saramin_jobs(
    html_content
):

    if not html_content:
        return []

    soup = BeautifulSoup(
        html_content,
        "html.parser"
    )

    list_body = soup.find(
        "div",
        class_="list_body"
    )

    if not list_body:

        print(
            "❌ 사람인 공고 목록을 찾을 수 없습니다."
        )

        return []

    jobs = []

    for item in list_body.find_all(
        "div",
        class_="list_item"
    ):

        try:

            rec_id = item.get(
                "id",
                ""
            ).replace(
                "rec-",
                ""
            )

            if not rec_id:
                continue

            support_info = item.find(
                "div",
                class_="support_info"
            )

            deadlines_elem = None

            if support_info:

                deadlines_elem = support_info.find(
                    "span",
                    class_="deadlines"
                )

            reg_date_text = (
                deadlines_elem.get_text(
                    strip=True
                )
                if deadlines_elem
                else ""
            )

            if not is_registered_today_saramin(
                reg_date_text
            ):
                continue

            company_elem = item.find(
                "div",
                class_="company_nm"
            )

            company_name = "회사명 없음"

            if company_elem:

                company = company_elem.find(
                    "a",
                    class_="str_tit"
                )

                if company:

                    company_name = company.get_text(
                        strip=True
                    )

                else:

                    company_name = company_elem.get_text(
                        strip=True
                    )

            job_title_elem = item.find(
                "a",
                class_="str_tit",
                id=f"rec_link_{rec_id}"
            )

            if job_title_elem:

                job_title = job_title_elem.get_text(
                    strip=True
                )

                job_link = job_title_elem.get(
                    "href",
                    "#"
                )

            else:

                continue

            job_sector_elem = item.find(
                "span",
                class_="job_sector"
            )

            if job_sector_elem:

                sectors = [
                    s.get_text(
                        strip=True
                    )
                    for s in job_sector_elem.find_all(
                        "span"
                    )
                ]

                job_type = ", ".join(
                    sectors[:3]
                )

                if len(sectors) > 3:
                    job_type += " 외"

            else:

                job_type = "정보 없음"

            recruit_info = item.find(
                "div",
                class_="recruit_info"
            )

            work_place = "정보 없음"
            career = "정보 없음"
            education = "정보 없음"

            if recruit_info:

                lis = recruit_info.find_all(
                    "li"
                )

                if len(lis) > 0:

                    elem = lis[0].find(
                        "p",
                        class_="work_place"
                    )

                    if elem:

                        work_place = elem.get_text(
                            strip=True
                        )

                if len(lis) > 1:

                    elem = lis[1].find(
                        "p",
                        class_="career"
                    )

                    if elem:

                        career = elem.get_text(
                            strip=True
                        )

                if len(lis) > 2:

                    elem = lis[2].find(
                        "p",
                        class_="education"
                    )

                    if elem:

                        education = elem.get_text(
                            strip=True
                        )

            deadline = "정보 없음"

            if support_info:

                date_elem = support_info.find(
                    "span",
                    class_="date"
                )

                if date_elem:

                    deadline = date_elem.get_text(
                        strip=True
                    )

            full_link = (
                f"https://www.saramin.co.kr{job_link}"
                if job_link.startswith("/")
                else job_link
            )

            jobs.append({

                "site": "saramin",
                "site_name": "사람인",
                "company": company_name,
                "title": job_title,
                "type": job_type,
                "location": work_place,
                "career": career,
                "education": education,
                "employment": "정보 없음",
                "deadline": deadline,
                "reg_date": reg_date_text,
                "status": "",
                "link": full_link

            })

        except Exception as e:

            print(
                f"⚠️ 사람인 파싱 오류: {e}"
            )

    print(
        f"🎯 사람인 결과: {len(jobs)}개"
    )

    return jobs


# ============================================================================
# 잡코리아
# ============================================================================

def fetch_jobkorea_jobs():

    url = "https://www.jobkorea.co.kr/Search"

    params = {

        "stext": "전산",

        "ord": "RegDtDesc",

        "FeatureCode": "SKL",

        "tabType": "recruit",

        "edu": "5",

        "careerType": "1"

    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=15
        )

        response.raise_for_status()

        response.encoding = response.apparent_encoding

        return response.text

    except Exception as e:

        print(
            f"❌ 잡코리아 크롤링 오류: {e}"
        )

        return None


def is_jobkorea_registered_today(
    reg_date_text
):

    if not reg_date_text:
        return False

    reg_date_text = reg_date_text.strip()

    if "등록" not in reg_date_text:
        return False

    if "수정" in reg_date_text:
        return False

    hours_match = re.search(
        r"(\d+)\s*시간\s*전\s*등록",
        reg_date_text
    )

    if hours_match:

        hours = int(
            hours_match.group(1)
        )

        return hours < 24

    minutes_match = re.search(
        r"(\d+)\s*분\s*전\s*등록",
        reg_date_text
    )

    if minutes_match:
        return True

    if "오늘 등록" in reg_date_text:
        return True

    date_match = re.search(
        r"(\d{1,2})/(\d{1,2})\s*\([^)]*\)\s*등록",
        reg_date_text
    )

    if date_match:

        month = int(
            date_match.group(1)
        )

        day = int(
            date_match.group(2)
        )

        today = now_kst()

        return (
            month == today.month
            and day == today.day
        )

    return False


def parse_jobkorea_jobs(
    html_content
):

    if not html_content:
        return []

    soup = BeautifulSoup(
        html_content,
        "html.parser"
    )

    jobs = []

    job_list = soup.find(
        "div",
        attrs={
            "data-sentry-component": "JobList"
        }
    )

    if not job_list:
        job_list = soup

    cards = job_list.find_all(
        "div",
        attrs={
            "data-sentry-component": "CardJob"
        }
    )

    if not cards:

        print(
            "❌ 잡코리아 공고 목록을 찾을 수 없습니다."
        )

        return []

    for card in cards:

        try:

            reg_date_text = ""

            for span in card.find_all("span"):

                text = span.get_text(
                    " ",
                    strip=True
                )

                if not text:
                    continue

                if "등록" in text:

                    reg_date_text = text

                    if "마감" not in text:
                        break

            if not is_jobkorea_registered_today(
                reg_date_text
            ):
                continue

            title_elem = card.find(
                "a",
                attrs={
                    "data-sentry-component": "Title"
                }
            )

            if not title_elem:

                title_elem = card.find(
                    "a",
                    href=re.compile(
                        r"/Recruit/GI_Read/"
                    )
                )

            if not title_elem:
                continue

            job_title_span = title_elem.find("span")

            if job_title_span:

                job_title = job_title_span.get_text(
                    strip=True
                )

            else:

                job_title = title_elem.get_text(
                    strip=True
                )

            job_link = title_elem.get(
                "href",
                "#"
            )

            company_name = "회사명 없음"

            links = card.find_all(
                "a",
                href=re.compile(
                    r"/Recruit/GI_Read/"
                )
            )

            for link in links:

                text = link.get_text(
                    " ",
                    strip=True
                )

                if text and text != job_title:

                    company_name = text

                    break

            location = "정보 없음"

            for span in card.find_all("span"):

                text = span.get_text(
                    " ",
                    strip=True
                )

                if re.search(
                    r"(서울|경기|인천|부산|대구|대전|광주|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)",
                    text
                ):

                    if len(text) <= 50:

                        location = text

                        break

            job_type = "정보 없음"

            chips = card.find_all(
                "div",
                attrs={
                    "data-sentry-component": "GrayChip"
                }
            )

            if len(chips) >= 2:

                job_type = chips[1].get_text(
                    " ",
                    strip=True
                )

            career = "정보 없음"

            card_text = card.get_text(
                " ",
                strip=True
            )

            for pattern in [
                "신입·경력",
                "신입/경력",
                "경력무관",
                "신입",
                "경력"
            ]:

                if pattern in card_text:

                    career = pattern

                    break

            deadline = "정보 없음"

            for span in card.find_all("span"):

                text = span.get_text(
                    " ",
                    strip=True
                )

                if "마감" in text:

                    deadline = text

                    break

            if job_link.startswith("/"):

                job_link = (
                    "https://www.jobkorea.co.kr"
                    + job_link
                )

            jobs.append({

                "site": "jobkorea",
                "site_name": "잡코리아",
                "company": company_name,
                "title": job_title,
                "type": job_type,
                "location": location,
                "career": career,
                "education": "정보 없음",
                "employment": "정보 없음",
                "deadline": deadline,
                "reg_date": reg_date_text,
                "status": "",
                "link": job_link

            })

        except Exception as e:

            print(
                f"⚠️ 잡코리아 파싱 오류: {e}"
            )

    print(
        f"🎯 잡코리아 결과: {len(jobs)}개"
    )

    return jobs


# ============================================================================
# JSON 저장
# ============================================================================

def save_jobs_json(
    alio_jobs,
    saramin_jobs,
    jobkorea_jobs
):

    all_jobs = (
        alio_jobs
        + saramin_jobs
        + jobkorea_jobs
    )

    data = {

        "updated_at": now_kst().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "total": len(all_jobs),

        "counts": {

            "alio": len(alio_jobs),

            "saramin": len(saramin_jobs),

            "jobkorea": len(jobkorea_jobs)

        },

        "jobs": all_jobs

    }

    with open(
        JSON_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )

    print(
        "\n💾 jobs.json 저장 완료"
    )

    print(
        f"📁 위치: {JSON_FILE}"
    )

    print(
        f"📊 총 공고: {len(all_jobs)}개"
    )

    print(
        f"🇰🇷 한국시간: "
        f"{now_kst().strftime('%Y-%m-%d %H:%M:%S')}"
    )


# ============================================================================
# 메인
# ============================================================================

def main():

    print("\n" + "=" * 100)

    print(
        "🔍 채용공고 크롤링 시작"
    )

    print(
        f"⏰ 한국시간: "
        f"{now_kst().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print("=" * 100)


    # ========================================================================
    # 알리오
    # ========================================================================

    alio_html = fetch_alio_jobs(
        area_code="R8018"
    )

    alio_jobs = parse_alio_jobs(
        alio_html
    )


    # ========================================================================
    # 사람인
    # ========================================================================

    print("\n📡 사람인(Saramin) 크롤링 중...")

    saramin_html = fetch_saramin_jobs()

    saramin_jobs = (
        parse_saramin_jobs(
            saramin_html
        )
        if saramin_html
        else []
    )


    # ========================================================================
    # 잡코리아
    # ========================================================================

    print("\n📡 잡코리아(JobKorea) 크롤링 중...")

    jobkorea_html = fetch_jobkorea_jobs()

    jobkorea_jobs = (
        parse_jobkorea_jobs(
            jobkorea_html
        )
        if jobkorea_html
        else []
    )


    # ========================================================================
    # JSON 저장
    # ========================================================================

    save_jobs_json(
        alio_jobs,
        saramin_jobs,
        jobkorea_jobs
    )


    # ========================================================================
    # 콘솔 요약
    # ========================================================================

    total = (
        len(alio_jobs)
        + len(saramin_jobs)
        + len(jobkorea_jobs)
    )

    print("\n" + "=" * 100)

    print("✅ 크롤링 완료!")

    print(
        f"   알리오: {len(alio_jobs)}개"
    )

    print(
        f"   사람인: {len(saramin_jobs)}개"
    )

    print(
        f"   잡코리아: {len(jobkorea_jobs)}개"
    )

    print(
        "   -----------------------"
    )

    print(
        f"   총 {total}개"
    )

    print(
        f"   🇰🇷 한국시간: "
        f"{now_kst().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print("=" * 100)


if __name__ == "__main__":

    main()
