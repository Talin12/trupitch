# API route modules, each exposing an `APIRouter` that main.py mounts
# under /api:
#   auth.py        - GitHub OAuth login/callback for hackers
#   campaigns.py    - campaign CRUD, leaderboard, live-update WebSocket
#   hacker.py       - authenticated hacker's GitHub repo listing
#   submissions.py  - submission ingestion and polling
