import os

from flask import Flask, render_template, request, jsonify
import json
from volcenginesdkarkruntime import Ark
import base64
from dotenv import load_dotenv
from volcengine.visual.VisualService import VisualService
import traceback

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

    def analyze_image(self, image_base64_list):
        try:
            content_list = [{"type": "text", "text": "作为资深心理学家与图像识别专家，通过分析人物的照片来分析不同方面因素。这涉及到心理学中的投射理论和图像识别技术的应用"
                                                     "请分析以下多张图片并给出以下内容：1.编写一个有趣的小故事（200字左右）\n"
                                                     "2.颜值分析（给出具体分数和特点，至少200字）:\n"
                                                     "具体格式为：EasyCheck评分：【分数】\n"
                                                     "         【人物特点】\n"
                                                     "替换【分数】，【人物特点】即可，分数后面需要<br/>\n"
                                                     "3.照片整体评价（包括灯光，角度，姿势），并换行给出改进意见，至少200字\n"
                                                     "4.性格特征分析，包括面部特征在内的面相分析，至少200字"
                                                     "文案均以第二人称进行叙述，用「你」指代照片中的人物"
                                                     "如果未识别到人脸，颜值分析，性格特征分析显示「未识别到人脸」"
                                                     "结果以json格式返回，不需要Markdown格式，记住返回结果只需要包含json即可，\n"
                                                     "key分别为story,appearance,review,personality\n"
                                                     "从输入的几张图片开始一步一步思考吧！"}]
            for image_base64 in image_base64_list:
                # 根据图片格式设置image/后的具体参数
                image_format = 'png'  # 默认格式
                if image_base64.startswith('data:image/jpeg'):
                    image_format = 'jpeg'
                elif image_base64.startswith('data:image/jpg'):
                    image_format = 'jpg'
                content_list.append(
                    {"type": "image_url", "image_url": {"url": f"data:image/{image_format};base64,{image_base64}"}})
            # 调用豆包的图像理解模型
            completion = self.client.chat.completions.create(
                model='ep-20250109143920-v49hz',
                messages=[
                    {"role": "system",
                     "content": "你是一个图像分析师，请对图片进行分析并给出幽默但不过分刻薄的评价。记住要输出纯文本，不要输出markdown"},
                    {"role": "user", "content": content_list}
                ]
            )
            print(completion.choices[0].message.content)
            return {
                "sections": json.loads(completion.choices[0].message.content)
            }
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"图片分析失败: {str(e)}")

    def generate_image(self, image_base64):
        try:
            image_base64 = base64.b64encode(image_base64).decode('utf-8')
            # 如果字符串包含 data:image 前缀，需要移除它
            if image_base64.startswith('data:image'):
                image_base64 = image_base64.split('base64,')[1]
            # 构建请求数据
            request_data = {
                "req_key": "img2img_chinese_style_usage",  # 中国红
                "binary_data_base64": [f"{image_base64}"],
                "return_url": False,
                "logo_info": {
                    "add_logo": True,
                    "position": 0,
                    "language": 1,
                    "logo_text_content": "轻舟Ai",
                    "opacity": "0.5",
                }
            }
            resp = self.visual_service.cv_process(request_data)
            print(resp['code'], resp['message'])
            return resp['data']['binary_data_base64'][0]
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"生成图片失败: {str(e)}")

    def process_user_message(self, history_message_list, image_base64):
        try:
            content_list = []
            if image_base64 is not None:
                content_list.append(
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}})
            messages = [
                {"role": "system",
                 "content": "作为专业的创意写作作家，通过分析人物的照片来分析不同方面因素，基于图片场景，已有故事情节以及用户回复信息继续文章的写作，作为故事的延续"
                            "故事需要以带有互动的方式展开，能够让用户参与进来，不要过于刻意，减少使用「快和说说」，「快和我讲讲」这类词语的使用方式"
                            "文案均以第二人称进行叙述，用「你」指代照片中的人物"
                            "结果以json格式返回，不需要Markdown格式，记住返回结果只需要包含json即可，\n"
                            "key分别为story\n"
                 },
                {"role": "user", "content": content_list}
            ]
            messages.extend(history_message_list)
            # 调用豆包的图像理解模型
            completion = self.client.chat.completions.create(
                model='ep-20250109143920-v49hz',
                messages=messages,
            )
            try:
                return json.loads(completion.choices[0].message.content)['story']
            except Exception as e:
                traceback.print_exc()
                print(f"json loads error: {completion.choices[0].message.content}")
                return completion.choices[0].message.content
        except Exception as e:
            raise Exception(f"图片分析失败: {str(e)}")


