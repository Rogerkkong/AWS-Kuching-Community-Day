"""Generate clearly marked synthetic sample documents (Malay) so the pipeline can run before the real
corpus arrives. Every page carries the watermark "SINTETIK - CONTOH SAHAJA".

Corpus (data/raw):
  PP 3/2018   cuti rehat, 10 days        -> superseded by PP 2/2024           (chain step 1)
  PP 2/2024   cuti rehat, 15 days        -> amended (para 6) by PP 5/2025     (chain step 2)
  PP 5/2025   cuti kuarantin amendment                                         (chain step 3)
  PAS 4/2023  Sarawak cuti rehat, 20 days (Federal vs Sarawak pair with PP 2/2024)
  SOP-SM 1/2024  SOP permohonan cuti rehat melalui HRMIS
  MMPJ 2/2026 minit mesyuarat pengurusan jabatan (12 Mac 2026)
  MJKK 1/2026 minit mesyuarat jawatankuasa kewangan (20 Januari 2026)
  PP 1/2025   kadar elaun perjalanan dalam negeri
  GP 1/2026   TERHAD garis panduan (synthetic restricted document)
Held back for the live "pack v2" demo (data/incoming):
  PP 3/2026   kadar elaun perjalanan (semakan) -> supersedes PP 1/2025

Usage: python scripts/make_synthetic_docs.py [--force]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
INCOMING = ROOT / "data" / "incoming"
WATERMARK = "SINTETIK - CONTOH SAHAJA"

JPA = "JABATAN PERKHIDMATAN AWAM MALAYSIA (CONTOH)"
SUK = "PEJABAT SETIAUSAHA KERAJAAN NEGERI SARAWAK (CONTOH)"

DOCS: dict[str, dict] = {
    "PP-3-2018.pdf": {
        "issuer": JPA,
        "header": ["PEKELILING PERKHIDMATAN BILANGAN 3 TAHUN 2018", "CUTI REHAT DAN GANTIAN CUTI REHAT"],
        "meta": ["Rujukan: JPA(S)CONTOH/3/2018", "Tarikh: 15 Mac 2018"],
        "body": [
            "1. TUJUAN",
            "Pekeliling Perkhidmatan ini bertujuan menetapkan peraturan cuti rehat dan Gantian Cuti Rehat bagi pegawai Perkhidmatan Awam Persekutuan.",
            "2. PEMAKAIAN",
            "2.1 Pekeliling ini terpakai kepada semua pegawai Perkhidmatan Awam Persekutuan yang dilantik secara tetap, kontrak atau sementara.",
            "3. KELAYAKAN CUTI REHAT",
            "3.1 Kelayakan cuti rehat tahunan adalah berdasarkan tempoh perkhidmatan pegawai, iaitu dua puluh lima (25) hari bagi pegawai yang berkhidmat kurang daripada sepuluh tahun dan tiga puluh (30) hari bagi pegawai yang berkhidmat sepuluh tahun atau lebih.",
            "4. MEMBAWA KE HADAPAN CUTI REHAT",
            "4.1 Cuti rehat yang tidak dihabiskan dalam sesuatu tahun boleh dibawa ke tahun berikutnya tidak melebihi sepuluh (10) hari.",
            "4.2 Baki cuti rehat yang melebihi had di perenggan 4.1 adalah luput.",
            "5. GANTIAN CUTI REHAT",
            "5.1 Pegawai yang bersara layak menerima bayaran tunai sebagai Gantian Cuti Rehat.",
            "5.2 Jumlah cuti rehat terkumpul bagi tujuan Gantian Cuti Rehat adalah tidak melebihi 150 hari sepanjang tempoh perkhidmatan.",
            "6. CUTI KUARANTIN",
            "6.1 Pegawai yang diarahkan menjalani kuarantin oleh Pegawai Perubatan layak diberi cuti kuarantin tidak melebihi tujuh (7) hari setiap kali.",
            "7. TARIKH KUAT KUASA",
            "Pekeliling Perkhidmatan ini berkuat kuasa mulai 1 April 2018.",
            "8. PEMBATALAN",
            "Dengan berkuat kuasanya Pekeliling ini, Surat Pekeliling Perkhidmatan Bilangan 5 Tahun 2011 adalah dibatalkan.",
        ],
    },
    "PP-2-2024.pdf": {
        "issuer": JPA,
        "header": ["PEKELILING PERKHIDMATAN BILANGAN 2 TAHUN 2024", "CUTI REHAT DAN GANTIAN CUTI REHAT"],
        "meta": ["Rujukan: JPA(S)CONTOH/2/2024", "Tarikh: 15 Januari 2024"],
        "body": [
            "1. TUJUAN",
            "Pekeliling Perkhidmatan ini bertujuan menetapkan peraturan baharu mengenai cuti rehat, cuti kuarantin, cuti tanpa gaji dan Gantian Cuti Rehat bagi pegawai Perkhidmatan Awam Persekutuan.",
            "2. LATAR BELAKANG",
            "Kerajaan telah mengkaji semula kemudahan cuti rehat bagi menggalakkan pegawai merancang cuti dengan lebih baik dan mengurangkan cuti yang luput pada akhir tahun.",
            "3. PEMAKAIAN",
            "3.1 Pekeliling ini terpakai kepada semua pegawai Perkhidmatan Awam Persekutuan termasuk pegawai yang dilantik secara kontrak.",
            "3.2 Pekeliling ini tidak terpakai kepada pegawai Perkhidmatan Awam Negeri Sarawak yang tertakluk kepada pekeliling Kerajaan Negeri.",
            "4. MEMBAWA KE HADAPAN CUTI REHAT",
            "4.1 Cuti rehat yang tidak dihabiskan dalam sesuatu tahun boleh dikumpul dan dibawa ke tahun berikutnya tidak melebihi lima belas (15) hari.",
            "4.2 Permohonan membawa ke hadapan cuti rehat hendaklah dikemukakan melalui modul Cuti HRMIS sebelum 31 Disember setiap tahun dan diluluskan oleh Ketua Jabatan.",
            "4.3 Cuti rehat yang melebihi had di perenggan 4.1 adalah luput dan tidak boleh dituntut dalam apa jua bentuk.",
            "5. GANTIAN CUTI REHAT",
            "5.1 Pegawai yang bersara atau ditamatkan perkhidmatan layak menerima bayaran tunai sebagai Gantian Cuti Rehat.",
            "5.2 Jumlah cuti rehat terkumpul bagi tujuan Gantian Cuti Rehat adalah tidak melebihi 150 hari sepanjang tempoh perkhidmatan.",
            "5.3 Kiraan Gantian Cuti Rehat adalah berdasarkan gaji hakiki terakhir pegawai.",
            "6. CUTI KUARANTIN",
            "6.1 Pegawai yang diarahkan menjalani kuarantin oleh Pegawai Perubatan layak diberi cuti kuarantin tidak melebihi tujuh (7) hari setiap kali.",
            "6.2 Surat arahan kuarantin daripada Pegawai Perubatan hendaklah dikemukakan kepada Ketua Jabatan dalam tempoh tiga (3) hari bekerja.",
            "7. CUTI TANPA GAJI",
            "7.1 Pegawai yang telah disahkan dalam perkhidmatan boleh memohon cuti tanpa gaji tidak melebihi sembilan puluh (90) hari dalam setahun atas sebab peribadi.",
            "7.2 Permohonan cuti tanpa gaji hendaklah dikemukakan sekurang-kurangnya tiga puluh (30) hari sebelum tarikh cuti bermula dan diluluskan oleh Ketua Jabatan.",
            "7.3 Tempoh cuti tanpa gaji tidak diambil kira bagi tujuan kenaikan gaji tahunan.",
            "8. TARIKH KUAT KUASA",
            "Pekeliling Perkhidmatan ini berkuat kuasa mulai 1 Februari 2024.",
            "9. PEMBATALAN",
            "Pekeliling Perkhidmatan Bilangan 3 Tahun 2018 adalah dibatalkan dan digantikan dengan Pekeliling ini.",
        ],
    },
    "PP-5-2025.pdf": {
        "issuer": JPA,
        "header": ["PEKELILING PERKHIDMATAN BILANGAN 5 TAHUN 2025", "PINDAAN KEMUDAHAN CUTI KUARANTIN"],
        "meta": ["Rujukan: JPA(S)CONTOH/5/2025", "Tarikh: 10 Jun 2025"],
        "body": [
            "1. TUJUAN",
            "Pekeliling Perkhidmatan ini bertujuan meminda kemudahan cuti kuarantin bagi pegawai Perkhidmatan Awam Persekutuan.",
            "2. PINDAAN",
            "2.1 Perenggan 6.1 Pekeliling Perkhidmatan Bilangan 2 Tahun 2024 adalah dipinda seperti berikut: Pegawai yang diarahkan menjalani kuarantin oleh Pegawai Perubatan layak diberi cuti kuarantin tidak melebihi empat belas (14) hari setiap kali.",
            "2.2 Peruntukan lain berkaitan cuti rehat dan Gantian Cuti Rehat kekal tanpa perubahan.",
            "3. TARIKH KUAT KUASA",
            "Pekeliling Perkhidmatan ini berkuat kuasa mulai 1 Julai 2025.",
        ],
    },
    "PAS-4-2023.pdf": {
        "issuer": SUK,
        "header": ["PEKELILING AM SARAWAK BILANGAN 4 TAHUN 2023",
                   "CUTI REHAT PEGAWAI PERKHIDMATAN AWAM NEGERI SARAWAK"],
        "meta": ["Rujukan: SUK.SWK/CONTOH/4/2023", "Tarikh: 20 Jun 2023"],
        "body": [
            "1. TUJUAN",
            "Pekeliling Am ini bertujuan menetapkan peraturan cuti rehat bagi pegawai Perkhidmatan Awam Negeri Sarawak.",
            "2. PEMAKAIAN",
            "2.1 Pekeliling ini terpakai kepada semua pegawai Perkhidmatan Awam Negeri Sarawak.",
            "3. MEMBAWA KE HADAPAN CUTI REHAT",
            "3.1 Cuti rehat yang tidak dihabiskan boleh dibawa ke tahun berikutnya tidak melebihi dua puluh (20) hari.",
            "3.2 Cuti rehat yang dibawa ke hadapan hendaklah direkodkan dalam Sistem Cuti Negeri sebelum 31 Januari tahun berikutnya dan diluluskan oleh Ketua Jabatan.",
            "3.3 Jumlah cuti rehat terkumpul bagi tujuan Gantian Cuti Rehat adalah tidak melebihi 150 hari.",
            "4. TARIKH KUAT KUASA",
            "Pekeliling Am ini berkuat kuasa mulai 1 Julai 2023.",
        ],
    },
    "SOP-SM-1-2024.pdf": {
        "issuer": "BAHAGIAN SUMBER MANUSIA, KEMENTERIAN CONTOH",
        "header": ["PROSEDUR OPERASI STANDARD SOP-SM 1/2024",
                   "PERMOHONAN CUTI REHAT MELALUI HRMIS"],
        "meta": ["Tarikh: 1 Mac 2024"],
        "body": [
            "1. TUJUAN",
            "Prosedur ini menerangkan langkah-langkah memohon cuti rehat melalui sistem HRMIS.",
            "2. SKOP",
            "Prosedur ini terpakai kepada semua pegawai di Kementerian Contoh.",
            "3. LANGKAH-LANGKAH",
            "3.1 Pegawai log masuk ke HRMIS dan memilih modul Cuti, kemudian Permohonan Cuti Rehat.",
            "3.2 Pegawai mengisi tarikh mula, tarikh tamat dan sebab cuti, dan mengemukakan permohonan sekurang-kurangnya tiga (3) hari bekerja sebelum tarikh cuti bermula.",
            "3.3 Penyelia menyemak permohonan dalam tempoh dua (2) hari bekerja.",
            "3.4 Ketua Jabatan meluluskan atau menolak permohonan, dan keputusan dimaklumkan kepada pegawai melalui e-mel HRMIS.",
            "3.5 Bagi cuti kecemasan, pegawai hendaklah memaklumkan penyelia melalui telefon pada hari yang sama dan mengemukakan permohonan dalam HRMIS dalam tempoh tiga (3) hari bekerja selepas kembali bertugas.",
            "4. TANGGUNGJAWAB",
            "Unit Sumber Manusia bertanggungjawab mengemas kini baki cuti rehat pegawai dalam HRMIS setiap bulan.",
        ],
    },
    "MMPJ-2-2026.pdf": {
        "issuer": "KEMENTERIAN CONTOH",
        "header": ["MINIT MESYUARAT PENGURUSAN JABATAN BIL. 2/2026"],
        "meta": ["Tarikh: 12 Mac 2026", "Masa: 9.00 pagi", "Tempat: Bilik Mesyuarat Utama"],
        "body": [
            "KEHADIRAN",
            "Ketua Setiausaha (Pengerusi), semua Ketua Bahagian dan Ketua Unit Sumber Manusia.",
            "PERKARA 1: PENGESAHAN MINIT MESYUARAT LALU",
            "Minit Mesyuarat Pengurusan Jabatan Bil. 1/2026 dibentangkan.",
            "KEPUTUSAN:",
            "Minit mesyuarat lalu disahkan tanpa pindaan.",
            "PERKARA 2: PERANCANGAN CUTI REHAT AKHIR TAHUN",
            "Unit Sumber Manusia melaporkan bahawa ramai pegawai mempunyai baki cuti rehat melebihi lima belas hari dan berisiko luput pada akhir tahun.",
            "KEPUTUSAN:",
            "Mesyuarat memutuskan semua bahagian hendaklah mengemukakan jadual cuti rehat suku tahun keempat kepada Unit Sumber Manusia selewat-lewatnya 30 September 2026. Mesyuarat juga memutuskan tidak lebih daripada 30 peratus pegawai sesuatu unit dibenarkan bercuti serentak dalam bulan Disember.",
            "TINDAKAN:",
            "Semua Ketua Bahagian dan Unit Sumber Manusia.",
            "PERKARA 3: PENGGUNAAN KENDERAAN JABATAN",
            "Unit Pentadbiran memaklumkan peningkatan tempahan kenderaan jabatan pada saat akhir.",
            "KEPUTUSAN:",
            "Mesyuarat memutuskan tempahan kenderaan jabatan hendaklah dibuat melalui sistem e-Tempahan sekurang-kurangnya dua (2) hari bekerja lebih awal.",
            "TINDAKAN:",
            "Unit Pentadbiran.",
        ],
    },
    "MJKK-1-2026.pdf": {
        "issuer": "KEMENTERIAN CONTOH",
        "header": ["MINIT MESYUARAT JAWATANKUASA KEWANGAN BIL. 1/2026"],
        "meta": ["Tarikh: 20 Januari 2026", "Masa: 2.30 petang", "Tempat: Bilik Mesyuarat Kewangan"],
        "body": [
            "KEHADIRAN",
            "Timbalan Ketua Setiausaha (Pengurusan) (Pengerusi), Ketua Unit Kewangan dan Ketua Unit Teknologi Maklumat.",
            "PERKARA 1: TUNTUTAN ELAUN PERJALANAN TERTUNGGAK",
            "Unit Kewangan melaporkan terdapat tuntutan elaun perjalanan yang dikemukakan melebihi tiga bulan selepas perjalanan.",
            "KEPUTUSAN:",
            "Mesyuarat memutuskan semua tuntutan elaun perjalanan hendaklah dikemukakan dalam tempoh tiga puluh (30) hari selepas perjalanan. Tuntutan lewat memerlukan justifikasi bertulis kepada Ketua Jabatan.",
            "TINDAKAN:",
            "Unit Kewangan dan semua Ketua Bahagian.",
            "PERKARA 2: PELAKSANAAN SISTEM e-TUNTUTAN",
            "Unit Teknologi Maklumat membentangkan status pembangunan sistem e-Tuntutan.",
            "KEPUTUSAN:",
            "Mesyuarat memutuskan semua tuntutan elaun dikemukakan melalui sistem e-Tuntutan mulai 1 Mac 2026.",
            "TINDAKAN:",
            "Unit Teknologi Maklumat dan Unit Kewangan.",
        ],
    },
    "PP-1-2025.pdf": {
        "issuer": JPA,
        "header": ["PEKELILING PERKHIDMATAN BILANGAN 1 TAHUN 2025", "KADAR ELAUN PERJALANAN DALAM NEGERI"],
        "meta": ["Rujukan: JPA(S)CONTOH/1/2025", "Tarikh: 2 Januari 2025"],
        "body": [
            "1. TUJUAN",
            "Pekeliling Perkhidmatan ini bertujuan menetapkan kadar elaun makan dan elaun lojing bagi perjalanan dalam negeri.",
            "2. PEMAKAIAN",
            "2.1 Pekeliling ini terpakai kepada semua pegawai Perkhidmatan Awam Persekutuan yang menjalankan tugas rasmi di luar ibu pejabat.",
            "3. ELAUN MAKAN",
            "3.1 Elaun makan bagi perjalanan dalam negeri adalah RM60 sehari bagi pegawai gred 41 hingga 48 dan RM50 sehari bagi pegawai gred 40 dan ke bawah.",
            "4. ELAUN LOJING",
            "4.1 Elaun lojing adalah RM120 semalam sekiranya pegawai tidak menginap di hotel.",
            "5. SYARAT TUNTUTAN",
            "5.1 Perjalanan melebihi tiga (3) hari memerlukan kelulusan awal Ketua Jabatan.",
            "5.2 Tuntutan hendaklah dikemukakan dalam tempoh tiga puluh (30) hari selepas perjalanan.",
            "6. TARIKH KUAT KUASA",
            "Pekeliling Perkhidmatan ini berkuat kuasa mulai 1 Februari 2025.",
        ],
    },
    "GP-1-2026-TERHAD.pdf": {
        "issuer": "UNIT KESELAMATAN, KEMENTERIAN CONTOH",
        "header": ["TERHAD", "GARIS PANDUAN BILANGAN 1 TAHUN 2026", "PENGENDALIAN FAIL TERHAD"],
        "meta": ["Tarikh: 2 Mac 2026"],
        "body": [
            "1. TUJUAN",
            "Garis panduan ini menerangkan cara pengendalian fail bertaraf Terhad di Kementerian Contoh.",
            "2. PENYIMPANAN",
            "2.1 Fail Terhad hendaklah disimpan dalam kabinet berkunci di Bilik Fail Terhad Aras 3 Blok Contoh.",
            "2.2 Kunci kabinet dipegang oleh Pegawai Keselamatan Kementerian sahaja.",
            "3. PERGERAKAN FAIL",
            "3.1 Setiap pergerakan fail Terhad hendaklah direkodkan dalam Buku Daftar Pergerakan Fail Terhad.",
            "3.2 Fail Terhad tidak boleh dibawa keluar dari premis Kementerian tanpa kebenaran bertulis Pegawai Keselamatan Kementerian.",
            "4. TARIKH KUAT KUASA",
            "Garis panduan ini berkuat kuasa mulai 2 Mac 2026.",
        ],
    },
}

INCOMING_DOCS: dict[str, dict] = {
    "PP-3-2026.pdf": {
        "issuer": JPA,
        "header": ["PEKELILING PERKHIDMATAN BILANGAN 3 TAHUN 2026",
                   "KADAR ELAUN PERJALANAN DALAM NEGERI (SEMAKAN 2026)"],
        "meta": ["Rujukan: JPA(S)CONTOH/3/2026", "Tarikh: 1 Oktober 2026"],
        "body": [
            "1. TUJUAN",
            "Pekeliling Perkhidmatan ini bertujuan menetapkan kadar baharu elaun makan dan elaun lojing bagi perjalanan dalam negeri.",
            "2. PEMAKAIAN",
            "2.1 Pekeliling ini terpakai kepada semua pegawai Perkhidmatan Awam Persekutuan yang menjalankan tugas rasmi di luar ibu pejabat.",
            "3. ELAUN MAKAN",
            "3.1 Elaun makan bagi perjalanan dalam negeri adalah RM75 sehari bagi pegawai gred 41 hingga 48 dan RM60 sehari bagi pegawai gred 40 dan ke bawah.",
            "4. ELAUN LOJING",
            "4.1 Elaun lojing adalah RM150 semalam sekiranya pegawai tidak menginap di hotel.",
            "5. SYARAT TUNTUTAN",
            "5.1 Perjalanan melebihi tiga (3) hari memerlukan kelulusan awal Ketua Jabatan.",
            "5.2 Tuntutan hendaklah dikemukakan melalui sistem e-Tuntutan dalam tempoh tiga puluh (30) hari selepas perjalanan.",
            "6. TARIKH KUAT KUASA",
            "Pekeliling Perkhidmatan ini berkuat kuasa mulai 1 Oktober 2026.",
            "7. PEMBATALAN",
            "Pekeliling Perkhidmatan Bilangan 1 Tahun 2025 adalah dibatalkan dan digantikan dengan Pekeliling ini.",
        ],
    },
}

PAGE_W, PAGE_H = pymupdf.paper_size("a4")
MARGIN_X, TOP, BOTTOM = 72, 72, PAGE_H - 72
FONT, BOLD = "helv", "hebo"


def _wrap(text: str, width: float, size: float, font: str) -> list[str]:
    words, lines, line = text.split(), [], ""
    for w in words:
        trial = f"{line} {w}".strip()
        if pymupdf.get_text_length(trial, fontname=font, fontsize=size) <= width:
            line = trial
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def _watermark(page: pymupdf.Page) -> None:
    centre = pymupdf.Point(PAGE_W / 2, PAGE_H / 2)
    size = 40
    length = pymupdf.get_text_length(WATERMARK, fontname=BOLD, fontsize=size)
    start = pymupdf.Point(centre.x - length / 2, centre.y)
    page.insert_text(start, WATERMARK, fontname=BOLD, fontsize=size, color=(0.82, 0.82, 0.82),
                     morph=(centre, pymupdf.Matrix(-35)), overlay=False)
    page.insert_text(pymupdf.Point(MARGIN_X, PAGE_H - 36), WATERMARK + " - dokumen sintetik untuk demonstrasi",
                     fontname=FONT, fontsize=7, color=(0.45, 0.45, 0.45))


def render(path: Path, spec: dict) -> None:
    doc = pymupdf.open()
    state = {"page": None, "y": TOP, "n": 0}

    def new_page() -> None:
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        _watermark(page)
        state.update(page=page, y=TOP, n=state["n"] + 1)

    def line(text: str, size: float = 10.5, font: str = FONT, center: bool = False, gap: float = 4) -> None:
        for chunk in _wrap(text, PAGE_W - 2 * MARGIN_X, size, font):
            if state["page"] is None or state["y"] + size > BOTTOM:
                new_page()
            x = MARGIN_X
            if center:
                x = (PAGE_W - pymupdf.get_text_length(chunk, fontname=font, fontsize=size)) / 2
            state["page"].insert_text(pymupdf.Point(x, state["y"]), chunk, fontname=font, fontsize=size)
            state["y"] += size + 3
        state["y"] += gap

    new_page()
    line(spec["issuer"], size=9, center=True)
    for h in spec["header"]:
        line(h, size=11.5, font=BOLD, center=True, gap=2)
    state["y"] += 8
    for m in spec["meta"]:
        line(m, size=9.5, gap=1)
    state["y"] += 10
    for para in spec["body"]:
        is_heading = para.isupper() or para.rstrip(":").isupper()
        # Push section headings to a fresh page when they would land at the very bottom.
        if is_heading and state["y"] > BOTTOM - 60:
            new_page()
        line(para, font=BOLD if is_heading else FONT, gap=6 if not is_heading else 3)
    doc.set_metadata({"title": " ".join(spec["header"]), "subject": WATERMARK, "creator": "make_synthetic_docs.py"})
    doc.save(path, garbage=3, deflate=True)
    doc.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="regenerate even if data/raw is not empty")
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    INCOMING.mkdir(parents=True, exist_ok=True)
    existing = [p for p in RAW.iterdir() if p.suffix.lower() == ".pdf"]
    if existing and not args.force:
        print(f"data/raw already has {len(existing)} PDF(s); use --force to regenerate the synthetic set.")
        return 0
    for name, spec in DOCS.items():
        render(RAW / name, spec)
        print("wrote", (RAW / name).relative_to(ROOT))
    for name, spec in INCOMING_DOCS.items():
        render(INCOMING / name, spec)
        print("wrote", (INCOMING / name).relative_to(ROOT), "(held back for pack v2)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
