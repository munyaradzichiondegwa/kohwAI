set -e
BASE=http://127.0.0.1:8000/api/v1

echo "--- seed admin (idempotent) ---"
/home/claude/venv/bin/python /home/claude/kohwAI/backend/scripts/seed_admin.py 0779990002 > /dev/null

login() {
  local phone=$1
  local req=$(curl -s -X POST $BASE/auth/otp/request -H "Content-Type: application/json" -d "{\"phone\":\"$phone\"}")
  local otp=$(echo "$req" | python3 -c "import sys,json; print(json.load(sys.stdin)['dev_otp'])")
  curl -s -X POST $BASE/auth/otp/verify -H "Content-Type: application/json" \
    -d "{\"phone\":\"$phone\",\"otp\":\"$otp\",\"district\":\"Chipinge\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"
}
ADMIN=$(login 0779990002)
FARMER=$(login 0771119999)
echo "tokens acquired"

echo "=== LIVESTOCK ==="
echo "--- register animal ---"
ANIMAL=$(curl -s -X POST $BASE/livestock/profiles -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER" \
  -d '{"name":"Bessie","animal_type":"cattle","breed":"Brahman","district":"Chipinge"}')
echo "$ANIMAL"
ANIMAL_ID=$(echo "$ANIMAL" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "--- diagnose (FMD case: symptom 3, animal cattle=1) ---"
curl -s -X POST $BASE/livestock/diagnose -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER" \
  -d "{\"animal_type_code\":\"1\",\"symptom_code\":\"3\",\"animal_id\":\"$ANIMAL_ID\"}"; echo
echo "--- list my animals ---"
curl -s $BASE/livestock/profiles -H "Authorization: Bearer $FARMER"; echo

echo "=== MVURA ==="
echo "--- admin creates borehole ---"
BH=$(curl -s -X POST $BASE/mvura/boreholes -H "Content-Type: application/json" -H "Authorization: Bearer $ADMIN" \
  -d '{"name":"Test Borehole 1","village":"Mutema","district":"Chipinge","lat":-20.19,"lng":32.62}')
echo "$BH"
BH_ID=$(echo "$BH" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "--- farmer reports it dry ---"
curl -s -X POST $BASE/mvura/boreholes/$BH_ID/report -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER" \
  -d '{"new_status":"dry","note":"No water since Monday"}'; echo
echo "--- list boreholes in district ---"
curl -s "$BASE/mvura/boreholes?district=Chipinge" -H "Authorization: Bearer $FARMER"; echo

echo "=== MUSIKA ==="
echo "--- create listing ---"
curl -s -X POST $BASE/musika/listings -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER" \
  -d '{"type":"seed","title":"SC403 Maize Seed","quantity":40,"unit":"kg","price_usd":1.8,"district":"Chipinge"}'; echo
echo "--- browse listings ---"
curl -s "$BASE/musika/listings?type=seed" -H "Authorization: Bearer $FARMER"; echo

echo "=== COMMUNITY / VALIDATOR ==="
echo "--- validator queue (should show pending pest sighting + borehole report) ---"
curl -s "$BASE/community/queue?district=Chipinge" -H "Authorization: Bearer $ADMIN"; echo
echo "--- farmer cannot access queue (should 403) ---"
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/community/queue" -H "Authorization: Bearer $FARMER"

echo "=== ANALYTICS ==="
curl -s $BASE/analytics/overview -H "Authorization: Bearer $ADMIN"; echo

echo "=== SETTINGS ==="
echo "--- list (auto-seeds defaults) ---"
curl -s $BASE/settings -H "Authorization: Bearer $FARMER"; echo
echo "--- admin updates a flag ---"
curl -s -X PUT $BASE/settings/maintenance_mode -H "Content-Type: application/json" -H "Authorization: Bearer $ADMIN" \
  -d '{"value":{"enabled":false,"message":""},"description":"Global maintenance toggle"}'; echo

echo "=== SIMBA ==="
curl -s "$BASE/simba/battery-forecast?district=Chipinge&battery_capacity_wh=2000&panel_watts=300&current_pct=70&load_watts=50" \
  -H "Authorization: Bearer $FARMER"; echo
