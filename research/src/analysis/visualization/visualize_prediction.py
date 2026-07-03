import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.config import DATASET_ROOT, WORKSPACE_ROOT

from PIL import Image, ImageDraw, ImageFont


def generate_distinct_color(
    species_name: str, ground_truth: str
) -> Tuple[int, int, int]:
    """
    Generate a distinct color for a species based on its name.
    Ground truth species always gets green.
    Other species get distinct colors from a predefined palette.
    """
    if species_name == ground_truth:
        return (0, 255, 0)  # Green for ground truth

    # Predefined color palette (avoiding green for ground truth)
    COLOR_PALETTE = [
        (255, 0, 0),  # Red
        (0, 0, 255),  # Blue
        (255, 165, 0),  # Orange
        (148, 0, 211),  # Dark Violet
        (255, 20, 147),  # Deep Pink
        (0, 191, 255),  # Deep Sky Blue
        (255, 215, 0),  # Gold
        (220, 20, 60),  # Crimson
        (138, 43, 226),  # Blue Violet
        (255, 105, 180),  # Hot Pink
        (70, 130, 180),  # Steel Blue
        (255, 69, 0),  # Orange Red
        (186, 85, 211),  # Medium Orchid
        (30, 144, 255),  # Dodger Blue
        (255, 140, 0),  # Dark Orange
    ]

    # Use hash to consistently assign the same color to the same species
    hash_val = abs(hash(species_name))
    color_index = hash_val % len(COLOR_PALETTE)

    return COLOR_PALETTE[color_index]


def _get_thumbnail_size(k: int) -> Tuple[int, int]:
    if k >= 11:
        return (72, 72)
    if k >= 9:
        return (80, 80)
    if k >= 7:
        return (92, 92)
    return (108, 108)


def _text_size(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont
) -> Tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    position: Tuple[int, int],
    max_width: int,
    font: ImageFont.ImageFont,
    fill: Tuple[int, int, int],
    line_spacing: int = 4,
) -> int:
    x_pos, y_pos = position
    words = text.split()
    lines: List[str] = []
    current_line = ""

    for word in words:
        candidate = word if not current_line else f"{current_line} {word}"
        candidate_width, _ = _text_size(draw, candidate, font)
        if candidate_width <= max_width or not current_line:
            current_line = candidate
            continue

        lines.append(current_line)
        current_line = word

    if current_line:
        lines.append(current_line)

    line_height = _text_size(draw, "Ag", font)[1]
    for line in lines:
        draw.text((x_pos, y_pos), line, fill=fill, font=font)
        y_pos += line_height + line_spacing

    return y_pos


