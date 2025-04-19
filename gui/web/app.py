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

st.title("PDF抗AI检测处理(SDU局域网特供版)")
st.write("上传 PDF 文件并设置加扰比例。")

uploaded_file = st.file_uploader("选择 PDF 文件", type=['pdf'])
scramble_ratio = st.slider("加扰比例", min_value=0.0, max_value=1.0, value=0.3, step=0.1)

# 显示参考图
st.image("images/recommended_reference_line_plot.svg", caption="参考调整图 \n 测试文件见")

if uploaded_file is not None:
    if st.button("开始加扰"):
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
                scramble_pdf(pdf, None, scramble_ratio)
                pdf.save(output_path)

                # 读取处理后的PDF并提供下载
                with open(output_path, 'rb') as file:
                    output_pdf = file.read()
                    st.download_button(
                        label="下载加扰后的PDF",
                        data=output_pdf,
                        file_name="scrambled.pdf",
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"处理过程中出现错误：{str(e)}")
            finally:
                # 清理临时文件
                os.unlink(input_path)
                os.unlink(output_path)

st.markdown("---")
st.markdown("""
### 使用说明
1. 点击"选择 PDF 文件"上传您要处理的 PDF 文件
2. 使用滑块调整加扰比例（0 表示不加扰，1 表示完全加扰）
3. 点击"开始加扰"按钮
4. 处理完成后，点击"下载加扰后的PDF"获取结果
""") 