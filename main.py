import os

from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import json
from volcenginesdkarkruntime import Ark
import base64
from dotenv import load_dotenv
from volcengine.visual.VisualService import VisualService
import traceback
import time

# 加载环境变量
load_dotenv()
print(os.environ)
ARK_API_KEY = os.getenv('ARK_API_KEY')
DOUBAO_AK = os.getenv('DOUBAO_AK')
DOUBAO_SK = os.getenv('DOUBAO_SK')

app = Flask(__name__)


class SarcasticAI:
    def __init__(self):
        self.client = Ark(api_key=ARK_API_KEY)
        self.visual_service = VisualService()
        self.visual_service.set_ak(DOUBAO_AK)
        self.visual_service.set_sk(DOUBAO_SK)

    def process_user_message(self, history_message_list):
        try:
            messages = [
                {"role": "system",
                 "content": "你是一位专业的光伏电站运维专家，具备丰富的光伏电站运维经验和技术知识。你的主要职责是：\n"
                            "1. 帮助用户分析和解决光伏电站运行中的各类问题\n"
                            "2. 提供专业的运维建议和最佳实践\n"
                            "3. 协助用户进行设备故障诊断和性能优化\n"
                            "4. 解答用户关于光伏电站运维的技术问题\n"
                            "5. 提供预防性维护建议和运维计划制定指导\n\n"
                            "在回答问题时，你需要：\n"
                            "- 保持专业性和准确性\n"
                            "- 提供具体可行的解决方案\n"
                            "- 必要时提供相关的技术参数和标准\n"
                            "- 注意安全事项和操作规范\n"
                            "- 使用清晰易懂的语言解释专业概念\n\n"
                            "- 切记不要出现需要用户补充的模块，类似于[具体日期]"
                            "结果需要包含你的专业建议和解决方案,请输出标准的MarkDown格式，注意空行和符号运用 \n"

                 },
                {"role": "system", "content": "这是今日(5月12日)光伏发电站的具体数据，发电量：2458kWh(较昨日增长12.5%),本月累计：32,156 kWh(较上月提升8.2%)"
                                              "光照强度:856W/m²(较昨日下降5.8%), 故障设备(3台): 逆变器 #A203 故障, 电池组 #B105 温度过高, 光伏板 #P312 灰尘积累"
                                              "基于传感器数据分析设备状态:91.2分,发电效率:18.6%(理论峰值22%)"
                                              "AI智能运维意见：1. 建议在明日上午9-11点进行逆变器#A203的维护，此时段发电量最低，影响最小。"
                                              "2. 根据天气预报，后日有降雨，建议提前检查排水系统。3. C区光伏板角度可调整+5度以提高下午发电效率。"
                 }
            ]
            messages.extend(history_message_list)

            def generate():
                stream = self.client.chat.completions.create(
                    model="doubao-pro-32k-241215",
                    temperature=0.7,
                    messages=messages,
                    stream=True  # 启用流式输出
                )

                collected_content = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        content = content.replace('\n', '<br/>')  # 替换换行符
                        print(content)
                        yield f'data: {content}\n\n'
                yield 'data: [END]\n\n'

            return generate()
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"处理消息失败: {str(e)}")


@app.route('/')
def home():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"渲染首页失败: {str(e)}")
        return jsonify({'error': '系统错误，请稍后重试'}), 500


@app.route('/chat', methods=['GET', 'POST'])
def chat():
    try:
        history_message_list = request.json.get('chatHistory', [])
        print(history_message_list)
        ai = SarcasticAI()
        return Response(
            stream_with_context(ai.process_user_message(history_message_list)),
            mimetype='text/event-stream'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/static/<path:filename>')
def static_files(filename):
    try:
        return app.send_static_file(filename)
    except Exception as e:
        print(f"加载静态资源失败: {str(e)}")
        return jsonify({'error': '静态资源加载失败'}), 404


if __name__ == '__main__':
    app.run(debug=True)
