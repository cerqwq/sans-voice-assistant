"""
Sans Web服务器 - 提供现代化Web界面
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from core.agent import Agent
from config import config

app = Flask(__name__, static_folder='static', template_folder='static')


@app.after_request
def after_request(response):
    """添加CORS头"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

# 初始化Agent
agent = None

def get_agent():
    global agent
    if agent is None:
        agent = Agent()
    return agent


@app.route('/')
def index():
    """主页"""
    return send_from_directory('static', 'index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天API"""
    data = request.json
    message = data.get('message', '')

    if not message:
        return jsonify({'error': '消息不能为空'}), 400

    try:
        agent = get_agent()
        response = agent.chat(message)
        return jsonify({
            'success': True,
            'response': response,
            'model': agent.assistant.current_model
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stream', methods=['POST'])
def stream():
    """流式聊天API"""
    data = request.json
    message = data.get('message', '')

    if not message:
        return jsonify({'error': '消息不能为空'}), 400

    def generate():
        try:
            agent = get_agent()
            for chunk in agent.run_task(message):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return app.response_class(
        generate(),
        mimetype='text/event-stream'
    )


@app.route('/api/status')
def status():
    """获取系统状态"""
    try:
        agent = get_agent()
        return jsonify({
            'success': True,
            'status': {
                'model': agent.assistant.current_model,
                'ollama_model': config.ollama_model,
                'mimo_model': config.mimo_model,
                'tools_count': len(agent.assistant.registry.get_tool_definitions()),
                'memory': agent.memory.get_user_info()
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tools')
def tools():
    """获取工具列表"""
    try:
        agent = get_agent()
        tools_list = agent.assistant.registry.get_tool_definitions()
        return jsonify({
            'success': True,
            'tools': [{'name': t['name'], 'description': t['description']} for t in tools_list]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/memory')
def memory():
    """获取记忆信息"""
    try:
        agent = get_agent()
        return jsonify({
            'success': True,
            'memory': agent.memory.memory
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def run_server(host='0.0.0.0', port=8080, debug=False):
    """启动服务器"""
    print(f"\n{'='*50}")
    print(f"  Sans Web 服务器")
    print(f"  http://localhost:{port}")
    print(f"{'='*50}\n")

    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Sans Web服务器')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8080, help='监听端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    args = parser.parse_args()

    run_server(args.host, args.port, args.debug)
