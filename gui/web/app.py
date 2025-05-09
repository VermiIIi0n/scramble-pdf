import streamlit as st
import os
import tempfile
import unicodedata
import csv
import datetime
import time
import random
from pikepdf import Pdf
from scramblepdf import scramble_pdf

# 定义日志文件路径
LOG_FILE = "savedpdf/log.csv"
SAVED_PDF_DIR = "savedpdf"

# 定义最大文件大小（MB）
MAX_FILE_SIZE_MB = 20

# 默认启用处理延迟（模拟处理耗时），但会被UI选项覆盖
enable_processing_delay = True

def log_pdf_processing(original_filename, saved_filename, file_size_mb, scramble_ratio, protected_chars=None):
    """将PDF处理信息记录到CSV日志文件中"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 确保savedpdf目录存在
    os.makedirs(SAVED_PDF_DIR, exist_ok=True)

    # 检查日志文件是否存在，不存在则创建并写入表头
    file_exists = os.path.isfile(LOG_FILE)

    with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as file:
        fieldnames = ['时间戳', '原文件名', '保存文件名', '文件大小(MB)', '处理比例', '保护字符']
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            '时间戳': timestamp,
            '原文件名': original_filename,
            '保存文件名': saved_filename,
            '文件大小(MB)': f"{file_size_mb:.2f}",
            '处理比例': scramble_ratio,
            '保护字符': protected_chars or ""
        })

    print(f"INFO: 已记录PDF处理信息 - 原文件名：{original_filename}，保存为：{saved_filename}")



st.set_page_config(
    page_title="抗AI检测",
    page_icon="🥳",
    layout="centered"
)

st.title("PDF抗AI检测工具")
st.write("出于网络文本著作内容的保护目的而开发")

st.markdown("""

