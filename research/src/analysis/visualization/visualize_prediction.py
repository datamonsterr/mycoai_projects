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
    """
    Create a visualization showing query images and their K nearest neighbors per environment.
    """
    # Extract metadata
    ground_truth = prediction_result["ground_truth"]
    predicted_specy = prediction_result["predicted_specy"]
    is_correct = prediction_result["correct"]
    confidence = prediction_result["predicted_confidence"]
    feature_extractor = prediction_result["feature_extractor"]
    aggregation_strategy = prediction_result["strategy"].upper()
    raw_results = prediction_result["raw_results"]
    aggregated_results = prediction_result.get("aggregated_results", [])

    # Sort raw_results by environment
    raw_results_sorted = sorted(
        raw_results, key=lambda x: x.get("query_environment", "")
    )

    num_environments = len(raw_results_sorted)
    if num_environments == 0:
        print("No raw results to visualize.")
        return

    resolved_thumbnail_size = thumbnail_size or _get_thumbnail_size(k)
    img_width, img_height = resolved_thumbnail_size
    padding = 24
    card_gap = 12
    row_spacing = 22
    env_label_gap = 34
    text_block_width = 62
    card_width = img_width + text_block_width
    columns = max(2, min(4, k + 1))
    canvas_width = padding * 2 + columns * card_width + (columns - 1) * card_gap

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 14)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 11)
    except IOError:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    title_text = f"Strain: {prediction_result['strain']} | Ground Truth: {ground_truth}"
    pred_text = (
        f"Predicted: {predicted_specy} ({confidence:.2f}) | Correct: {is_correct}"
    )
    info_text = f"Extractor: {feature_extractor} | Strategy: {aggregation_strategy}"

    measure_canvas = Image.new("RGB", (canvas_width, 200), bg_color)
    measure_draw = ImageDraw.Draw(measure_canvas)

    header_bottom = 12
    if show_header:
        header_y = 20
        header_y = _draw_wrapped_text(
            measure_draw,
            title_text,
            (padding, header_y),
            canvas_width - 2 * padding,
            title_font,
            text_color,
        )
        header_y = _draw_wrapped_text(
            measure_draw,
            pred_text,
            (padding, header_y + 4),
            canvas_width - 2 * padding,
            title_font,
            (0, 128, 0) if is_correct else (255, 0, 0),
        )
        header_y = _draw_wrapped_text(
            measure_draw,
            info_text,
            (padding, header_y + 4),
            canvas_width - 2 * padding,
            text_font,
            text_color,
        )
        header_bottom = header_y + 8
    if show_legend:
        header_bottom = _draw_legend(
            measure_draw,
            aggregated_results,
            ground_truth,
            padding,
            header_bottom,
            canvas_width,
            text_font,
            small_font,
            text_color,
            padding,
        )

    env_block_heights: List[int] = []
    for result in raw_results_sorted:
        cards: List[Dict[str, Any]] = [
            {
                "lines": [(query_label, text_font)],
            }
        ]
        for i, neighbor in enumerate(result["neighbors"][:k], start=1):
            n_specy = neighbor.get("specy", "unknown")
            n_score = neighbor.get("score", 0.0)
            n_strain = neighbor.get("strain", "unknown")
            neighbor_title = {
                "rank_species": f"#{i} {n_specy}",
                "species": n_specy,
                "score_species": f"{n_specy}",
            }.get(neighbor_label_mode, f"#{i} {n_specy}")
            neighbor_lines: List[Tuple[str, ImageFont.ImageFont]] = [(neighbor_title, text_font)]
            neighbor_lines.append((f"Score: {n_score:.4f}", small_font))
            if show_neighbor_strain:
                neighbor_lines.append((f"Strain: {n_strain}", small_font))
            cards.append(
                {
                    "lines": neighbor_lines,
                }
            )

        card_heights = [
            _measure_card_height(measure_draw, card_width, resolved_thumbnail_size, card["lines"])
            for card in cards
        ]
        rows = (len(cards) + columns - 1) // columns
        row_heights = []
        for row_index in range(rows):
            start = row_index * columns
            row_heights.append(max(card_heights[start : start + columns]))
        env_block_heights.append(env_label_gap + sum(row_heights) + row_spacing * max(rows - 1, 0) + row_spacing)

    canvas_height = header_bottom + 16 + sum(env_block_heights)

    canvas = Image.new("RGB", (canvas_width, canvas_height), bg_color)
    draw = ImageDraw.Draw(canvas)

    current_y = 12
    if show_header:
        header_y = 20
        header_y = _draw_wrapped_text(
            draw,
            title_text,
            (padding, header_y),
            canvas_width - 2 * padding,
            title_font,
            text_color,
        )
        header_y = _draw_wrapped_text(
            draw,
            pred_text,
            (padding, header_y + 4),
            canvas_width - 2 * padding,
            title_font,
            (0, 128, 0) if is_correct else (255, 0, 0),
        )
        header_y = _draw_wrapped_text(
            draw,
            info_text,
            (padding, header_y + 4),
            canvas_width - 2 * padding,
            text_font,
            text_color,
        )
        current_y = header_y + 8
    if show_legend:
        current_y = (
            _draw_legend(
                draw,
                aggregated_results,
                ground_truth,
                padding,
                current_y,
                canvas_width,
                text_font,
                small_font,
                text_color,
                padding,
            )
            + 16
        )

    for block_index, result in enumerate(raw_results_sorted):
        environment = result.get("query_environment", "unknown")
        neighbors = result["neighbors"]

        env_text = f"Environment: {environment}"
        env_width, _ = _text_size(draw, env_text, title_font)
        draw.text(
            ((canvas_width - env_width) // 2, current_y),
            env_text,
            fill=text_color,
            font=title_font,
        )

        cards: List[Dict[str, Any]] = [
            {
                "image_path": _resolve_image_path(
                    result,
                    segmented_image_dir,
                    "query_image_id",
                ),
                "border_color": (0, 0, 0),
                "lines": [(query_label, text_font)],
            }
        ]

        for i, neighbor in enumerate(neighbors[:k], start=1):
            n_specy = neighbor.get("specy", "unknown")
            n_score = neighbor.get("score", 0.0)
            n_strain = neighbor.get("strain", "unknown")
            neighbor_title = {
                "rank_species": f"#{i} {n_specy}",
                "species": n_specy,
                "score_species": f"{n_specy}",
            }.get(neighbor_label_mode, f"#{i} {n_specy}")
            neighbor_lines: List[Tuple[str, ImageFont.ImageFont]] = [(neighbor_title, text_font)]
            neighbor_lines.append((f"Score: {n_score:.4f}", small_font))
            if show_neighbor_strain:
                neighbor_lines.append((f"Strain: {n_strain}", small_font))
            cards.append(
                {
                    "image_path": _resolve_image_path(
                        neighbor,
                        segmented_image_dir,
                        "image_id",
                    ),
                    "border_color": generate_distinct_color(n_specy, ground_truth),
                    "lines": neighbor_lines,
                }
            )

        card_heights = [
            _measure_card_height(draw, card_width, resolved_thumbnail_size, card["lines"])
            for card in cards
        ]
        row_heights = []
        total_rows = (len(cards) + columns - 1) // columns
        for row_index in range(total_rows):
            start = row_index * columns
            row_heights.append(max(card_heights[start : start + columns]))

        y_cursor = current_y + env_label_gap
        for row_index in range(total_rows):
            row_height = row_heights[row_index]
            start = row_index * columns
            end = min(start + columns, len(cards))
            cards_in_row = end - start
            row_width = cards_in_row * card_width + max(cards_in_row - 1, 0) * card_gap
            row_start_x = max(padding, (canvas_width - row_width) // 2)
            for offset, card_index in enumerate(range(start, end)):
                x_pos = row_start_x + offset * (card_width + card_gap)
                card = cards[card_index]
                _draw_image_card(
                    canvas,
                    draw,
                    card["image_path"],
                    (x_pos, y_cursor),
                    card_width,
                    resolved_thumbnail_size,
                    card["border_color"],
                    border_width if card_index > 0 else 4,
                    card["lines"],
                    text_color,
                )
            y_cursor += row_height + row_spacing

        current_y += env_block_heights[block_index]

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path)
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
