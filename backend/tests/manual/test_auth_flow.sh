set -e
BASE=http://127.0.0.1:8000/api/v1

echo "--- 1. OTP request ---"
REQ=$(curl -s -X POST $BASE/auth/otp/request -H "Content-Type: application/json" -d '{"phone":"0771234567"}')
echo "$REQ"
OTP=$(echo "$REQ" | python3 -c "import sys,json; print(json.load(sys.stdin)['dev_otp'])")
echo "extracted dev_otp=$OTP"

echo "--- 2. OTP verify ---"
VERIFY=$(curl -s -X POST $BASE/auth/otp/verify -H "Content-Type: application/json" \
  -d "{\"phone\":\"0771234567\",\"otp\":\"$OTP\",\"language\":\"sn\",\"district\":\"Chipinge\"}")
echo "$VERIFY"
ACCESS=$(echo "$VERIFY" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
REFRESH=$(echo "$VERIFY" | python3 -c "import sys,json; print(json.load(sys.stdin)['refresh_token'])")

echo "--- 3. GET /me with access token ---"
curl -s $BASE/auth/me -H "Authorization: Bearer $ACCESS"; echo

echo "--- 4. Refresh token ---"
curl -s -X POST $BASE/auth/refresh -H "Content-Type: application/json" -d "{\"refresh_token\":\"$REFRESH\"}"; echo

echo "--- 5. Wrong OTP should fail ---"
curl -s -X POST $BASE/auth/otp/verify -H "Content-Type: application/json" \
  -d '{"phone":"0779999999","otp":"000000"}'; echo

echo "--- 6. /me with no token should 401 ---"
curl -s -o /dev/null -w "%{http_code}\n" $BASE/auth/me
