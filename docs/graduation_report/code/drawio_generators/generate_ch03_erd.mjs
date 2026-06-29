#!/usr/bin/env node
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { Diagram } from "../../../../tools/drawio-ai-kit/src/builder.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const out = resolve(__dirname, "../../latex/figures/src/ch03_erd.drawio");
mkdirSync(dirname(out), { recursive: true });

const d = new Diagram("hierarchy", { page: [2600, 1600] });

const table = (id, x, y, w, h, title, body, color) => {
  d.box(id, [x, y], [w, h], `${title}\n\n${body}`, {
    fill: "#FFFFFF",
    stroke: color,
    bold: true,
    va: "top",
  });
};

table("users", 60, 80, 250, 220, "users", "PK id : uuid\nemail\npassword_hash\nname\nrole\nis_active\ncreated_at\nupdated_at", "#6C8EBF");
table("refresh_tokens", 60, 340, 250, 180, "refresh_tokens", "PK id : uuid\nFK user_id → users.id\ntoken_hash\nexpires_at\ncreated_at", "#6C8EBF");
table("invite_tokens", 60, 560, 250, 190, "invite_tokens", "PK id : uuid\nFK user_id → users.id\nemail\ntoken_hash\nis_used\ncreated_at", "#6C8EBF");
table("retrieval_jobs", 60, 790, 270, 230, "retrieval_jobs", "PK id : uuid\nFK user_id → users.id\njob_type\nstatus\nconfig\ninput_summary\nerror_message\nstarted_at\ncompleted_at\ncreated_at", "#9673A6");
table("retrieval_results", 380, 790, 280, 220, "retrieval_results", "PK id : uuid\nFK job_id → retrieval_jobs.id\nstrain_name\nrank\nspecies_name\nscore", "#9673A6");
table("retrieval_neighbors", 710, 790, 300, 220, "retrieval_neighbors", "PK id : uuid\nFK result_id → retrieval_results.id\nneighbor_image_id\nneighbor_strain\nneighbor_species\nsimilarity\nmedia\nsegment_index", "#9673A6");

table("species", 390, 80, 250, 200, "species", "PK id : uuid\nname\ndescription\nis_archived\ncreated_at\nupdated_at\narchived_at", "#82B366");
table("media", 690, 80, 220, 190, "media", "PK id : uuid\nname\ndescription\nis_archived\ncreated_at\nupdated_at\narchived_at", "#82B366");
table("strains", 390, 340, 260, 220, "strains", "PK id : uuid\nFK species_id → species.id\nname\nsource\nis_archived\ncreated_at\nupdated_at\narchived_at", "#82B366");
table("images", 710, 330, 320, 280, "images", "PK id : uuid\nFK strain_id → strains.id\nFK species_id → species.id?\nFK media_id → media.id?\nangle\nfile_path\nprepared_path\npipeline_path\ndata_update_status\nis_archived\narchived_at\ncreated_at\nupdated_at", "#D6B656");
table("segments", 1080, 340, 300, 250, "segments", "PK id : uuid\nFK image_id → images.id\nsegment_index\ncrop_path\nbbox_x, bbox_y\nbbox_w, bbox_h\nsegmentation_method\nqdrant_point_id\nis_archived\ncreated_at", "#D6B656");
table("feedback", 1080, 790, 330, 260, "feedback", "PK id : uuid\nFK submitter_id → users.id\nFK reviewer_id → users.id?\nFK result_id → retrieval_results.id?\nFK image_id → images.id?\nsource\nfeedback_type\nquery_strain\npredicted_species\nsuggested_species\ndescription\nstatus\nreview_note\nsubmitted_at\nreviewed_at", "#B85450");
table("audit_log", 1460, 790, 280, 220, "audit_log", "PK id : bigint\nFK user_id → users.id\naction\nentity_type\nentity_id\nchanges\nip_address\ncreated_at", "#B85450");
table("system_state", 1460, 520, 240, 150, "system_state", "PK key\nvalue : JSONB\nupdated_at", "#23445D");

d.link("users", "refresh_tokens", "1:N", { dir: "TB" });
d.link("users", "invite_tokens", "1:N", { dir: "TB" });
d.link("users", "retrieval_jobs", "1:N", { dir: "TB" });
d.link("retrieval_jobs", "retrieval_results", "1:N", { dir: "LR" });
d.link("retrieval_results", "retrieval_neighbors", "1:N", { dir: "LR" });
d.link("species", "strains", "1:N", { dir: "TB" });
d.link("species", "images", "1:N", { dir: "LR" });
d.link("media", "images", "1:N", { dir: "TB" });
d.link("strains", "images", "1:N", { dir: "LR" });
d.link("images", "segments", "1:N", { dir: "LR" });
d.link("users", "feedback", "submitter_id", { dir: "LR" });
d.link("users", "feedback", "reviewer_id", { dir: "TB" });
d.link("retrieval_results", "feedback", "0..N", { dir: "LR" });
d.link("images", "feedback", "0..N", { dir: "TB" });
d.link("users", "audit_log", "1:N", { dir: "LR" });

d.title("MycoAI Retrieval Backend — ERD (schema-aligned)");
writeFileSync(out, d.mxfile("Backend ERD"));
