#!/usr/bin/env node
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const out = resolve(__dirname, "../../latex/figures/src/ch02_research_pipeline.drawio");
mkdirSync(dirname(out), { recursive: true });

const W = 3200, H = 2300;
let eid = 1;

function esc(s) { return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function rc(c) { return `rounded=1;whiteSpace=wrap;html=1;fillColor=${c.fill};strokeColor=${c.stroke};fontSize=${c.fontSize||18};fontStyle=${c.bold?1:0};verticalAlign=${c.va||"middle"};align=center;spacingTop=8;spacingBottom=8;spacingLeft=8;spacingRight=8;overflow=fill;`; }
function box(id, x, y, w, h, label, style) {
  return `<mxCell id="${id}" value="${esc(label)}" style="${rc(style)}" vertex="1" parent="1"><mxGeometry x="${x}" y="${y}" width="${w}" height="${h}" as="geometry"/></mxCell>`;
}
function edge(id, src, tgt, label, ex, ey, enx, eny) {
  const s = `edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;exitX=${ex};exitY=${ey};exitDx=0;exitDy=0;entryX=${enx};entryY=${eny};entryDx=0;entryDy=0;fontSize=16;`;
  return `<mxCell id="${id}" value="${esc(label)}" style="${s}" edge="1" parent="1" source="${src}" target="${tgt}"><mxGeometry relative="1" as="geometry"/></mxCell>`;
}

const cells = [];

// Colors — scaled-up fonts, stage uses top-aligned
const S = { fill: "#6C8EBF", stroke: "#4A6A9F", bold: 1, fontSize: 22, va: "middle" },
      P = { fill: "#E1F5FE", stroke: "#6C8EBF", bold: 1, fontSize: 20, va: "middle" },
      B = { fill: "#D5E8D4", stroke: "#82B366", fontSize: 18, va: "middle" },
      A = { fill: "#F8CECC", stroke: "#B85450", fontSize: 18, va: "middle" },
      O = { fill: "#FFF2CC", stroke: "#D6B656", bold: 1, fontSize: 18, va: "middle" },
      IO = { fill: "#FFF2CC", stroke: "#D6B656", bold: 1, fontSize: 22, va: "middle" },
      T = { fill: "#EEEEEE", stroke: "#AAAAAA", bold: 1, fontSize: 28, va: "middle" };

const GAP = 40;
const TOP = 100;
const CW = Math.floor((W - 3*GAP) / 2); // column width = 1540

// ── Stage 1 ──────────────────────────────────────────────────────────────
const S1H = 620;
cells.push(box("s1", GAP, TOP, CW, S1H, "Stage 1: Preprocessing & Colony Segmentation", T));
cells.push(box("s1a", GAP+30,  TOP+70,  300, 130, "Resize 256×256\nCircle detection\nBackground masking\nCrop to dish", P));
cells.push(box("s1b", GAP+380, TOP+70,  300, 130, "K-Means branch\nHSV K=2 clustering\nLocal K=2 shrink\nBounding box", B));
cells.push(box("s1c", GAP+210, TOP+240, 300, 130, "YOLO26n-seg branch\nTop-3 detections\nInstance masks", A));
cells.push(box("s1d", GAP+210, TOP+430, 300, 110, "Output: colony segs (~3 per plate)", O));

// ── Stage 2 ──────────────────────────────────────────────────────────────
const S2X = GAP + CW + GAP;  // = 1620
cells.push(box("s2", S2X, TOP, CW, S1H, "Stage 2: Feature Extraction & Vector Indexing", T));
cells.push(box("s2a", S2X+170, TOP+70,  300, 100, "Extractor family", P));
cells.push(box("s2b", S2X+25,  TOP+210, 240, 150, "Hand-crafted\nHOG · Gabor\nColorHist\nColorHistHS", B));
cells.push(box("s2c", S2X+285, TOP+210, 240, 150, "Pretrained DL\nResNet50 · EffNetB1\nMobileNetV2\n(ImageNet)", A));
cells.push(box("s2d", S2X+545, TOP+210, 240, 150, "Fine-tuned DL\nResNet50 · EffNetB1\nMobileNetV2\n(fungal)", B));
cells.push(box("s2e", S2X+170, TOP+400, 300, 100, "L2-normalize vectors", O));
cells.push(box("s2f", S2X+170, TOP+530, 300, 100, "Qdrant vector DB (cosine index)", O));

// ── Stage 3 ──────────────────────────────────────────────────────────────
const S3Y = TOP + S1H + GAP;  // = 760
const S3H = 760;
cells.push(box("s3", GAP, S3Y, CW, S3H, "Stage 3: KNN Retrieval & Multi-Image Aggregation", T));
cells.push(box("s3a", GAP+210, S3Y+80,  300, 100, "Query colony\nextract feature", P));
cells.push(box("s3b", GAP+210, S3Y+220, 300, 100, "Top-K cosine search (K=7)\nexclude query strain", B));
cells.push(box("s3c", GAP+210, S3Y+360, 300, 100, "Sibling filtering\nremove same-parent leakage", A));
cells.push(box("s3d", GAP+25,  S3Y+500, 220, 100, "weighted\nΣscores / N", B));
cells.push(box("s3e", GAP+265, S3Y+500, 220, 100, "freq_strength\nfreq × avg score", A));
cells.push(box("s3f", GAP+505, S3Y+500, 220, 100, "relative\nΣscores / Σall", B));
cells.push(box("s3g", GAP+210, S3Y+640, 300, 100, "Strain-Level Species Ranking", O));

// ── Stage 4 ──────────────────────────────────────────────────────────────
cells.push(box("s4", S2X, S3Y, CW, S3H, "Stage 4: Species Prediction & Validation", T));
cells.push(box("s4a", S2X+170, S3Y+80,  300, 100, "Top-1 species\nwith confidence", P));
cells.push(box("s4b", S2X+170, S3Y+220, 300, 100, "Threshold check\nknown vs unknown", B));
cells.push(box("s4c", S2X+170, S3Y+360, 300, 100, "5-fold CV\naccuracy · F1 · precision · recall", A));
cells.push(box("s4d", S2X+170, S3Y+560, 300, 100, "Species Prediction\nwith Retrieval Evidence", O));

// ── I/O boxes ────────────────────────────────────────────────────────────
cells.push(box("raw", W/2-190, TOP-85, 380, 70, "Raw Petri Dish Images", IO));
cells.push(box("final", W/2-230, S3Y+S3H+50, 460, 70, "Species Prediction with Retrieval Evidence", IO));

// ── Helper for edges ─────────────────────────────────────────────────────
function L(src, tgt, label, ex, ey, enx, eny) { cells.push(edge("e"+eid++, src, tgt, label, ex, ey, enx, eny)); }

// Inter-stage flow
L("raw", "s1a", "dataset", 0.5, 1, 0.5, 0);
L("s1d", "s2a", "colony segments", 1, 0.5, 0, 0.5);
L("s2f", "s3a", "embeddings", 1, 0.5, 0, 0.5);
L("s3g", "s4a", "strain ranking", 1, 0.5, 0, 0.5);
L("s4d", "final", "report", 0.5, 1, 0.5, 0);

// Stage 1 internal
L("s1a", "s1b", "K-Means", 1, 0.5, 0, 0.5);
L("s1a", "s1c", "YOLO", 0.5, 1, 0.5, 0);
L("s1b", "s1d", "", 0.5, 1, 0.5, 0);
L("s1c", "s1d", "", 0.5, 1, 0.5, 0);

// Stage 2 internal
L("s2a", "s2b", "HC", 0.5, 1, 0.5, 0);
L("s2a", "s2c", "PT", 0.5, 1, 0.5, 0);
L("s2a", "s2d", "FT", 0.5, 1, 0.5, 0);
L("s2b", "s2e", "", 0.5, 1, 0.5, 0);
L("s2c", "s2e", "", 0.5, 1, 0.5, 0);
L("s2d", "s2e", "", 0.5, 1, 0.5, 0);
L("s2e", "s2f", "upsert", 0.5, 1, 0.5, 0);

// Stage 3 internal
L("s3a", "s3b", "Qdrant query", 0.5, 1, 0.5, 0);
L("s3b", "s3c", "neighbors", 0.5, 1, 0.5, 0);
L("s3c", "s3d", "", 0.5, 1, 0.5, 0);
L("s3c", "s3e", "", 0.5, 1, 0.5, 0);
L("s3c", "s3f", "", 0.5, 1, 0.5, 0);
L("s3d", "s3g", "", 0.5, 1, 0.5, 0);
L("s3e", "s3g", "", 0.5, 1, 0.5, 0);
L("s3f", "s3g", "", 0.5, 1, 0.5, 0);

// Stage 4 internal
L("s4a", "s4b", "decision", 0.5, 1, 0.5, 0);
L("s4b", "s4c", "evaluate", 0.5, 1, 0.5, 0);
L("s4c", "s4d", "evidence", 0.5, 1, 0.5, 0);

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net">
  <diagram name="Research Pipeline" id="d">
    <mxGraphModel dx="2400" dy="1600" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="${W}" pageHeight="${H}" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        ${cells.join("\n        ")}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>`;

writeFileSync(out, xml, "utf-8");
