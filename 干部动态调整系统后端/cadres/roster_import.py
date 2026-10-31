"""新版花名册 Excel 导入映射（兼容旧版带 * 列名）。"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd


ANNUAL_YEARS = [str(year) for year in range(2010, 2017)]


def normalize_header(value: Any) -> str:
    text = '' if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)
    text = text.replace('\n', '').replace('\r', '').replace(' ', '').replace('*', '')
    text = text.replace('（未核对原件）', '')
    return text.strip()


def build_column_map(columns) -> dict[str, str]:
    """把 Excel 列名映射为规范化中文名；重复列按出现顺序加后缀。"""
    seen: dict[str, int] = {}
    mapping: dict[str, str] = {}
    for col in columns:
        raw = str(col)
        base = normalize_header(col)
        if not base or base.startswith('Unnamed'):
            continue
        count = seen.get(base, 0)
        seen[base] = count + 1
        key = base if count == 0 else f'{base}.{count}'
        mapping[key] = raw
    return mapping


def _cell(row: pd.Series, column_map: dict[str, str], *candidates: str, default=None):
    for name in candidates:
        raw = column_map.get(name)
        if raw is None or raw not in row.index:
            continue
        value = row.get(raw)
        if pd.isna(value):
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return default


def _text(row, column_map, *candidates, default='') -> str:
    value = _cell(row, column_map, *candidates, default=None)
    if value is None:
        return default
    text = str(value).strip()
    return default if text.lower() == 'nan' else text


def _int(row, column_map, *candidates):
    value = _cell(row, column_map, *candidates, default=None)
    if value is None or value == '':
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _boolish(row, column_map, *candidates) -> bool:
    value = _text(row, column_map, *candidates, default='')
    return value in {'1', 'true', 'True', '是', 'Y', 'y'}


def map_gender(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 'U'
    text = str(value).strip()
    if text == '男':
        return 'M'
    if text == '女':
        return 'F'
    return 'U'


def parse_date(value):
    if value is None or value == '' or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        if isinstance(value, str):
            text = value.strip()
            for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%Y%m%d'):
                try:
                    from datetime import datetime
                    return datetime.strptime(text, fmt).date()
                except ValueError:
                    continue
            return pd.to_datetime(text).date()
        return pd.to_datetime(value).date()
    except Exception:
        return None


def normalize_id_card(value: str) -> str | None:
    text = re.sub(r'\s+', '', value or '')
    if not text or text.lower() == 'nan':
        return None
    if len(text) > 18:
        text = text[:18]
    return text or None


def normalize_police_number(value: str) -> str | None:
    text = re.sub(r'\s+', '', value or '')
    if not text or text.lower() == 'nan':
        return None
    return text[:20]


def row_to_roster_data(row: pd.Series, column_map: dict[str, str], fallback_serial: int) -> dict:
    """将一行 Excel 转为 PersonnelRoster 字段字典。"""
    annual = {}
    for year in ANNUAL_YEARS:
        text = _text(row, column_map, f'{year}年', year)
        if text:
            annual[year] = text

    gender_raw = _cell(row, column_map, '性别', '性别*', default=None)
    # 新模板偶发把年龄写进性别列：若不是男女，则当作未知，年龄另取
    if gender_raw is not None and str(gender_raw).strip() not in {'男', '女', 'M', 'F'}:
        gender = 'U'
    else:
        gender = map_gender(gender_raw)

    serial = _int(row, column_map, '序号', '序号*')
    if serial is None:
        serial = fallback_serial

    id_card = normalize_id_card(_text(row, column_map, '身份证号', '身份证号*'))
    police_number = normalize_police_number(_text(row, column_map, '警号', '警号*'))

    return {
        'serial_number': serial,
        'name': _text(row, column_map, '姓名', '姓名*'),
        'department': _text(row, column_map, '部门', '部门*'),
        'gender': gender,
        'age': _int(row, column_map, '年龄', '年龄*'),
        'birth_date': parse_date(_cell(row, column_map, '出生年月', '出生年月*')),
        'ethnicity': _text(row, column_map, '民族', '民族*'),
        'native_place': _text(row, column_map, '籍贯', '籍贯*'),
        'household_registration': _text(row, column_map, '户籍所在地', '户籍所在地（未核对原件）'),
        'working_years': _int(row, column_map, '工龄'),
        'join_work_date': parse_date(_cell(row, column_map, '参加工作时间', '参加工作时间*')),
        'join_prison_date': parse_date(_cell(row, column_map, '参加监狱工作时间', '参加监狱工作时间*')),
        'continuous_service_date': parse_date(_cell(row, column_map, '连续工龄计算时间', '连续工龄计算时间*')),
        'has_2years_grassroots': _text(row, column_map, '是否有2年基层工作经历'),
        'political_status': _text(row, column_map, '政治面貌', '政治面貌*'),
        'join_party_date': parse_date(_cell(row, column_map, '入党时间', '入党时间*')),
        'position': _text(row, column_map, '职务', '职务*'),
        'promotion_category': _text(row, column_map, '晋升四高及以上序列分类'),
        'position_category': _text(row, column_map, '职务类别'),
        'current_position_years': _text(row, column_map, '任职年限', '任现职年限'),
        'current_position_date': parse_date(_cell(row, column_map, '任现职时间', '任现职务时间')),
        'position_level': _text(row, column_map, '级别', '职务级别'),
        'position_rank': _text(row, column_map, '职务层次'),
        'same_level_leadership_years': _text(row, column_map, '任同级领导职务年限'),
        'same_level_leadership_date': parse_date(_cell(row, column_map, '任同级领导职务时间')),
        'same_level_rank_years': _text(row, column_map, '任同级领导职务层次时间年限'),
        'same_level_rank_date': parse_date(_cell(row, column_map, '任同级领导职务层次时间')),
        'current_rank_years': _text(row, column_map, '任级年限', '任现职级年限', '任现职级年限（即任现警员职级年限）'),
        'current_rank_date': parse_date(_cell(row, column_map, '任级时间', '任现职级时间', '任现职级时间（即任现警员职级时间）')),
        'calculation_start_date': parse_date(_cell(row, column_map, '量化计分起算时间')),
        'police_rank': _text(row, column_map, '现警员职级', '现警员职级*'),
        'police_rank_start_date': parse_date(_cell(row, column_map, '任现警员职级起算时间')),
        'first_set_rank': _text(row, column_map, '首套警员职级'),
        'first_set_rank_date': parse_date(_cell(row, column_map, '首套警员职级起算时间')),
        'first_promote_rank': _text(row, column_map, '首晋警员职级'),
        'first_promote_rank_date': parse_date(_cell(row, column_map, '首晋警员职级起算时间')),
        'work_charge': _text(row, column_map, '分管工作'),
        'fulltime_education': _text(row, column_map, '全日制教育学历', '全日制教育学历*'),
        'fulltime_school': _text(row, column_map, '毕业院校', '毕业院校*'),
        'fulltime_major': _text(row, column_map, '专业', '专业*'),
        'fulltime_degree': _text(row, column_map, '学位', '学位*'),
        'fulltime_start_date': parse_date(_cell(row, column_map, '入学时间')),
        'fulltime_graduate_date': parse_date(_cell(row, column_map, '毕业时间')),
        'inservice_education': _text(row, column_map, '在职学历', '在职学历*'),
        'inservice_school': _text(row, column_map, '毕业院校.1', '毕业院校*.1'),
        'inservice_form': _text(row, column_map, '学习形式'),
        'inservice_major': _text(row, column_map, '专业.1', '专业*.1'),
        'inservice_degree': _text(row, column_map, '学位.1', '学位*.1'),
        'inservice_start_date': parse_date(_cell(row, column_map, '入学时间.1')),
        'inservice_graduate_date': parse_date(_cell(row, column_map, '毕业时间.1')),
        'police_title': _text(row, column_map, '警衔', '警衔（已更新至20250526）', '警衔*（已更新至20250526）'),
        'police_number': police_number,
        'profession_name': _text(row, column_map, '专业资格名称', '专业资格/名称'),
        'profession_level': _text(row, column_map, '专业资格级别'),
        'technical_title': _text(row, column_map, '专业技术职务'),
        'counseling_cert_level': _text(row, column_map, '心理咨询证书级别'),
        'english_level': _text(row, column_map, '英语专业'),
        'annual_assessments': annual,
        'remark': _text(row, column_map, '备注'),
        'quarterly_remark': _text(row, column_map, '季度报表备注'),
        'dept_work_years': _text(row, column_map, '在本部门工作年限'),
        'dept_work_date': parse_date(_cell(row, column_map, '本部门工作时间', '本部门工作时间*')),
        'unit_work_years': _text(row, column_map, '在本单位年限'),
        'enter_unit_date': parse_date(_cell(row, column_map, '进入本单位时间', '进入本单位时间*')),
        'enter_unit_form': _text(row, column_map, '进入单位形式', '进入本单位形式'),
        'identity_source': _text(row, column_map, '身份来源'),
        'is_clerk': _text(row, column_map, '是否干事'),
        'clerk_date': parse_date(_cell(row, column_map, '任干事时间')),
        'military_experience': _text(row, column_map, '军转干/部队经历', '军转干/部队经历*'),
        'highest_education': _text(row, column_map, '最高学历', '最高学历*'),
        'highest_school': _text(row, column_map, '最高学历毕业院校', '最高学历毕业院校*'),
        'education_level': _text(row, column_map, '学历', '学历*'),
        'highest_major': _text(row, column_map, '专业.2', '最高学历专业', '最高学历专业*'),
        'highest_degree': _text(row, column_map, '最高学位', '最高学位*'),
        'major_category': _text(row, column_map, '最高学历专业类别'),
        'id_card': id_card,
        'id_card_inconsistent': _boolish(row, column_map, '出生年月与身份证信息不一致'),
        'phone': _text(row, column_map, '电话', '电话*'),
        'cert_level': _text(row, column_map, '证书级别'),
    }


def required_columns_present(column_map: dict[str, str]) -> list[str]:
    required = ['姓名', '部门']
    missing = []
    for name in required:
        if name not in column_map and f'{name}*' not in column_map:
            # build_column_map already strips *
            if name not in column_map:
                missing.append(name)
    return missing
