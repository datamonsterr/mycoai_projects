# Chapter 2: Fungal Species Retrieval Model

## 2.1 Motivation

Traditional fungal identification relies on morphological features observed under a microscope—colony color, texture, growth rate, and sporulation patterns. These features can be subtle and are often subjective when assessed by different mycologists. By utilizing deep learning embeddings, the system can capture complex visual patterns that are invariant to minor lighting or scale changes, providing a "similarity search" that mimics how mycologists compare unknown samples to known reference slides.

The retrieval-based approach offers a key advantage over end-to-end classification: when a new fungal strain is added to the reference database, no model retraining is required. The new strain's colony images are simply embedded and inserted into the vector index, making the system inherently scalable and suitable for the "long tail" of rare species that plague traditional classifiers.

## 2.2 Related Work

Current state-of-the-art in fungal identification often uses Convolutional Neural Networks (CNNs) such as ResNet~\cite{he2016resnet}, EfficientNet~\cite{tan2019efficientnet}, or Vision Transformers (ViTs). However, these models often struggle with the "long tail" of rare species where few training examples exist. Image retrieval via instance-based learning is more robust for these cases, as it only requires a few reference examples per species.

Recent work on content-based image retrieval (CBIR) for biological specimens demonstrates that combining hand-crafted features (HOG, Gabor filters, color histograms) with deep features can yield complementary improvements. Vector databases such as Qdrant enable low-latency cosine similarity search over high-dimensional embeddings, making retrieval-based classification practical at scale.

## 2.3 Methodology

The retrieval pipeline consists of four main stages: (1) preprocessing and colony segmentation, (2) feature extraction and embedding, (3) vector database indexing and retrieval, and (4) multi-image aggregation for strain-level prediction.

![System Overview](figures/query_flow.png)

### 2.3.1 Preprocessing Pipeline

Raw Petri dish images undergo a multi-stage preprocessing pipeline to isolate individual fungal colonies. Given an original microscopy image \(I_{\text{raw}} \in \mathbb{R}^{H \times W \times 3}\), the pipeline operates as follows:

**Stage 1 — Full-Image Preprocessing:**
1. **Resizing**: Images are standardized to \(256 \times 256\) pixels to ensure consistent input dimensions.
2. **Circle Detection**: The Hough Circle Transform detects the circular Petri dish boundary, producing a center \((c_x, c_y)\) and radius \(R\).
3. **Background Masking**: Pixels outside the detected dish are masked to black, removing irrelevant background (labels, shadows, bench surface).
4. **Cropping**: The dish region is extracted, discarding the remainder.

**Stage 2 — Colony Segmentation:**

Three complementary approaches were developed for colony segmentation:

#### K-Means Clustering Segmentation

The image is converted from RGB to HSV color space to better separate fungal colonies from the agar medium. A Gaussian blur with kernel size \(9 \times 9\) and \(\sigma = 1.5\) reduces high-frequency noise. K-Means clustering partitions pixels into foreground (colony) and background (agar) clusters.

A key innovation is the **Local K=2 Shrink** method, which addresses a specific failure mode: bright small colonies that produce light halos on certain media (notably MEA and YES). The flare phenomenon occurs when the agar near a colony appears bright, causing K-Means to group the halo with the colony foreground rather than the background. The Local K=2 method operates as follows:

For each candidate colony region \(R_i\) in HSV space:
1. Apply a second K=2 clustering on the V (value) channel pixels within \(R_i\) only.
2. Identify the bright cluster (higher mean V value) and the dim cluster.
3. Construct a mask retaining only pixels belonging to the bright cluster.
4. Shrink the mask via morphological erosion to remove borderline halo pixels.

This two-stage approach strips light halos from bright small colonies without affecting larger textured colonies, where the halo is already negligible relative to colony area.

