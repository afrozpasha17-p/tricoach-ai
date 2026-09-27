# My agent: TriCoach AI (Personal Fitness & Triathlon Coach)
One-liner: A conversational agent that helps endurance athletes log workouts, compute training zones, and receive personalized training plans and visual milestone badges.

Tool coverage:
- Memory: Athlete profile (age, resting HR, max HR, FTP, triathlon distance goal, injury notes, preferences)
- Tools: Log workout entry, retrieve workout history, fetch recommended training session plans
- Catalog/UI: Catalog of logged workouts and training plans (rendered as A2UI cards and tables)
- Image gen: Custom motivational milestone badges and race goal progress graphics
- Sandbox: Python code sandbox for computing Karvonen heart rate zones, Training Stress Score (TSS), and FTP pacing targets

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): Code sandbox for training stress calculations, Event-driven reminders via Pub/Sub
