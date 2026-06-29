#!/usr/bin/env node
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { Diagram } from "../../../../tools/drawio-ai-kit/src/builder.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const out = resolve(__dirname, "../../latex/figures/src/threshold_pipeline_diagram.drawio");
mkdirSync(dirname(out), { recursive: true });

const d = new Diagram("sequence", { page: [1180, 980] });

// Row 1: retrieval input and formula construction
d.box("input_data", [40, 70], [220, 110], "Incoming diverse strains\n6 query sets per strain\n(3 segments × 2 angles)", { fill: "#FFF2CC", stroke: "#D6B656", bold: true, fs: 15 });
d.box("segment", [320, 70], [200, 110], "Segment colonies\nK-Means boxes\nfull_prepared set", { fill: "#DAE8FC", stroke: "#6C8EBF", bold: true, fs: 15 });
d.box("embed", [580, 70], [200, 110], "Embed with\nEfficientNetB1 FT", { fill: "#DAE8FC", stroke: "#6C8EBF", bold: true, fs: 15 });
d.box("retrieve", [840, 70], [270, 110], "Retrieve from full\nreference Qdrant collection\nweighted, E1, K=11", { fill: "#DAE8FC", stroke: "#6C8EBF", bold: true, fs: 15 });

d.box("formula", [410, 250], [330, 120], "Threshold formula\nmap top-5 aggregated scores\n(s0, s1, s2, s3, s4) → confidence", { fill: "#E1D5E7", stroke: "#9673A6", bold: true, fs: 15 });

// Row 2: three threshold-selection algorithms
d.box("f1", [90, 470], [230, 90], "F1-grid\nmax F1 over threshold sweep", { fill: "#D5E8D4", stroke: "#82B366", bold: true, fs: 14 });
d.box("roc", [470, 470], [230, 90], "ROC / Youden's J\nmaximize sensitivity + specificity − 1", { fill: "#D5E8D4", stroke: "#82B366", bold: true, fs: 14 });
d.box("otsu", [850, 470], [230, 90], "Otsu\nminimize intra-class variance", { fill: "#D5E8D4", stroke: "#82B366", bold: true, fs: 14 });

// Row 3: threshold and decision
d.box("threshold", [450, 650], [270, 90], "Best threshold from one algorithm", { fill: "#F8CECC", stroke: "#B85450", bold: true, fs: 16 });
d.box("decision", [445, 805], [280, 90], "Confidence ≥ threshold ?", { fill: "#FFFFFF", stroke: "#9673A6", bold: true, fs: 16 });

// Row 4: output nodes
d.box("known", [250, 930], [220, 90], "Known species\naccept top-1 retrieval label", { fill: "#D5E8D4", stroke: "#82B366", bold: true, fs: 15 });
d.box("unknown", [700, 930], [220, 90], "Unknown species\nreject as foreign", { fill: "#F8CECC", stroke: "#B85450", bold: true, fs: 15 });

// Edges — top-down flow
d.link("input_data", "segment", "incoming set");
d.link("segment", "embed", "colony crops");
d.link("embed", "retrieve", "query vectors");
d.link("retrieve", "formula", "top-5 scores");
d.link("formula", "f1", "", { dir: "TB" });
d.link("formula", "roc", "", { dir: "TB" });
d.link("formula", "otsu", "", { dir: "TB" });
d.link("f1", "threshold", "", { dir: "TB" });
d.link("roc", "threshold", "", { dir: "TB" });
d.link("otsu", "threshold", "", { dir: "TB" });
d.link("threshold", "decision", "apply");
d.link("decision", "known", "Yes");
d.link("decision", "unknown", "No");

d.title("Threshold Retrieval Pipeline for Open-Set Species Detection");
writeFileSync(out, d.mxfile("Threshold Pipeline"));
