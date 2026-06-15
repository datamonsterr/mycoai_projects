# Chapter 1: Problem Statement

## 1.1 Overview
Fungal species identification is a critical yet challenging task in mycology, often requiring expert knowledge and time-consuming manual analysis. The **MycoAI Retrieval** system addresses this by automating the identification process through an image-based retrieval system, allowing users to find matching species from a reference database based on visual similarity.

## 1.2 Dataset Description
The project utilizes a curated dataset of fungal strain images. Each record consists of:
- **Images**: High-resolution photographs of fungal colonies.
- **Metadata**: Associated species names, growth media (e.g., PDA, MEA), and strain identifiers.
The dataset is stored in `Dataset/original/` and is used both for building the reference index in Qdrant and for evaluating the retrieval accuracy in the `research/` module.

## 1.3 Scope of Work

The scope of this thesis encompasses three primary domains:

1. **Algorithmic Research**: Developing and optimizing a retrieval pipeline including K-means segmentation and KNN-based species prediction.
2. **System Engineering**: Implementing a production-ready web application with authenticated access, dataset governance, and real-time retrieval.
3. **Process Innovation**: Applying "Agentic Engineering" to the development process, using a multi-agent system (Autolab) to iteratively optimize the retrieval model.

## 1.4 Proposed Solution
The proposed solution is a hybrid retrieval system:
- **Frontend**: A React 19 application for intuitive image upload and bounding-box review.
- **Backend**: A FastAPI server managing the logic between the user and the data stores.
- **Retrieval Engine**: A pipeline that segments the image, extracts high-dimensional embeddings, and performs a nearest-neighbor search in **Qdrant**.
- **Governance**: A data-owner role to manage the species catalog and promote candidate models.

## 1.5 Rationale
- **KNN over Classification**: Standard classifiers are limited to a fixed number of classes. A retrieval (KNN) approach allows the system to handle new species by simply adding reference images to the database without retraining the entire model.
- **Qdrant Vector DB**: Qdrant is used for its efficiency in handling high-dimensional vectors and its ability to perform filtered searches (e.g., filtering by growth media).
- **Dual-DB Architecture**: PostgreSQL is used for structured metadata (Users, Species, Audit logs) to ensure ACID compliance, while Qdrant handles the unstructured vector data for speed.