@app.route('/')
def home():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"渲染首页失败: {str(e)}")
        return jsonify({'error': '系统错误，请稍后重试'}), 500


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        if 'images' not in request.files:
            return jsonify({'error': '没有上传图片'}), 400

        files = request.files.getlist('images')
        if not files:
            return jsonify({'error': '没有选择任何图片'}), 400

        image_base64_list = []
        filenames = []

        for image in files:
            # 检查文件类型
            if not image.filename or not image.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                print(image.filename)
                return jsonify({'error': f'文件 {image.filename} 格式不支持，只支持PNG、JPG、JPEG格式的图片'}), 400

            # 读取文件内容
            image_data = image.read()

            # 转换为base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_base64_list.append(image_base64)
            filenames.append(image.filename)

        if not image_base64_list:
            return jsonify({'error': '没有有效的图片文件'}), 400

        ai = SarcasticAI()
        sections_result = ai.analyze_image(image_base64_list)

        return jsonify({
            'results': [{
                'filename': filenames[0],
                'analysis': sections_result
            }]
        })

    except Exception as e:
        print(f"处理图片分析请求失败: {str(e)}")
        return jsonify({'error': '分析失败，请重试'}), 500


@app.route('/generate_image', methods=['POST'])
def generate_cartoon():
    try:
        if 'image' not in request.files:
            return jsonify({'error': '没有上传图片'}), 400

        image = request.files['image']
        if not image.filename:
            return jsonify({'error': '没有选择图片'}), 400

        # 检查文件类型
        if not image.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            return jsonify({'error': '只支持PNG、JPG、JPEG格式的图片'}), 400

        # 读取图片数据
        image_data = image.read()
        if len(image_data) > 5 * 1024 * 1024:  # 5MB
            return jsonify({'error': '图片大小不能超过5MB'}), 400

        # 这里添加生成卡通图像的逻辑
        # 返回base64编码的图片数据
        ai = SarcasticAI()
        cartoon_image = ai.generate_image(image_data)  # 你需要实现这个函数

        return jsonify({
            'cartoon_image': f'data:image/jpeg;base64,{cartoon_image}'
        })

    except Exception as e:
        print(f"生成图像失败: {str(e)}")
        return jsonify({'error': '生成失败，请重试'}), 500


@app.route('/chat', methods=['POST'])
def chat():
    try:
        image_base64 = None
        if 'image' not in request.files:
            print('没有上传图片')
        else:
            image_base64 = request.files['image']
        history_message = request.form.get('history')
        history_message_list = json.loads(history_message)
        print(history_message_list)
        # 这里可以调用你的AI模型进行处理
        ai = SarcasticAI()
        # 假设你有一个方法可以处理用户消息并返回回复
        reply = ai.process_user_message(history_message_list, image_base64)

        return jsonify({'reply': reply})

    except Exception as e:
        traceback.print_exc()
        print(f"处理聊天请求失败: {str(e)}")
        return jsonify({'error': '聊天失败，请重试'}), 500


if __name__ == '__main__':
    print(ARK_API_KEY, DOUBAO_SK, DOUBAO_AK)
    app.run(host="0.0.0.0", port=6378, debug=True)
