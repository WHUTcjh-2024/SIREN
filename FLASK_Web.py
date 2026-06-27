"""
FLASK_Web.py — Flask 应用入口
服务 Jinja2 模板，匹配截图中的 UI 布局
"""
import os
from flask import Flask, render_template, send_from_directory
from config import COMPETITION_CONFIG

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'siren-dev-key')


@app.route('/')
def index():
    return render_template(
        'index.html',
        competition=COMPETITION_CONFIG,
        active_nav='home',
    )


@app.route('/preview-quiz')
def preview_quiz():
    return render_template(
        'preview_quiz_page.html',
        competition=COMPETITION_CONFIG,
        active_nav='preview',
    )


@app.route('/laser-diffraction')
def laser_diffraction():
    return render_template(
        'laser_diffraction.html',
        competition=COMPETITION_CONFIG,
        active_nav='static_capture',
        surface3d_siren_src='/static/img/surface3d-siren.png',
        surface3d_pinn_src='/static/img/surface3d-pinn.png',
    )


@app.route('/data-processing')
def data_processing():
    return render_template(
        'data_processing.html',
        competition=COMPETITION_CONFIG,
        active_nav='static_process',
    )


@app.route('/dynamic-video-capture')
def dynamic_video_capture():
    return render_template(
        'experiment_module_placeholder.html',
        competition=COMPETITION_CONFIG,
        active_nav='dynamic_capture',
        module_title='动态图像采集',
        module_subtitle='表面张力 σ · 变温衍射图',
        module_icon='fa-video-camera',
    )


@app.route('/dynamic-data-processing')
def dynamic_data_processing():
    return render_template(
        'experiment_module_placeholder.html',
        competition=COMPETITION_CONFIG,
        active_nav='dynamic_process',
        module_title='动态数据处理',
        module_subtitle='σ–T 关系 · 拟合与对比',
        module_icon='fa-line-chart',
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
