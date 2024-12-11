from flask import Flask, request, jsonify
from flask_cors import CORS
from excutor.excutor import CodeExecutor
from excutor.utils import CodeBlock, File
from excutor.manager import ExecutorManage
import os

app = Flask(__name__)
CORS(app)
manager = ExecutorManage()

@app.route('/setup', methods=['POST'])
def setup():
    flow_id = request.json.get('flowId')
    packages = request.json.get('packages')
    language = request.json.get('language')
    container_name = f"csflow-{flow_id}"
    executor = manager.get_executor(container_name)
    if executor is None:
        executor = CodeExecutor(container_name=container_name)
        manager.register_excutor(executor)
        code_result = executor.setup(packages=packages, lang=language)
    else:
        code_result = executor.setup(packages=packages, lang=language)
    print(f"Setup Flow ID: {flow_id}, Console: {code_result.console}")
    return jsonify({
        'container_name': executor._container_name,
        'exit_code': code_result.exit_code, 
        'console': code_result.console,
        'output': code_result.output,
    })

@app.route('/keep_alive', methods=['POST'])
def keep_alive():
    flowId = request.json.get('flowId')
    container_name = f"csflow-{flowId}"
    print(f"Update Flow ID: {flowId}")
    executor = manager.get_executor(container_name)
    if executor is None:
        executor = CodeExecutor(container_name=container_name)
        manager.register_excutor(executor)
        manager.keep_alive(executor._container_name)
    else:
        manager.keep_alive(executor._container_name)
    return jsonify({
        'container_name': executor._container_name,
        'last_update': executor._last_update_time
    })

@app.route('/execute', methods=['POST'])
def execute():
    flow_id = request.json.get('flowId')
    session_id = request.json.get('sessionId')
    print(f"Execute Flow ID: {flow_id}, Session ID: {session_id}")
    code_blocks = request.json.get('codeBlocks')
    container_name = f"csflow-{flow_id}"
    if code_blocks is None:
        return jsonify({'error': 'No code blocks provided.'}), 400
    executor = manager.get_executor(container_name)
    if executor is None:
        executor = CodeExecutor(container_name=container_name)
        manager.register_excutor(executor)
    
    exeucte_blocks = []
    for code_block in code_blocks:
        code_block = CodeBlock(
            session_id = session_id,
            code=code_block["code"],
            language=code_block["language"],
            files=[File(path=file["path"], data=file["data"]) for file in code_block["files"]] if "files" in code_block else None
        )
        exeucte_blocks.append(code_block)
    code_result= executor.execute(exeucte_blocks)
    return jsonify({
        'container_name': executor._container_name,
        'exit_code': code_result.exit_code, 
        'console': code_result.console,
        'output': code_result.output
    })

@app.route('/remove_session', methods=['POST'])
def remove_ssesion():
    flow_id = request.json.get('flowId')
    session_id = request.json.get('sessionId')
    print(f"Remove Flow ID: {flow_id}, Session ID: {session_id}")
    container_name = f"csflow-{flow_id}"
    executor = manager.get_executor(container_name)
    if executor:
        executor = CodeExecutor(container_name=container_name)
        manager.register_excutor(executor)
        executor.remove_session(session_id)
        return jsonify({
            'container_name': executor._container_name,
            'session_id': session_id, 
        })
    else:
        return jsonify({
            'container_name': None,
            'session_id': None,
            'warning': 'Container not found.'
        })

@app.route('/kill', methods=['POST'])
def kill_executor():
    flow_id = request.json.get('flowId')
    container_name = f"csflow-{flow_id}"
    print(f"Kill Flow ID: {flow_id}")
    executor = manager.get_executor(container_name)
    if executor:
        manager.unregister_excutor(container_name)
        return jsonify({
            'container_name': container_name,
            'exit_code': 0,
            'output': 'Container has been removed.'
        })
    else:
        return jsonify({
            'container_name': container_name,
            'exit_code': 1,
            'output': 'Container not found.'
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)




