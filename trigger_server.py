import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)
process = None  # To keep track of the running script

@app.route('/start', methods=['POST'])
def start_script():
    global process
    data = request.json
    input_val = data.get('input', '').lower()

    if process and process.poll() is None:
        return jsonify({"status": "already running"})

    cmd = ['python3', '/home/stikeez/Desktop/project/read_data.py']
    if input_val == 'y':
        cmd.append('y')  # if your script accepts args for different modes

    process = subprocess.Popen(cmd)
    return jsonify({"input": input_val, "status": "started"})

@app.route('/stop', methods=['POST'])
def stop_script():
    global process
    if process and process.poll() is None:
        process.terminate()  # or process.kill() for force kill
        process.wait()
        return jsonify({"status": "stopped"})
    else:
        return jsonify({"status": "not running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
