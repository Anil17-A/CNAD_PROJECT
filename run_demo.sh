#!/usr/bin/env bash
# End-to-end demo: simulator surges zone 1 after ~30s -> warning alert; then post a damage assessment.
KEY="x-api-key: change-me-demo-key"
echo "1) services health";  curl -s localhost:8000/health
echo; echo "2) wait ~40s for the flood surge, then check alerts"; sleep 40
curl -s -H "$KEY" localhost:8000/api/alert/alerts | python3 -m json.tool
echo "3) damage assessment for Riverside (expect SI 62.3)"
curl -s -X POST -H "$KEY" -H "content-type: application/json" localhost:8000/api/damage/assess \
  -d '{"zone_id":1,"structural_damage_pct":62,"population_exposure":0.81,"access_difficulty":0.35}'
echo; echo "4) dispatch plan"; curl -s -H "$KEY" localhost:8000/api/resource/dispatch | python3 -m json.tool
echo "Open dashboard: http://localhost:3000"
