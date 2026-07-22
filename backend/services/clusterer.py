import logging
import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans
from backend.config import (
    CLUSTER_MIN_CHUNKS,
    CLUSTER_MIN_CLUSTERS,
    CLUSTER_MAX_CLUSTERS,
    CLUSTER_UMAP_COMPONENTS,
)

logger = logging.getLogger(__name__)


def _reduce_dims(embeddings: np.ndarray, n_components: int) -> np.ndarray:
    n_samples = len(embeddings)
    n_features = embeddings.shape[1]
    n = min(n_components, n_features, n_samples - 1)

    if n < 1 or n_samples < 3:
        logger.info("Too few samples for dim reduction (%d), using raw embeddings", n_samples)
        return embeddings

    if n_samples <= 15:
        from sklearn.decomposition import PCA

        pca = PCA(n_components=n, random_state=42)
        return pca.fit_transform(embeddings)

    try:
        import umap

        reducer = umap.UMAP(
            n_components=n,
            random_state=42,
            n_neighbors=max(2, min(15, n_samples - 1)),
            min_dist=0.0,
        )
        return reducer.fit_transform(embeddings)
    except ImportError:
        logger.warning("umap-learn not installed, falling back to PCA")
        from sklearn.decomposition import PCA

        pca = PCA(n_components=n, random_state=42)
        return pca.fit_transform(embeddings)
    except Exception as e:
        logger.warning("UMAP failed (%s), falling back to PCA", e)
        from sklearn.decomposition import PCA

        pca = PCA(n_components=n, random_state=42)
        return pca.fit_transform(embeddings)


def _optimal_n_clusters(embeddings_reduced: np.ndarray) -> int:
    max_clusters = min(CLUSTER_MAX_CLUSTERS, len(embeddings_reduced) // 2)
    min_clusters = min(CLUSTER_MIN_CLUSTERS, max_clusters)

    if max_clusters <= min_clusters:
        return max_clusters

    best_k = min_clusters
    best_bic = float("inf")

    for k in range(min_clusters, max_clusters + 1):
        gmm = GaussianMixture(n_components=k, random_state=42, max_iter=100, n_init=3)
        gmm.fit(embeddings_reduced)
        bic = gmm.bic(embeddings_reduced)
        if bic < best_bic:
            best_bic = bic
            best_k = k

    return best_k


def _cluster_with_gmm(embeddings_reduced: np.ndarray, n_clusters: int) -> np.ndarray:
    try:
        gmm = GaussianMixture(n_components=n_clusters, random_state=42, max_iter=200, n_init=5)
        gmm.fit(embeddings_reduced)
        return gmm.predict(embeddings_reduced)
    except Exception as e:
        logger.warning("GMM failed (%s), falling back to KMeans", e)
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=5)
        return km.fit_predict(embeddings_reduced)


def cluster_chunks(
    texts: list[str],
    embeddings: np.ndarray,
) -> list[dict]:
    if len(texts) < CLUSTER_MIN_CHUNKS:
        logger.info("Only %d chunks, skipping clustering", len(texts))
        return [{"cluster_id": 0, "texts": texts, "indices": list(range(len(texts)))}]

    n_components = min(CLUSTER_UMAP_COMPONENTS, len(texts) - 1, embeddings.shape[1])
    logger.info("Reducing %d dims to %d with UMAP", embeddings.shape[1], n_components)
    reduced = _reduce_dims(embeddings, n_components)

    n_clusters = _optimal_n_clusters(reduced)
    logger.info("Optimal clusters via BIC: %d", n_clusters)

    labels = _cluster_with_gmm(reduced, n_clusters)

    clusters_dict: dict[int, dict] = {}
    for idx, label in enumerate(labels):
        if label not in clusters_dict:
            clusters_dict[label] = {"cluster_id": int(label), "texts": [], "indices": []}
        clusters_dict[label]["texts"].append(texts[idx])
        clusters_dict[label]["indices"].append(idx)

    result = sorted(clusters_dict.values(), key=lambda c: c["cluster_id"])
    logger.info("Clustering produced %d clusters", len(result))
    for c in result:
        logger.debug("  Cluster %d: %d chunks", c["cluster_id"], len(c["texts"]))
    return result
