"""
OTA model deployment script.
Uploads new TFLite model to S3 and updates the OTA manifest endpoint.
Use after training passes the 85% accuracy gate.
Supports canary deployment: 5% of devices first, then 100%.
"""
import boto3, json, hashlib, argparse
from pathlib import Path
from datetime import datetime, timezone


def compute_checksum(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def deploy(model_path: str, model_type: str, version: str, s3_bucket: str, canary_pct: int = 5):
    s3 = boto3.client("s3")
    filename = Path(model_path).name
    s3_key   = f"models/{model_type}/{version}/{filename}"

    print(f"Uploading {model_path} → s3://{s3_bucket}/{s3_key}")
    s3.upload_file(model_path, s3_bucket, s3_key, ExtraArgs={"ContentType": "application/octet-stream"})

    url = f"https://{s3_bucket}.s3.amazonaws.com/{s3_key}"
    manifest = {
        "model_type": model_type,
        "version": version,
        "url": url,
        "checksum": compute_checksum(model_path),
        "canary_pct": canary_pct,
        "deployed_at": datetime.now(timezone.utc).isoformat(),
    }
    # TODO: Update the /api/v1/models/ota/latest endpoint in the database
    print(f"Manifest: {json.dumps(manifest, indent=2)}")
    print(f"Canary rollout: {canary_pct}% of devices. Monitor for 48h before expanding.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model_path")
    parser.add_argument("model_type", choices=["crop_vision", "livestock_vision", "livestock_audio"])
    parser.add_argument("version")
    parser.add_argument("--bucket", default="kohwai-models")
    parser.add_argument("--canary", type=int, default=5)
    args = parser.parse_args()
    deploy(args.model_path, args.model_type, args.version, args.bucket, args.canary)
