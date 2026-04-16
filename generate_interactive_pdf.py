from pathlib import Path

from bidi.algorithm import get_display
import arabic_reshaper
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 40
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2)
LINE_GAP = 18
FIELD_GAP = 16

BG = HexColor("#F9F6F0")
ACCENT = HexColor("#3B729C")
ACCENT_DARK = HexColor("#244E70")
TEXT = HexColor("#1F1B18")
MUTED = HexColor("#5E6770")
LINE = HexColor("#D7E1EA")
WHITE = HexColor("#FFFFFF")

FONT_PATH = "/System/Library/Fonts/SFArabic.ttf"
FONT_NAME = "SFArabic"

MULTILINE = 1 << 12


def rtl(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


def ensure_font() -> None:
    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))


def split_rtl_text(
    text: str, font_name: str, font_size: int, max_width: float
) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines = []
    current = []
    for word in words:
        trial = " ".join(current + [word])
        shaped = rtl(trial)
        if (
            pdfmetrics.stringWidth(shaped, font_name, font_size) <= max_width
            or not current
        ):
            current.append(word)
            continue
        lines.append(rtl(" ".join(current)))
        current = [word]

    if current:
        lines.append(rtl(" ".join(current)))
    return lines


class PdfFormBuilder:
    def __init__(self, output_path: Path) -> None:
        self.c = canvas.Canvas(str(output_path), pagesize=A4)
        self.form = self.c.acroForm
        self.y = PAGE_HEIGHT - MARGIN
        self.page_number = 1
        self._new_page()

    def _new_page(self) -> None:
        self.c.setFillColor(BG)
        self.c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
        self.c.setFillColor(ACCENT)
        self.c.rect(0, PAGE_HEIGHT - 22, PAGE_WIDTH, 22, fill=1, stroke=0)
        self.c.setFillColor(TEXT)
        self.y = PAGE_HEIGHT - 50

    def maybe_page_break(self, needed: float) -> None:
        if self.y - needed >= MARGIN:
            return
        self.c.showPage()
        self.page_number += 1
        self._new_page()

    def draw_title(self, title: str, subtitle: str) -> None:
        self.c.setFont(FONT_NAME, 22)
        self.c.setFillColor(ACCENT_DARK)
        self.c.drawRightString(PAGE_WIDTH - MARGIN, self.y, rtl(title))
        self.y -= 28

        self.c.setFont(FONT_NAME, 11)
        self.c.setFillColor(MUTED)
        for line in split_rtl_text(subtitle, FONT_NAME, 11, CONTENT_WIDTH):
            self.c.drawRightString(PAGE_WIDTH - MARGIN, self.y, line)
            self.y -= 15
        self.y -= 6

    def draw_section(self, number: int, title: str, subtitle: str) -> None:
        self.maybe_page_break(76)
        self.c.setFillColor(WHITE)
        self.c.setStrokeColor(LINE)
        self.c.roundRect(MARGIN, self.y - 38, CONTENT_WIDTH, 42, 10, fill=1, stroke=1)

        self.c.setFont(FONT_NAME, 13)
        self.c.setFillColor(ACCENT_DARK)
        self.c.drawRightString(
            PAGE_WIDTH - MARGIN - 12, self.y - 12, rtl(f"{number}. {title}")
        )

        self.c.setFont(FONT_NAME, 10)
        self.c.setFillColor(MUTED)
        self.c.drawRightString(PAGE_WIDTH - MARGIN - 12, self.y - 28, rtl(subtitle))
        self.y -= 56

    def draw_label(self, text: str, note: str | None = None) -> None:
        self.c.setFont(FONT_NAME, 11)
        self.c.setFillColor(TEXT)
        self.c.drawRightString(PAGE_WIDTH - MARGIN, self.y, rtl(text))
        self.y -= 16
        if note:
            self.c.setFont(FONT_NAME, 9)
            self.c.setFillColor(MUTED)
            self.c.drawRightString(PAGE_WIDTH - MARGIN, self.y, rtl(note))
            self.y -= 14

    def text_field(
        self,
        name: str,
        label: str,
        height: float = 26,
        multiline: bool = False,
        note: str | None = None,
    ) -> None:
        needed = 50 + height + (14 if note else 0)
        self.maybe_page_break(needed)
        self.draw_label(label, note)
        y = self.y - height
        self.form.textfield(
            name=name,
            x=MARGIN,
            y=y,
            width=CONTENT_WIDTH,
            height=height,
            fontName="Helvetica",
            fontSize=11,
            borderStyle="solid",
            borderWidth=1,
            borderColor=ACCENT,
            fillColor=WHITE,
            textColor=TEXT,
            forceBorder=True,
            fieldFlags=MULTILINE if multiline else 0,
        )
        self.y = y - FIELD_GAP

    def three_text_fields(self, fields: list[tuple[str, str]]) -> None:
        self.maybe_page_break(70)
        col_gap = 12
        col_width = (CONTENT_WIDTH - (2 * col_gap)) / 3
        label_y = self.y
        field_y = self.y - 44

        for idx, (name, label) in enumerate(fields):
            x = MARGIN + idx * (col_width + col_gap)
            self.c.setFont(FONT_NAME, 10)
            self.c.setFillColor(TEXT)
            self.c.drawRightString(x + col_width, label_y, rtl(label))
            self.form.textfield(
                name=name,
                x=x,
                y=field_y,
                width=col_width,
                height=26,
                fontName="Helvetica",
                fontSize=10,
                borderStyle="solid",
                borderWidth=1,
                borderColor=ACCENT,
                fillColor=WHITE,
                textColor=TEXT,
                forceBorder=True,
            )

        self.y = field_y - FIELD_GAP

    def radio_group(
        self, name: str, label: str, options: list[str], note: str | None = None
    ) -> None:
        needed = 54 + len(options) * 22 + (14 if note else 0)
        self.maybe_page_break(needed)
        self.draw_label(label, note)

        for option in options:
            button_y = self.y - 10
            self.form.radio(
                name=name,
                value=option,
                selected=False,
                x=PAGE_WIDTH - MARGIN - 16,
                y=button_y,
                buttonStyle="circle",
                borderStyle="solid",
                size=12,
                borderColor=ACCENT,
                fillColor=WHITE,
                textColor=ACCENT_DARK,
            )
            self.c.setFont(FONT_NAME, 11)
            self.c.setFillColor(TEXT)
            self.c.drawRightString(PAGE_WIDTH - MARGIN - 24, self.y, rtl(option))
            self.y -= 22

        self.y -= 4

    def checkbox_group(
        self, name_prefix: str, label: str, options: list[str], note: str | None = None
    ) -> None:
        needed = 54 + len(options) * 22 + (14 if note else 0)
        self.maybe_page_break(needed)
        self.draw_label(label, note)

        for idx, option in enumerate(options, start=1):
            box_y = self.y - 10
            self.form.checkbox(
                name=f"{name_prefix}_{idx}",
                checked=False,
                x=PAGE_WIDTH - MARGIN - 16,
                y=box_y,
                size=12,
                borderWidth=1,
                borderColor=ACCENT,
                fillColor=WHITE,
                textColor=ACCENT_DARK,
                buttonStyle="check",
            )
            self.c.setFont(FONT_NAME, 11)
            self.c.setFillColor(TEXT)
            self.c.drawRightString(PAGE_WIDTH - MARGIN - 24, self.y, rtl(option))
            self.y -= 22

        self.y -= 4

    def choice_field(
        self, name: str, label: str, options: list[str], note: str | None = None
    ) -> None:
        needed = 58 + (14 if note else 0)
        self.maybe_page_break(needed)
        self.draw_label(label, note)
        y = self.y - 26
        self.form.choice(
            name=name,
            x=MARGIN,
            y=y,
            width=CONTENT_WIDTH,
            height=26,
            options=["-"] + options,
            value="-",
            fontName="Helvetica",
            fontSize=10,
            borderStyle="solid",
            borderWidth=1,
            borderColor=ACCENT,
            fillColor=WHITE,
            textColor=TEXT,
            forceBorder=True,
        )
        self.y = y - FIELD_GAP

    def save(self) -> None:
        self.c.save()


