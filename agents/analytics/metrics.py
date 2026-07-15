"""Metric calculation algorithms."""

from agents.analytics.models import CampaignStats


def calculate_rates(stats: dict) -> CampaignStats:
    """Calculate percentages based on absolute totals."""
    sent = stats.get("total_sent", 0)
    delivered = stats.get("total_delivered", 0)
    opened = stats.get("total_opened", 0)
    clicked = stats.get("total_clicked", 0)
    replied = stats.get("total_replied", 0)

    delivery_rate = (delivered / sent * 100.0) if sent > 0 else 0.0
    open_rate = (opened / delivered * 100.0) if delivered > 0 else 0.0
    click_rate = (clicked / delivered * 100.0) if delivered > 0 else 0.0
    reply_rate = (replied / delivered * 100.0) if delivered > 0 else 0.0

    # Simple heuristic health score
    health = 100.0
    if sent > 0:
        bounce_rate = (stats.get("total_bounced", 0) / sent * 100.0)
        spam_rate = (stats.get("total_spam_complaints", 0) / sent * 100.0)

        health -= (bounce_rate * 5) # Heavy penalty for bounces
        health -= (spam_rate * 20)  # Extreme penalty for spam

        # Reward engagement
        health += (open_rate * 0.1)
        health += (reply_rate * 2)

    health = max(0.0, min(100.0, health))

    return CampaignStats(
        **stats,
        delivery_rate=round(delivery_rate, 2),
        open_rate=round(open_rate, 2),
        click_rate=round(click_rate, 2),
        reply_rate=round(reply_rate, 2),
        health_score=round(health, 2)
    )
