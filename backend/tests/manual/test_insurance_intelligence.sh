set -e
BASE=http://127.0.0.1:8000/api/v1

/home/claude/venv/bin/python /home/claude/kohwAI/backend/scripts/seed_admin.py 0779990003 > /dev/null

login() {
  local phone=$1
  local req=$(curl -s -X POST $BASE/auth/otp/request -H "Content-Type: application/json" -d "{\"phone\":\"$phone\"}")
  local otp=$(echo "$req" | python3 -c "import sys,json; print(json.load(sys.stdin)['dev_otp'])")
  curl -s -X POST $BASE/auth/otp/verify -H "Content-Type: application/json" \
    -d "{\"phone\":\"$phone\",\"otp\":\"$otp\",\"district\":\"Chipinge\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"
}
ADMIN=$(login 0779990003)
FARMER=$(login 0771118888)
echo "tokens acquired"

echo "=== INSURANCE ==="
echo "--- enroll ---"
curl -s -X POST $BASE/musika/insurance/enroll -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER" \
  -d '{"district":"Chipinge","season":"2026-27","ecocash_number":"0771118888"}'; echo
echo "--- my enrollment ---"
curl -s $BASE/musika/insurance/my-enrollment -H "Authorization: Bearer $FARMER"; echo
echo "--- admin evaluates district payout (real NASA POWER call, low threshold to force trigger even w/o live data) ---"
curl -s -X POST $BASE/musika/insurance/evaluate-payout -H "Content-Type: application/json" -H "Authorization: Bearer $ADMIN" \
  -d '{"district":"Chipinge","season":"2026-27","drought_index_threshold":0}'; echo
echo "--- my payouts ---"
curl -s $BASE/musika/insurance/my-payouts -H "Authorization: Bearer $FARMER"; echo
echo "--- farmer cannot evaluate payout (403) ---"
curl -s -o /dev/null -w "%{http_code}\n" -X POST $BASE/musika/insurance/evaluate-payout -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER" \
  -d '{"district":"Chipinge","season":"2026-27"}'

echo "=== CROSS-PILLAR INTELLIGENCE ==="
echo "--- farmer diagnoses drought stress crop ---"
curl -s -X POST $BASE/zunde/diagnose -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER" \
  -d '{"crop_type_code":"1","symptom_code":"2","district":"Chipinge"}'; echo
echo "--- register + diagnose a sick animal ---"
ANIMAL=$(curl -s -X POST $BASE/livestock/profiles -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER" \
  -d '{"name":"Tanaka","animal_type":"cattle","district":"Chipinge"}')
ANIMAL_ID=$(echo "$ANIMAL" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X POST $BASE/livestock/diagnose -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER" \
  -d "{\"animal_type_code\":\"1\",\"symptom_code\":\"1\",\"animal_id\":\"$ANIMAL_ID\"}" > /dev/null
echo "--- my insights (should now include drought_water_risk + livestock_followup) ---"
curl -s $BASE/intelligence/insights -H "Authorization: Bearer $FARMER"; echo
echo "--- risk score (real NASA POWER call) ---"
curl -s "$BASE/zunde/risk-score?district=Chipinge" -H "Authorization: Bearer $FARMER"; echo

echo "--- 3 pest sightings to trigger outbreak escalation ---"
for i in 1 2 3; do
  curl -s -X POST $BASE/zunde/pest-sightings -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER" \
    -d '{"species":"Fall Armyworm","severity":"high","district":"Chipinge","affected_ha":0.3}' > /dev/null
done
echo "--- admin triggers district-wide evaluation ---"
curl -s -X POST $BASE/intelligence/evaluate/district -H "Content-Type: application/json" -H "Authorization: Bearer $ADMIN" \
  -d '{"district":"Chipinge"}'; echo
echo "--- farmer's insights again (should now include pest_outbreak) ---"
curl -s $BASE/intelligence/insights -H "Authorization: Bearer $FARMER"; echo
