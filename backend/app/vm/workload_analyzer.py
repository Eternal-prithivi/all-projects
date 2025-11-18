# backend/app/vm/workload_analyzer.py
"""
Analyzes user workload descriptions and recommends optimal cluster assignment.
"""

import re
from typing import Dict, Tuple
from app.vm.models import ClusterType


class WorkloadAnalyzer:
    """
    Classifies user workloads and recommends appropriate VM clusters.
    Uses keyword matching and pattern recognition.
    """
    
    # Keywords that indicate general/performance workloads
    GENERAL_KEYWORDS = [
        'web', 'app', 'application', 'api', 'server', 'backend', 'frontend',
        'compute', 'cpu', 'processing', 'calculation', 'machine learning',
        'ml', 'ai', 'training', 'model', 'analytics', 'real-time',
        'service', 'microservice', 'container', 'docker', 'kubernetes'
    ]
    
    # Keywords that indicate storage-heavy workloads
    STORAGE_KEYWORDS = [
        'storage', 'database', 'db', 'data', 'file', 'files', 'backup',
        'archive', 'logs', 'logging', 'media', 'video', 'image', 'upload',
        'download', 'transfer', 'sync', 'etl', 'data warehouse', 'big data',
        'object storage', 's3', 'blob', 'disk', 'volume', 'persistent'
    ]
    
    # High-priority keywords (double the weight)
    HIGH_WEIGHT_GENERAL = ['cpu-intensive', 'compute-heavy', 'processing', 'calculation']
    HIGH_WEIGHT_STORAGE = ['storage-heavy', 'data-intensive', 'large files', 'terabyte']
    
    @staticmethod
    def analyze(workload_description: str) -> Tuple[ClusterType, int, Dict[str, any]]:
        """
        Analyze workload description and return recommended cluster.
        
        Args:
            workload_description: Natural language description of workload
            
        Returns:
            Tuple of (recommended_cluster, confidence_score, analysis_details)
            - confidence_score: 0-100 (higher = more confident)
        """
        if not workload_description:
            return ClusterType.GENERAL, 50, {
                "reason": "No description provided, defaulting to general cluster",
                "matched_keywords": []
            }
        
        desc_lower = workload_description.lower()
        
        # Count keyword matches
        general_score = 0
        storage_score = 0
        matched_general = []
        matched_storage = []
        
        # Check general keywords
        for keyword in WorkloadAnalyzer.GENERAL_KEYWORDS:
            if keyword in desc_lower:
                weight = 2 if keyword in WorkloadAnalyzer.HIGH_WEIGHT_GENERAL else 1
                general_score += weight
                matched_general.append(keyword)
        
        # Check storage keywords
        for keyword in WorkloadAnalyzer.STORAGE_KEYWORDS:
            if keyword in desc_lower:
                weight = 2 if keyword in WorkloadAnalyzer.HIGH_WEIGHT_STORAGE else 1
                storage_score += weight
                matched_storage.append(keyword)
        
        # Pattern-based detection
        if re.search(r'\d+\s*(gb|tb|pb)\s*(storage|data|files)', desc_lower):
            storage_score += 3
            matched_storage.append("large data volume pattern")
        
        if re.search(r'(high\s*cpu|many\s*cores|parallel\s*processing)', desc_lower):
            general_score += 3
            matched_general.append("high CPU requirement pattern")
        
        # Determine winner and confidence
        total_score = general_score + storage_score
        if total_score == 0:
            return ClusterType.GENERAL, 40, {
                "reason": "No clear indicators, defaulting to general cluster",
                "matched_keywords": []
            }
        
        if general_score > storage_score:
            confidence = min(100, int((general_score / total_score) * 100) + 20)
            return ClusterType.GENERAL, confidence, {
                "reason": f"General workload detected ({general_score} vs {storage_score} points)",
                "matched_keywords": matched_general,
                "score_breakdown": {"general": general_score, "storage": storage_score}
            }
        elif storage_score > general_score:
            confidence = min(100, int((storage_score / total_score) * 100) + 20)
            return ClusterType.STORAGE, confidence, {
                "reason": f"Storage workload detected ({storage_score} vs {general_score} points)",
                "matched_keywords": matched_storage,
                "score_breakdown": {"general": general_score, "storage": storage_score}
            }
        else:
            # Tie - default to general
            return ClusterType.GENERAL, 50, {
                "reason": f"Equal indicators ({general_score} each), defaulting to general",
                "matched_keywords": matched_general + matched_storage
            }
    
    @staticmethod
    def get_workload_examples() -> Dict[ClusterType, List[str]]:
        """Returns example workload descriptions for each cluster type"""
        return {
            ClusterType.GENERAL: [
                "Running a Node.js web application with REST API",
                "Machine learning model training with TensorFlow",
                "Real-time analytics processing service",
                "High CPU computation for scientific simulations",
                "Microservices backend with Docker containers"
            ],
            ClusterType.STORAGE: [
                "File storage server with 500GB of media files",
                "Database server with large PostgreSQL instance",
                "Backup and archival system for logs",
                "Data warehouse with ETL pipelines",
                "Object storage service similar to S3"
            ]
        }
    
    @staticmethod
    def validate_cluster_preference(
        workload_description: Optional[str],
        cluster_preference: Optional[ClusterType]
    ) -> Tuple[ClusterType, str]:
        """
        Validates user's explicit cluster choice against workload analysis.
        Issues a warning if there's a mismatch but respects user preference.
        
        Returns:
            Tuple of (final_cluster, warning_message)
        """
        if cluster_preference:
            if workload_description:
                recommended_cluster, confidence, _ = WorkloadAnalyzer.analyze(workload_description)
                if recommended_cluster != cluster_preference and confidence > 70:
                    return cluster_preference, (
                        f"Warning: Your workload seems better suited for {recommended_cluster.value} cluster "
                        f"(confidence: {confidence}%), but respecting your explicit choice of {cluster_preference.value}."
                    )
            return cluster_preference, ""
        
        # No explicit preference, use analysis
        if workload_description:
            recommended_cluster, confidence, details = WorkloadAnalyzer.analyze(workload_description)
            return recommended_cluster, f"Recommended {recommended_cluster.value} cluster based on workload analysis (confidence: {confidence}%)"
        
        # No description, no preference
        return ClusterType.GENERAL, "No workload description provided, assigned to general cluster by default"
