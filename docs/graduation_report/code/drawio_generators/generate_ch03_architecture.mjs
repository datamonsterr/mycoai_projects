#!/usr/bin/env node
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { Diagram } from "../../../../tools/drawio-ai-kit/src/builder.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const out = resolve(__dirname, "../../latex/figures/src/ch03_architecture.drawio");
mkdirSync(dirname(out), { recursive: true });

const d = new Diagram("network", { page: [1100, 780] });

// Users/Browsers boundary (plain dashed)
d.box("internet", [30, 80], [150, 160], "Users / Browsers", { fill: "#F5F5F5", stroke: "#7D8998", bold: true, fs: 13, va: "top" });
d.box("browser", [50, 130], [110, 70], "React SPA\nFrontend", { parent: "internet", fill: "#FFFFFF", stroke: "#D79B00", bold: true, fs: 14 });

// Docker Compose Host boundary (plain box, dashed)
d.box("compose", [210, 80], [840, 630], "Docker Compose Host", { fill: "#FAFAFA", stroke: "#666666", bold: true, fs: 13, va: "top" });

// All services directly inside compose — NO redundant container wrappers
d.box("frontend", [250, 140], [150, 70], "Nginx / Vite\nStatic SPA", { parent: "compose", fill: "#FFFFFF", stroke: "#6C8EBF", bold: true, fs: 14 });
d.box("backend", [250, 280], [180, 90], "FastAPI API\nAuth · Search · Admin", { parent: "compose", fill: "#FFFFFF", stroke: "#82B366", bold: true, fs: 14 });

d.box("postgres", [500, 140], [180, 100], "PostgreSQL\nUsers · Metadata\nJobs · Feedback", { parent: "compose", fill: "#FFFFFF", stroke: "#23445D", bold: true, fs: 14 });
d.box("qdrant", [500, 290], [180, 90], "Qdrant\nVectors · Payloads", { parent: "compose", fill: "#FFFFFF", stroke: "#0E8088", bold: true, fs: 14 });

d.box("redis", [740, 140], [140, 70], "Redis\nQueue / Cache", { parent: "compose", fill: "#FFFFFF", stroke: "#9673A6", bold: true, fs: 14 });
d.box("celery", [740, 270], [180, 110], "Celery Worker\nSegmentation · Indexing\nTraining", { parent: "compose", fill: "#FFFFFF", stroke: "#B85450", bold: true, fs: 14 });

d.box("dataset", [520, 450], [240, 100], "Shared Filesystem\nImages · Segments · Models\nGenerated artifacts", { parent: "compose", fill: "#FFF2CC", stroke: "#D6B656", bold: true, fs: 14 });

d.box("caption", [250, 600], [740, 80], "High-level runtime: browser loads React SPA, SPA calls FastAPI, FastAPI persists relational metadata in PostgreSQL, stores embeddings in Qdrant, and dispatches long-running jobs through Redis-backed Celery workers inside containerized boundaries.", { parent: "compose", fill: "#F5F5F5", stroke: "#CCCCCC", fs: 12, va: "middle" });

// Edges
d.link("browser", "frontend", "HTTPS");
d.link("frontend", "backend", "REST / JWT");
d.link("backend", "postgres", "SQLAlchemy\nCRUD", { dir: "TB" });
d.link("backend", "qdrant", "Vector search\nupsert / query", { dir: "TB" });
d.link("backend", "redis", "enqueue\ncache", { dir: "LR" });
d.link("redis", "celery", "task queue", { dir: "TB" });
d.link("celery", "postgres", "job status", { dir: "TB" });
d.link("celery", "qdrant", "reindex\nembeddings", { dir: "TB" });
d.link("backend", "dataset", "read / write\nimages", { dir: "TB" });
d.link("celery", "dataset", "produce\nartifacts", { dir: "TB" });

d.title("MycoAI Retrieval System — High-Level Architecture");
writeFileSync(out, d.mxfile("MycoAI Architecture"));