\textbf{Limitation:} On plates with strong agar flare (e.g., certain YES medium images where the agar itself reflects light unevenly), K-Means occasionally misclassifies the flare region as foreground. This motivated exploration of the contour-based and YOLO-based alternatives described below.

#### Contour-Based Segmentation

An alternative segmentation pipeline based on edge detection was developed to bypass K-Means sensitivity to lighting:

1. **Canny Edge Detection**: Applied to the blurred grayscale image with thresholds \(t_{\text{low}} = 30\), \(t_{\text{high}} = 80\).
2. **Morphological Closing**: Dilation (\(5 \times 5\) kernel, 3 iterations) followed by erosion (\(3 \times 3\) kernel, 2 iterations) to seal gaps in colony edges.
3. **Circularity Filter**: Contours are scored by \(\text{area} \times \text{circularity}\), where circularity is defined as \(4\pi A / P^2\) (\(A\) = contour area, \(P\) = perimeter). A perfect circle scores 1.0. Contours are ranked and the top-3 are selected per dish, subject to area constraints (\(400 \leq A \leq 23,700\) px\(^2\)).
4. **Bounding Box Extraction**: For each selected contour, the axis-aligned bounding rectangle is computed; boxes with area below the minimum threshold are filtered.

This approach is more robust to uneven illumination but less reliable when colonies touch or overlap.

#### YOLO-Based Segmentation

To leverage modern deep learning for the segmentation task, a YOLOv8 instance segmentation model was prepared from a Roboflow COCO export and converted to an Ultralytics segmentation dataset inside the research pipeline.

- **Dataset source**: Roboflow COCO export with `train/`, `valid/`, and `test/` splits.
- **Conversion step**: polygons from `_annotations.coco.json` are converted to YOLO segmentation labels before training.
- **Model**: YOLOv8n-seg (nano variant, \(\sim\)3.2M parameters).
- **Verified smoke run**: 1 epoch, image size 640, batch size 2.
- **Verified metrics**: box mAP50 = 0.9522, box mAP50-95 = 0.7495, mask mAP50 = 0.9437, mask mAP50-95 = 0.6329.
- **Artifact**: `weights/segmentation/yolo_segmentation_best.pt`.

This smoke run verifies that the end-to-end COCO\(\rightarrow\)YOLO conversion, training, and checkpoint export path is working. A longer GPU run remains the next step for production-quality segmentation.

![Preprocessing Pipeline](figures/pipeline_montage.jpg)

### 2.3.2 Feature Extraction and Embedding

Each segmented colony image is passed through a feature extractor \(f_\theta: \mathbb{R}^{256 \times 256 \times 3} \to \mathbb{R}^d\) that maps the image to a high-dimensional embedding vector. All extracted features are L2-normalized to unit length for cosine similarity comparison:

\[
\mathbf{v} = \frac{f_\theta(\mathbf{x})}{\|f_\theta(\mathbf{x})\|_2}
\]

**Hand-Crafted Extractors:**

\begin{table}[h]
\centering
\caption{Summary of hand-crafted feature extractors}
\begin{tabular}{@{}lccc@{}}
\toprule
\textbf{Extractor} & \textbf{Dimension} \(d\) & \textbf{Captures} & \textbf{Accuracy} \\
\midrule
HOG & 3,780 & Edge orientation, shape structure & 52\% \\
Gabor & 40 & Texture at multiple frequencies/orientations & 55\% \\
ColorHist (RGB) & 96 & RGB color distribution (32 bins/channel) & -- \\
ColorHistHS & 64 & Hue/Saturation profile (32 bins each) & 65\% \\
\bottomrule
\end{tabular}
\end{table}

**Deep Learning Extractors:**

Three CNN architectures were evaluated, both pretrained on ImageNet-1K and fine-tuned on the fungal dataset:

