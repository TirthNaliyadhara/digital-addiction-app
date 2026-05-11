def get_recommendations(metrics: dict) -> dict:
    recs = {
        'critical': [],
        'warnings': [],
        'tips': [],
        'detox_plan': [],
        'weekly_plan': [],
    }

    screen = metrics.get('total_screen_time', 0)
    night = metrics.get('nighttime_usage', 0)
    notif = metrics.get('notifications_per_day', 0)
    pickups = metrics.get('phone_pickups_per_hour', 0)
    binge = metrics.get('binge_sessions_per_week', 0)
    sleep = metrics.get('sleep_hours', 7)
    prod = metrics.get('productivity_score', 5)
    fomo = metrics.get('fomo_score', 0)
    anxiety = metrics.get('anxiety_score', 0)

    # Screen time
    if screen > 12:
        recs['critical'].append("🚨 Extreme screen time detected (>12 hrs). Immediate digital detox recommended.")
        recs['detox_plan'].append("Day 1-2: Reduce by 2 hrs. Day 3-4: Use grayscale mode. Day 5-7: No social media after 8 PM.")
    elif screen > 8:
        recs['warnings'].append("⚠️ High screen time (>8 hrs). Set daily app limits via Digital Wellbeing settings.")
        recs['detox_plan'].append("Reduce screen time by 30 min each day this week. Use app timers.")

    # Night usage
    if night > 2:
        recs['critical'].append("🌙 Severe nighttime usage detected. Blue light exposure disrupts melatonin production.")
        recs['tips'].append("Enable Night Shift / Blue Light Filter after 9 PM.")
        recs['tips'].append("Place phone outside the bedroom — use an alarm clock instead.")
    elif night > 1:
        recs['warnings'].append("🌙 Moderate nighttime usage. Set phone to Do Not Disturb after 10 PM.")

    # Notifications
    if notif > 200:
        recs['critical'].append("🔔 Notification overload! >200 notifications/day creates chronic stress.")
        recs['tips'].append("Disable non-essential notifications for all social media apps.")
        recs['tips'].append("Use notification batching — check notifications only 3x/day.")
    elif notif > 100:
        recs['warnings'].append("🔔 High notification count. Review and mute low-priority apps.")

    # Phone pickups
    if pickups > 30:
        recs['warnings'].append("📲 Compulsive phone checking behavior detected (>30 pickups/hr).")
        recs['tips'].append("Practice the '20-minute rule': check phone only every 20 minutes.")

    # Binge sessions
    if binge > 10:
        recs['warnings'].append("📺 Excessive binge sessions (>10/week). Implement content time limits.")
        recs['tips'].append("Use platform built-in screen time reminders (YouTube, Netflix, etc.).")

    # Sleep
    if sleep < 5:
        recs['critical'].append("😴 Critical sleep deprivation! Less than 5 hrs of sleep detected.")
        recs['tips'].append("Create a strict sleep schedule. No screens 1 hr before bed.")
    elif sleep < 6.5:
        recs['warnings'].append("😴 Insufficient sleep (<6.5 hrs). Digital usage is likely disrupting your sleep cycle.")

    # Productivity
    if prod < 4:
        recs['warnings'].append("📉 Very low productivity score. Digital distraction is severely impacting work/study.")
        recs['tips'].append("Use the Pomodoro Technique: 25 min focus, 5 min break. No phone during focus blocks.")

    # FOMO / Anxiety
    if fomo >= 8 or anxiety >= 8:
        recs['tips'].append("🧠 High FOMO/anxiety detected. Try a 24-hour social media break to reset.")
        recs['tips'].append("Practice mindfulness: 10-min meditation before checking phone in morning.")

    # Weekly plan
    recs['weekly_plan'] = [
        "📅 Mon: Audit your top 5 most-used apps. Set 30-min limits.",
        "📅 Tue: Phone-free meals. No phone for 1 hr after waking up.",
        "📅 Wed: Notification audit — disable all non-essential alerts.",
        "📅 Thu: Screen-free hour before bed. Read a physical book.",
        "📅 Fri: Productivity day — use Focus/Do Not Disturb mode.",
        "📅 Sat: Outdoor activity for 2+ hours. Track steps instead of scrolling.",
        "📅 Sun: Reflect on usage. Review weekly screen time report.",
    ]

    if not recs['critical'] and not recs['warnings']:
        recs['tips'].append("✅ Your digital habits look healthy! Keep maintaining balance.")

    return recs
