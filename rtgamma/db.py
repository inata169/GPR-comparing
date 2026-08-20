import json
import logging
import sqlite3
from typing import Any, Dict

from .report import sanitize_for_json


def init_db(db_path: str):
    """Initialize the SQLite database schema if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gamma_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ref TEXT,
            eval TEXT,
            profile TEXT,
            mode TEXT,
            plane TEXT,
            plane_index INTEGER,
            dd_percent REAL,
            dta_mm REAL,
            cutoff_percent REAL,
            gamma_type TEXT,
            norm TEXT,
            gamma_engine TEXT,
            gamma_engine_version TEXT,
            report_schema_version INTEGER,
            provenance_json TEXT,
            pass_rate_percent REAL,
            best_shift_x REAL,
            best_shift_y REAL,
            best_shift_z REAL,
            best_shift_mag_mm REAL,
            absolute_geometry_only BOOLEAN,
            same_for_uid BOOLEAN,
            warnings TEXT,
            gamma_mean REAL,
            gamma_median REAL,
            gamma_max REAL,
            cutoff_qualified_points INTEGER,
            common_spatial_points INTEGER,
            spatially_excluded_points INTEGER,
            evaluated_points INTEGER,
            per_structure_json TEXT
        )
    ''')
    existing_columns = {
        row[1] for row in cursor.execute('PRAGMA table_info(gamma_results)')
    }
    migrations = {
        'gamma_engine': 'TEXT',
        'gamma_engine_version': 'TEXT',
        'report_schema_version': 'INTEGER',
        'provenance_json': 'TEXT',
        'cutoff_qualified_points': 'INTEGER',
        'common_spatial_points': 'INTEGER',
        'spatially_excluded_points': 'INTEGER',
        'evaluated_points': 'INTEGER',
    }
    for column, column_type in migrations.items():
        if column not in existing_columns:
            cursor.execute(
                f'ALTER TABLE gamma_results ADD COLUMN {column} {column_type}'
            )
    conn.commit()
    conn.close()

def save_summary_db(db_path: str, summary: Dict[str, Any]):
    """Save the gamma analysis summary to the SQLite database."""
    try:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Extract shift components safely
        shift = summary.get('best_shift_mm', (0.0, 0.0, 0.0))
        sx, sy, sz = 0.0, 0.0, 0.0
        if isinstance(shift, (tuple, list)) and len(shift) >= 3:
            sx, sy, sz = float(shift[0]), float(shift[1]), float(shift[2])

        # Serialize per_structure to JSON string if it exists
        per_struct_json = None
        if 'per_structure' in summary and summary['per_structure']:
            # Handle NaN values for JSON serialization
            def sanitize_nans(obj):
                import math
                if isinstance(obj, float) and math.isnan(obj):
                    return None
                if isinstance(obj, list):
                    return [sanitize_nans(v) for v in obj]
                if isinstance(obj, dict):
                    return {k: sanitize_nans(v) for k, v in obj.items()}
                return obj
            per_struct_json = json.dumps(sanitize_nans(summary['per_structure']))

        cursor.execute('''
            INSERT INTO gamma_results (
                ref, eval, profile, mode, plane, plane_index,
                dd_percent, dta_mm, cutoff_percent, gamma_type, norm,
                gamma_engine, gamma_engine_version,
                report_schema_version, provenance_json,
                pass_rate_percent, best_shift_x, best_shift_y, best_shift_z,
                best_shift_mag_mm, absolute_geometry_only, same_for_uid,
                warnings, gamma_mean, gamma_median, gamma_max,
                cutoff_qualified_points, common_spatial_points,
                spatially_excluded_points, evaluated_points,
                per_structure_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            summary.get('ref'),
            summary.get('eval'),
            summary.get('profile'),
            summary.get('mode'),
            summary.get('plane'),
            summary.get('plane_index'),
            summary.get('dd_percent'),
            summary.get('dta_mm'),
            summary.get('cutoff_percent'),
            summary.get('gamma_type'),
            summary.get('norm'),
            summary.get('gamma_engine'),
            summary.get('gamma_engine_version'),
            summary.get('report_schema_version'),
            json.dumps(
                sanitize_for_json(summary.get('provenance')),
                ensure_ascii=False,
                allow_nan=False,
            ),
            summary.get('pass_rate_percent'),
            sx, sy, sz,
            summary.get('best_shift_mag_mm'),
            summary.get('absolute_geometry_only'),
            summary.get('same_for_uid'),
            summary.get('warnings'),
            summary.get('gamma_mean'),
            summary.get('gamma_median'),
            summary.get('gamma_max'),
            summary.get('cutoff_qualified_points'),
            summary.get('common_spatial_points'),
            summary.get('spatially_excluded_points'),
            summary.get('evaluated_points'),
            per_struct_json
        ))
        
        conn.commit()
        conn.close()
        logging.info(f"Successfully saved results to database: {db_path}")
    except Exception as e:
        logging.error(f"Failed to save results to database {db_path}: {e}")
