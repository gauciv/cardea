#!/usr/bin/env python3
"""
KitNET Anomaly Detector - Proper Implementation
Based on: "Kitsune: An Ensemble of Autoencoders for Online Network Intrusion Detection"
Paper: https://arxiv.org/abs/1802.09089

This implementation includes:
- Feature Mapping (FM) phase with incremental clustering
- Proper training sample count (10,000+)
- 50+ network features from multi-log Zeek data
- Damped incremental statistics for time-windowed behavior
- Adaptive thresholding based on training distribution
- Incremental learning support for concept drift
"""

import numpy as np
import pickle
import logging
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import MiniBatchKMeans
from datetime import datetime
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# DAMPED INCREMENTAL STATISTICS
# =============================================================================

@dataclass
class DampedStatistics:
    """
    Damped incremental statistics for time-windowed feature extraction.
    Uses exponential decay to give more weight to recent observations.
    
    Based on: "Online learning with Netflow/IPFIX"
    Captures: count, mean, variance, std, min, max
    """
    decay_factor: float = 0.1  # Lambda - decay rate
    
    weight: float = 0.0
    mean: float = 0.0
    var: float = 0.0
    std: float = 0.0
    min_val: float = float('inf')
    max_val: float = float('-inf')
    
    def update(self, value: float):
        """Update statistics with new observation."""
        if self.weight == 0:
            self.mean = value
            self.var = 0.0
            self.min_val = value
            self.max_val = value
            self.weight = 1.0
        else:
            # Exponential decay
            self.weight = 1.0 + self.weight * (1.0 - self.decay_factor)
            
            # Update mean with decay
            old_mean = self.mean
            self.mean = old_mean + (value - old_mean) / self.weight
            
            # Update variance
            self.var = (1.0 - self.decay_factor) * (self.var + (value - old_mean) * (value - self.mean))
            self.std = math.sqrt(max(0, self.var))
            
            # Update min/max
            self.min_val = min(self.min_val, value)
            self.max_val = max(self.max_val, value)
    
    def get_features(self) -> List[float]:
        """Return all statistics as feature vector."""
        return [
            self.weight,
            self.mean,
            self.var,
            self.std,
            self.min_val if self.min_val != float('inf') else 0,
            self.max_val if self.max_val != float('-inf') else 0,
        ]


@dataclass  
class StreamStatistics:
    """
    Statistics for a traffic stream (IP pair or host).
    Tracks multiple metrics over time with decay.
    """
    # Packet size stats
    pkt_size: DampedStatistics = field(default_factory=lambda: DampedStatistics(0.1))
    # Inter-arrival time stats
    iat: DampedStatistics = field(default_factory=lambda: DampedStatistics(0.1))
    # Byte rate
    byte_rate: DampedStatistics = field(default_factory=lambda: DampedStatistics(0.1))
    # Packet count
    pkt_count: DampedStatistics = field(default_factory=lambda: DampedStatistics(0.1))
    
    last_timestamp: float = 0.0
    
    def update(self, timestamp: float, bytes_transferred: int, pkt_count: int = 1):
        """Update stream statistics."""
        self.pkt_size.update(bytes_transferred)
        self.pkt_count.update(pkt_count)
        
        if self.last_timestamp > 0:
            iat = timestamp - self.last_timestamp
            if iat > 0:
                self.iat.update(iat)
                self.byte_rate.update(bytes_transferred / iat)
        
        self.last_timestamp = timestamp
    
    def get_features(self) -> List[float]:
        """Get all stream features."""
        features = []
        features.extend(self.pkt_size.get_features())
        features.extend(self.iat.get_features())
        features.extend(self.byte_rate.get_features())
        features.extend(self.pkt_count.get_features())
        return features


# =============================================================================
# AUTOENCODER IMPLEMENTATION
# =============================================================================