def _draw_legend(
    draw: ImageDraw.ImageDraw,
    aggregated_results: List[Dict[str, Any]],
    ground_truth: str,
    start_x: int,
    start_y: int,
    canvas_width: int,
    text_font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
    text_color: Tuple[int, int, int],
    padding: int,
) -> int:
    title = "Top Species Ranking"
    title_width, title_height = _text_size(draw, title, text_font)
    title_x = max(start_x, (canvas_width - title_width) // 2)
    draw.text(
        (title_x, start_y),
        title,
        fill=text_color,
        font=text_font,
    )
    y_pos = start_y + title_height + 10
    box_size = 14
    item_gap_y = 8
    item_padding_x = 12
    item_padding_y = 8
    max_text_width = max(240, canvas_width - 2 * padding - 48)
    max_y = y_pos

    for i, res in enumerate(aggregated_results[:5]):
        specy = res["specy"]
        score = res["score"]
        color = generate_distinct_color(specy, ground_truth)
        legend_text = f"{i + 1}. {specy} (s0={score:.2f})"
        text_w, text_h = _text_size(draw, legend_text, text_font)
        item_width = min(max_text_width, text_w + box_size + item_padding_x * 2 + 8)
        item_x = (canvas_width - item_width) // 2

        draw.rounded_rectangle(
            [item_x, y_pos, item_x + item_width, y_pos + text_h + item_padding_y * 2],
            radius=10,
            outline=(180, 180, 180),
            width=1,
            fill=(248, 248, 248),
        )
        draw.rectangle(
            [
                item_x + item_padding_x,
                y_pos + item_padding_y + 1,
                item_x + item_padding_x + box_size,
                y_pos + item_padding_y + 1 + box_size,
            ],
            fill=color,
        )
        draw.text(
            (item_x + item_padding_x + box_size + 10, y_pos + item_padding_y - 1),
            legend_text,
            fill=text_color,
            font=text_font,
        )

        max_y = y_pos + text_h + item_padding_y * 2
        y_pos = max_y + item_gap_y

    return max_y + 12


def _draw_image_card(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    image_path: str,
    position: Tuple[int, int],
    card_width: int,
    thumbnail_size: Tuple[int, int],
    border_color: Tuple[int, int, int],
    border_width: int,
    lines: List[Tuple[str, ImageFont.ImageFont]],
    text_color: Tuple[int, int, int],
    line_spacing: int = 4,
) -> int:
    x_pos, y_pos = position
    img_width, img_height = thumbnail_size

    if os.path.exists(image_path):
        try:
            img = Image.open(image_path).convert("RGB")
            img = img.resize(thumbnail_size)
            canvas.paste(img, (x_pos, y_pos))
            print(f"  [viz] OK {image_path}")
        except Exception as exc:
            print(f"  [viz] ERROR {image_path}: {exc}")
    else:
        print(f"  [viz] MISSING {image_path}")
        draw.rectangle(
            [x_pos, y_pos, x_pos + img_width, y_pos + img_height],
            outline=(160, 160, 160),
            width=2,
        )
        draw.text((x_pos + 8, y_pos + 8), "Missing image", fill=text_color)

    draw.rectangle(
        [x_pos, y_pos, x_pos + img_width, y_pos + img_height],
        outline=border_color,
        width=border_width,
    )

    text_y = y_pos + img_height + 6
    text_width = max(card_width - 8, 40)
    for text, font in lines:
        text_y = _draw_wrapped_text(
            draw,
            text,
            (x_pos, text_y),
            text_width,
            font,
            text_color,
            line_spacing=line_spacing,
        )

    return text_y - y_pos


def _measure_card_height(
    draw: ImageDraw.ImageDraw,
    card_width: int,
    thumbnail_size: Tuple[int, int],
    lines: List[Tuple[str, ImageFont.ImageFont]],
    line_spacing: int = 4,
) -> int:
    _, img_height = thumbnail_size
    text_width = max(card_width - 8, 40)
    text_height = 0
    for text, font in lines:
        words = text.split()
        current_line = ""
        wrapped_lines = 0
        for word in words:
            candidate = word if not current_line else f"{current_line} {word}"
            candidate_width, _ = _text_size(draw, candidate, font)
            if candidate_width <= text_width or not current_line:
                current_line = candidate
                continue
            wrapped_lines += 1
            current_line = word
        if current_line:
            wrapped_lines += 1
        line_height = _text_size(draw, "Ag", font)[1]
        text_height += wrapped_lines * line_height + max(wrapped_lines - 1, 0) * line_spacing
        text_height += line_spacing
    return img_height + 6 + text_height


def _normalize_explicit_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.exists():
        return path
    if path.is_absolute():
        parts = path.parts
        dataset_markers = [
            "Dataset",
            "results",
            "weights",
        ]
        for marker in dataset_markers:
            if marker in parts:
                idx = parts.index(marker)
                candidate = WORKSPACE_ROOT.joinpath(*parts[idx:])
                if candidate.exists():
                    return candidate
    return path


def _resolve_image_path(
    item: Dict[str, Any],
    default_dir: str,
    id_key: str,
) -> str:
    explicit_path = item.get("image_path") or item.get("query_image_path")
    if explicit_path:
        normalized_path = _normalize_explicit_path(str(explicit_path))
        if normalized_path.is_absolute():
            return str(normalized_path)
        return str((WORKSPACE_ROOT / normalized_path).resolve())

    image_id = item.get(id_key) or item.get("id") or ""
    candidates = [
        Path(default_dir) / f"{image_id}.jpg",
        DATASET_ROOT / "original_prepared" / f"{image_id}.jpg",
        DATASET_ROOT / "segmented_image" / f"{image_id}.jpg",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    parts = image_id.split("__")
    if len(parts) >= 5:
        segment_name = parts[4].split("_seg", 1)[0]
        prepared_candidates = [
            DATASET_ROOT / "original_prepared" / parts[0] / parts[1] / parts[2] / parts[3] / "segments_yolo" / f"{segment_name}.jpg",
            DATASET_ROOT / "prepared" / parts[0] / parts[1] / parts[2] / parts[3] / "segments_yolo" / f"{segment_name}.jpg",
            DATASET_ROOT / "full_prepared" / parts[0] / parts[1] / parts[2] / parts[3] / "segments_kmeans" / f"{segment_name}.jpg",
            DATASET_ROOT / "full_prepared" / parts[0] / parts[1] / parts[2] / parts[3] / "segments_yolo" / f"{segment_name}.jpg",
        ]
        for candidate in prepared_candidates:
            if candidate.exists():
                return str(candidate)
    matches = list(DATASET_ROOT.glob(f"**/{image_id}.jpg"))
    if matches:
        return str(matches[0])
    segment_matches = list(DATASET_ROOT.glob(f"**/{image_id.split('_seg', 1)[0]}.jpg"))
    if segment_matches:
        return str(segment_matches[0])
    return str(candidates[0])


def visualize_prediction_by_environment(
    prediction_result: Dict[str, Any],
    segmented_image_dir: str,
    output_path: str,
    k: int = 7,
    thumbnail_size: Optional[Tuple[int, int]] = None,
    text_color: Tuple[int, int, int] = (0, 0, 0),
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    border_width: int = 8,
    show_header: bool = True,
    show_legend: bool = True,
    query_label: str = "Query",
    neighbor_label_mode: str = "rank_species",
    show_neighbor_strain: bool = True,
) -> None:
    """Create compact thesis-ready prediction visualization."""
    ground_truth = prediction_result["ground_truth"]
    predicted_specy = prediction_result["predicted_specy"]
    is_correct = prediction_result["correct"]
    confidence = prediction_result["predicted_confidence"]
    feature_extractor = prediction_result["feature_extractor"]
    aggregation_strategy = prediction_result["strategy"]
    raw_results_sorted = sorted(
        prediction_result["raw_results"], key=lambda x: x.get("query_environment", "")
    )
    aggregated_results = prediction_result.get("aggregated_results", [])

    if not raw_results_sorted:
        print("No raw results to visualize.")
        return

    resolved_thumbnail_size = thumbnail_size or (78, 78)
    img_width, img_height = resolved_thumbnail_size
    padding = 18
    panel_gap_x = 18
    panel_gap_y = 20
    card_gap_x = 10
    card_gap_y = 10
    text_gap = 3
    panel_cols = 2
    card_cols = 3
    line_spacing = 2

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 15)
        body_font = ImageFont.truetype("DejaVuSans.ttf", 15)
        label_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 12)
        rank_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
        rank_small_font = ImageFont.truetype("DejaVuSans.ttf", 13)
    except IOError:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        rank_font = ImageFont.load_default()
        rank_small_font = ImageFont.load_default()

    def wrap_lines(draw_ctx: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
        words = text.split()
        if not words:
            return [""]
        lines: List[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if _text_size(draw_ctx, candidate, font)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def draw_centered_lines(
        draw_ctx: ImageDraw.ImageDraw,
        lines: List[Tuple[str, ImageFont.ImageFont, Tuple[int, int, int]]],
        x_pos: int,
        y_pos: int,
        width: int,
    ) -> int:
        cursor_y = y_pos
        for text, font, color in lines:
            wrapped = wrap_lines(draw_ctx, text, font, width)
            line_height = _text_size(draw_ctx, "Ag", font)[1]
            for line in wrapped:
                line_width, _ = _text_size(draw_ctx, line, font)
                draw_ctx.text((x_pos + (width - line_width) / 2, cursor_y), line, fill=color, font=font)
                cursor_y += line_height + line_spacing
            cursor_y += 1
        return cursor_y

    def measure_centered_lines(
        draw_ctx: ImageDraw.ImageDraw,
        lines: List[Tuple[str, ImageFont.ImageFont, Tuple[int, int, int]]],
        width: int,
    ) -> int:
        total = 0
        for text, font, _ in lines:
            wrapped = wrap_lines(draw_ctx, text, font, width)
            line_height = _text_size(draw_ctx, "Ag", font)[1]
            total += len(wrapped) * (line_height + line_spacing) + 1
        return total

    measure_canvas = Image.new("RGB", (100, 100), bg_color)
    measure_draw = ImageDraw.Draw(measure_canvas)

    card_width = img_width + 6
    text_width = card_width
    card_inner_height = img_height + text_gap + measure_centered_lines(
        measure_draw,
        [("Sample", label_font, text_color), ("0.9999", small_font, text_color), ("DTO 123", small_font, text_color)],
        text_width,
    )

    panel_width = card_cols * card_width + (card_cols - 1) * card_gap_x + 14

    def build_card_lines(result: Dict[str, Any], index: int, is_query: bool = False) -> List[Tuple[str, ImageFont.ImageFont, Tuple[int, int, int]]]:
        if is_query:
            medium_label = result.get("query_environment", query_label)
            return [(medium_label, label_font, text_color)]

        species = result.get("specy", "unknown")
        score = result.get("score", 0.0)
        strain = result.get("strain", "unknown")
        title = {
            "rank_species": f"#{index} {species}",
            "species": species,
            "score_species": species,
        }.get(neighbor_label_mode, f"#{index} {species}")
        lines: List[Tuple[str, ImageFont.ImageFont, Tuple[int, int, int]]] = [
            (title, label_font, text_color),
            (f"Score {score:.4f}", small_font, text_color),
        ]
        if show_neighbor_strain:
            lines.append((strain, small_font, text_color))
        return lines

    def measure_panel_height(result: Dict[str, Any]) -> int:
        cards = [result] + result["neighbors"][:k]
        rows = (len(cards) + card_cols - 1) // card_cols
        return rows * card_inner_height + max(rows - 1, 0) * card_gap_y + 14

    panel_heights = [measure_panel_height(result) for result in raw_results_sorted]
    row_heights: List[int] = []
    for start in range(0, len(panel_heights), panel_cols):
        row_heights.append(max(panel_heights[start : start + panel_cols]))

    canvas_width = padding * 2 + panel_cols * panel_width + (panel_cols - 1) * panel_gap_x
    header_estimate = 140 if show_header or show_legend else 20
    canvas_height = padding * 2 + header_estimate + sum(row_heights) + max(len(row_heights) - 1, 0) * panel_gap_y
    canvas = Image.new("RGB", (canvas_width, canvas_height), bg_color)
    draw = ImageDraw.Draw(canvas)

    current_y = padding
    status_color = (0, 128, 0) if is_correct else (200, 0, 0)
    if show_header:
        header_lines = [
            (f"Strain: {prediction_result['strain']}", title_font, text_color),
            (f"Ground truth: {ground_truth}", body_font, text_color),
            (f"Predicted: {predicted_specy} ({confidence:.2f})", body_font, status_color),
            (f"Extractor: {feature_extractor} | Aggregation: {aggregation_strategy} | K={k}", small_font, text_color),
        ]
        current_y = draw_centered_lines(draw, header_lines, padding, current_y, canvas_width - 2 * padding) + 6

    if show_legend and aggregated_results:
        ranking_title = "Species ranking"
        title_width, title_height = _text_size(draw, ranking_title, rank_font)
        draw.text(((canvas_width - title_width) / 2, current_y), ranking_title, fill=text_color, font=rank_font)
        current_y += title_height + 8
        for idx, res in enumerate(aggregated_results[:5], start=1):
            specy = res["specy"]
            score = res["score"]
            color = generate_distinct_color(specy, ground_truth)
            line = f"{idx}. {specy}  ({score:.3f})"
            line_width, line_height = _text_size(draw, line, rank_small_font)
            box_width = line_width + 42
            box_height = line_height + 10
            box_x = int((canvas_width - box_width) / 2)
            draw.rounded_rectangle(
                [box_x, current_y, box_x + box_width, current_y + box_height],
                radius=8,
                fill=(248, 248, 248),
                outline=(190, 190, 190),
                width=1,
            )
            draw.rectangle([box_x + 10, current_y + 8, box_x + 22, current_y + 20], fill=color)
            draw.text((box_x + 28, current_y + 5), line, fill=text_color, font=rank_small_font)
            current_y += box_height + 6
        current_y += 6

    panel_top = current_y
    row_index = 0
    for start in range(0, len(raw_results_sorted), panel_cols):
        row_results = raw_results_sorted[start : start + panel_cols]
        row_height = row_heights[row_index]
        total_width = len(row_results) * panel_width + max(len(row_results) - 1, 0) * panel_gap_x
        row_x = int((canvas_width - total_width) / 2)

        for panel_offset, result in enumerate(row_results):
            panel_x = row_x + panel_offset * (panel_width + panel_gap_x)
            panel_y = panel_top
            cards = [
                {
                    "image_path": _resolve_image_path(result, segmented_image_dir, "query_image_id"),
                    "border_color": (60, 60, 60),
                    "lines": build_card_lines(result, 0, is_query=True),
                    "border": 3,
                }
            ]
            for idx, neighbor in enumerate(result["neighbors"][:k], start=1):
                cards.append(
                    {
                        "image_path": _resolve_image_path(neighbor, segmented_image_dir, "image_id"),
                        "border_color": generate_distinct_color(neighbor.get("specy", "unknown"), ground_truth),
                        "lines": build_card_lines(neighbor, idx),
                        "border": border_width,
                    }
                )

            for card_index, card in enumerate(cards):
                card_row = card_index // card_cols
                card_col = card_index % card_cols
                x_pos = panel_x + 7 + card_col * (card_width + card_gap_x)
                y_pos = panel_y + 7 + card_row * (card_inner_height + card_gap_y)

                image_path = card["image_path"]
                if os.path.exists(image_path):
                    try:
                        image = Image.open(image_path).convert("RGB").resize(resolved_thumbnail_size)
                        canvas.paste(image, (x_pos, y_pos))
                    except Exception as exc:
                        print(f"  [viz] ERROR {image_path}: {exc}")
                        draw.rectangle([x_pos, y_pos, x_pos + img_width, y_pos + img_height], outline=(160, 160, 160), width=2)
                else:
                    print(f"  [viz] MISSING {image_path}")
                    draw.rectangle([x_pos, y_pos, x_pos + img_width, y_pos + img_height], outline=(160, 160, 160), width=2)

                draw.rectangle(
                    [x_pos, y_pos, x_pos + img_width, y_pos + img_height],
                    outline=card["border_color"],
                    width=card["border"],
                )
                draw_centered_lines(draw, card["lines"], x_pos - 3, y_pos + img_height + text_gap, text_width)

        panel_top += row_height + panel_gap_y
        row_index += 1

    cropped = canvas.crop((0, 0, canvas_width, panel_top - panel_gap_y + padding))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cropped.save(output_path)
    print(f"Saved visualization to {output_path}")


def batch_visualize_predictions(
    prediction_results: List[Dict[str, Any]],
    segmented_image_dir: str,
    output_dir: str,
    k: int = 7,
    filter_correct: Optional[bool] = None,
    max_visualizations: Optional[int] = None,
) -> List[str]:
    """
    Batch visualize predictions.
    """
    saved_paths = []
    count = 0

    for result in prediction_results:
        if filter_correct is not None:
            if result["correct"] != filter_correct:
                continue

        if max_visualizations and count >= max_visualizations:
            break

        strain = result["strain"]
        test_set_index = result.get("test_set_index", "")

        if test_set_index != "":
            filename = f"pred_{strain}_set{test_set_index}.jpg"
        else:
            filename = f"pred_{strain}.jpg"

        output_path = os.path.join(output_dir, filename)

        visualize_prediction_by_environment(
            prediction_result=result,
            segmented_image_dir=segmented_image_dir,
            output_path=output_path,
            k=k,
        )

        saved_paths.append(output_path)
        count += 1

    return saved_paths
