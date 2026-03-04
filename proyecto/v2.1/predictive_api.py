import os
import json
from pathlib import Path
from importlib import util
from flask import Flask, request, jsonify

BASE = Path(__file__).parent
MODULE_PATH = BASE / '6_Predictive_Maintenance.py'

def load_module(path):
    spec = util.spec_from_file_location('predictive_mod', str(path))
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

app = Flask('predictive_api')

# load predictive module on startup
PRED = load_module(MODULE_PATH)

@app.route('/report')
def report():
    line = int(request.args.get('line', 1))
    start = request.args.get('start')
    end = request.args.get('end')
    rpt = PRED.generate_report(PRED.load_maintenance(), line, start, end)
    return jsonify(rpt)

@app.route('/predict')
def predict():
    line = int(request.args.get('line', 1))
    window = int(request.args.get('window', 1))
    df = PRED.build_training_data_from_logs(PRED.LOGS_FILE, window_hours=window)
    if df is None:
        return jsonify({'error': 'no training data'}), 400
    df_line = df[df['linea'] == line]
    if df_line.empty:
        return jsonify({'error': 'no data for line'}), 400
    if PRED.MODEL is not None:
        X = df_line[['avg_tc', 'total', 'scrap', 'error']]
        probs = PRED.MODEL.predict_proba(X)[:, 1]
        out = [{'t': str(t), 'risk': float(p*100.0)} for t, p in zip(df_line['t'], probs)]
    else:
        out = [{'t': str(t), 'risk': float(((e+s)/(tot+1))*100.0)} for t, e, s, tot in zip(df_line['t'], df_line['error'], df_line['scrap'], df_line['total'])]
    return jsonify(out)

if __name__ == '__main__':
    port = int(os.environ.get('PRED_API_PORT', 5005))
    app.run(host='0.0.0.0', port=port)
