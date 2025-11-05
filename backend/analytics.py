"""
Analytics and reporting functions for manager dashboard
"""
from typing import Dict, List, Any
from datetime import datetime, timezone, timedelta


async def calculate_agent_performance(db, agent_id: str = None) -> List[Dict[str, Any]]:
    """Calculate performance metrics for each agent"""
    match_filter = {"status": "completed"}
    if agent_id:
        match_filter["agent_number"] = agent_id
    
    pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": "$agent_number",
                "total_calls": {"$sum": 1},
                "avg_overall_score": {"$avg": "$overall_score"},
                "avg_script_score": {"$avg": "$analysis.script_adherence_score"},
                "avg_communication_score": {"$avg": "$analysis.communication_score"},
                "script_followed_count": {
                    "$sum": {"$cond": [{"$eq": ["$analysis.script_followed", True]}, 1, 0]}
                },
                "leads_qualified_count": {
                    "$sum": {"$cond": [{"$eq": ["$analysis.lead_qualified", True]}, 1, 0]}
                },
                "site_visits_confirmed_count": {
                    "$sum": {"$cond": [{"$eq": ["$analysis.site_visit_confirmed", True]}, 1, 0]}
                },
                "positive_sentiment_count": {
                    "$sum": {"$cond": [{"$eq": ["$analysis.sentiment", "positive"]}, 1, 0]}
                },
                "neutral_sentiment_count": {
                    "$sum": {"$cond": [{"$eq": ["$analysis.sentiment", "neutral"]}, 1, 0]}
                },
                "negative_sentiment_count": {
                    "$sum": {"$cond": [{"$eq": ["$analysis.sentiment", "negative"]}, 1, 0]}
                }
            }
        },
        {
            "$project": {
                "agent_id": "$_id",
                "total_calls": 1,
                "avg_overall_score": {"$round": ["$avg_overall_score", 2]},
                "avg_script_score": {"$round": ["$avg_script_score", 2]},
                "avg_communication_score": {"$round": ["$avg_communication_score", 2]},
                "script_adherence_rate": {
                    "$round": [
                        {"$multiply": [{"$divide": ["$script_followed_count", "$total_calls"]}, 100]},
                        2
                    ]
                },
                "lead_qualification_rate": {
                    "$round": [
                        {"$multiply": [{"$divide": ["$leads_qualified_count", "$total_calls"]}, 100]},
                        2
                    ]
                },
                "conversion_rate": {
                    "$round": [
                        {"$multiply": [{"$divide": ["$site_visits_confirmed_count", "$total_calls"]}, 100]},
                        2
                    ]
                },
                "positive_sentiment_rate": {
                    "$round": [
                        {"$multiply": [{"$divide": ["$positive_sentiment_count", "$total_calls"]}, 100]},
                        2
                    ]
                },
                "script_followed_count": 1,
                "leads_qualified_count": 1,
                "site_visits_confirmed": "$site_visits_confirmed_count",
                "sentiment_distribution": {
                    "positive": "$positive_sentiment_count",
                    "neutral": "$neutral_sentiment_count",
                    "negative": "$negative_sentiment_count"
                }
            }
        },
        {"$sort": {"conversion_rate": -1}}
    ]
    
    results = await db.audio_audits.aggregate(pipeline).to_list(None)
    return results


async def get_overall_analytics(db) -> Dict[str, Any]:
    """Get overall system analytics"""
    total_audits = await db.audio_audits.count_documents({})
    completed_audits = await db.audio_audits.count_documents({"status": "completed"})
    
    # Average scores
    score_pipeline = [
        {"$match": {"status": "completed"}},
        {
            "$group": {
                "_id": None,
                "avg_overall_score": {"$avg": "$overall_score"},
                "avg_script_score": {"$avg": "$analysis.script_adherence_score"},
                "avg_communication_score": {"$avg": "$analysis.communication_score"},
                "total_site_visits": {
                    "$sum": {"$cond": [{"$eq": ["$analysis.site_visit_confirmed", True]}, 1, 0]}
                },
                "total_qualified_leads": {
                    "$sum": {"$cond": [{"$eq": ["$analysis.lead_qualified", True]}, 1, 0]}
                }
            }
        }
    ]
    
    score_results = await db.audio_audits.aggregate(score_pipeline).to_list(1)
    
    if score_results:
        stats = score_results[0]
        overall_conversion_rate = (stats["total_site_visits"] / completed_audits * 100) if completed_audits > 0 else 0
        overall_qualification_rate = (stats["total_qualified_leads"] / completed_audits * 100) if completed_audits > 0 else 0
        
        return {
            "total_audits": total_audits,
            "completed_audits": completed_audits,
            "avg_overall_score": round(stats["avg_overall_score"], 2),
            "avg_script_score": round(stats["avg_script_score"], 2),
            "avg_communication_score": round(stats["avg_communication_score"], 2),
            "total_site_visits": stats["total_site_visits"],
            "total_qualified_leads": stats["total_qualified_leads"],
            "overall_conversion_rate": round(overall_conversion_rate, 2),
            "overall_qualification_rate": round(overall_qualification_rate, 2)
        }
    
    return {
        "total_audits": total_audits,
        "completed_audits": completed_audits,
        "avg_overall_score": 0,
        "avg_script_score": 0,
        "avg_communication_score": 0,
        "total_site_visits": 0,
        "total_qualified_leads": 0,
        "overall_conversion_rate": 0,
        "overall_qualification_rate": 0
    }