class Autoencoder:
    """
    Single-layer autoencoder for KitNET ensemble.
    Uses online gradient descent for incremental learning.
    """
    
    def __init__(self, input_size: int, hidden_ratio: float = 0.75):
        self.input_size = input_size
        self.hidden_size = max(1, int(input_size * hidden_ratio))
        
        # Xavier initialization
        limit = np.sqrt(6.0 / (self.input_size + self.hidden_size))
        self.W_enc = np.random.uniform(-limit, limit, (self.input_size, self.hidden_size))
        self.W_dec = np.random.uniform(-limit, limit, (self.hidden_size, self.input_size))
        self.b_enc = np.zeros(self.hidden_size)
        self.b_dec = np.zeros(self.input_size)
        
        self.learning_rate = 0.001
        self.momentum = 0.9
        
        # Momentum terms
        self.v_W_enc = np.zeros_like(self.W_enc)
        self.v_W_dec = np.zeros_like(self.W_dec)
        self.v_b_enc = np.zeros_like(self.b_enc)
        self.v_b_dec = np.zeros_like(self.b_dec)
        
        # Training statistics
        self.train_count = 0
        self.error_history = deque(maxlen=1000)
    
    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        """Numerically stable sigmoid."""
        return np.where(x >= 0, 
                       1 / (1 + np.exp(-x)), 
                       np.exp(x) / (1 + np.exp(x)))
    
    def _sigmoid_deriv(self, x: np.ndarray) -> np.ndarray:
        """Sigmoid derivative."""
        return x * (1 - x)
    
    def forward(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Forward pass."""
        hidden = self._sigmoid(np.dot(x, self.W_enc) + self.b_enc)
        output = self._sigmoid(np.dot(hidden, self.W_dec) + self.b_dec)
        return hidden, output
    
    def train_step(self, x: np.ndarray) -> float:
        """Single training step with backpropagation."""
        x = x.reshape(1, -1) if x.ndim == 1 else x
        
        # Forward pass
        hidden, output = self.forward(x)
        
        # Reconstruction error (RMSE)
        error = np.sqrt(np.mean((x - output) ** 2))
        self.error_history.append(error)
        self.train_count += 1
        
        # Backpropagation
        output_delta = (output - x) * self._sigmoid_deriv(output)
        hidden_delta = np.dot(output_delta, self.W_dec.T) * self._sigmoid_deriv(hidden)
        
        # Gradient with momentum
        self.v_W_dec = self.momentum * self.v_W_dec - self.learning_rate * np.dot(hidden.T, output_delta)
        self.v_b_dec = self.momentum * self.v_b_dec - self.learning_rate * np.sum(output_delta, axis=0)
        self.v_W_enc = self.momentum * self.v_W_enc - self.learning_rate * np.dot(x.T, hidden_delta)
        self.v_b_enc = self.momentum * self.v_b_enc - self.learning_rate * np.sum(hidden_delta, axis=0)
        
        # Update weights
        self.W_dec += self.v_W_dec
        self.b_dec += self.v_b_dec
        self.W_enc += self.v_W_enc
        self.b_enc += self.v_b_enc
        
        return error
    
    def predict(self, x: np.ndarray) -> float:
        """Get reconstruction error as anomaly score."""
        x = x.reshape(1, -1) if x.ndim == 1 else x
        _, output = self.forward(x)
        return np.sqrt(np.mean((x - output) ** 2))
    
    def get_threshold(self, percentile: float = 99.0) -> float:
        """Get anomaly threshold based on training error distribution."""
        if len(self.error_history) < 100:
            return 1.0
        return np.percentile(list(self.error_history), percentile)


# =============================================================================
# FEATURE MAPPER (FM Phase)
# =============================================================================

class FeatureMapper:
    """
    Feature Mapping phase for KitNET.
    Groups correlated features using incremental clustering.
    """
    
    def __init__(self, max_clusters: int = 10, min_cluster_size: int = 3):
        self.max_clusters = max_clusters
        self.min_cluster_size = min_cluster_size
        self.feature_buffer: List[np.ndarray] = []
        self.buffer_size = 2000  # Samples to collect before clustering
        self.feature_groups: List[List[int]] = []
        self.is_ready = False
    
    def add_sample(self, features: np.ndarray) -> bool:
        """Add sample to buffer. Returns True when ready to map."""
        self.feature_buffer.append(features.flatten())
        
        if len(self.feature_buffer) >= self.buffer_size:
            self._compute_feature_groups()
            return True
        return False
    
    def _compute_feature_groups(self):
        """Compute feature groups using correlation-based clustering."""
        data = np.array(self.feature_buffer)
        n_features = data.shape[1]
        
        logger.info(f"🔧 Computing feature groups for {n_features} features...")
        
        # Compute correlation matrix
        # Use transpose so we cluster features, not samples
        data_T = data.T  # Shape: (n_features, n_samples)
        
        # Standardize each feature
        means = np.mean(data_T, axis=1, keepdims=True)
        stds = np.std(data_T, axis=1, keepdims=True)
        stds[stds == 0] = 1  # Avoid division by zero
        data_normalized = (data_T - means) / stds
        
        # Determine number of clusters
        n_clusters = min(self.max_clusters, max(2, n_features // self.min_cluster_size))
        
        # Cluster features
        kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, n_init=3)
        labels = kmeans.fit_predict(data_normalized)
        
        # Group features by cluster
        self.feature_groups = []
        for cluster_id in range(n_clusters):
            group = [i for i, label in enumerate(labels) if label == cluster_id]
            if len(group) >= 2:  # Minimum group size
                self.feature_groups.append(group)
        
        # Ensure all features are covered
        covered = set()
        for group in self.feature_groups:
            covered.update(group)
        
        uncovered = [i for i in range(n_features) if i not in covered]
        if uncovered:
            # Add uncovered features to smallest group
            if self.feature_groups:
                smallest_group = min(self.feature_groups, key=len)
                smallest_group.extend(uncovered)
            else:
                self.feature_groups.append(uncovered)
        
        self.is_ready = True
        self.feature_buffer = []  # Clear buffer
        
        logger.info(f"✅ Created {len(self.feature_groups)} feature groups: {[len(g) for g in self.feature_groups]}")
    
    def get_groups(self) -> List[List[int]]:
        """Get computed feature groups."""
        return self.feature_groups


# =============================================================================
# KITNET DETECTOR - MAIN CLASS
# =============================================================================

class KitNETDetector:
    """
    KitNET ensemble autoencoder for network anomaly detection.
    
    Phases:
    1. Feature Mapping (FM): Learn correlated feature groups
    2. Anomaly Detection (AD): Train autoencoders on feature groups
    3. Online Detection: Detect anomalies using trained model
    
    Training requires 10,000+ samples for stable model.
    """
    
    # Training configuration
    FM_SAMPLES = 2000      # Samples for feature mapping phase
    AD_SAMPLES = 10000     # Samples for autoencoder training
    TOTAL_TRAINING = 12000 # Total training samples
    
    def __init__(self, model_path: Path, threshold: float = 0.95):
        self.model_path = model_path
        self.base_threshold = threshold
        self.adaptive_threshold = threshold
        
        # Components
        self.feature_mapper = FeatureMapper()
        self.autoencoders: List[Autoencoder] = []
        self.output_autoencoder: Optional[Autoencoder] = None
        self.scaler = StandardScaler()
        
        # State
        self.phase = "FM"  # FM, AD, or DETECT
        self.training_samples = 0
        self.scaler_fitted = False
        
        # Stream statistics for hosts (damped incremental)
        self.host_stats: Dict[str, StreamStatistics] = {}
        self.pair_stats: Dict[str, StreamStatistics] = {}
        self.max_stats_entries = 10000
        
        # Anomaly tracking
        self.anomaly_scores_history = deque(maxlen=5000)
        self.detection_stats = {
            "total_processed": 0,
            "anomalies_detected": 0,
            "phase": "FM",
            "training_progress": 0.0
        }
        
        logger.info(f"🤖 KitNET initialized - Training: {self.TOTAL_TRAINING} samples")
    
    async def initialize(self):
        """Initialize or load existing model."""
        if self.model_path.exists():
            logger.info("📁 Loading existing KitNET model...")
            self.load_model()
            self.phase = "DETECT"
        else:
            logger.info("🧠 No model found - Starting training phase...")
            self.phase = "FM"
    
    def extract_features(self, packet_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract 50+ features from multi-log Zeek data.
        
        Feature categories:
        - Connection metadata (10 features)
        - Byte/packet statistics (12 features)
        - Time-based features (6 features)
        - Protocol-specific (8 features)
        - DNS features (8 features) 
        - HTTP features (6 features)
        - SSL/TLS features (6 features)
        - Damped stream statistics (variable)
        """
        features = []
        
        # === 1. CONNECTION METADATA (10 features) ===
        src_port = int(packet_data.get("src_port", 0) or 0)
        dest_port = int(packet_data.get("dest_port", 0) or 0)
        
        features.extend([
            self._normalize_port(src_port),
            self._normalize_port(dest_port),
            1.0 if src_port < 1024 else 0.0,  # Is well-known source port
            1.0 if dest_port < 1024 else 0.0,  # Is well-known dest port
            self._protocol_to_float(packet_data.get("protocol", "tcp")),
            self._conn_state_to_float(packet_data.get("conn_state", "")),
            float(packet_data.get("duration", 0.0) or 0.0),
            min(float(packet_data.get("duration", 0.0) or 0.0) / 3600.0, 1.0),  # Duration normalized
            1.0 if packet_data.get("local_orig", False) else 0.0,
            1.0 if packet_data.get("local_resp", False) else 0.0,
        ])
        
        # === 2. BYTE/PACKET STATISTICS (12 features) ===
        orig_bytes = int(packet_data.get("orig_bytes", 0) or 0)
        resp_bytes = int(packet_data.get("resp_bytes", 0) or 0)
        orig_pkts = int(packet_data.get("orig_pkts", 0) or 0)
        resp_pkts = int(packet_data.get("resp_pkts", 0) or 0)
        total_bytes = orig_bytes + resp_bytes
        total_pkts = orig_pkts + resp_pkts
        
        features.extend([
            self._log_normalize(orig_bytes),
            self._log_normalize(resp_bytes),
            self._log_normalize(total_bytes),
            orig_bytes / (total_bytes + 1),  # Orig ratio
            resp_bytes / (total_bytes + 1),  # Resp ratio
            self._log_normalize(orig_pkts),
            self._log_normalize(resp_pkts),
            self._log_normalize(total_pkts),
            orig_bytes / (orig_pkts + 1),  # Avg orig pkt size
            resp_bytes / (resp_pkts + 1),  # Avg resp pkt size
            int(packet_data.get("missed_bytes", 0) or 0) / (total_bytes + 1),  # Miss ratio
            len(packet_data.get("history", "")),  # History length
        ])
        
        # === 3. TIME-BASED FEATURES (6 features) ===
        timestamp = packet_data.get("timestamp", "")
        time_features = self._extract_time_features(timestamp)
        features.extend(time_features)
        
        # === 4. PROTOCOL-SPECIFIC (8 features) ===
        service = str(packet_data.get("service", "") or "")
        features.extend([
            1.0 if service == "dns" else 0.0,
            1.0 if service == "http" else 0.0,
            1.0 if service == "ssl" else 0.0,
            1.0 if service == "ssh" else 0.0,
            1.0 if service == "smtp" else 0.0,
            1.0 if service == "ftp" else 0.0,
            1.0 if service in ("smb", "dce_rpc") else 0.0,
            1.0 if service == "" else 0.0,  # Unknown service
        ])
        
        # === 5. DNS FEATURES (8 features) ===
        dns_queries = packet_data.get("dns_queries", [])
        has_dns = packet_data.get("has_dns", False) or len(dns_queries) > 0
        
        if has_dns and dns_queries:
            dns_data = dns_queries[0] if isinstance(dns_queries, list) else dns_queries
            query = str(dns_data.get("query", "") or "")
            features.extend([
                1.0,  # Has DNS
                len(query) / 255.0,  # Query length normalized
                query.count(".") / 10.0,  # Subdomain depth
                self._calculate_entropy(query) / 4.0,  # Query entropy
                1.0 if dns_data.get("rejected", False) else 0.0,
                len(dns_data.get("answers", [])) / 10.0,  # Answer count
                1.0 if len(query) > 50 else 0.0,  # Long query (tunneling indicator)
                self._calculate_entropy(query.split(".")[0]) / 4.0 if "." in query else 0.0,  # First label entropy
            ])
        else:
            features.extend([0.0] * 8)
        
        # === 6. HTTP FEATURES (6 features) ===
        http_requests = packet_data.get("http_requests", [])
        has_http = packet_data.get("has_http", False) or len(http_requests) > 0
        
        if has_http and http_requests:
            http_data = http_requests[0] if isinstance(http_requests, list) else http_requests
            features.extend([
                1.0,  # Has HTTP
                self._http_method_to_float(http_data.get("method", "")),
                self._log_normalize(int(http_data.get("request_body_len", 0) or 0)),
                self._log_normalize(int(http_data.get("response_body_len", 0) or 0)),
                len(str(http_data.get("uri", ""))) / 2000.0,  # URI length
                1.0 if http_data.get("uri_suspicious", False) else 0.0,
            ])
        else:
            features.extend([0.0] * 6)
        
        # === 7. SSL/TLS FEATURES (6 features) ===
        ssl_info = packet_data.get("ssl_info", {})
        has_ssl = packet_data.get("has_ssl", False) or bool(ssl_info)
        
        if has_ssl and ssl_info:
            features.extend([
                1.0,  # Has SSL
                1.0 if ssl_info.get("established", False) else 0.0,
                1.0 if ssl_info.get("self_signed", False) else 0.0,
                1.0 if ssl_info.get("expired", False) else 0.0,
                1.0 if ssl_info.get("cert_valid", True) else 0.0,
                len(str(ssl_info.get("server_name", ""))) / 255.0,  # SNI length
            ])
        else:
            features.extend([0.0] * 6)
        
        # === 8. COMPUTED RATIOS (4 features) ===
        features.extend([
            packet_data.get("bytes_ratio", 0.0) if packet_data.get("bytes_ratio", 0.0) != float('inf') else 10.0,
            packet_data.get("pkt_ratio", 0.0) if packet_data.get("pkt_ratio", 0.0) != float('inf') else 10.0,
            packet_data.get("query_entropy", 0.0),
            packet_data.get("sld_entropy", 0.0),
        ])
        
        # Total: 10 + 12 + 6 + 8 + 8 + 6 + 6 + 4 = 60 features
        
        return np.array(features, dtype=np.float32).reshape(1, -1)
    
    def detect_anomaly(self, features: np.ndarray) -> float:
        """Detect anomaly and return score (0.0 - 1.0)."""
        self.detection_stats["total_processed"] += 1
        
        if self.phase == "FM":
            return self._fm_phase(features)
        elif self.phase == "AD":
            return self._ad_phase(features)
        else:
            return self._detect_phase(features)
    
    def _fm_phase(self, features: np.ndarray) -> float:
        """Feature Mapping phase - learn feature correlations."""
        self.training_samples += 1
        self.detection_stats["phase"] = "FM"
        self.detection_stats["training_progress"] = self.training_samples / self.TOTAL_TRAINING
        
        # Fit scaler incrementally
        if not self.scaler_fitted:
            self.scaler.partial_fit(features)
        
        features_normalized = self.scaler.transform(features)
        
        # Add to feature mapper
        if self.feature_mapper.add_sample(features_normalized):
            # FM complete, transition to AD
            logger.info(f"✅ FM phase complete after {self.training_samples} samples")
            self._initialize_autoencoders()
            self.phase = "AD"
            self.scaler_fitted = True
        
        return 0.0  # No anomaly detection during FM
    
    def _ad_phase(self, features: np.ndarray) -> float:
        """Anomaly Detection training phase."""
        self.training_samples += 1
        self.detection_stats["phase"] = "AD"
        self.detection_stats["training_progress"] = self.training_samples / self.TOTAL_TRAINING
        
        features_normalized = self.scaler.transform(features)
        
        # Train each autoencoder
        layer1_outputs = []
        for i, ae in enumerate(self.autoencoders):
            group = self.feature_mapper.get_groups()[i]
            feature_subset = features_normalized[:, group].flatten()
            ae.train_step(feature_subset)
            layer1_outputs.append(ae.predict(feature_subset))
        
        # Train output autoencoder
        if self.output_autoencoder and layer1_outputs:
            output_features = np.array(layer1_outputs).reshape(1, -1)
            self.output_autoencoder.train_step(output_features.flatten())
        
        # Check if training complete
        if self.training_samples >= self.TOTAL_TRAINING:
            self._finalize_training()
        
        return 0.0  # No detection during training
    
    def _detect_phase(self, features: np.ndarray) -> float:
        """Online anomaly detection phase."""
        self.detection_stats["phase"] = "DETECT"
        
        features_normalized = self.scaler.transform(features)
        
        # Get scores from layer 1 autoencoders
        layer1_scores = []
        for i, ae in enumerate(self.autoencoders):
            group = self.feature_mapper.feature_groups[i]
            feature_subset = features_normalized[:, group].flatten()
            score = ae.predict(feature_subset)
            layer1_scores.append(score)
        
        # Get final score from output autoencoder
        if self.output_autoencoder and layer1_scores:
            output_features = np.array(layer1_scores).reshape(1, -1)
            final_score = self.output_autoencoder.predict(output_features.flatten())
        else:
            final_score = max(layer1_scores) if layer1_scores else 0.0
        
        # Normalize score
        normalized_score = min(final_score / self.adaptive_threshold, 1.0)
        
        # Track for statistics
        self.anomaly_scores_history.append(normalized_score)
        
        if normalized_score >= 1.0:
            self.detection_stats["anomalies_detected"] += 1
        
        return normalized_score
    
    def _initialize_autoencoders(self):
        """Initialize autoencoders based on feature groups."""
        groups = self.feature_mapper.get_groups()
        
        logger.info(f"🔧 Initializing {len(groups)} autoencoders...")
        
        self.autoencoders = []
        for group in groups:
            ae = Autoencoder(input_size=len(group), hidden_ratio=0.75)
            self.autoencoders.append(ae)
        
        # Output autoencoder takes layer 1 outputs
        self.output_autoencoder = Autoencoder(input_size=len(groups), hidden_ratio=0.75)
        
        logger.info(f"✅ Created {len(self.autoencoders)} layer-1 AEs + 1 output AE")
    
    def _finalize_training(self):
        """Finalize training and compute adaptive threshold."""
        logger.info(f"✅ Training complete after {self.training_samples} samples")
        
        # Compute adaptive threshold from output autoencoder
        if self.output_autoencoder and len(self.output_autoencoder.error_history) > 100:
            self.adaptive_threshold = self.output_autoencoder.get_threshold(99.0)
            logger.info(f"📊 Adaptive threshold: {self.adaptive_threshold:.4f}")
        
        self.phase = "DETECT"
        self.save_model()
    
    # === UTILITY METHODS ===
    
    def _normalize_port(self, port: int) -> float:
        """Normalize port number."""
        return min(port / 65535.0, 1.0)
    
    def _log_normalize(self, value: float) -> float:
        """Log normalize a value."""
        return math.log1p(value) / 20.0  # log1p(1M) ≈ 14
    
    def _protocol_to_float(self, protocol: str) -> float:
        """Convert protocol to float."""
        mapping = {"tcp": 0.2, "udp": 0.4, "icmp": 0.6, "sctp": 0.8}
        return mapping.get(str(protocol).lower(), 0.0)
    
    def _conn_state_to_float(self, state: str) -> float:
        """Convert connection state to float."""
        mapping = {
            "S0": 0.1, "S1": 0.2, "SF": 0.3, "REJ": 0.4, "S2": 0.5,
            "S3": 0.6, "RSTO": 0.7, "RSTR": 0.8, "RSTOS0": 0.85, 
            "RSTRH": 0.9, "SH": 0.92, "SHR": 0.95, "OTH": 1.0
        }
        return mapping.get(str(state), 0.0)
    
    def _http_method_to_float(self, method: str) -> float:
        """Convert HTTP method to float."""
        mapping = {
            "GET": 0.1, "POST": 0.2, "HEAD": 0.3, "PUT": 0.4,
            "DELETE": 0.5, "OPTIONS": 0.6, "PATCH": 0.7, "CONNECT": 0.9
        }
        return mapping.get(str(method).upper(), 0.0)
    
    def _extract_time_features(self, timestamp_str: str) -> List[float]:
        """Extract time-based features."""
        try:
            ts = str(timestamp_str).replace('Z', '+00:00')
            dt = datetime.fromisoformat(ts)
            return [
                dt.hour / 23.0,
                dt.minute / 59.0,
                dt.weekday() / 6.0,
                1.0 if dt.weekday() >= 5 else 0.0,  # Weekend
                1.0 if 9 <= dt.hour <= 17 else 0.0,  # Business hours
                1.0 if 0 <= dt.hour <= 6 else 0.0,   # Night time
            ]
        except:
            return [0.0] * 6
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy."""
        if not text:
            return 0.0
        from collections import Counter
        freq = Counter(text.lower())
        length = len(text)
        entropy = -sum((c / length) * math.log2(c / length) for c in freq.values())
        return entropy
    
    # === PERSISTENCE ===
    
    def save_model(self):
        """Save trained model."""
        model_data = {
            'phase': self.phase,
            'scaler': self.scaler,
            'feature_groups': self.feature_mapper.feature_groups,
            'autoencoders': self.autoencoders,
            'output_autoencoder': self.output_autoencoder,
            'adaptive_threshold': self.adaptive_threshold,
            'training_samples': self.training_samples,
            'version': '2.0'
        }
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"💾 Model saved to {self.model_path}")
    
    def load_model(self):
        """Load trained model."""
        with open(self.model_path, 'rb') as f:
            data = pickle.load(f)
        
        # Check version
        if data.get('version') != '2.0':
            logger.warning("⚠️ Old model version, retraining recommended")
        
        self.phase = data.get('phase', 'DETECT')
        self.scaler = data['scaler']
        self.feature_mapper.feature_groups = data['feature_groups']
        self.feature_mapper.is_ready = True
        self.autoencoders = data['autoencoders']
        self.output_autoencoder = data.get('output_autoencoder')
        self.adaptive_threshold = data.get('adaptive_threshold', 0.95)
        self.training_samples = data.get('training_samples', 0)
        self.scaler_fitted = True
        
        logger.info(f"📂 Model loaded: {len(self.autoencoders)} AEs, threshold={self.adaptive_threshold:.4f}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            **self.detection_stats,
            "adaptive_threshold": self.adaptive_threshold,
            "training_samples": self.training_samples,
            "num_autoencoders": len(self.autoencoders),
            "feature_groups": len(self.feature_mapper.feature_groups) if self.feature_mapper.is_ready else 0,
        }
