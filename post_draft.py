import db

email_content = """Subject: Request for a Brief Meeting to Discuss Class Progress

Dear Professor,

I hope this email finds you well. 

I am writing to see if you might have some time in the coming days for a brief meeting to discuss my overall progress in the class. I would greatly appreciate the opportunity to get your feedback on my work so far and ensure I am on the right track for the remainder of the semester.

I am happy to meet via phone call or Zoom, whichever you prefer. Please let me know what days or times work best for your schedule.

Thank you for your time and guidance.

Best regards,
[Your Name]"""

db.init_db()
db.add_clip(f"Here is the draft for your professor. Review it tomorrow morning!\n\n```email\n{email_content}\n```", "Antigravity")
