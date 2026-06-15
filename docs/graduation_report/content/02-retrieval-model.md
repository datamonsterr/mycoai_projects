# Chapter 2: Fungal Species Retrieval Model

## 2.1 Motivation
Traditional fungal identification relies on morphological features which can be subtle. By utilizing deep learning embeddings, the system can capture complex visual patterns that are invariant to minor lighting or scale changes, providing a "similarity search" that mimics how mycologists compare unknown samples to known reference slides.

## 2.2 Related Work
Current state-of-the-art in fungal ID often uses Convolutional Neural Networks (CNNs) or Vision Transformers (ViTs). However, these models often struggle with the "long tail" of rare species. Image retrieval (Instance-based learning) is more robust for these cases as it only requires a few reference examples per species.

## 2.3 Methodology
The retrieval pipeline consists of three main stages:

### 2.3.1 K-Means Segmentation
To remove background noise and focus on the fungal colony, a K-means clustering algorithm is applied to the image. The process involves a median blur to flatten texture, followed by a Gaussian blur to smooth the image.

A key innovation is the **Local K=2 Shrink** method, which strips light halos from bright small colonies without affecting larger textured colonies:

\begin{lstlisting}[language=Python, caption=K-means Local K=2 Shrink Logic]
# Local K=2 to separate bright core from dimmer halo
labels = KMeans(n_clusters=2, random_state=0, n_init=5).fit_predict(v_channel)
cluster0_mean = float(v_channel[labels == 0].mean())
cluster1_mean = float(v_channel[labels == 1].mean())
bright_label = 0 if cluster0_mean >= cluster1_mean else 1
# Build a mask of just the bright pixels
bright_mask = (labels == bright_label).reshape(roi_hsv.shape[:2]).astype(np.uint8) * 255
\end{lstlisting}

### 2.3.2 Feature Extraction & Embedding
The cropped colony images are passed through a pre-trained feature extractor (e.g., a Vision Transformer or ResNet variant) to produce a high-dimensional embedding vector. This vector represents the "visual fingerprint" of the fungal colony.

### 2.3.3 KNN Strategies
To improve accuracy, the system implements two retrieval strategies:
- **Same-media KNN**: Search restricted to the same growth medium.
- **All-media KNN**: Search across the entire reference database.

The final species prediction is derived by aggregating results from multiple segments using either a **weighted** (score-based) or **uni** (count-based) strategy:

\begin{lstlisting}[language=Python, caption=KNN Prediction Aggregation]
for specy, total_score in species_scores.items():
    if strategy == "weighted":
        final_score = total_score / total_neighbors if total_neighbors > 0 else 0.0
    elif strategy == "uni":
        count = species_counts[specy]
        final_score = count / total_neighbors if total_neighbors > 0 else 0.0
    aggregated.append((specy, final_score))
\end{lstlisting}

## 2.4 Experiments & Results
### 2.4.1 Experiment Setup
Experiments were conducted using the `research/` module, employing an iterative autoresearch loop. The primary metric used was the **F1 Score**, balancing precision and recall across different species.

### 2.4.2 Segmentation Experiments
The K-means approach was tested against various cluster counts (k) and preprocessing filters to maximize the IoU (Intersection over Union) with ground-truth colony masks.

### 2.4.3 Retrieval Experiments
The "Staircase Chart" method was used to track the best performing formulas and algorithms. By iterating through hundreds of combinations of distance metrics and aggregation strategies, the system achieved a peak F1 score (as documented in `results/autoresearch/retrieval.csv`).

## 2.5 Discussion
The results demonstrate that the Same-media KNN strategy significantly outperforms the All-media approach, proving that growth medium is a critical latent variable in fungal morphology.
