"""Audit TFLite model predictions vs folder-name labels. Usage: python label_tool.py --model_path M --data_dir D --labels c1,c2"""
import argparse, csv
from pathlib import Path
import numpy as np

def run(model_path,data_dir,labels,output_csv="audit.csv"):
    try:
        import tflite_runtime.interpreter as tflite; Interp=tflite.Interpreter
    except ImportError:
        from tensorflow.lite.python.interpreter import Interpreter as Interp
    from PIL import Image
    interp=Interp(model_path=model_path); interp.allocate_tensors()
    ii=interp.get_input_details()[0]["index"]; oi=interp.get_output_details()[0]["index"]
    rows=[]
    for p in Path(data_dir).rglob("*.jpg"):
        img=np.array(Image.open(p).convert("RGB").resize((224,224)),dtype=np.float32)[np.newaxis]/255.0
        interp.set_tensor(ii,img); interp.invoke(); probs=interp.get_tensor(oi)[0]; top=int(np.argmax(probs))
        rows.append({"file":str(p),"true":p.parent.name,"pred":labels[top] if top<len(labels) else str(top),"conf":round(float(probs[top]),3),"ok":p.parent.name==(labels[top] if top<len(labels) else "")})
    with open(output_csv,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["file","true","pred","conf","ok"]); w.writeheader(); w.writerows(rows)
    ok=sum(1 for r in rows if r["ok"]); print(f"{ok}/{len(rows)} correct ({ok/max(len(rows),1)*100:.1f}%) → {output_csv}")

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--model_path",required=True); p.add_argument("--data_dir",required=True)
    p.add_argument("--labels",required=True); p.add_argument("--output_csv",default="audit.csv")
    a=p.parse_args(); run(a.model_path,a.data_dir,a.labels.split(","),a.output_csv)
