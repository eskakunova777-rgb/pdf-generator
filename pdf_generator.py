import csv
import json
import os
import platform
import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import pandas as pd
from weasyprint import HTML

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"


def init():
    for d in (DATA_DIR, TEMPLATES_DIR, OUTPUT_DIR):
        d.mkdir(parents=True, exist_ok=True)


def list_data_files():
    files = list(DATA_DIR.glob("*.csv")) + list(DATA_DIR.glob("*.json"))
    return sorted(files)


def list_templates():
    return sorted(TEMPLATES_DIR.glob("*.html"))


def load_records(path):
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, dtype=str)
        return df.to_dict(orient="records")
    if path.suffix.lower() == ".json":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else [data]
    raise ValueError(f"Неподдерживаемый формат файла: {path.suffix}")


def compute_total(record):
    try:
        price = float(record.get("price", 0))
        qty = float(record.get("qty", 1))
        return f"{price * qty:,.2f}".replace(",", " ").rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return record.get("total", "")


def render_html(template_path, record):
    html = template_path.read_text(encoding="utf-8")
    data = dict(record)
    data.setdefault("total", compute_total(record))
    for key, value in data.items():
        html = html.replace("{{ " + key + " }}", str(value))
    return html


def open_pdf(path):
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", str(path)], check=False)
        elif system == "Windows":
            os.startfile(str(path))  # noqa: attribute exists on Windows only
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception as e:
        print(f"Не удалось автоматически открыть файл: {e}")
        print(f"Открой вручную: {path}")


def choose_from_list(items, label_fn, prompt):
    for i, item in enumerate(items, start=1):
        print(f"  {i}. {label_fn(item)}")
    while True:
        choice = input(prompt).strip()
        if choice.isdigit() and 1 <= int(choice) <= len(items):
            return items[int(choice) - 1]
        print("Некорректный ввод, попробуй ещё раз.")


def run():
    init()

    data_files = list_data_files()
    templates = list_templates()

    if not data_files:
        print(f"Нет файлов с данными в {DATA_DIR}. Добавь .csv или .json и запусти снова.")
        sys.exit(1)
    if not templates:
        print(f"Нет HTML-шаблонов в {TEMPLATES_DIR}. Добавь шаблон и запусти снова.")
        sys.exit(1)

    print("=== PDF-генератор чеков ===\n")

    print("Доступные файлы с данными:")
    data_file = choose_from_list(data_files, lambda p: p.name, "\nВыбери файл (номер): ")

    print("\nДоступные шаблоны:")
    template = choose_from_list(templates, lambda p: p.name, "\nВыбери шаблон (номер): ")

    records = load_records(data_file)
    if not records:
        print("В выбранном файле нет записей.")
        sys.exit(1)

    has_invoice_id = "invoice_id" in records[0]

    print("\nДоступные записи:")
    if has_invoice_id:
        label_fn = lambda r: f"invoice_id {r['invoice_id']} — {r.get('customer_name', '')} — {r.get('product', '')}"
    else:
        label_fn = lambda r: f"{r.get('product', '')} — {r.get('qty', '')} шт."

    record = choose_from_list(records, label_fn, "\nВыбери запись (номер): ")

    html_content = render_html(template, record)

    file_tag = record.get("invoice_id") or record.get("product", "document")
    safe_tag = str(file_tag).replace(" ", "_").replace("/", "_")
    output_path = OUTPUT_DIR / f"{safe_tag}.pdf"

    HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf(str(output_path))
    print(f"\nГотово! PDF сохранён: {output_path}")

    open_pdf(output_path)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