\begin{table}[h]
\centering
\caption{Deep learning feature extractors: architecture and performance}
\begin{tabular}{@{}lcccc@{}}
\toprule
\textbf{Model} & \textbf{Parameters} & \textbf{Dim} \(d\) & \textbf{Accuracy} & \textbf{vs. Pretrained} \\
\midrule
ResNet50 (Pretrained) & 25.6M & 2,048 & 63\% & baseline \\
ResNet50 (Fine-tuned) & 25.6M & 2,048 & 78.6\% & +15.6\% \\
MobileNetV2 (Pretrained) & 3.5M & 1,280 & 60\% & baseline \\
MobileNetV2 (Fine-tuned) & 3.5M & 1,280 & 78.6\% & +18.6\% \\
EfficientNetB1 (Pretrained) & 7.8M & 1,280 & 63\% & baseline \\
\textbf{EfficientNetB1 (Fine-tuned)} & 7.8M & 1,280 & \textbf{83.3\%} & \textbf{+20.3\%} \\
HS+ResNet50 (Hybrid) & -- & 2,112 & 72\% & -- \\
\bottomrule
\end{tabular}
\end{table}

The hybrid HS+ResNet50 extractor concatenates ColorHistHS (64-dim) and ResNet50 (2,048-dim) features, with HS weighted 3.0\(\times\) before concatenation to balance the contribution of color and texture modalities.

**Fine-Tuning Methodology:**

The three CNN backbones were fine-tuned on the fungal dataset using supervised classification as a proxy task. Key training parameters:

\begin{table}[h]
\centering
\caption{Fine-tuning hyperparameters}
\begin{tabular}{@{}lll@{}}
\toprule
\textbf{Parameter} & \textbf{Value} & \textbf{Rationale} \\
\midrule
Batch size & 16 & Memory/gradient stability balance \\
Learning rate & 0.0001 & Conservative; prevents catastrophic forgetting \\
Optimizer & Adam & Adaptive learning, robust convergence \\
Loss function & CrossEntropyLoss & Standard multi-class \\
Max epochs & 50 & Early stopping prevents overtraining \\
Early stopping patience & 10 & Halts when validation plateaus \\
Augmentation & HFlip(0.5), Rot\(\pm\)10\(^\circ\) & Moderate to preserve morphology \\
\bottomrule
\end{tabular}
\end{table}

After training, the classification head is discarded; only the backbone encoder is retained for feature extraction. The training set comprised 1,011 images from 24 strains (8 species); the validation set used 294 images from 7 held-out test strains.

![Training Curves](figures/training_curves.png)

\begin{table}[h]
\centering
\caption{Training convergence summary}
\begin{tabular}{@{}lccc@{}}
\toprule
\textbf{Model} & \textbf{Training Time} & \textbf{Val Accuracy} & \textbf{Convergence Epoch} \\
\midrule
ResNet50 & \(\sim\)2 h & 78.6\% & 35 \\
MobileNetV2 & \(\sim\)1.5 h & 78.6\% & 25 \\
EfficientNetB1 & \(\sim\)2 h & 83.3\% & 35 \\
\bottomrule
\end{tabular}
\end{table}

**Alternative: Triplet Loss Training:**

A contrastive training approach using triplet margin loss was explored as a theoretically better fit for retrieval tasks. For each anchor image \(\mathbf{x}_a\), a positive \(\mathbf{x}_p\) (same species) and negative \(\mathbf{x}_n\) (different species) form a triplet. The loss optimizes:

\[
\mathcal{L}_{\text{triplet}} = \max\left(0,\; \|f(\mathbf{x}_a) - f(\mathbf{x}_p)\|_2 - \|f(\mathbf{x}_a) - f(\mathbf{x}_n)\|_2 + \alpha\right)
\]

with margin \(\alpha = 1.0\) and embedding dimension \(d = 128\).

