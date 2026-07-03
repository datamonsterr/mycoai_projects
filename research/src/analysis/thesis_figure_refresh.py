from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np

from src.analysis.visualization.visualize_prediction import visualize_prediction_by_environment
from src.preprocessing.kmeans import draw_bbox, segment_kmeans_image

ROOT = Path('/home/dat/dev/mycoai')
FIG_ROOT = ROOT / 'graduation_report' / 'figures'


def build_proposed_solution_diagram() -> Path:
    out = FIG_ROOT / '01_chapter2_methodology' / 'ch01_proposed_solution_simple.png'
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 4.4), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    def box(x, y, w, h, text, fc, ec='#334155', fs=12):
        rect = plt.matplotlib.patches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle='round,pad=0.02,rounding_size=0.03',
            linewidth=1.5,
            edgecolor=ec,
            facecolor=fc,
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=fs, weight='bold')
        return rect

    def arrow(x1, y1, x2, y2):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle='->', lw=1.8, color='#334155'))

    box(0.03, 0.37, 0.13, 0.22, 'Multi-media\nstrain images', '#DBEAFE')
    box(0.21, 0.37, 0.13, 0.22, 'Segmentation\nYOLO or KMeans', '#DCFCE7')
    box(0.39, 0.37, 0.15, 0.22, 'Feature extraction\ntraditional / PT / FT', '#FEF3C7')
    box(0.59, 0.37, 0.14, 0.22, 'Qdrant retrieval\ntop-K neighbors', '#FCE7F3')
    box(0.78, 0.37, 0.12, 0.22, 'Aggregation\nspecies ranking', '#EDE9FE')
    box(0.72, 0.07, 0.12, 0.17, 'Threshold', '#F3F4F6', fs=11)
    box(0.89, 0.52, 0.09, 0.14, 'Ranked\nspecies', '#DCFCE7', fs=11)
    box(0.89, 0.11, 0.09, 0.14, 'Unknown\nwarning', '#FEE2E2', fs=11)

    arrow(0.16, 0.48, 0.21, 0.48)
    arrow(0.34, 0.48, 0.39, 0.48)
    arrow(0.54, 0.48, 0.59, 0.48)
    arrow(0.73, 0.48, 0.78, 0.48)
    arrow(0.90, 0.53, 0.89, 0.59)
    arrow(0.84, 0.37, 0.78, 0.24)
    arrow(0.84, 0.15, 0.89, 0.18)

    ax.text(0.84, 0.29, 'confidence check', fontsize=10, ha='center', color='#475569')
    fig.tight_layout()
    fig.savefig(out, bbox_inches='tight')
    plt.close(fig)
    return out


