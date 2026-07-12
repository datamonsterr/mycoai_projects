import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.sync_research_yolo_to_product import run_sync


def test_sync_research_yolo_to_product_dry_run_reports_counts(tmp_path: Path) -> None:
    features_path = tmp_path / 'features.json'
    segment_path = (
        tmp_path
        / 'Dataset'
        / 'original_prepared'
        / 'species-a'
        / 'strain-a'
        / 'MEA'
        / 'ob'
        / 'segments_yolo'
        / 'segment_0.jpg'
    )
    segment_path.parent.mkdir(parents=True)
    segment_path.write_bytes(b'jpg')
    features_path.write_text(json.dumps([
        {
            'id': 'seg-1',
            'segment_path': str(segment_path),
            'metadata': {
                'instance_info': {
                    'species': 'Species A',
                    'strain': 'Strain A',
                    'environment': 'MEA',
                    'angle': 'ob',
                },
                'segmentation': {'method': 'yolo'},
                'index': 0,
            },
            'features': {
                'efficientnetb1_finetuned': {'vector': [0.1, 0.2], 'dimension': 2},
            },
        }
    ]))

    result = run_sync(features_path=features_path, dry_run=True)

    assert result['rows'] == 1
    assert result['would_upsert_species'] == 1
    assert result['would_upsert_strains'] == 1
    assert result['would_upsert_segments'] == 1
    assert result['missing_segment_objects'] == []


def test_sync_research_yolo_to_product_reports_missing_segment_objects(
    tmp_path: Path,
) -> None:
    features_path = tmp_path / 'features.json'
    missing_segment = (
        tmp_path
        / 'Dataset'
        / 'original_prepared'
        / 'species-a'
        / 'strain-a'
        / 'MEA'
        / 'ob'
        / 'segments_yolo'
        / 'segment_0.jpg'
    )
    features_path.write_text(
        json.dumps([
            {
                'id': 'seg-1',
                'segment_path': str(missing_segment),
                'metadata': {
                    'instance_info': {
                        'species': 'Species A',
                        'strain': 'Strain A',
                        'environment': 'MEA',
                        'angle': 'ob',
                    },
                    'segmentation': {'method': 'yolo'},
                    'index': 0,
                },
                'features': {
                    'efficientnetb1_finetuned': {
                        'vector': [0.1, 0.2],
                        'dimension': 2,
                    },
                },
            }
        ])
    )

    result = run_sync(features_path=features_path, dry_run=True)

    assert result['missing_segment_objects'] == [str(missing_segment)]