\textbf{Result:} Triplet loss achieved only 64.3\% accuracy, a 19\% drop from cross-entropy fine-tuning. Analysis identified several causes:
\begin{itemize}
\item Small dataset (1,011 images): triplet loss typically requires 10\(\times\) more data than classification.
\item Reduced embedding dimension (128 vs. 1,280) limits representational capacity.
\item Random negative sampling without hard negative mining fails to push apart visually similar but different species.
\item Class imbalance: \textit{P. polonicum} (6 strains) dominates triplet sampling, biasing predictions.
\end{itemize}

The cross-entropy fine-tuning approach was therefore selected as the production method.

### 2.3.3 Vector Database Retrieval

All 1,305 segmented colony images from training strains are embedded and indexed in a Qdrant vector database. The database supports cosine similarity search with dynamic metadata filtering:

\begin{itemize}
\item \textbf{Collections:} `myco_fungi_features_full` (pretrained) and `myco_fungi_features_full_finetuned` (fine-tuned).
\item \textbf{Payload:} Strain ID, species label, growth medium, camera angle (ob/reverse), segment index.
\item \textbf{Multi-vector support:} Each image point can store vectors from multiple extractors simultaneously (ResNet50, EfficientNetB1, etc.).
\item \textbf{Dynamic filtering:} During evaluation, vectors belonging to the query strain are excluded to prevent data leakage ("sibling filtering").
\end{itemize}

For a query image \(\mathbf{x}_q\) with feature \(\mathbf{v}_q\), retrieval returns the top-\(k\) nearest neighbors:

\[
\mathcal{N}_k(\mathbf{v}_q) = \underset{\mathbf{v} \in \mathcal{D} \setminus \mathcal{D}_{\text{strain}}}{\text{argmax}^{(k)}} \;\frac{\mathbf{v}_q \cdot \mathbf{v}}{\|\mathbf{v}_q\| \cdot \|\mathbf{v}\|}
\]

where \(\mathcal{D}\) is the full database and \(\mathcal{D}_{\text{strain}}\) is the subset of vectors from the test strain.

### 2.3.4 Aggregation Strategy

A single strain produces multiple query segments (typically 18 segments: 3 colonies \(\times\) 2 angles \(\times\) 3 media conditions). Each segment independently retrieves \(k\) neighbors. Aggregation combines these results for a single strain-level prediction.

Let the strain produce \(m\) query segments, and let the \(i\)-th segment retrieve \(k\) neighbors with species labels \(c_{i,1}, \ldots, c_{i,k}\) and similarity scores \(s_{i,1}, \ldots, s_{i,k}\).

\textbf{Weighted Aggregation (default):} For each candidate species \(c\),

\[
S_c^{\text{weighted}} = \frac{\sum_{i=1}^{m} \sum_{j=1}^{k} s_{i,j} \cdot \mathbf{1}[c_{i,j} = c]}{\sum_{i=1}^{m} \sum_{j=1}^{k} \mathbf{1}[c_{i,j} = c]}
\]

This normalizes for species that may appear frequently but with low similarity (e.g., common but visually dissimilar species).

\textbf{Uniform Aggregation:} Simple voting counts occurrences:

\[
S_c^{\text{uni}} = \frac{1}{m \cdot k} \sum_{i=1}^{m} \sum_{j=1}^{k} \mathbf{1}[c_{i,j} = c]
\]

The weighted strategy is more robust to outliers and is used as the default.

The final predicted species is:

\[
\hat{c} = \underset{c}{\arg\max}\; S_c
\]

with confidence \(\text{conf}(\hat{c}) = S_{\hat{c}}\).

### 2.3.5 Environment Selection Strategies

To evaluate robustness across growth conditions, four testing strategies are employed:

\begin{table}[h]
\centering
\caption{Environment evaluation strategies}
\begin{tabular}{@{}llll@{}}
\toprule
\textbf{Strategy} & \textbf{Training Set} & \textbf{Test Set} & \textbf{Purpose} \\
\midrule
E1 (All) & All media & All media & Standard benchmark \\
E2 (Balanced) & All media & Equal per-media samples & Fair per-condition evaluation \\
E3 (Single-Env) & All media & One specific medium & Test single-condition robustness \\
E4 (Leave-One-Out) & All media & All except one medium & Test generalization with missing condition \\
\bottomrule
\end{tabular}
\end{table}

