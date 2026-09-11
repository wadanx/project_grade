
import openpyxl as xl
import json
import re
import pandas as pd

from dataclasses import dataclass, field
from preprocessor import calc_grades, process
from pathlib import Path

class Parser:
    def __init__(self,):
        self.sheet = None
        self.ctx={
            'subject_name_col': None,
            'credit_hours_col': None,
            'points_col': None,
            'score_col': None,
            'grade_col': None,
            'level': 0,
            'semester': 0,
        }


    def parse(self, sheet=None):
        if sheet is not None:
            self.sheet = sheet
            self.update_ctx()
            max_row = sheet.max_row
            max_col = sheet.max_column
            name = self.parse_name()

            subjects = []
            for row in range(1, max_row + 1):
                for col in range(1, max_col + 1):
                    cell_value = self.sheet.cell(row=row, column=col).value
                    if isinstance(cell_value, str) :
                        if cell_value == 'م':
                            row = row + 1
                            while self.sheet.cell(row=row, column=col).value:
                                if (self.sheet.cell(row=row, column=self.ctx.get('grade_col')).value == 'اعتذار'):
                                    print('execuse detected')
                                    row = row + 1
                                    continue
                                subjects.append(self.read_subject(row))
                                row = row + 1

                        else:
                            level, semester = self.get_level_semester(cell_value)
                            if level != -1:
                                self.ctx['level'], self.ctx['semester'] = level, semester

            return name, pd.DataFrame(subjects)
        return None
    
    def get_level_semester(self, cell_value: str) -> int:
        if cell_value == 'المستوى/الفصل :المستوى الاول/الفصل الدراسي الأول':
            return 1, 1
        elif cell_value == 'المستوى/الفصل :المستوى الاول/الفصل الدراسي الثاني':
            return 1, 2
        elif cell_value == 'المستوى/الفصل :المستوى الاول/الفصل الصيفي':
            return 1, 3
        elif cell_value == 'المستوى/الفصل :المستوى الثاني/الفصل الدراسي الأول':
            return 2, 1
        elif cell_value == 'المستوى/الفصل :المستوى الثاني/الفصل الدراسي الثاني':
            return 2, 2
        elif cell_value == 'المستوى/الفصل :المستوى الثاني/الفصل الصيفي':
            return 2, 3
        elif cell_value == 'المستوى/الفصل :المستوى الثالث/الفصل الدراسي الأول':
            return 3, 1
        elif cell_value == 'المستوى/الفصل :المستوى الثالث/الفصل الدراسي الثاني':
            return 3, 2
        elif cell_value == 'المستوى/الفصل :المستوى الثالث/الفصل الصيفي':
            return 3, 3
        elif cell_value == 'المستوى/الفصل :المستوى الرابع/الفصل الدراسي الأول':
            return 4, 1
        elif cell_value == 'المستوى/الفصل :المستوى الرابع/الفصل الدراسي الثاني':
            return 4, 2
        elif cell_value == 'المستوى/الفصل :المستوى الرابع/الفصل الصيفي':
            return 4, 3
        else:
            return -1, -1


    def read_subject(self, row_index: int):
        return  {
            
            'name': self.sheet.cell(row=row_index, column=self.ctx['subject_name_col']).value,
            'credit_hours': float(self.sheet.cell(row=row_index, column=self.ctx['credit_hours_col']).value),
            'points': float(self.sheet.cell(row=row_index, column=self.ctx['points_col']).value) if isinstance(self.sheet.cell(row=row_index, column=self.ctx['points_col']).value, (int, float)) else 0.0,
            'score': float(self.sheet.cell(row=row_index, column=self.ctx['score_col']).value) if isinstance(self.sheet.cell(row=row_index, column=self.ctx['score_col']).value, (int, float)) else 0.0,
            'level': self.ctx['level'],
            'semester': self.ctx['semester'],
        }

    def parse_name(self,):
        for row in range(1, self.sheet.max_row + 1):
            for col in range(1, self.sheet.max_column + 1):
                cell_value = self.sheet.cell(row=row, column=col).value
                if isinstance(cell_value, str):
                    match = re.search(r"أسم الطالب\s*:\s*(.+)", cell_value)
                    if match:
                        return match.group(1)
        return None
    
    def update_ctx(self,):
        self.ctx['level'] = 0
        self.ctx['semester'] = 0
        for row in range(1, self.sheet.max_row + 1):
            for col in range(1, self.sheet.max_column + 1):
                cell_value = self.sheet.cell(row=row, column=col).value
                if isinstance(cell_value, str):
                    if cell_value == 'م':
                        self.ctx['m_col'] = col
                    elif cell_value == 'اسم المقرر':
                        self.ctx['subject_name_col'] = col
                    elif cell_value == 'ساعات':
                        self.ctx['credit_hours_col'] = col
                    elif cell_value == 'نقاط':
                        self.ctx['points_col'] = col
                    elif cell_value == 'درجة':
                        self.ctx['score_col'] = col
                    elif cell_value == 'تقدير':
                        self.ctx['grade_col'] = col


LEVEL_NAMES_AR = {1: 'الاول', 2: 'الثاني', 3: 'الثالث', 4: 'الرابع'}

OVERALL_HEADERS = [
    'المجموع الكلي للتراكمي',
    'عدد الساعات',
    'المعدل التراكمي للطالب',
    'المجموعات بالدرجات',
    'التقدير الكلي',
    'التقدير الوصفي الكلي',
]

HONOR_HEADER = 'مرتبة الشرف'


def build_result_columns(n_columns: int) -> list[str]:
    """Column labels for parse_wb's output rows:

    [name] + 6 metrics per level (repeated per level) + 6 overall totals + [honor flag].
    """
    columns = ['اسم الطالب']
    remaining = n_columns - 1 - len(OVERALL_HEADERS) - 1  # minus name, overall block, honor
    n_levels = max(remaining // 6, 0)
    for level in range(1, n_levels + 1):
        level_name = LEVEL_NAMES_AR.get(level, str(level))
        columns.extend([
            'مجموع التراكمي',
            'عدد الساعات',
            f'تراكمي المستوى {level_name}',
            'التقدير',
            'التقدير الوصفي',
            'المجوع بالدرجات',
        ])
    columns.extend(OVERALL_HEADERS)
    while len(columns) < n_columns - 1:
        columns.append(f'عمود {len(columns)}')
    columns.append(HONOR_HEADER)
    return columns[:n_columns]


def parse_wb(wb_path: str, reg, write_intermediate: bool = True) -> list:
    workbook = xl.load_workbook(wb_path, data_only=True)
    rows = []
    parser = Parser()

    if write_intermediate:
        intermediate_dir = Path('intermediate') / Path(wb_path).stem
        intermediate_dir.mkdir(parents=True, exist_ok=True)

    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        name, df = parser.parse(sheet)
        df = process(df)

        if write_intermediate:
            df.sort_values(['level', 'semester'], ascending=True).to_excel(intermediate_dir / f'{name}.xlsx')

        data = calc_grades(df, reg.points_to_grade)

        rows.append([name] + list(data))

    return rows