async def get_sentiment_trends(db) -> Dict[str, int]:
    """Get sentiment distribution across all completed audits"""
    pipeline = [
        {"$match": {"status": "completed"}},
        {
            "$group": {
                "_id": "$analysis.sentiment",
                "count": {"$sum": 1}
            }
        }
    ]
    
    results = await db.audio_audits.aggregate(pipeline).to_list(None)
    
    sentiment_map = {
        "positive": 0,
        "neutral": 0,
        "negative": 0
    }
    
    for result in results:
        if result["_id"] in sentiment_map:
            sentiment_map[result["_id"]] = result["count"]
    
    return sentiment_map


async def get_leadership_insights(db) -> Dict[str, Any]:
    """Generate leadership insights and recommendations"""
    
    # Get agent performance
    agent_performance = await calculate_agent_performance(db)
    
    # Identify top and bottom performers
    top_performers = [agent for agent in agent_performance if agent["conversion_rate"] >= 60][:3]
    needs_training = [agent for agent in agent_performance if agent["conversion_rate"] < 40][:3]
    
    # Calculate trends
    completed_audits = await db.audio_audits.count_documents({"status": "completed"})
    
    # Get recent performance (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_audits = await db.audio_audits.count_documents({
        "status": "completed",
        "processed_at": {"$gte": week_ago.isoformat()}
    })
    
    # Site visit forecast
    site_visit_pipeline = [
        {"$match": {"status": "completed", "analysis.site_visit_confirmed": True}},
        {"$count": "total"}
    ]
    site_visits = await db.audio_audits.aggregate(site_visit_pipeline).to_list(1)
    total_site_visits = site_visits[0]["total"] if site_visits else 0
    
    # Qualification trends
    qualified_pipeline = [
        {"$match": {"status": "completed", "analysis.lead_qualified": True}},
        {"$count": "total"}
    ]
    qualified = await db.audio_audits.aggregate(qualified_pipeline).to_list(1)
    total_qualified = qualified[0]["total"] if qualified else 0
    
    # Common missed points
    missed_points_pipeline = [
        {"$match": {"status": "completed"}},
        {"$unwind": "$analysis.script_adherence_details.missed_points"},
        {
            "$group": {
                "_id": "$analysis.script_adherence_details.missed_points",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    
    missed_points = await db.audio_audits.aggregate(missed_points_pipeline).to_list(5)
    
    # Calculate conversion forecast
    avg_conversion = (total_site_visits / completed_audits * 100) if completed_audits > 0 else 0
    forecasted_bookings = int(total_site_visits * 0.3)  # Assume 30% booking rate from site visits
    
    return {
        "top_performers": [{"agent_id": a["agent_id"], "conversion_rate": a["conversion_rate"]} for a in top_performers],
        "needs_training": [{"agent_id": a["agent_id"], "conversion_rate": a["conversion_rate"]} for a in needs_training],
        "total_completed_audits": completed_audits,
        "recent_week_audits": recent_audits,
        "total_site_visits_confirmed": total_site_visits,
        "total_qualified_leads": total_qualified,
        "avg_conversion_rate": round(avg_conversion, 2),
        "forecasted_monthly_bookings": forecasted_bookings * 4 if recent_audits > 0 else 0,
        "common_training_gaps": [{"point": item["_id"], "frequency": item["count"]} for item in missed_points],
        "recommendations": generate_recommendations(agent_performance, total_site_visits, total_qualified, completed_audits)
    }


def generate_recommendations(agent_performance: List[Dict], site_visits: int, qualified: int, total: int) -> List[str]:
    """Generate actionable recommendations for leadership"""
    recommendations = []
    
    if agent_performance:
        avg_conversion = sum(a["conversion_rate"] for a in agent_performance) / len(agent_performance)
        
        if avg_conversion < 40:
            recommendations.append("🔴 CRITICAL: Overall conversion rate below 40%. Immediate script review and agent training required.")
        elif avg_conversion < 60:
            recommendations.append("🟡 WARNING: Conversion rate needs improvement. Focus on closing techniques training.")
        else:
            recommendations.append("✅ GOOD: Conversion rates are healthy. Continue current training practices.")
    
    # Qualification insights
    qualification_rate = (qualified / total * 100) if total > 0 else 0
    if qualification_rate < 50:
        recommendations.append("📋 Focus on improving lead qualification questions. Agents missing key customer data.")
    
    # Site visit insights
    if site_visits > 0:
        booking_forecast = int(site_visits * 0.3)
        recommendations.append(f"📈 FORECAST: Expected {booking_forecast} bookings this month based on {site_visits} site visits confirmed.")
    
    # Top performer insights
    top_agents = sorted(agent_performance, key=lambda x: x["conversion_rate"], reverse=True)[:3]
    if top_agents:
        top_agent_ids = [a["agent_id"] for a in top_agents]
        recommendations.append(f"🏆 REWARD: Top performers {', '.join(top_agent_ids)} - Consider performance bonuses or recognition.")
    
    # Training needs
    low_performers = [a for a in agent_performance if a["conversion_rate"] < 30]
    if low_performers:
        low_agent_ids = [a["agent_id"] for a in low_performers]
        recommendations.append(f"📚 TRAINING: Agents {', '.join(low_agent_ids)} need immediate coaching on script adherence and closing.")
    
    return recommendations
