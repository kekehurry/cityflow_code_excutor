import docker.errors
from flask import Flask, request, jsonify,session
from flask_cors import CORS
from excutor.excutor import CodeExecutor
from excutor.utils import CodeBlock
import time,threading
import docker
import uuid


app = Flask(__name__)
CORS(app)
app.secret_key = 'cs-python-executor'
container_registry = {}

# if the container is inactive for 5 minutes, stop the container
idle_time = 60  # 1 minutes timeout
idle_threshold = 0.1 # if lower than 0.1% CPU usage, stops the container
check_interval = 10 # check every 10 seconds

client = docker.from_env()
def get_executor(session_id):
    if session_id in container_registry:
        container_name = container_registry[session_id]
        executor = CodeExecutor(container_name=container_name)
    else:
        executor = CodeExecutor()
        container_registry[session_id] = executor._container_name
    return executor

def calculate_cpu_percent(docker_stats):
    cpu_delta = docker_stats["cpu_stats"]["cpu_usage"]["total_usage"] - docker_stats["precpu_stats"]["cpu_usage"]["total_usage"]
    system_cpu_delta = docker_stats["cpu_stats"]["system_cpu_usage"] - docker_stats["precpu_stats"]["system_cpu_usage"]
    number_cpus = docker_stats["cpu_stats"]["online_cpus"]
    if system_cpu_delta > 0 and cpu_delta > 0:
        cpu_percent = (cpu_delta / system_cpu_delta) * number_cpus * 100.0
    else:
        cpu_percent = 0.0
    return cpu_percent

def is_container_idle(container, idle_threshold=60):
    # Get container stats
    stats = container.stats(stream=False)
    cpu_perc = calculate_cpu_percent(stats)
    # If CPU usage is below a certain threshold, consider it idle
    return cpu_perc <= idle_threshold

def stop_if_idle(check_interval=10, idle_time=60):
    idle_start = {}
    while True:
        for session_id in list(container_registry.keys()):
            container_name = container_registry.get(session_id)
            if container_name is None:
                continue
            try:
                container = client.containers.get(container_name)
                if is_container_idle(container, idle_threshold):
                    if session_id not in idle_start:
                        idle_start[session_id] = time.time()
                    elif time.time() - idle_start[session_id] >= idle_time:
                        container.stop()
                        print(f"Container {container_name} stopped due to inactivity.")
                        del container_registry[session_id]
                        del idle_start[session_id]
                else:
                    if session_id in idle_start:
                        del idle_start[session_id]
            except docker.errors.NotFound:
                if session_id in container_registry:
                    del container_registry[session_id]
        time.sleep(check_interval)

@app.route('/api/execute', methods=['POST'])
def execute_code_block():
    session_id = request.json.get('session_id')
    code_blocks = request.json.get('code_blocks')
    if code_blocks is None:
        return jsonify({'error': 'No code blocks provided.'}), 400
    if session_id is None:
        session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    executor = get_executor(session_id)
    code_blocks = [CodeBlock(code=code_block["code"],language=code_block["language"]) for code_block in code_blocks]
    code_result= executor.execute_code_blocks(code_blocks)
    return jsonify({
        'exit_code': code_result.exit_code, 
        'output': code_result.output, 
        'session_id': session['session_id'], 
        'container_name': container_registry[session['session_id']]
    })

if __name__ == '__main__':
    # Start the inactivity monitor thread
    inactivity_thread = threading.Thread(target=stop_if_idle, args=(check_interval, idle_time))
    inactivity_thread.daemon = True
    inactivity_thread.start()
    
    app.run(debug=True, host='0.0.0.0', port=8000)




