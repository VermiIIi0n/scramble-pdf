import streamlit as st
import os
import tempfile
from pikepdf import Pdf
from scramblepdf import scramble_pdf

st.set_page_config(
    page_title="抗AI检测",
    page_icon="📄",
    layout="centered"
)

st.title("PDF抗AI处理工具")
st.write("SDU特供版")

uploaded_file = st.file_uploader(
    label="上传 PDF 文件并设置处理比例", 
    type=['pdf'],
    accept_multiple_files=False,
    help="请上传单个PDF文件，大小不超过20MB"
)

if uploaded_file is not None:
    # 检查文件大小（20MB = 20 * 1024 * 1024 字节）
    file_size = len(uploaded_file.getvalue()) / (1024 * 1024)  # 转换为 MB
    if file_size > 20:
        st.error(f"文件大小（{file_size:.1f}MB）超过20MB限制，请上传更小的文件。")
    else:
        scramble_ratio = st.slider("处理比例", min_value=0.0, max_value=1.0, value=0.3, step=0.01)
        
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
                    # 打开PDF并进行加扰
                    pdf = Pdf.open(input_path)
                    # 添加调试信息
                    st.info(f"正在使用scramble_ratio={scramble_ratio}处理PDF...")
                    scramble_pdf(pdf, None, scramble_ratio)
                    pdf.save(output_path)

                    # 获取处理前后的文件大小以进行比较
                    input_size = os.path.getsize(input_path) / 1024  # KB
                    output_size = os.path.getsize(output_path) / 1024  # KB
                    
                    # 显示处理成功的信息
                    st.success(f"PDF处理成功！处理前大小: {input_size:.2f}KB, 处理后大小: {output_size:.2f}KB")

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
    scramble_ratio = st.slider("处理比例", min_value=0.0, max_value=1.0, value=0.3, step=0.01)

# 显示参考图
st.image("gui/web/images/recommended_reference_line_plot.svg", caption="参考调整图，实验数据源于AIGC完全编写的PDF文档，未处理情况下paperYY-AI检测率为92%")

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
1. 处理完毕后自行使用AI检测服务完成pdf检测
2. 对于毕设系统，可将pdf打包zip格式提交

### 源码
https://github.com/VermiIIi0n/scramble-pdf
""")
