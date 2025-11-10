#!/usr/bin/env python3
"""validate_csv.py

Valida um arquivo CSV com as colunas esperadas:
 - name, address, phone, site, description

Checagens realizadas:
 - arquivo existe e pode ser aberto em UTF-8 (tenta fallback latin-1)
 - cabeçalho contém as colunas esperadas (erros se faltar)
 - nenhuma célula contém quebras de linha (\n ou \r)
 - formato básico de telefone (dígitos e símbolos aceitáveis)
 - formato básico de URL para o campo site
 - checa duplicatas por (name, address)

Uso:
    python validate_csv.py --file path/to/results.csv

Retorna código 0 se nenhum erro crítico (falta de colunas) for encontrado; imprime relatório no stdout.
"""

import argparse
import csv
import os
import re
from urllib.parse import urlparse

EXPECTED_FIELDS = ['name', 'address', 'phone', 'site', 'description']
PHONE_RE = re.compile(r'^[\d\+\-\(\)\s\.]{6,}$')  # permissivo


def try_open(path):
    """Tenta abrir o arquivo em utf-8, com fallback para latin-1. Retorna (fileobj, encoding) ou raise."""
    try:
        f = open(path, 'r', encoding='utf-8', newline='')
        # try reading a small chunk to force decode
        _ = f.read(0)
        f.seek(0)
        return f, 'utf-8'
    except UnicodeDecodeError:
        try:
            f = open(path, 'r', encoding='latin-1', newline='')
            return f, 'latin-1'
        except Exception as e:
            raise


def is_valid_url(u):
    if not u:
        return True
    parsed = urlparse(u if '://' in u else ('http://' + u))
    return bool(parsed.netloc and '.' in parsed.netloc)


def validate_csv(path):
    report = {
        'file': path,
        'encoding': None,
        'rows': 0,
        'missing_columns': [],
        'extra_columns': [],
        'rows_with_newlines': [],
        'invalid_phones': [],
        'invalid_sites': [],
        'duplicates': [],
        'errors': []
    }

    if not os.path.exists(path):
        report['errors'].append(f'File not found: {path}')
        return report

    try:
        f, enc = try_open(path)
        report['encoding'] = enc
    except Exception as e:
        report['errors'].append(f'Could not open file: {e}')
        return report

    with f:
        # Try to detect delimiter (comma or semicolon) using Sniffer
        try:
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=[',',';','\t','|'])
                delimiter = dialect.delimiter
            except Exception:
                # fallback to comma
                delimiter = ','
            reader = csv.DictReader(f, delimiter=delimiter)
        except Exception as e:
            report['errors'].append(f'CSV parse error: {e}')
            return report

        if reader.fieldnames is None:
            report['errors'].append('CSV has no header')
            return report

        # normalize fieldnames and remove BOM if present
        fieldnames_norm = [fn.strip().lstrip('\ufeff') for fn in reader.fieldnames]
        missing = [c for c in EXPECTED_FIELDS if c not in fieldnames_norm]
        extra = [c for c in fieldnames_norm if c not in EXPECTED_FIELDS]
        report['missing_columns'] = missing
        report['extra_columns'] = extra

        if missing:
            report['errors'].append(f'Missing columns: {missing}')
            # We continue to gather more info but this is considered critical

        seen = {}
        row_index = 1  # consider header at 1, data starts at 2
        for row in reader:
            row_index += 1
            report['rows'] += 1
            # check newline chars in cells
            for k, v in row.items():
                if v and ('\n' in v or '\r' in v):
                    report['rows_with_newlines'].append({'row': row_index, 'column': k, 'value_sample': v[:100]})
            # phone validation
            phone = (row.get('phone') or '').strip()
            if phone and not PHONE_RE.match(phone):
                report['invalid_phones'].append({'row': row_index, 'phone': phone})
            # site validation
            site = (row.get('site') or '').strip()
            if site and not is_valid_url(site):
                report['invalid_sites'].append({'row': row_index, 'site': site})
            # duplicates by (name, address)
            name = (row.get('name') or '').strip().lower()
            address = (row.get('address') or '').strip().lower()
            key = (name, address)
            if key in seen:
                report['duplicates'].append({'first_row': seen[key], 'dup_row': row_index, 'name': name, 'address': address})
            else:
                seen[key] = row_index

    return report


def print_report(r):
    print('CSV Validation Report')
    print('File:', r['file'])
    print('Encoding detected:', r.get('encoding'))
    if r.get('errors'):
        print('\nErrors:')
        for e in r['errors']:
            print(' -', e)
    print('\nSummary:')
    print(' - Rows:', r.get('rows'))
    print(' - Missing columns:', r.get('missing_columns'))
    print(' - Extra columns:', r.get('extra_columns'))
    print(' - Rows with newline chars in cells:', len(r.get('rows_with_newlines', [])))
    print(' - Invalid phones:', len(r.get('invalid_phones', [])))
    print(' - Invalid sites:', len(r.get('invalid_sites', [])))
    print(' - Duplicates:', len(r.get('duplicates', [])))

    if r.get('rows_with_newlines'):
        print('\nSample rows with newlines (up to 5):')
        for item in r['rows_with_newlines'][:5]:
            print('  ', item)

    if r.get('invalid_phones'):
        print('\nSample invalid phones (up to 5):')
        for item in r['invalid_phones'][:5]:
            print('  ', item)

    if r.get('invalid_sites'):
        print('\nSample invalid sites (up to 5):')
        for item in r['invalid_sites'][:5]:
            print('  ', item)

    if r.get('duplicates'):
        print('\nDuplicate entries (up to 5):')
        for item in r['duplicates'][:5]:
            print('  ', item)

    # Final verdict
    critical = bool(r.get('missing_columns') or r.get('errors'))
    if critical:
        print('\nVERDICT: FAIL (critical issues found)')
    else:
        print('\nVERDICT: PASS (no critical issues)')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Validate results CSV produced by scraping.py')
    p.add_argument('--file', '-f', help='Path to CSV file', default=os.path.join(os.path.dirname(__file__), 'results.csv'))
    args = p.parse_args()

    report = validate_csv(args.file)
    print_report(report)

    # exit code: 0 if no critical issues (missing columns or file errors), 2 otherwise
    if report.get('errors') or report.get('missing_columns'):
        raise SystemExit(2)
    else:
        raise SystemExit(0)