\textbf{Key finding:} E1 performs best. t-SNE visualizations (Section 2.4.6) confirm that fine-tuned models learn environment-invariant features, so training with all environments provides maximum diversity without introducing confusion.

### 2.3.6 Ensemble Methods

Multiple feature extractors can be combined via weighted score fusion. Given extractors \(f_1, f_2, \ldots, f_n\) with per-extractor scores \(S_c^{(t)}\) and weights \(w_t\):

\[
S_c^{\text{ensemble}} = \sum_{t=1}^{n} w_t \cdot S_c^{(t)}
\]

Analysis of complementary cases (where one extractor succeeds but another fails) informs weight tuning. For instance, EfficientNetB1 excels at texture discrimination while ColorHistHS captures color profiles critical for separating \textit{P. tricolor} (greenish) from \textit{P. viridicatum}.

## 2.4 Experiments and Results

### 2.4.1 Dataset and Split Strategy

\begin{table}[h]
\centering
\caption{Dataset statistics}
\begin{tabular}{@{}ll@{}}
\toprule
\textbf{Metric} & \textbf{Value} \\
\midrule
Total Petri dish images & 435 \\
Processed successfully & 435 (100\%) \\
Total colony segments & 1,305 \\
Failed segmentations & 0 \\
Species & 8 \textit{Penicillium} species \\
Training strains & 24 (1,011 segments) \\
Test strains & 7 (294 segments) \\
\bottomrule
\end{tabular}
\end{table}

The split is performed at the \textbf{strain level}: entire strains are held out from training, ensuring the model generalizes to novel strains rather than memorizing known ones. Test strains are strictly excluded from all training, fine-tuning, and database indexing. During retrieval evaluation, sibling filtering additionally removes segments from the same parent image as the query.

\begin{table}[h]
\centering
\caption{Species and strain distribution}
\begin{tabular}{@{}lcc@{}}
\toprule
\textbf{Species} & \textbf{Train Strains} & \textbf{Test Strain} \\
\midrule
\textit{P. aurantiogriseum} & 3 (DTO 457-A6, 470-H9, 473-D6) & DTO 469-I5 \\
\textit{P. cyclopium} & 1 (DTO 148-C8) & -- \\
\textit{P. freii} & 3 (DTO 162-C6, 470-A1, 470-A2) & DTO 469-I4 \\
\textit{P. melanoconidium} & 3 (DTO 148-D2, 216-I7, 470-H3) & DTO 158-D1 \\
\textit{P. neoechinulatum} & 3 (DTO 206-F5, 251-A1, 470-F3) & DTO 217-D9 \\
\textit{P. polonicum} & 6 (DTO 148-C9, 157-A3, ...) & DTO 148-D1 \\
\textit{P. tricolor} & 2 (DTO 157-A4, 472-B6) & DTO 470-I9 \\
\textit{P. viridicatum} & 3 (DTO 148-D3, 470-F1, 478-C6) & DTO 163-I2 \\
\bottomrule
\end{tabular}
\end{table}

Note: \textit{P. cyclopium} has only 1 strain and therefore cannot serve as a test strain under the strain-level split; it is used for training only.

### 2.4.2 Segmentation Experiments

K-Means segmentation parameters were swept to maximize colony extraction quality. The contour-based pipeline was tested as a complementary approach on images with strong agar flare.

The YOLOv8n-seg model was trained on a manually labeled subset. Key metrics:

