"""테스트용 거래처원장 PDF를 만든다.

성운에프에스 거래처원장(PDF) 양식을 본떠 가상 업체 자료를 만든다.
변환 단계의 "확인 필요" 검사를 시험하려고 일부러 틀린 줄을 넣었다.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle

OUT_PATH = Path(__file__).resolve().parent / "테스트_한빛식자재_9월거래처원장.pdf"

pdfmetrics.registerFont(TTFont("Malgun", r"C:\Windows\Fonts\malgun.ttf"))
pdfmetrics.registerFont(TTFont("MalgunBd", r"C:\Windows\Fonts\malgunbd.ttf"))

SUPPLIER = {
    "상호": "(테스트)한빛식자재",
    "등록번호": "000-00-00000",
    "성명": "홍길동",
    "주소": "테스트시 테스트구 테스트로 1",
    "업태": "도소매",
    "종목": "학교급식납품",
    "전화": "000-000-0000",
    "팩스": "000-000-0001",
}
PERIOD = "26-09-01 ~ 26-09-30"

# 일자, 품목명, 단위, 수량, 단가, 금액(None이면 수량x단가), 과면, 배송도착지
ROWS = [
    ("09-01", "(9월)불고기가득메밀전병-오븐용", "봉", 3, 13230, None, "과", "감물초 2일"),
    ("09-01", "(9월)콰트로열대과일", "봉", 5, 6840, None, "면", "오성중 2일"),
    ("09-02", "(국내산)치즈쌀떡볶이(냉동)", "KG", 2, 7560, None, "과", "목도초9/3"),
    ("09-03", "메론50g(국내산)", "개", 60, 980, None, "과", "오성중9/3"),
    ("09-07", "(9월)프로바이오틱스훈제오리-중", "봉", 27, 24030, None, "과", "동인초 7일"),
    ("09-10", "분모자_250g", "봉", 4, 2550, None, "과", "백봉초9/11"),
    ("09-15", "다진전복살(내장제거)(국내산)", "KG", 2, 227430, None, "면", "오성중조식9/15"),
    ("09-16", "(9월)미소담은오리불고기SET(생", "봉", 1.75, 79920, None, "면", "동인초 17일(7키로)"),
    # 확인 필요 시험용 1: 금액이 수량x단가와 맞지 않음 (정상 19,600)
    ("09-17", "메론50g(국내산)", "개", 20, 980, 21600, "과", "오성중9/17"),
    # 확인 필요 시험용 2: 매핑표에 없을 새 품목
    ("09-22", "(테스트)신규품목_유기농사과즙", "봉", 10, 1500, None, "면", "칠성초9/23"),
    ("09-22", "(9월)오복담은꿀송편", "봉", 9, 8640, None, "과", "북중 23일"),
    ("09-23", "[냉장]그릭요거트플레인450g", "개", 2, 7880, None, "과", "칠성초9/23"),
    # 확인 필요 시험용 3: 평소 단가(980)보다 크게 높음
    ("09-28", "메론50g(국내산)", "개", 10, 9800, None, "과", "오성중9/28"),
    ("09-29", "(9월)망고스틱(냉동/개별포장)", "봉", 3, 12240, None, "면", "감물초 30일(60개)"),
    ("09-30", "(10월)직접만드는우리버터휘낭시", "봉", 4, 24200, None, "과", "칠성초 10/1"),
]


def amount(row):
    qty, price, fixed = row[3], row[4], row[5]
    return fixed if fixed is not None else round(qty * price)


def won(n):
    return f"{n:,}"


def qty_text(q):
    return f"{q:g}"


def korean_amount(n):
    digits = "영일이삼사오육칠팔구"
    small = ["", "십", "백", "천"]
    big = ["", "만", "억"]
    parts = []
    for i, unit in enumerate(big):
        chunk = (n // (10000 ** i)) % 10000
        if chunk == 0:
            continue
        text = ""
        for j in range(3, -1, -1):
            d = (chunk // (10 ** j)) % 10
            if d:
                text += digits[d] + small[j]
        parts.append(text + unit)
    return "".join(reversed(parts))


def main():
    taxable = sum(amount(r) for r in ROWS if r[6] == "과")
    exempt = sum(amount(r) for r in ROWS if r[6] == "면")
    supply = round(taxable / 1.1)
    vat = taxable - supply
    total = taxable + exempt

    base = ParagraphStyle("base", fontName="Malgun", fontSize=9, leading=12)
    title = ParagraphStyle("title", parent=base, fontName="MalgunBd", fontSize=20, leading=26, alignment=1)
    big = ParagraphStyle("big", parent=base, fontName="MalgunBd", fontSize=12, leading=16)
    warn = ParagraphStyle("warn", parent=base, fontName="MalgunBd", fontSize=11, textColor=colors.red, alignment=1)

    story = [
        Paragraph("※ 테스트용 자료입니다. 실제 거래 자료가 아닙니다. ※", warn),
        Spacer(1, 3 * mm),
        Paragraph("거 래 처 원 장", title),
        Spacer(1, 3 * mm),
    ]

    header = Table(
        [
            ["괴산먹거리연대 귀중", "공 급 자", "", "", ""],
            ["", "등록번호", SUPPLIER["등록번호"], "", ""],
            ["", "상호", SUPPLIER["상호"], "성명", SUPPLIER["성명"]],
            [f"집계기간:{PERIOD}", "사업장주소", SUPPLIER["주소"], "", ""],
            ["", "업태", SUPPLIER["업태"], "종목", SUPPLIER["종목"]],
            ["", "전화", SUPPLIER["전화"], "팩스", SUPPLIER["팩스"]],
        ],
        colWidths=[85 * mm, 25 * mm, 45 * mm, 20 * mm, 40 * mm],
    )
    header.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Malgun", 9),
        ("FONT", (0, 0), (0, 0), "Malgun", 12),
        ("GRID", (1, 0), (-1, -1), 0.5, colors.black),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("SPAN", (1, 0), (-1, 0)),
        ("SPAN", (2, 1), (-1, 1)),
        ("SPAN", (2, 3), (-1, 3)),
        ("SPAN", (0, 0), (0, 2)),
        ("SPAN", (0, 3), (0, 5)),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [header]

    summary = Table(
        [["공급가", won(supply), "부가세", won(vat), "과세", won(taxable), "면세", won(exempt)]],
        colWidths=[18 * mm, 32 * mm, 18 * mm, 32 * mm, 18 * mm, 32 * mm, 18 * mm, 47 * mm],
    )
    summary.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Malgun", 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
    ]))
    story += [summary, Spacer(1, 4 * mm)]
    story += [Paragraph(f"합계금액 : 일금 {korean_amount(total)}원정(\\{won(total)})", big), Spacer(1, 4 * mm)]

    lines = [["일 자", "품 목 명", "단위", "수량", "단가", "금 액", "과", "배송도착지"]]
    for r in ROWS:
        lines.append([r[0], r[1], r[2], qty_text(r[3]), won(r[4]), won(amount(r)), r[6], r[7]])
    lines.append(["", "합 계", "", "", "", won(total), "", ""])

    detail = Table(
        lines,
        colWidths=[16 * mm, 70 * mm, 14 * mm, 16 * mm, 22 * mm, 32 * mm, 9 * mm, 60 * mm],
        repeatRows=1,
    )
    detail.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Malgun", 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#CCCCFF")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (3, 1), (5, -1), "RIGHT"),
        ("ALIGN", (6, 1), (6, -1), "CENTER"),
    ]))
    story.append(detail)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Malgun", 8)
        w, h = landscape(A4)
        canvas.drawString(10 * mm, h - 8 * mm, "인쇄일자 : 2026-10-02 (테스트)")
        canvas.drawRightString(w - 10 * mm, h - 8 * mm, f"페이지 : {doc.page}")
        canvas.drawRightString(w - 10 * mm, 8 * mm, SUPPLIER["상호"])
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(OUT_PATH), pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)

    print(f"생성: {OUT_PATH}")
    print(f"건수 {len(ROWS)} / 과세 {won(taxable)} (공급가 {won(supply)}, 부가세 {won(vat)}) / 면세 {won(exempt)} / 합계 {won(total)}")


if __name__ == "__main__":
    main()
