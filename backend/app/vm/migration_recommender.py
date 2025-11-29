# backend/app/vm/migration_recommender.py
"""
AI-powered migration recommendation engine.
Analyzes cluster state and suggests optimal migrations with confidence scores.
"""

from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
import uuid
from app.vm.models import (
    MigrationRecommendation, RecommendationStatus, ClusterType,
    VMMetricsResponse, UserAssignmentResponse
)


class MigrationRecommender:
    """
    Intelligent migration recommendation system using rule-based scoring.
    Future enhancement: Replace with ML model trained on historical data.
    """
    
    # Configuration
    MAX_USERS_PER_VM = 5
    CPU_OVERLOAD_THRESHOLD = 70.0  # %
    CPU_UNDERLOAD_THRESHOLD = 30.0  # %
    LOAD_IMBALANCE_THRESHOLD = 30.0  # % difference
    COST_SAVINGS_THRESHOLD = 0.005  # USD/hour
    
    @staticmethod
    def calculate_migration_score(
        source_vm: VMMetricsResponse,
        target_vm: VMMetricsResponse,
        user_session_duration_minutes: float,
        user_priority: int = 1
    ) -> Tuple[int, List[str], Dict[str, str]]:
        """
        Calculate migration score (0-100) and reasons.
        Higher score = stronger recommendation.
        
        Returns:
            Tuple of (score, reasons_list, expected_improvements)
        """
        score = 0
        reasons = []
        improvements = {}
        
        # Factor 1: CPU Load Imbalance (weight: 35 points)
        cpu_diff = source_vm.cpu_usage - target_vm.cpu_usage
        if cpu_diff > MigrationRecommender.LOAD_IMBALANCE_THRESHOLD:
            imbalance_score = min(35, int((cpu_diff / 100) * 35) + 10)
            score += imbalance_score
            reasons.append(
                f"Severe CPU imbalance: Source VM at {source_vm.cpu_usage:.1f}%, "
                f"Target at {target_vm.cpu_usage:.1f}%"
            )
            improvements["cpu_reduction_source"] = f"{cpu_diff / source_vm.active_users:.1f}%"
            improvements["cpu_increase_target"] = f"{cpu_diff / (target_vm.active_users + 1):.1f}%"
        
        # Factor 2: Source VM Overloaded (weight: 25 points)
        if source_vm.cpu_usage > MigrationRecommender.CPU_OVERLOAD_THRESHOLD:
            overload_severity = int(
                ((source_vm.cpu_usage - MigrationRecommender.CPU_OVERLOAD_THRESHOLD) / 30) * 25
            )
            score += min(25, overload_severity)
            reasons.append(f"Source VM overloaded at {source_vm.cpu_usage:.1f}% CPU")
            improvements["performance_gain"] = "30-50% faster response times expected"
        
        # Factor 3: Target VM Has Capacity (weight: 15 points)
        if target_vm.cpu_usage < 50 and target_vm.active_users < MigrationRecommender.MAX_USERS_PER_VM:
            score += 15
            reasons.append(
                f"Target VM has available capacity "
                f"({target_vm.active_users}/{MigrationRecommender.MAX_USERS_PER_VM} users, "
                f"{target_vm.cpu_usage:.1f}% CPU)"
            )
        
        # Factor 4: Cost Savings via Consolidation (weight: 15 points)
        if source_vm.active_users == 1:  # Only this user on source VM
            score += 15
            reasons.append("Migration allows stopping source VM, saving costs")
            improvements["cost_savings"] = f"${source_vm.estimated_cost_usd:.4f}/hour"
        
        # Factor 5: Session Duration (weight: 10 points)
        # Shorter sessions = less disruption = higher score
        if user_session_duration_minutes < 30:
            score += 10
            reasons.append(f"Short session ({user_session_duration_minutes:.0f} min) = minimal disruption")
        elif user_session_duration_minutes < 60:
            score += 5
            reasons.append(f"Moderate session ({user_session_duration_minutes:.0f} min)")
        else:
            reasons.append(f"Long session ({user_session_duration_minutes:.0f} min) = higher disruption")
        
        # Factor 6: User Priority Bonus (weight: varies)
        if user_priority >= 3:
            score = max(score - 10, 0)  # Lower priority = lower score
            reasons.append("Lower priority user = deprioritized migration")
        elif user_priority <= 1:
            score = min(score + 5, 100)  # Higher priority = boost score
        
        # Ensure score is within 0-100
        score = max(0, min(100, score))
        
        return score, reasons, improvements
    
    @staticmethod
    def generate_recommendations(
        cluster_type: ClusterType,
        vm_metrics: List[VMMetricsResponse],
        user_assignments: List[Dict[str, Any]]
    ) -> List[MigrationRecommendation]:
        """
        Generate all migration recommendations for a cluster.
        
        Args:
            cluster_type: Which cluster to analyze
            vm_metrics: Current metrics for all VMs in cluster
            user_assignments: List of active user assignments
            
        Returns:
            List of recommendations sorted by score (highest first)
        """
        recommendations = []
        
        if len(vm_metrics) < 2:
            return recommendations  # Need at least 2 VMs for migration
        
        # Identify overloaded and underloaded VMs
        overloaded_vms = [vm for vm in vm_metrics if vm.cpu_usage > MigrationRecommender.CPU_OVERLOAD_THRESHOLD]
        underloaded_vms = [vm for vm in vm_metrics if vm.cpu_usage < MigrationRecommender.CPU_UNDERLOAD_THRESHOLD]
        
        # Scenario 1: Rebalance overloaded VMs
        for source_vm in overloaded_vms:
            for target_vm in vm_metrics:
                if (target_vm.vm_name != source_vm.vm_name and 
                    target_vm.active_users < MigrationRecommender.MAX_USERS_PER_VM):
                    
                    # Find users on source VM to migrate
                    users_on_source = [
                        u for u in user_assignments 
                        if u.get("vm_name") == source_vm.vm_name
                    ]
                    
                    for user_assignment in users_on_source:
                        session_duration = (
                            datetime.utcnow() - user_assignment.get("assigned_at", datetime.utcnow())
                        ).total_seconds() / 60
                        
                        score, reasons, improvements = MigrationRecommender.calculate_migration_score(
                            source_vm, target_vm, session_duration,
                            user_assignment.get("priority_level", 1)
                        )
                        
                        if score >= 30:  # Only recommend if score > 30
                            rec_id = f"rec_{uuid.uuid4().hex[:8]}"
                            recommendations.append(MigrationRecommendation(
                                recommendation_id=rec_id,
                                action="migrate_user",
                                user_id=user_assignment.get("user_id"),
                                source_vm=source_vm.vm_name,
                                target_vm=target_vm.vm_name,
                                score=score,
                                reasons=reasons,
                                expected_improvements=improvements,
                                estimated_downtime_seconds=20,
                                cost_impact_usd=0.0,
                                confidence=min(95, score + 10),
                                generated_at=datetime.utcnow(),
                                status=RecommendationStatus.PENDING
                            ))
        
        # Scenario 2: Consolidate underutilized VMs
        if len(underloaded_vms) >= 2:
            for source_vm in underloaded_vms:
                if source_vm.active_users == 0:
                    continue  # Skip empty VMs
                
                for target_vm in underloaded_vms:
                    if (target_vm.vm_name != source_vm.vm_name and
                        target_vm.active_users + source_vm.active_users <= MigrationRecommender.MAX_USERS_PER_VM):
                        
                        # Recommend consolidating entire source VM to target
                        rec_id = f"rec_{uuid.uuid4().hex[:8]}"
                        cost_savings = source_vm.estimated_cost_usd
                        
                        recommendations.append(MigrationRecommendation(
                            recommendation_id=rec_id,
                            action="consolidate",
                            user_id=None,  # Multiple users
                            source_vm=source_vm.vm_name,
                            target_vm=target_vm.vm_name,
                            score=70,  # High score for cost savings
                            reasons=[
                                f"Consolidate {source_vm.active_users} users from underutilized VM",
                                f"Both VMs under {MigrationRecommender.CPU_UNDERLOAD_THRESHOLD}% CPU",
                                f"Save ${cost_savings:.4f}/hour by stopping source VM"
                            ],
                            expected_improvements={
                                "cost_savings": f"${cost_savings:.4f}/hour",
                                "resource_efficiency": "Better utilization"
                            },
                            estimated_downtime_seconds=30,
                            cost_impact_usd=-cost_savings,  # Negative = savings
                            confidence=85,
                            generated_at=datetime.utcnow(),
                            status=RecommendationStatus.PENDING
                        ))
                        break  # Only one consolidation recommendation per source VM
        
        # Scenario 3: Proactive scaling (if cluster is getting busy)
        total_users = sum(vm.active_users for vm in vm_metrics)
        total_capacity = len(vm_metrics) * MigrationRecommender.MAX_USERS_PER_VM
        utilization = total_users / total_capacity
        
        if utilization > 0.8:  # Over 80% capacity
            stopped_vms = [vm for vm in vm_metrics if vm.status.value == "STOPPED"]
            if stopped_vms:
                rec_id = f"rec_{uuid.uuid4().hex[:8]}"
                recommendations.append(MigrationRecommendation(
                    recommendation_id=rec_id,
                    action="preemptive_scale",
                    user_id=None,
                    source_vm="cluster",
                    target_vm=stopped_vms[0].vm_name,
                    score=60,
                    reasons=[
                        f"Cluster at {utilization*100:.0f}% capacity",
                        "Start additional VM proactively to handle incoming requests"
                    ],
                    expected_improvements={
                        "capacity_increase": f"+{MigrationRecommender.MAX_USERS_PER_VM} user slots",
                        "response_time": "Prevent overload during peak"
                    },
                    estimated_downtime_seconds=0,  # No downtime for starting new VM
                    cost_impact_usd=0.007,  # Cost to run new VM
                    confidence=75,
                    generated_at=datetime.utcnow(),
                    status=RecommendationStatus.PENDING
                ))
        
        # Sort by score (highest first)
        recommendations.sort(key=lambda r: r.score, reverse=True)
        
        return recommendations
    
    @staticmethod
    def filter_recommendations(
        recommendations: List[MigrationRecommendation],
        min_score: int = 50,
        max_count: int = 10
    ) -> List[MigrationRecommendation]:
        """
        Filter recommendations by minimum score and limit count.
        Returns top recommendations.
        """
        filtered = [r for r in recommendations if r.score >= min_score]
        return filtered[:max_count]
    
    @staticmethod
    def predict_cluster_health_1_hour(
        current_metrics: List[VMMetricsResponse],
        historical_trend: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Predict cluster state in 1 hour based on current metrics and trends.
        Simple linear extrapolation (can be replaced with ML model).
        
        Returns:
            Dict with predicted CPU, user count, and recommendation
        """
        if not current_metrics:
            return {"prediction": "No data available"}
        
        avg_cpu = sum(vm.cpu_usage for vm in current_metrics) / len(current_metrics)
        total_users = sum(vm.active_users for vm in current_metrics)
        
        # Simple trend-based prediction
        if historical_trend == "increasing":
            predicted_cpu = min(100, avg_cpu * 1.3)
            predicted_users = int(total_users * 1.2)
            recommendation = "Consider starting additional VM preemptively"
        elif historical_trend == "decreasing":
            predicted_cpu = max(0, avg_cpu * 0.7)
            predicted_users = max(0, int(total_users * 0.8))
            recommendation = "Possible consolidation opportunity in 1 hour"
        else:
            predicted_cpu = avg_cpu
            predicted_users = total_users
            recommendation = "Stable load expected"
        
        return {
            "predicted_in_1_hour": {
                "average_cpu": round(predicted_cpu, 1),
                "total_users": predicted_users
            },
            "current": {
                "average_cpu": round(avg_cpu, 1),
                "total_users": total_users
            },
            "trend": historical_trend or "stable",
            "recommendation": recommendation
        }