\begin{table}[h]
\centering
\caption{Segmentation approach comparison}
\begin{tabular}{@{}lccc@{}}
\toprule
\textbf{Method} & \textbf{Colonies/Plate} & \textbf{Robust to Flare?} & \textbf{Requires Labels?} \\
\midrule
K-Means (K=2, HSV) & 3 & Partial (Local K=2 helps) & No \\
Contour (Canny + Circ.) & 2-3 & Yes (edge-based) & No \\
YOLOv8n-seg & Variable & Yes (learned) & Yes \\
\bottomrule
\end{tabular}
\end{table}

For downstream retrieval, the K-Means pipeline with Local K=2 Shrink was selected as the primary segmentation method. The YOLO-based approach is reserved for the cross-validation experiment pipeline where segmentation quality can be assessed per fold.

### 2.4.3 Retrieval Experiments: Staircase Chart

The primary metric for retrieval experiments is the F1 score, balancing precision and recall across species. An iterative autoresearch loop tested hundreds of combinations of distance metrics, aggregation strategies, and neighbor counts (\(k\)). Each combination is a single dot on the staircase chart.

The staircase chart (Figure~\ref{fig:staircase}) plots experiment index on the x-axis and F1 score on the y-axis. Gray dots represent experiments below the running best; green dots set a new best and step the staircase upward. Each green dot is labeled with the formula-algorithm pair that achieved the improvement.

![Staircase Chart](figures/staircase_retrieval.png)

### 2.4.4 Overall Performance Comparison

\begin{table}[h]
\centering
\caption{Comprehensive accuracy comparison across all feature extractors}
\begin{tabular}{@{}lcrr@{}}
\toprule
\textbf{Feature Extractor} & \textbf{Type} & \textbf{Accuracy} & \textbf{Improvement} \\
\midrule
\textbf{EfficientNetB1 (Fine-tuned)} & Deep Learning & \textbf{83.3\%} & +20.3\% \\
ResNet50 (Fine-tuned) & Deep Learning & 78.6\% & +15.6\% \\
MobileNetV2 (Fine-tuned) & Deep Learning & 78.6\% & +18.6\% \\
HS+ResNet50 & Hybrid & 72\% & -- \\
ColorHistHS & Hand-crafted & 65\% & -- \\
ResNet50 (Pretrained) & Deep Learning & 63\% & -- \\
EfficientNetB1 (Pretrained) & Deep Learning & 63\% & -- \\
MobileNetV2 (Pretrained) & Deep Learning & 60\% & -- \\
Gabor & Hand-crafted & 55\% & -- \\
HOG & Hand-crafted & 52\% & -- \\
Triplet Loss (EfficientNetB1) & Deep Learning & 64.3\% & -- \\
\bottomrule
\end{tabular}
\end{table}

Key insights:
\begin{enumerate}
\item \textbf{Fine-tuning is critical}: +15--20\% improvement over pretrained ImageNet models.
\item \textbf{EfficientNetB1 dominates}: 83.3\% accuracy with only 7.8M parameters.
\item \textbf{MobileNetV2 is efficient}: Matches ResNet50 (78.6\%) with 7\(\times\) fewer parameters (3.5M vs. 25.6M).
\item \textbf{Hand-crafted features plateau}: Maximum 65\% accuracy, insufficient alone.
\item \textbf{Triplet loss underperforms}: 19\% worse than cross-entropy, confirming that supervised fine-tuning is superior for small datasets.
\end{enumerate}

### 2.4.5 Cross-Validation Results

A 5-fold strain-level cross-validation experiment was conducted to assess stability and sensitivity to hyperparameters. Fixed extractor: EfficientNetB1 (Fine-tuned). Factors:

\[
\text{Folds} = 5,\quad \text{Env strategies} = 2\ (\text{E1, E2}),\quad \text{Agg strategies} = 2\ (\text{weighted, uni}),\quad K = \{3, 5, 7, 9, 11\}
\]

Total: \(5 \times 2 \times 2 \times 5 = 100\) runs.

![Accuracy vs K](figures/accuracy_vs_k.png)

