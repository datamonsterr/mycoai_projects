# Chapter 3: Web Application

## 3.1 Requirements Analysis
The system requirements are defined in `docs/SRS.md`, focusing on two primary actors: the **User** and the **Data Owner**.

### 3.1.1 Functional Requirements
- **UC-RETRIEVE-01**: The core workflow where users upload images, review segmentation, and receive ranked species predictions.
- **UC-DATA-01**: Allows the Data Owner to index new reference data, ensuring the retrieval database stays current.
- **UC-MODEL-01**: Provides tools for the Data Owner to evaluate and promote "Candidate Models" to the production index.

### 3.1.2 Non-Functional Requirements
- **Performance**: Retrieval must complete within 5 seconds.
- **Security**: Implementation of JWT-based authentication and Role-Based Access Control (RBAC) to protect sensitive dataset mutations.
- **Auditability**: Every change made by a Data Owner is recorded in an audit log.

## 3.2 High-Level Architecture
The system follows a decoupled client-server architecture:
- **Frontend**: Built with **React 19** and **Vite**, utilizing a scientist-facing design language for high-density data display.
- **Backend**: A **FastAPI** server that orchestrates communication between the frontend, the vector store, and the relational database.

## 3.3 Database Design & Optimization
### 3.3.1 Relational Database (PostgreSQL)
Used for structured data:
- `users`: Authentication and role management.
- `species` & `media`: Managed catalogs of fungal taxa and growth media.
- `dataset_items`: Metadata linking images to their species and strains.

### 3.3.2 Vector Database (Qdrant)
Used for high-dimensional search:
- Stores embeddings of the reference dataset.
- Enables payload filtering (e.g., `where media == 'PDA'`) during the KNN search.

### 3.3.3 Why Dual-DB?
A single database cannot efficiently handle both complex relational queries and high-dimensional vector searches. PostgreSQL provides the necessary consistency for governance, while Qdrant provides the sub-second latency required for retrieval.

## 3.4 API Design
The API utilizes an asynchronous job pattern for long-running retrieval tasks to prevent request timeouts.

\begin{lstlisting}[language=Python, caption=Asynchronous Retrieval Endpoint]
@router.post("/query", response_model=RetrievalJobResponse, status_code=202)
def start_query(data: RetrievalQueryRequest, user: User = Depends(get_current_user)) -> dict:
    job_id = new_id()
    job = {
        "id": job_id,
        "status": "processing",
        "config": data.model_dump(),
        "created_at": utcnow(),
    }
    get_retrieval_job_store().put(job)
    return {"job_id": job_id, "status": "processing"}
\end{lstlisting}

### 3.4.1 Authentication
JWT implementation and RBAC.

### 3.4.2 Retrieval Endpoint
Design of the `/retrieve` endpoint.

### 3.4.3 Indexing Endpoint
Design of the `/index` endpoint.

## 3.5 UI/UX Design
The UI is optimized for a research workflow:
- **Upload Interface**: Supports both single-image and batch-folder uploads.
- **Segmentation Review**: An interactive canvas allowing users to drag and resize bounding boxes before final prediction.
- **Results View**: Displays ranked species with confidence scores and visual matches from the reference set.
