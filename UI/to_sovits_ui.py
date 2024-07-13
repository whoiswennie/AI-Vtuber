import shutil
import streamlit as st
import os
import subprocess
import utils

def main():
    if 'so_vits_protect_root_path' not in st.session_state:
        if os.path.exists("template/json/project_path.json"):
            sovits_path = utils.load_json("template/json/project_path.json").get("sovits_path")
            if sovits_path:
                st.session_state.so_vits_protect_root_path = sovits_path
            else:
                st.session_state.so_vits_protect_root_path = ""
        else:
            st.session_state.so_vits_protect_root_path = ""
    st.write("---")
    so_vits_protect_root_path = st.text_input("请填写本地so-vits-svc项目的根目录路径",value=st.session_state.so_vits_protect_root_path)
    if so_vits_protect_root_path:
        st.session_state.so_vits_protect_root_path = so_vits_protect_root_path
    utils.write_json({"sovits_path":so_vits_protect_root_path},"template/json/project_path.json")
    try:
        if so_vits_protect_root_path:
            with st.expander("查看教程"):
                with open(os.path.join(so_vits_protect_root_path,"README_zh_CN.md"), 'r',encoding="utf-8") as file:
                    readme_content = file.read()
                st.markdown(readme_content)

        with st.expander("0.前置准备"):
            st.caption("你应该提前将音色数据集以下面的格式存放在so-vits-svc项目文件夹中，其中如果希望训练的是单说话人，dataset_raw中仅需存在一个speaker；如果希望训练多说话人，dataset_raw中需要存在多个speaker的子文件夹。")
            st.caption("原始音色数据集存放格式:")
            st.code("""
                        dataset_raw
                        ├───speaker0
                        │   ├───xxx1-xxx1.wav
                        │   ├───...
                        │   └───Lxx-0xx8.wav
                        └───speaker1
                            ├───xx2-0xxx2.wav
                            ├───...
                            └───xxx7-xxx007.wav
                        """)
            st.caption("其中每一条音频要求为，清晰的，干净的，单个说话人音频（说话与唱歌都可以），需要切片至5-15秒（稍微长一点或者短一点都行）")
            st.write("---")
        with st.expander("1.重采样"):
            st.caption("虽然本项目拥有重采样、转换单声道与响度匹配的脚本 resample.py，但是默认的响度匹配是匹配到 0db。这可能会造成音质的受损。而 python 的响度匹配包 pyloudnorm 无法对电平进行压限，这会导致爆音。所以建议可以考虑使用专业声音处理软件如`adobe audition`等软件做响度匹配处理。若已经使用其他软件做响度匹配，可以在运行前选择`跳过响度匹配步骤`。")
            st.write("---")
            is_skip_loudnorm = st.checkbox("跳过响度匹配步骤")
            if st.button("1.重采样"):
                if is_skip_loudnorm:
                    command = f'cd /d "{st.session_state.so_vits_protect_root_path}" && start "" "{st.session_state.so_vits_protect_root_path}/1重采样-skip_loudnorm.bat"'
                else:
                    command = f'cd /d "{st.session_state.so_vits_protect_root_path}" && start "" "{st.session_state.so_vits_protect_root_path}/1重采样.bat"'
                subprocess.Popen(command, shell=True)
        with st.expander("2.自动划分训练集、验证集，以及自动生成配置文件"):
            st.caption("**使用响度嵌入**若使用响度嵌入，需要选择`使用响度嵌入`")
            st.write("---")
            is_vol_aug = st.checkbox("使用响度嵌入")
            if st.button("2.自动划分训练集、验证集，以及自动生成配置文件"):
                if is_vol_aug:
                    command = f'cd /d "{st.session_state.so_vits_protect_root_path}" && start "" "{st.session_state.so_vits_protect_root_path}/2划分训练验证集-vol_aug.bat"'
                else:
                    command = f'cd /d "{st.session_state.so_vits_protect_root_path}" && start "" "{st.session_state.so_vits_protect_root_path}/2划分训练验证集.bat"'
                subprocess.Popen(command, shell=True)
        with st.expander("打开config文件夹"):
            if st.button("打开config文件夹"):
                subprocess.run(['explorer', os.path.abspath(os.path.join(st.session_state.so_vits_protect_root_path, "configs"))])
        with st.expander("3.生成hubert与f0"):
            is_use_diff = st.checkbox("启用浅扩散功能")
            if st.button("3.生成hubert与f0"):
                if is_use_diff:
                    command = f'cd /d "{st.session_state.so_vits_protect_root_path}" && start "" "{st.session_state.so_vits_protect_root_path}/3生成hubert与f0_use_diff.bat"'
                else:
                    command = f'cd /d "{st.session_state.so_vits_protect_root_path}" && start "" "{st.session_state.so_vits_protect_root_path}/3生成hubert与f0.bat"'
                subprocess.Popen(command, shell=True)
        with st.expander("4.模型训练"):
            col1,col2 = st.columns(2)
            is_diffusion = col1.checkbox("是否训练扩散模型",key=0)
            is_tensorboard = col2.checkbox("启动tensorboard",key=1)
            if is_tensorboard:
                command = f'cd /d "{st.session_state.so_vits_protect_root_path}" && start "" "{st.session_state.so_vits_protect_root_path}/启动tensorboard.bat"'
                subprocess.Popen(command, shell=True)
            if st.button("4.开始训练"):
                if is_diffusion:
                    shutil.copy2(f"{st.session_state.so_vits_protect_root_path}/pretrain/diffusion/model_0.pt",
                                 f"{st.session_state.so_vits_protect_root_path}/logs/44k/diffusion")
                    command = f'cd /d "{st.session_state.so_vits_protect_root_path}" && start "" "{st.session_state.so_vits_protect_root_path}/4模型训练_diffusion.bat"'
                else:
                    shutil.copy2(f"{st.session_state.so_vits_protect_root_path}/pretrain/vec768l12/G_0.pth", f"{st.session_state.so_vits_protect_root_path}/logs/44k")
                    shutil.copy2(f"{st.session_state.so_vits_protect_root_path}/pretrain/vec768l12/D_0.pth", f"{st.session_state.so_vits_protect_root_path}/logs/44k")
                    command = f'cd /d "{st.session_state.so_vits_protect_root_path}" && start "" "{st.session_state.so_vits_protect_root_path}/4模型训练.bat"'
                subprocess.Popen(command, shell=True)
        with st.expander("5.模型推理"):
            if st.button("启动webUI"):
                command = f'cd /d "{st.session_state.so_vits_protect_root_path}" && start "" "{st.session_state.so_vits_protect_root_path}/启动webUI.bat"'
                subprocess.Popen(command, shell=True)
        with st.expander("项目初始化"):
            if st.button("项目初始化"):
                folder_path_lists = [f'{st.session_state.so_vits_protect_root_path}/dataset',f'{st.session_state.so_vits_protect_root_path}/filelists',f'{st.session_state.so_vits_protect_root_path}/logs/44k',f'{st.session_state.so_vits_protect_root_path}/logs/44k/diffusion']
                for folder_path in folder_path_lists:
                    if os.path.exists(folder_path) and os.path.isdir(folder_path):
                        for filename in os.listdir(folder_path):
                            file_path = os.path.join(folder_path, filename)
                            if filename == "diffusion":
                                continue
                            try:
                                if os.path.isdir(file_path):
                                    shutil.rmtree(file_path)
                                else:
                                    os.remove(file_path)
                            except Exception as e:
                                print(f'Error deleting {file_path}: {e}')
                    else:
                        print(f'The folder {folder_path} does not exist or is not a directory.')
                st.success("项目初始化成功！")
    except Exception as e:
        st.error(e)


if __name__ == '__main__':
    main()