\begin{table}[h]
\centering
\caption{Cross-validation top configurations}
\begin{tabular}{@{}lccrrr@{}}
\toprule
\textbf{Env} & \textbf{Agg} & \textbf{K} & \textbf{Mean Acc.} & \textbf{Std} & \textbf{Min} & \textbf{Max} \\
\midrule
E1 & weighted & 7 & 0.833 & 0.052 & 0.762 & 0.905 \\
E1 & weighted & 9 & 0.829 & 0.048 & 0.762 & 0.905 \\
E1 & uni & 5 & 0.810 & 0.065 & 0.714 & 0.905 \\
E1 & uni & 7 & 0.810 & 0.055 & 0.714 & 0.905 \\
E2 & weighted & 9 & 0.805 & 0.072 & 0.714 & 0.905 \\
\bottomrule
\end{tabular}
\end{table}

\textbf{Findings:}
\begin{itemize}
\item \textbf{E1 (all environments)} consistently outperforms E2 (balanced), confirming that environment diversity in training improves generalization.
\item \textbf{Weighted aggregation} outperforms uniform, especially at higher \(k\).
\item \textbf{\(k=7\)} is the sweet spot: smaller \(k\) is sensitive to noise, larger \(k\) risks including dissimilar neighbors.
\item \textbf{Stability}: Standard deviation across folds is 5--7\%, indicating robustness to which specific strains are held out.
\end{itemize}

![Fold Variance Box Plot](figures/fold_variance.png)

The fold variance box plot shows accuracy distributions for each configuration. E1/weighted configurations exhibit the tightest inter-quartile ranges, confirming stability.

![Heatmap: env \(\times\) strategy vs K](figures/heatmap_env_strategy_k.png)

![E1 vs E2 Bar Chart](figures/env_comparison.png)

### 2.4.6 Feature Space Analysis (t-SNE)

To understand feature quality, the 2,048-dimensional feature space from fine-tuned ResNet50 was projected to 2D using t-SNE (\(t\)-parameter = 30, perplexity = 40). Each point represents one segmented colony image.

\textbf{By Species} — The projection reveals clear species-level clustering:
\begin{itemize}
\item \textit{P. polonicum}, \textit{P. freii}, and \textit{P. neoechinulatum} form well-separated, compact clusters.
\item \textit{P. melanoconidium} and \textit{P. aurantiogriseum} show partial overlap, explaining their high confusion rate.
\item \textit{P. tricolor} and \textit{P. viridicatum} are adjacent but distinguishable, consistent with the 67\% and 83\% per-species accuracies.
\end{itemize}

\textbf{By Environment} — The same projection colored by growth medium shows \textbf{no environment-based clustering}: all media colors are uniformly distributed throughout the space. This is a \textbf{positive finding}—it confirms the model successfully learns environment-invariant, species-discriminative features. Training with all environments (E1) therefore maximizes diversity without introducing medium-specific confusion.

### 2.4.7 Confusion Matrix and Per-Species Analysis

\begin{table}[h]
\centering
\caption{Per-species accuracy — EfficientNetB1 (Fine-tuned)}
\begin{tabular}{@{}lccc@{}}
\toprule
\textbf{Species} & \textbf{Test Sets} & \textbf{Correct} & \textbf{Accuracy} \\
\midrule
\textit{P. polonicum} & 6 & 6 & 100\% \\
\textit{P. freii} & 6 & 6 & 100\% \\
\textit{P. neoechinulatum} & 6 & 6 & 100\% \\
\textit{P. aurantiogriseum} & 6 & 5 & 83\% \\
\textit{P. viridicatum} & 6 & 5 & 83\% \\
\textit{P. tricolor} & 6 & 4 & 67\% \\
\textit{P. melanoconidium} & 6 & 3 & 50\% \\
\midrule
\textbf{Total} & \textbf{42} & \textbf{35} & \textbf{83.3\%} \\
\bottomrule
\end{tabular}
\end{table}

