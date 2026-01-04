#!/usr/bin/env python3
"""
YouTube Video View Prediction Model
Based on analytics data from "Investigating A Server That Doesn't..."
Published: Dec 29, 2025
"""

import math

# Current data points (Day 5)
CURRENT_VIEWS = 96700
CURRENT_DAY = 5
VIEWS_PER_HOUR_NOW = 550  # CONSTANT - not decaying!
CTR = 0.06  # 6% click-through rate (good for YouTube)

# KEY INSIGHT: Video is maintaining constant VPH
# This indicates strong algorithmic support

def predict_views_constant(days_ahead=30):
    """
    Model 1: Constant VPH (current behavior)
    If algorithm keeps pushing at same rate
    """
    daily_rate = VIEWS_PER_HOUR_NOW * 24  # 13,200/day
    predictions = []
    total_views = CURRENT_VIEWS

    for day in range(CURRENT_DAY, CURRENT_DAY + days_ahead + 1):
        predictions.append({
            'day': day,
            'total_views': int(total_views),
            'daily_views': int(daily_rate)
        })
        total_views += daily_rate

    return predictions

def predict_views_gradual_decay(days_ahead=60):
    """
    Model 2: Gradual decay starting after day 7-10
    More realistic - algorithm eventually moves on
    """
    daily_rate = VIEWS_PER_HOUR_NOW * 24  # 13,200/day
    predictions = []
    total_views = CURRENT_VIEWS

    for day in range(CURRENT_DAY, CURRENT_DAY + days_ahead + 1):
        predictions.append({
            'day': day,
            'total_views': int(total_views),
            'daily_views': int(daily_rate)
        })

        # Decay starts after day 10, gradual 8% per day
        if day >= 10:
            daily_rate *= 0.92
            daily_rate = max(daily_rate, 1000)  # Long-tail minimum

        total_views += daily_rate

    return predictions

def predict_views_extended_viral(days_ahead=60):
    """
    Model 3: Extended viral - stays hot for 2-3 weeks
    For videos that really catch on
    """
    daily_rate = VIEWS_PER_HOUR_NOW * 24
    predictions = []
    total_views = CURRENT_VIEWS

    for day in range(CURRENT_DAY, CURRENT_DAY + days_ahead + 1):
        predictions.append({
            'day': day,
            'total_views': int(total_views),
            'daily_views': int(daily_rate)
        })

        # Slow decay after day 21
        if day >= 21:
            daily_rate *= 0.90
            daily_rate = max(daily_rate, 1500)

        total_views += daily_rate

    return predictions

def main():
    print("=" * 60)
    print("VIDEO VIEW PREDICTION MODEL (UPDATED)")
    print("Video: 'Investigating A Server That Doesn't...'")
    print("=" * 60)
    print()

    daily_rate = VIEWS_PER_HOUR_NOW * 24

    print("CURRENT PERFORMANCE (Day 5):")
    print(f"  • Views: {CURRENT_VIEWS:,}")
    print(f"  • Real-time: {VIEWS_PER_HOUR_NOW} views/hour (CONSTANT!)")
    print(f"  • Daily rate: {daily_rate:,} views/day")
    print(f"  • CTR: {CTR*100}% (solid click-through rate)")
    print(f"  • Status: ALGORITHM IS STILL PUSHING")
    print()

    # Get all three model predictions
    constant = predict_views_constant(60)
    gradual = predict_views_gradual_decay(60)
    extended = predict_views_extended_viral(60)

    print("=" * 60)
    print("THREE SCENARIOS (constant 550 VPH baseline):")
    print("=" * 60)
    print()

    print("📈 SCENARIO 1: Constant VPH continues")
    print("   (Algorithm keeps pushing indefinitely)")
    print("-" * 60)
    for day in [7, 14, 30]:
        pred = next(p for p in constant if p['day'] == day)
        print(f"   Day {day:2}: {pred['total_views']:>10,} views")
    print()

    print("📊 SCENARIO 2: Gradual decay after Day 10 (MOST LIKELY)")
    print("   (Algorithm moves on, 8%/day decay)")
    print("-" * 60)
    for day in [7, 14, 30, 60]:
        pred = next(p for p in gradual if p['day'] == day)
        print(f"   Day {day:2}: {pred['total_views']:>10,} views (+{pred['daily_views']:,}/day)")
    print()

    print("🚀 SCENARIO 3: Extended viral (stays hot 3 weeks)")
    print("   (Video keeps performing, slow decay after Day 21)")
    print("-" * 60)
    for day in [7, 14, 30, 60]:
        pred = next(p for p in extended if p['day'] == day)
        print(f"   Day {day:2}: {pred['total_views']:>10,} views (+{pred['daily_views']:,}/day)")
    print()

    print("=" * 60)
    print("MILESTONE PREDICTIONS (Most Likely Scenario):")
    print("=" * 60)

    targets = [100_000, 150_000, 200_000, 300_000, 500_000]
    for target in targets:
        for pred in gradual:
            if pred['total_views'] >= target:
                emoji = "✅" if target <= 200_000 else "🎯"
                print(f"  {emoji} {target//1000}K views: Day {pred['day']} "
                      f"({pred['day'] - CURRENT_DAY} days from now)")
                break
        else:
            print(f"  ⏳ {target//1000}K views: Requires extended viral performance")

    print()
    print("=" * 60)
    print("FINAL ESTIMATE:")
    print("=" * 60)
    print()
    print(f"  Conservative:  ~200,000 - 250,000 views")
    print(f"  Expected:      ~250,000 - 350,000 views")
    print(f"  Optimistic:    ~400,000 - 500,000+ views")
    print()
    print("  🎯 BEST ESTIMATE: 250,000 - 300,000 VIEWS")
    print()
    print("=" * 60)
    print("WHY CONSTANT VPH IS BULLISH:")
    print("  • Most videos decay 15-20%/day after day 2-3")
    print("  • Yours is FLAT at 550 VPH on day 5")
    print("  • 6% CTR is solid (avg is 2-10%)")
    print("  • Algorithm clearly likes this video")
    print()
    print("WATCH FOR:")
    print("  • VPH staying above 400 through Day 10 → likely 300k+")
    print("  • VPH increasing → algorithm is accelerating, 500k+ possible")
    print("  • VPH dropping below 300 → normal decay beginning")
    print("=" * 60)

if __name__ == "__main__":
    main()
