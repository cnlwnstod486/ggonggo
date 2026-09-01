import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
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

    match = re.search(
        r"(\d{2})[./-](\d{1,2})[./-](\d{1,2})",
        text
    )

    if match:

        year = int(match.group(1))

        if year <= 69:
            year += 2000
        else:
            year += 1900

        month = int(match.group(2))
        day = int(match.group(3))

        return f"{year:04d}.{month:02d}.{day:02d}"

    return text


def fetch_alio_jobs(days_back=2, area_code="R8018"):

    today = now_kst()
    start_date = today - timedelta(days=days_back)

    params = {
        "pageNo": "1",
        "s_date": format_date(start_date),
        "e_date": format_date(today),
        "area": area_code,
        "org_type": "",
        "org_name": "",
        "search_type": "",
        "keyword": "",
        "order": "REG_DATE",
        "sort": "DESC",
        "pageSet": "50",
    }

    print("\n" + "=" * 80)
    print("📡 알리오(Alio) 크롤링 중...")
    print("=" * 80)

    session = requests.Session()
    session.headers.update(HEADERS)

    # 최대 3회 재시도
    for attempt in range(1, 4):

        try:

            print(
                f"🔄 알리오 요청 시도 "
                f"{attempt}/3"
            )

            response = session.get(
                ALIO_BASE_URL,
                params=params,
                timeout=(15, 60)
            )

            print(
                f"🌐 HTTP 상태: "
                f"{response.status_code}"
            )

            response.raise_for_status()

            response.encoding = "utf-8"

            print("✅ 알리오 응답 성공")

            return response.text

        except requests.exceptions.Timeout as e:

            print(
                f"⏰ 알리오 요청 시간 초과 "
                f"({attempt}/3)"
            )

            print(f"   {e}")

            if attempt < 3:
                print("   잠시 후 다시 시도합니다...")

        except requests.exceptions.ConnectionError as e:

            print(
                f"🌐 알리오 연결 오류 "
                f"({attempt}/3)"
            )

            print(f"   {e}")

            if attempt < 3:
                print("   잠시 후 다시 시도합니다...")

        except requests.RequestException as e:

            print(
                f"❌ 알리오 요청 실패 "
                f"({attempt}/3)"
            )

            print(f"   {e}")

            if attempt < 3:
                print("   잠시 후 다시 시도합니다...")

        except Exception as e:

            print(
                f"❌ 알리오 예상치 못한 오류: {e}"
            )

            break

    print()
    print("⚠️ 알리오 크롤링 실패")
    print("   사람인/잡코리아 크롤링은 계속 진행합니다.")

    return None


def parse_alio_jobs(
    html_content,
    filter_today_only=True
):

    if not html_content:
        return []

    soup = BeautifulSoup(
        html_content,
        "html.parser"
    )

    today = now_kst().strftime("%Y.%m.%d")

    tables = soup.find_all("table")

    target_table = None

    required_headers = [
        "채용제목",
        "기관명",
        "근무지",
        "고용형태",
        "등록일",
        "마감일",
        "상태",
    ]

    print(
        f"📋 알리오 테이블 개수: {len(tables)}"
    )

    for table in tables:

        headers = [
            th.get_text(" ", strip=True)
            for th in table.find_all("th")
        ]

        if all(
            header in headers
            for header in required_headers
        ):

            target_table = table

            print(
                "✅ 알리오 채용공고 테이블 발견"
            )

            break

    if target_table is None:

        print(
            "⚠️ 알리오 채용공고 테이블을 찾지 못했습니다."
        )

        return []

    header_row = target_table.find("tr")

    headers = [
        th.get_text(" ", strip=True)
        for th in header_row.find_all("th")
    ]

    try:

        title_idx = headers.index("채용제목")
        agency_idx = headers.index("기관명")
        location_idx = headers.index("근무지")
        employment_idx = headers.index("고용형태")
        reg_date_idx = headers.index("등록일")
        deadline_idx = headers.index("마감일")
        status_idx = headers.index("상태")

    except ValueError as e:

        print(
            f"❌ 알리오 컬럼 확인 실패: {e}"
        )

        return []

    rows = target_table.find_all("tr")

    jobs = []

    for row in rows:

        if row.find("th"):
            continue

        tds = row.find_all("td")

        if not tds:
            continue

        max_idx = max(
            title_idx,
            agency_idx,
            location_idx,
            employment_idx,
            reg_date_idx,
            deadline_idx,
            status_idx
        )

        if len(tds) <= max_idx:
            continue

        try:

            title_td = tds[title_idx]

            job_title = title_td.get_text(
                " ",
                strip=True
            )

            if not job_title:
                continue

            title_link = title_td.find(
                "a",
                href=True
            )

            job_link = ""

            if title_link:

                job_link = title_link.get(
                    "href",
                    ""
                )

            if not job_link:

                any_link = row.find(
                    "a",
                    href=True
                )

                if any_link:

                    job_link = any_link.get(
                        "href",
                        ""
                    )

            agency = tds[agency_idx].get_text(
                " ",
                strip=True
            )

            location = tds[location_idx].get_text(
                " ",
                strip=True
            )

            employment_type = tds[
                employment_idx
            ].get_text(
                " ",
                strip=True
            )

            reg_date_raw = tds[
                reg_date_idx
            ].get_text(
                " ",
                strip=True
            )

            reg_date = normalize_alio_date(
                reg_date_raw
            )

            if filter_today_only:

                if reg_date != today:
                    continue

            deadline_raw = tds[
                deadline_idx
            ].get_text(
                " ",
                strip=True
            )

            deadline_match = re.search(
                r"\d{2,4}[./-]\d{1,2}[./-]\d{1,2}",
                deadline_raw
            )

            if deadline_match:

                deadline = deadline_match.group(0)

            else:

                deadline = deadline_raw

            status = tds[
                status_idx
            ].get_text(
                " ",
                strip=True
            )

            job_link = urljoin(
                "https://job.alio.go.kr",
                job_link
            )

            jobs.append({

                "site": "alio",
                "site_name": "알리오",
                "company": agency,
                "title": job_title,
                "type": "공공기관 채용",
                "location": location,
                "career": "정보 없음",
                "education": "정보 없음",
                "employment": employment_type,
                "deadline": deadline,
                "reg_date": reg_date,
                "status": status,
                "link": job_link

            })

        except Exception as e:

            print(
                f"⚠️ 알리오 파싱 오류: {e}"
            )

    print(
        f"🎯 알리오 결과: {len(jobs)}개"
    )

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
        days_back=2,
        area_code="R8018"
    )

    alio_jobs = (
        parse_alio_jobs(
            alio_html,
            filter_today_only=True
        )
        if alio_html
        else []
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