Recurring confusion patterns:
\begin{itemize}
\item \textbf{\textit{P. melanoconidium} \(\leftrightarrow\) \textit{P. aurantiogriseum}}: Both produce dark colonies, causing reciprocal misclassification. \textit{P. melanoconidium} is the hardest species (50\%).
\item \textbf{\textit{P. tricolor} \(\leftrightarrow\) \textit{P. viridicatum}}: Shared greenish pigmentation leads to bidirectional confusion.
\item \textbf{\textit{P. aurantiogriseum} \(\leftrightarrow\) \textit{P. polonicum}}: Under certain growth conditions, similar texture and edge patterns cause rare misclassifications.
\end{itemize}

![Confusion Matrix](figures/confusion_matrix_efficientnetb1.png)

### 2.4.8 Prediction Examples

Visualizations show the query colony image (left) alongside its top-7 retrieved neighbors with similarity scores. Successful predictions (\(\text{accuracy} \geq 83\%\)) show high confidence (\(\geq 0.30\)) and visually consistent neighbors. Failed predictions show lower confidence (0.15--0.25) and mixed species among retrieved neighbors.

\begin{figure}[h]
\centering
\includegraphics[width=0.48\textwidth]{figures/pred_correct_example.jpg}
\includegraphics[width=0.48\textwidth]{figures/pred_incorrect_example.jpg}
\caption{Left: Correct prediction (\textit{P. polonicum} DTO 148-D1). Right: Incorrect prediction (\textit{P. melanoconidium} DTO 158-D1 misclassified as \textit{P. aurantiogriseum}).}
\end{figure}

## 2.5 Discussion

The results demonstrate that a retrieval-based classification system with fine-tuned deep features can achieve 83.3\% strain-level accuracy across 8 \textit{Penicillium} species. Several findings merit discussion:

\textbf{Fine-tuning is the single most impactful factor.} The 15--20\% improvement over ImageNet-pretrained features shows that domain adaptation—even with a modest 1,011 training images—is essential for microscopy images. The domain gap between natural photographs (ImageNet) and fungal colony microscopy is substantial.

\textbf{Environment-invariant learning emerges naturally.} The t-SNE analysis confirms that fine-tuned models ignore growth medium variations, a critical requirement for real-world deployment where a query strain may be cultivated on any medium. This justifies the E1 (all environments) training strategy.

\textbf{Efficient architectures are competitive.} MobileNetV2 matches ResNet50 with 7\(\times\) fewer parameters, making it suitable for edge deployment. EfficientNetB1 provides the best accuracy at a reasonable computational cost.

\textbf{The triplet loss result is a valuable negative finding.} Despite theoretical alignment with retrieval tasks, triplet loss severely underperformed (64.3\% vs. 83.3\%). This aligns with literature: triplet loss requires very large datasets and hard negative mining, neither of which was feasible with 1,011 training samples.

\textbf{Challenging species remain.} \textit{P. melanoconidium} at 50\% accuracy is the primary bottleneck. Potential solutions include collecting additional strains, implementing hard negative mining, or using a two-stage classifier (genus \(\to\) species).

\textbf{Segmentation quality matters.} The K-Means Local K=2 Shrink innovation successfully mitigates agar flare on most images, but plates with extreme lighting remain problematic. Future work could integrate the YOLO-based segmentation with larger manually labeled datasets.

\textbf{Model selection recommendations:}

\begin{table}[h]
\centering
\begin{tabular}{@{}lll@{}}
\toprule
\textbf{Use Case} & \textbf{Recommended Model} & \textbf{Accuracy} \\
\midrule
Maximum accuracy & EfficientNetB1 (Fine-tuned) & 83.3\% \\
Balanced performance & ResNet50 (Fine-tuned) & 78.6\% \\
Edge/mobile deployment & MobileNetV2 (Fine-tuned) & 78.6\% \\
\bottomrule
\end{tabular}
\end{table}
