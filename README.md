# 石墨烯双槽天线：论文图 2d 的 HFSS 近似复现

本仓库提供按论文显微图估计尺寸的 HFSS 参数化建模脚本，目标为 100–220 GHz 的输入阻抗与 S₁₁。

**尚未进行 HFSS 全波求解。** 当前已完成 Python 语法、PyAEDT 0.18.1 接口核对和二维导体连通性检查；不代表 HFSS 内建模或求解已验证，也不保证与论文曲线重合。

- [中文运行说明](hfss/README_中文.md)
- [下载完整脚本包](downloads/HFSS_fig2d.zip)（打开后点击 Download raw file；也可用仓库 Code → Download ZIP）
- [建模脚本](hfss/build_hfss.py)
- [参数文件](hfss/parameters.json)
- [结果绘图脚本](hfss/plot_results.py)

## 近似版图预览

下图是建模预览，不是仿真场图或计算结果。

![近似双槽天线及扼流结构](hfss/output/layout.png)

## 论文对照图

图片来自用户提供的论文 arXiv:2603.03554v3，仅用于核对目标和结构，不是本次仿真结果。

![论文图 2d 对照](hfss/reference_fig2d.png)

## 本地运行

需要可用的 AEDT/HFSS 安装和许可证，推荐独立 CPython 3.11。详细的安装、建模、求解和收敛检查步骤见中文说明。

```powershell
cd hfss
python -m pip install -r requirements.txt
python build_hfss.py --dry-run --output preview
python build_hfss.py --aedt-version 2025.1 --output model_01
python build_hfss.py --aedt-version 2025.1 --solve --cores 4 --output run_01
python plot_results.py run_01
```

请将 AEDT 版本替换为本机版本。首次先只建模，检查端口与几何后再求解。