def main() -> None:
    ensure_font()
    output_path = Path(__file__).with_name("interactive-questionnaire-fillable.pdf")
    pdf = PdfFormBuilder(output_path)

    pdf.draw_title(
        "نموذج ملخص المبادرة",
        "نسخة PDF تفاعلية قابلة للتعبئة وتتضمن الحقول الأساسية نفسها الموجودة في صفحة HTML.",
    )

    pdf.draw_section(1, "الأساسيات", "اسم المشروع والخلفية المختصرة")
    pdf.text_field("projectName", "1. اسم المشروع والشركة التابعة")
    pdf.text_field(
        "projectBackground",
        "2. ما هو المشروع؟ ولماذا نقوم به الآن؟",
        height=78,
        multiline=True,
        note="خلفية المشروع",
    )

    pdf.draw_section(2, "المواعيد", "الجدول الزمني والمرحلة الحالية")
    pdf.three_text_fields(
        [
            ("contractDate", "3. تاريخ توقيع العقد"),
            ("startDate", "تاريخ انطلاق المشروع"),
            ("endDate", "تاريخ انتهاء المشروع"),
        ]
    )
    pdf.radio_group(
        "projectStage",
        "4. المرحلة الحالية",
        ["تشخيص", "تحديد", "تصميم", "تنفيذ"],
        note="اختر واحدة",
    )

    pdf.draw_section(3, "الأهداف", "الركيزة والأثر الاستراتيجي")
    pdf.choice_field(
        "goalPillar",
        "5. ما هو هدفنا؟",
        ["تطوير بيئة", "تمكين قطاع", "الارتقاء بالمدينة", "خدمة المواطن"],
        note="اختر الركيزة المناسبة",
    )
    pdf.text_field(
        "strategicImpact",
        "6. كيف سيجعل هذا المشروع حياة سكان الرياض أفضل أو يدعم اقتصاد المدينة؟",
        height=78,
        multiline=True,
    )
    pdf.text_field(
        "keyMessage",
        "7. ما هي المعلومة الواحدة التي تريد أن يتذكرها الناس عن هذا المشروع؟",
        height=78,
        multiline=True,
    )

    pdf.draw_section(4, "الرسائل", "حقائق داعمة تبرز نجاح المبادرة")
    pdf.text_field(
        "supportingFacts",
        "8. قدم 2-3 حقائق تثبت نجاح المشروع",
        height=92,
        multiline=True,
    )

    pdf.draw_section(
        5, "التنفيذ الإعلامي", "الاحتياج الإعلامي والترويج والمواد المتوفرة"
    )
    pdf.radio_group(
        "prSupport",
        "9. هل يتطلب المشروع دعما من العلاقات العامة؟",
        ["نعم", "لا", "غير محدد"],
        note="خبر صحفي أو توقيع أو متحدث رسمي",
    )
    pdf.radio_group(
        "paidPromotion",
        "10. هل تحتاج إلى إعلانات ممولة على منصات التواصل؟",
        ["نعم", "لا", "بحاجة لدراسة"],
        note="Paid Social Media",
    )
    pdf.checkbox_group(
        "assets",
        "11. ما المواد المتوفرة حاليا للنشر؟",
        ["صور", "فيديوهات", "تصاميم هندسية", "عروض تقديمية", "لا توجد مواد حاليا"],
        note="يمكن اختيار أكثر من عنصر",
    )
    pdf.text_field("assetsNotes", "ملاحظات إضافية", height=78, multiline=True)

    pdf.save()
    print(output_path)


if __name__ == "__main__":
    main()
