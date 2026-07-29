set -e
BASE=http://127.0.0.1:8000/api/v1

echo "--- seed admin user ---"
/home/claude/venv/bin/python /home/claude/kohwAI/backend/scripts/seed_admin.py 0779990001

echo "--- login as admin (dev OTP) ---"
REQ=$(curl -s -X POST $BASE/auth/otp/request -H "Content-Type: application/json" -d '{"phone":"0779990001"}')
OTP=$(echo "$REQ" | python3 -c "import sys,json; print(json.load(sys.stdin)['dev_otp'])")
ADMIN_TOKEN=$(curl -s -X POST $BASE/auth/otp/verify -H "Content-Type: application/json" \
  -d "{\"phone\":\"0779990001\",\"otp\":\"$OTP\",\"district\":\"Chipinge\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "admin token acquired: ${ADMIN_TOKEN:0:20}..."

echo "--- login as farmer ---"
REQ2=$(curl -s -X POST $BASE/auth/otp/request -H "Content-Type: application/json" -d '{"phone":"0771112222"}')
OTP2=$(echo "$REQ2" | python3 -c "import sys,json; print(json.load(sys.stdin)['dev_otp'])")
FARMER_TOKEN=$(curl -s -X POST $BASE/auth/otp/verify -H "Content-Type: application/json" \
  -d "{\"phone\":\"0771112222\",\"otp\":\"$OTP2\",\"district\":\"Chipinge\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "farmer token acquired: ${FARMER_TOKEN:0:20}..."

echo "--- 1. crop symptom reference ---"
curl -s $BASE/zunde/reference/crop-symptoms; echo

echo "--- 2. diagnose crop (fall armyworm case: symptom 3, crop maize) ---"
curl -s -X POST $BASE/zunde/diagnose -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER_TOKEN" \
  -d '{"crop_type_code":"1","symptom_code":"3","district":"Chipinge"}'; echo

echo "--- 3. admin creates an alert ---"
curl -s -X POST $BASE/alerts -H "Content-Type: application/json" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"pillar":"zunde","type":"pest","severity":"red","title":"Fall Armyworm reported","body":"Community reports nearby.","district":"Chipinge"}'; echo

echo "--- 4. farmer lists active alerts (should include the one just created) ---"
curl -s "$BASE/alerts/active" -H "Authorization: Bearer $FARMER_TOKEN"; echo

echo "--- 5. non-admin cannot create alert (should 403) ---"
curl -s -o /dev/null -w "%{http_code}\n" -X POST $BASE/alerts -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER_TOKEN" \
  -d '{"pillar":"zunde","type":"pest","severity":"red","title":"x","body":"x","district":"Chipinge"}'

echo "--- 6. planting calendar (real NASA POWER call — network is restricted in this sandbox, expect graceful failure) ---"
curl -s "$BASE/zunde/planting-calendar?district=Chipinge" -H "Authorization: Bearer $FARMER_TOKEN"; echo

echo "--- 7. pest sighting report ---"
curl -s -X POST $BASE/zunde/pest-sightings -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER_TOKEN" \
  -d '{"species":"Fall Armyworm","severity":"high","district":"Chipinge","affected_ha":0.5}'; echo