> ### ⚠️免责声明
> 
> 本技术仅供学习与学术交流之用，旨在探索网络文本著作内容的保护机制。
请用户在合法、合理的范围内使用本工具，严禁用于侵犯他人权益或规避内容审核等不当用途。
若因不当使用（即出于非正当目的的使用）而产生任何法律后果，责任概由使用者自行承担，开发者不对此承担任何责任。
""")

# 增加文件大小限制提示
# st.info(f"文件大小限制：{MAX_FILE_SIZE_MB}MB。较大的PDF文件处理可能需要较长时间。")

uploaded_file = st.file_uploader(
    label="上传 PDF 文件并设置处理比例",
    type=['pdf'],
    accept_multiple_files=False,
    help=f"请上传单个PDF文件，大小不超过{MAX_FILE_SIZE_MB}MB"
)

# 添加自定义保护字符输入框
st.markdown(
    '''
    ---
    保护相关字符以不参与混淆，详情点击下框右侧帮助符号
    '''
)
protected_chars = st.text_input(
    "自定义保护字符（这些字符将不会被处理）", 
    value="图表XX大学本科毕业论文设计IV",
    help="输入您希望保护的字符，字符间无需分隔。例如：图表东京大学本科毕业论文设计IV。本程序强制保护除各语言字母之外的符号（例如：\"您OK\"不受保护，\"123!,?!123\"受保护，不参与混淆），如有特殊需求请自行修改源码。"
)


def select_func(c: str) -> bool:
    """选择要保护的字符
    当 select_as_blacklist=True 时:
    - 返回True表示字符将被列入黑名单(保护，不被处理)
    - 返回False表示字符可能被处理(取决于ratio)
    
    注意：在scramble_pdf函数中，判断逻辑是：
    if selector(dstc) != select_as_blacklist:
        字符可能被处理
    else:
        字符被保护
    """
    # 对于用户自定义的保护字符或非字母类字符，返回True保护它们
    if c in protected_chars or not unicodedata.category(c).startswith("L"):
        return True
    
    # 对于其他字符(主要是字母类)，返回False允许处理
    return False


if uploaded_file is not None:
    # 检查文件大小
    file_size = len(uploaded_file.getvalue()) / (1024 * 1024)  # 转换为 MB
    if file_size > MAX_FILE_SIZE_MB:
        st.error(f"文件大小（{file_size:.1f}MB）超过{MAX_FILE_SIZE_MB}MB限制，请上传更小的文件。")
    else:
        scramble_ratio = st.slider("处理比例", min_value=0.0,
                                   max_value=1.0, value=0.3, step=0.05)

        # 创建三列布局，使按钮居中且宽度为50%
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            start_button = st.button("开始处理", type="secondary", use_container_width=True)

        # 修正缩进，确保只有在点击按钮时才处理PDF
        if start_button:
            with st.spinner("正在处理..."):
                # 创建临时文件来处理上传的PDF
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_input:
                    tmp_input.write(uploaded_file.getvalue())
                    input_path = tmp_input.name

                # 创建临时文件用于输出
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_output:
                    output_path = tmp_output.name

                try:
                    # 生成时间戳文件名并保存原始PDF
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    saved_filename = f"{timestamp}.pdf"
                    saved_path = os.path.join(SAVED_PDF_DIR, saved_filename)

                    # 确保目录存在
                    os.makedirs(SAVED_PDF_DIR, exist_ok=True)

                    # 保存原始PDF
                    with open(saved_path, "wb") as f:
                        f.write(uploaded_file.getvalue())

                    # 记录日志
                    log_pdf_processing(
                        original_filename=uploaded_file.name,
                        saved_filename=saved_filename,
                        file_size_mb=file_size,
                        scramble_ratio=scramble_ratio,
                        protected_chars=protected_chars
                    )

                    # 打开PDF并进行加扰
                    pdf = Pdf.open(input_path)
                    # 添加调试信息
                    st.info(f"正在使用scramble_ratio={scramble_ratio}处理PDF...")

                    # 添加随机延迟，模拟处理时间
                    if enable_processing_delay:
                        delay_seconds = random.uniform(2, 5)
                        time.sleep(delay_seconds)
                        
                    try:
                        scramble_pdf(
                            pdf,
                            scramble_ratio,
                            selector=select_func,
                            select_as_blacklist=True,
                        )
                        pdf.save(output_path)
                    except ValueError as e:
                        if "not enough values to unpack" in str(e):
                            st.warning("处理过程中没有找到符合条件的字符，尝试使用默认处理方式...")
                            # 重新打开PDF
                            pdf = Pdf.open(input_path)
                            # 使用默认设置处理
                            scramble_pdf(pdf, scramble_ratio)
                            pdf.save(output_path)
                        else:
                            raise

                    # 获取处理前后的文件大小以进行比较
                    input_size = os.path.getsize(input_path) / 1024  # KB
                    output_size = os.path.getsize(output_path) / 1024  # KB

                    # 显示处理成功的信息
                    st.success(
                        f"PDF处理成功！处理前大小: {input_size:.2f}KB, 处理后大小: {output_size:.2f}KB")

                    # 读取处理后的PDF并提供下载
                    with open(output_path, 'rb') as file:
                        output_pdf = file.read()
                        # 创建三列布局使按钮居中
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.download_button(
                                label="下载处理后的PDF",
                                data=output_pdf,
                                file_name="processed.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                type="primary"
                            )
                except Exception as e:
                    st.error(f"处理过程中出现错误：{str(e)}")
                finally:
                    # 清理临时文件
                    os.unlink(input_path)
                    os.unlink(output_path)
else:
    scramble_ratio = st.slider("处理比例", min_value=0.0,
                               max_value=1.0, value=0.3, step=0.05)

# 显示参考图
st.image("gui/web/images/recommended_reference_line_plot.svg",
         caption="本图表示了在测试数据上不同的处理比例对AIGC检测的影响，实验数据源于完全由AIGC编写的PDF文档，处理前的paperYY-AI检测率为92%")

# 添加测试文件下载按钮
col1, col2, col3 = st.columns(3)
with col1:
    with open("tests/testPDF/AIGC.pdf", "rb") as file1:
        test_file1 = file1.read()
        st.container().download_button(
            label="下载测试文件:PDF[处理前]",
            data=test_file1,
            file_name="AIGC.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    st.caption("完全由AI生成主要内容的PDF文件")

with col2:
    with open("tests/testPDF/AIGC.typ", "rb") as file2:
        test_file2 = file2.read()
        st.container().download_button(
            label="下载测试文件:typst源码",
            data=test_file2,
            file_name="AIGC.typ",
            mime="text/plain",
            use_container_width=True
        )
    st.caption(
        "测试文件的Typst源文件，PDF使用[unofficial-sdu-thesis](https://github.com/GrooveWJH/unofficial-sdu-thesis)生成")

with col3:
    with open("tests/testPDF/AIGC-100.pdf", "rb") as file1:
        test_file1 = file1.read()
        st.container().download_button(
            label="下载测试文件:PDF[55%扰乱处理后]",
            data=test_file1,
            file_name="AIGC-100.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    st.caption("已经处理过的PDF文件示例")


st.markdown("---")
st.markdown("""
### 说明
1. 处理完毕后，用户应当自行使用各类检测服务完成各项指标检测。
2. 本程序确保布局与关键字格式上的前后一致，但对于内容不做保证。
### 来源
源码
https://github.com/VermiIIi0n/scramble-pdf
-->
""")