def _load_bold_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        '/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf',
        '/usr/share/fonts/truetype/msttcorefonts/Arialbd.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def build_clean_strain_grid() -> Path:
    out = FIG_ROOT / '12_misc' / 'example_strain_grid_clean.png'
    out.parent.mkdir(parents=True, exist_ok=True)

    media = ['crea', 'cya', 'dg18', 'mea', 'yes']
    rows = [
        ('penicillium-polonicum', 'dto-148-d1', 'P. polonicum\nDTO 148-D1', '#22c55e'),
        ('penicillium-polonicum', 'dto-469-g8', 'P. polonicum\nDTO 469-G8', '#22c55e'),
        ('penicillium-aurantiogriseum', 'dto-469-i5', 'P. aurantiogriseum\nDTO 469-I5', '#2563eb'),
    ]

    cell_w = 240
    cell_h = 240
    left_w = 180
    top_h = 64
    pad = 10
    border_w = 4
    canvas = Image.new('RGB', (left_w + len(media) * cell_w, top_h + len(rows) * cell_h), 'white')
    draw = ImageDraw.Draw(canvas)
    title_font = _load_bold_font(24)
    row_font = _load_bold_font(21)

    for col, medium in enumerate(media):
        x = left_w + col * cell_w + cell_w // 2
        text = medium.upper()
        text_box = draw.textbbox((0, 0), text, font=title_font)
        draw.text((x - (text_box[2] - text_box[0]) // 2, 18), text, fill='black', font=title_font)

    for row_idx, (species, strain, label, color_hex) in enumerate(rows):
        y0 = top_h + row_idx * cell_h
        text_box = draw.multiline_textbbox((0, 0), label, font=row_font, spacing=4)
        text_h = text_box[3] - text_box[1]
        draw.multiline_text((18, y0 + (cell_h - text_h) // 2), label, fill='black', font=row_font, spacing=4)
        for col, medium in enumerate(media):
            img_dir = ROOT / 'Dataset' / 'original_prepared' / species / strain / medium / 'ob'
            source = next(img_dir.glob('source*.jpg'))
            image = Image.open(source).convert('RGB').resize((cell_w - 2 * pad, cell_h - 2 * pad))
            x0 = left_w + col * cell_w + pad
            y1 = y0 + pad
            canvas.paste(image, (x0, y1))
            draw.rectangle([x0, y1, x0 + image.width, y1 + image.height], outline=color_hex, width=border_w)

    canvas.save(out)
    return out


def build_segmentation_io() -> Path:
    base = ROOT / 'Dataset' / 'original_prepared' / 'penicillium-polonicum' / 'dto-148-d1' / 'crea' / 'ob'
    source = next(base.glob('source*.jpg'))
    segments = [base / 'segments_yolo' / f'segment_{idx}.jpg' for idx in (1, 2, 3)]
    out = FIG_ROOT / '09_segmentation' / 'segmentation_input_output.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 4, figsize=(15, 4), dpi=300)
    axes[0].imshow(mpimg.imread(source))
    axes[0].set_title('Full image', fontsize=12)
    axes[0].axis('off')
    for axis, segment, title in zip(axes[1:], segments, ['YOLO segment 1', 'YOLO segment 2', 'YOLO segment 3'], strict=False):
        axis.imshow(mpimg.imread(segment))
        axis.set_title(title, fontsize=12)
        axis.axis('off')
    fig.tight_layout()
    fig.savefig(out, bbox_inches='tight')
    plt.close(fig)
    return out


def build_kmeans_vs_yolo() -> Path:
    base = ROOT / 'Dataset' / 'original_prepared' / 'penicillium-polonicum' / 'dto-148-d1'
    samples = [
        base / 'crea' / 'ob',
        base / 'cya30' / 'ob',
        base / 'yes' / 'rev',
    ]
    out = FIG_ROOT / '06_retrieval' / 'kmeans_vs_yolo_latest.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), dpi=300)
    for col, sample in enumerate(samples):
        axes[0, col].imshow(mpimg.imread(sample / 'bbox_kmeans.jpg'))
        axes[0, col].set_title(f'KMeans - {sample.parent.name.upper()} {sample.name}', fontsize=11)
        axes[0, col].axis('off')
        axes[1, col].imshow(mpimg.imread(sample / 'bbox_yolo.jpg'))
        axes[1, col].set_title(f'YOLO - {sample.parent.name.upper()} {sample.name}', fontsize=11)
        axes[1, col].axis('off')
    fig.tight_layout()
    fig.savefig(out, bbox_inches='tight')
    plt.close(fig)
    return out


def build_compact_heatmap() -> Path:
    src = FIG_ROOT / '04_eda' / 'eda_media_species_heatmap.png'
    out = FIG_ROOT / '04_eda' / 'eda_media_species_heatmap_compact.png'
    image = Image.open(src).convert('RGB')
    resized = image.resize((image.width, int(image.height * 0.72)))
    resized.save(out)
    return out


def build_pipeline_steps_oneline() -> Path:
    base = ROOT / 'Dataset' / 'original_prepared' / 'penicillium-polonicum' / 'dto-148-d1' / 'yes' / 'ob'
    source = next(base.glob('source*.jpg'))
    out = FIG_ROOT / '09_segmentation' / 'pipeline_kmeans_steps.jpg'
    out.parent.mkdir(parents=True, exist_ok=True)

    image_bgr = cv2.imread(str(source))
    bboxes, _, debug = segment_kmeans_image(image_bgr, return_debug=True)
    final_boxes = draw_bbox(image_bgr, bboxes)

    step_images = [
        ('Source dish', cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)),
        ('Color clustering', cv2.cvtColor(debug['color_dimension'], cv2.COLOR_BGR2RGB)),
        ('Foreground mask', cv2.cvtColor(debug['foreground_mask'], cv2.COLOR_BGR2RGB)),
        ('Location clusters', cv2.cvtColor(debug['location_clusters'], cv2.COLOR_BGR2RGB)),
        ('Final boxes', cv2.cvtColor(final_boxes, cv2.COLOR_BGR2RGB)),
    ]

    segment_paths = [base / 'segments_yolo' / f'segment_{idx}.jpg' for idx in (1, 2, 3)]
    segment_images = [np.array(Image.open(path).convert('RGB')) for path in segment_paths if path.exists()]
    if segment_images:
        tile_h = max(img.shape[0] for img in segment_images)
        tile_w = max(img.shape[1] for img in segment_images)
        row_tiles = []
        for img in segment_images:
            tile = Image.new('RGB', (tile_w, tile_h), 'white')
            pil_img = Image.fromarray(img)
            x = (tile_w - pil_img.width) // 2
            y = (tile_h - pil_img.height) // 2
            tile.paste(pil_img, (x, y))
            row_tiles.append(np.array(tile))
        segment_strip = np.concatenate(row_tiles, axis=1)
        step_images.append(('Exported crops', segment_strip))

    fig, axes = plt.subplots(1, len(step_images), figsize=(18, 4.1), dpi=300)
    for axis, (title, img) in zip(axes, step_images, strict=False):
        axis.imshow(img)
        axis.set_title(title, fontsize=11, fontweight='bold')
        axis.axis('off')
    fig.tight_layout()
    fig.savefig(out, bbox_inches='tight')
    plt.close(fig)
    return out


def build_oneline_augmentation() -> Path:
    src = FIG_ROOT / '12_misc' / 'finetune_augmentation_preview.png'
    out = FIG_ROOT / '08_training' / 'augmentation_preview_oneline.png'
    image = Image.open(src).convert('RGB')
    panel_width = image.width // 3
    panel_height = image.height // 2
    tiles = []
    for row in range(2):
        for col in range(3):
            left = col * panel_width
            top = row * panel_height
            right = image.width if col == 2 else (col + 1) * panel_width
            bottom = image.height if row == 1 else (row + 1) * panel_height
            tiles.append(image.crop((left, top, right, bottom)))
    canvas = Image.new('RGB', (sum(tile.width for tile in tiles), max(tile.height for tile in tiles)), 'white')
    x_offset = 0
    for tile in tiles:
        y_offset = (canvas.height - tile.height) // 2
        canvas.paste(tile, (x_offset, y_offset))
        x_offset += tile.width
    canvas.save(out)
    return out
def build_knn_prediction_visuals() -> list[Path]:
    import json

    result_path = ROOT / 'results' / 'retrieval_batch1' / 'efficientnetb1_finetuned_5_freq_strength_E1_yolo' / 'evaluation_results.json'
    payload = json.loads(result_path.read_text())
    results = payload['results']

    targets = [
        ('DTO 148-D1', True, 'Penicillium polonicum', 'prediction_visual_example.jpg'),
        ('DTO 469-I4', True, 'Penicillium freii', 'prediction_visual_correct_2.jpg'),
        ('DTO 158-D1', False, 'Penicillium freii', 'prediction_visual_incorrect_1.jpg'),
    ]

    saved: list[Path] = []
    for strain, correct, predicted_specy, filename in targets:
        match = next(
            (
                result
                for result in results
                if result['strain'] == strain
                and result['correct'] == correct
                and result['predicted_specy'] == predicted_specy
            ),
            None,
        )
        if match is None:
            raise ValueError(f'Missing prediction case for {strain} {predicted_specy} correct={correct}')

        output = FIG_ROOT / '06_retrieval' / filename
        output.parent.mkdir(parents=True, exist_ok=True)
        visualize_prediction_by_environment(
            prediction_result={
                **match,
                'feature_extractor': 'EfficientNetB1 finetuned',
                'strategy': 'freq_strength',
            },
            segmented_image_dir=str(ROOT / 'Dataset' / 'original_prepared'),
            output_path=str(output),
            k=5,
            thumbnail_size=(78, 78),
            show_header=True,
            show_legend=True,
            query_label='Growth medium',
            neighbor_label_mode='rank_species',
            show_neighbor_strain=False,
        )
        saved.append(output)

    return saved



def main() -> None:
    build_proposed_solution_diagram()
    build_clean_strain_grid()
    build_segmentation_io()
    build_pipeline_steps_oneline()
    build_kmeans_vs_yolo()
    build_compact_heatmap()
    build_oneline_augmentation()
    build_knn_prediction_visuals()


if __name__ == '__main__':
    main()
